import json
import os
import requests
import sqlite3
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import time
import multiprocessing
import re
import glob
from constants import (
    HEADERS_REQUEST,
    PATH_DATA,
    DB_NAME_NEWS, 
    DB_TIMEOUT, 
    PATH_STATS,
    DIGITAL_MEDIAS_URL,
    DIGITAL_MEDIAS_MAIN_ROOT,
    SYMBOLS,
    DEFAULT_HEADERS_CSV_STATS
)
from typing import List, Union

# Local constants
TODAY_LOCAL_DATETIME = datetime.now().replace(tzinfo=timezone.utc)

def direct_recursive_destructure(data: dict, 
                                 n_nestings: int=0,
                                 on_key_trail: bool=True,
                                 sep: str="-"
                                 ):
    """
    Recursively de-structure a JSON object and collect key-related information.

    Args:
        data (dict): The input JSON object to be de-structured.
        n_nestings (int): The number of nestings in the JSON structure.
        on_key_trail (bool): Whether to include key trails.
        sep (str): The separator used in key trails.

    Returns:
        tuple: A tuple containing the de-structured information, including keys, values, key trails, and nesting level.
    """
    if on_key_trail:
        trailed_keys = []
    keys_with_their_values = []
    only_keys = []
    nesting_found = False
    for key, value in data.items():
        # Only for nested dict-objects
        if isinstance(value, dict):
            if not nesting_found:
                n_nestings += 1
                nesting_found = True
            returned_only_keys, returned_keys_with_their_values, returned_trailed_keys, returned_n_nestings = direct_recursive_destructure(value,
                                                                                                                                         n_nestings)
            only_keys.append(key)
            keys_with_their_values.extend(returned_keys_with_their_values)
            if on_key_trail:
                temp = []
                for subkey in returned_trailed_keys:
                    if not isinstance(subkey, tuple):
                        temp.append(f"{key}{sep}{subkey}")
                    else:
                        sub1, sub2 = subkey
                        temp.append(f"{key}{sep}{sub1}{sep}{sub2}")
                trailed_keys.extend(tuple(temp))
            keys_with_their_values.append((key, tuple(returned_only_keys)))
        # Only for last dict-objects
        else:
            only_keys.append(key)
            keys_with_their_values.append((key, str(value)))
    if on_key_trail:
        return only_keys, keys_with_their_values, trailed_keys, n_nestings
    else:
        return only_keys, keys_with_their_values, returned_n_nestings

def find_invalid_files(url: str) -> bool:
    if url.endswith(".xml") \
    or url.endswith(".pdf") \
    or url.endswith(".lxml") \
    or url.endswith(".jpg") \
    or url.endswith(".png") \
    or url.endswith(".gif"):
        return True
    return False

def find_invalid_sections(url: str) -> bool:
    if "pagina-1.html" in url \
    or "/firmas" in url \
    or "/humor/" in url \
    or "/autor" in url \
    or "/autores/" in url \
    or "/foto/" in url \
    or "/fotos/" in url \
    or "/video/" in url \
    or "/videos/" in url \
    or "/opinión/" in url \
    or "/opinion/" in url:
        return True
    return False

def clean_topics(raw_topics):
    if isinstance(raw_topics, (tuple, list)):
        topics = ",".join(raw_topics).replace(" ", "-").lower()
    elif isinstance(raw_topics, str):
        if ", " in raw_topics:
            topics = raw_topics.replace(", ", ",").replace(" ", "-").lower()
        else:
           topics = raw_topics.lower()

    for s in SYMBOLS:
        if s in topics:
            topics = topics.replace(s, "")

    return topics

def update_date(current_date, current_time):
    new_date, new_time = str(datetime.today()).split(" ")
    if new_date != current_date:
        return new_date, new_time
    return current_date, current_time

def get_region_to_url(ignores, file_path=None, on_save=False, on_override=False):
    response = requests.get(DIGITAL_MEDIAS_URL, headers=HEADERS_REQUEST)
    parsed_hmtl = BeautifulSoup(response.content, "html.parser")

    tags = parsed_hmtl.find_all(lambda tag: tag.name == "a" and tag.attrs["href"] is not None)
    region_urls = [x.attrs["href"] for x in tags]
    region_urls = [x for x in region_urls if x.endswith(".php") and x.startswith("/") and not any(1 if node in x else 0 for node in ignores)]
    region_names = [x[1:-4] for x in region_urls]
    region_urls = [DIGITAL_MEDIAS_MAIN_ROOT + url for url in region_urls]
    region_to_url = {name: url for url, name in zip(region_urls, region_names)}

    region_to_media_urls = {}
    for region, media_url in region_to_url.items():
        print(media_url)
        region_to_media_urls[region] = _get_url_medias_from_region(media_url)

    print(f"Number of regions: {len(region_to_media_urls)};\nNumber of total digital media available: {sum(len(region_to_media_urls[k]) for k in region_to_media_urls)}")
    if on_save:
        saving_status = _save_media_urls(file_path, region_to_media_urls, on_override)
        if saving_status:
            print(f"Media urls have been saved successfully. Override: {on_override}")
        else:
            print("The file already exists")
    return region_to_media_urls

def _get_url_medias_from_region(url):
    response = requests.get(url, headers=HEADERS_REQUEST)
    parsed_hmtl = BeautifulSoup(response.content, "html.parser")
    links = parsed_hmtl.find_all("a", string=lambda text: text and "www." in text)
    return [l["href"] for l in links]

def _save_media_urls(file_path, data, on_override=False):
    if not os.path.exists(file_path) or on_override:
        with open(file_path, "w") as file:
            json.dump(data, file)

def read_json_file(path, f_name):
    with open(os.path.join(path, f_name), "r") as file:
        c = 0
        while c < 100:
            try:
                return json.load(file)
            except:
                c += 1
    print("read not done")
    return {}

def read_garbage(where_params):
    with sqlite3.connect(DB_NAME_NEWS, 
                         timeout=DB_TIMEOUT) as conn:
        cursor = conn.cursor()
        is_params_container = isinstance(where_params, (tuple, list))

        if not is_params_container:
            where_params = (where_params, )
        query_str = """
            SELECT 
                url,
                mediaUrl
            FROM 
                garbage
            WHERE
                mediaUrl = ?
                """
    return cursor.execute(query_str, 
                          where_params) \
                 .fetchall()

def save_checkpoint(pid, last_value):
    with open(os.path.join(PATH_DATA, f"checkpoint_{pid}.json"), "w") as file:
        json.dump({"last_value": last_value}, file)

def read_news_checkpoint(pid: str, 
                         mod: str="r"):
    with open(os.path.join(PATH_DATA, f"checkpoint_{pid}.json"), mod) as file:
        try:
            return json.load(file)["last_value"]
        except:
            return ""

def read_media_sections(pid: str):
    with open(os.path.join(PATH_DATA, f"media_sections_{pid}.txt"), "r") as file:
        sections = file.readline()
        return sections

def has_http_attribute_value(tag):
    for attr in tag.attrs:
        attr_value = tag.attrs[attr]
        if isinstance(attr_value, str) and ('http://' in attr_value or 'https://' in attr_value):
            return True
    return False

def store_failed_urls(wrapped_func):
    failed_urls = []
    def wrapper(*args, **kwargs):
        try:
            result = wrapped_func(*args, **kwargs)
            return result
        except Exception as e:
            if 'url' in kwargs:
                failed_urls.append((wrapped_func, kwargs['url']))
            print(f"Error processing URL: {kwargs.get('media_url')}")
            print(f"Error message: {str(e)}")

    wrapper.failed_urls = failed_urls
    return wrapper

class StatisticsManager():
    def __init__(self, start_time=False, log_dir="", sub_dir="") -> None:
        #self.start_datetime = datetime.now().replace(tzinfo=timezone.utc)
        self.start_datetime = TODAY_LOCAL_DATETIME
        self.datetime_fmt, self.date, self.time, self.hour_min = self._iso_datetime_to_str(self.start_datetime)
        
        # Start the timer
        self.start_time = start_time
        self.last_duration = 0.0
        if start_time:
            self.time_start = time.time()
        else:
            self.time_start = 0.0
        
        # Setup main folder
        if log_dir == "":
            self.log_dir = os.path.join(PATH_STATS)
        else:
            self.log_dir = log_dir
        
        # Setup sub_dir
        if sub_dir == "":
            self.sub_dir = os.path.join(f"scraping_date_{self.date}_time_{self.hour_min}")
        else:
            self.sub_dir = sub_dir
        
        self.log_path = os.path.join(self.log_dir, self.sub_dir)
        
        # Make sure the sub_dir exists
        os.makedirs(self.log_path, exist_ok=True)
    
    def restart_time(self):
        self.time_start = time.time()
        return self

    def set_duration(self, round_digits: int=1):
        self.last_duration = round(time.time() - self.time_start, round_digits)
        self.restart_time()
        
        return self.last_duration

    def _iso_datetime_to_str(self, iso_datetime, s=" "):
        """
        Format ISO datetime dtype into str
        Input: 
            · 'iso_datetime'. Iso Datetime dtype
            · 's'. Separator between years, months, etc; hours, minutes, etc.
        Output: 
            str datetime (y{sep}m{sep}d_H{sep}M{sep}S).
            str date (y{sep}m{sep}d).
        """
        complete_datetime = iso_datetime.strftime(f"%Y{s}%m{s}%d_%H{s}%M{s}%S")
        date = iso_datetime.strftime(f"%Y{s}%m{s}%d")
        time = iso_datetime.strftime(f"%H{s}%M{s}%S")
        hour_min = iso_datetime.strftime(f"%H{s}%M{s}%S")

        return complete_datetime, date, time, hour_min
    
    def write_stats(
            self, 
            data, 
            header:str=DEFAULT_HEADERS_CSV_STATS, 
            writer_id: str=0, 
            ):
        """
        Writes statistical data to a CSV file.
        
        Args:
            data: The data to write.
            header (str): The default header for the CSV. 
                          Defaults to the constant DEFAULT_HEADERS_CSV_STATS.
            writer_id (str): An identifier for the writer instance.
                             Defaults to 0.
        """
        
        # Set the end time of the process for duration
        duration = str(self.set_duration())
        
        # Wrap the data into list
        if isinstance(data, tuple):
            data = list(data)
        
        #stats_file_name = f"process_{self.datetime_fmt}_pid_{writer_id}.csv"
        stats_file_name = f"stats_time_{self.hour_min}_writer_{writer_id}.csv"
        stats_file_path = os.path.join(self.log_path, stats_file_name)
        
        # Check first time writing on path
        if not os.path.exists(stats_file_path):
            write_header = True
        else:
            write_header = False
        
        # Set header if first time writting and if header is None
        if write_header and header == "":
            header = DEFAULT_HEADERS_CSV_STATS
        
        # Add skipline to header
        if write_header and not header.endswith("\n"):
            header += "\n"
        
        # Catch lock
        lock = multiprocessing.Lock()
        with lock:
            # Write statistics 
            with open(stats_file_path, "a") as stats_file:
                if write_header:
                    stats_file.write(header)
                stats_file.write(";".join([str(x) for x in data] + [duration + "\n"]))

class FileManager():
    def __init__(self) -> None:
        self.files_map = {}
    def add_files(self, path: str, files: list, **kwargs):
        for file_name in files:
            self._add_file(path,file_name, **kwargs)
    def _add_file(self, path: str, file_name: str, **kwargs):
        open_mode = kwargs.get("open_mode", "a")
        
        if not os.path.exists(path):
            os.makedirs(path)
        
        full_path = os.path.join(path, file_name)
        self.files_map[file_name] = open(full_path, open_mode)

def write_on_file(path: str, file_name: str, msg: str, mode: str="a"):
    lock = multiprocessing.Lock()
    with lock:
        with open(os.path.join(path, file_name), mode) as f:
            _write_on_file(f, msg)

def write_batch_on_file(
        path: str,
        file_name: str,
        msgs: Union[List[str], tuple[str]],
        mode: str="a"
        ):
    lock = multiprocessing.Lock()
    with lock:
        with open(os.path.join(path, file_name), mode) as file_handler:
            for msg in msgs:
                _write_on_file(file_handler, msg)

def _write_on_file(file_handler, msg: str,):
    file_handler.write(msg)

def remove_body_tags(text: str) -> str:
    return re.sub("<.*?>", "", text)

def get_last_sections_file_num(full_path: str):
    return max(int(x.split("_")[-1][1:-5]) for x in glob.glob(full_path))