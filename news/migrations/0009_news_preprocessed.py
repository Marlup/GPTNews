# Generated by Django 4.2.5 on 2023-09-08 20:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0008_alter_news_creationdate_alter_news_insertdate_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='news',
            name='preprocessed',
            field=models.BooleanField(default=False),
        ),
    ]
