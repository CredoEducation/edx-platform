# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2020-06-25 17:11
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('credo_modules', '0044_auto_20200625_0515'),
    ]

    operations = [
        migrations.CreateModel(
            name='TrackingLogConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=255)),
                ('value', models.CharField(max_length=255)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.RemoveField(
            model_name='trackinglog',
            name='properties_data',
        ),
    ]
