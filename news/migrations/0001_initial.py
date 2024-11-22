# Generated by Django 4.2.5 on 2023-09-07 12:12

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='News',
            fields=[
                ('url', models.CharField(default='', max_length=255, primary_key=True, serialize=False)),
                ('mediaUrl', models.CharField(default='', max_length=255)),
                ('creationDate', models.DateField(default='NULL', max_length=32)),
                ('insertDate', models.DateField(default='NULL', max_length=32)),
                ('updateDate', models.DateField(default='NULL', max_length=32)),
                ('title', models.CharField(default='', max_length=255)),
                ('description', models.CharField(default='', max_length=512)),
                ('articleBody', models.TextField(default='noArticleBody')),
                ('tags', models.TextField(default='')),
                ('imageUrl', models.CharField(default='', max_length=255)),
                ('country', models.CharField(default='', max_length=32)),
                ('nTokens', models.SmallIntegerField(default=-1)),
            ],
        ),
    ]
