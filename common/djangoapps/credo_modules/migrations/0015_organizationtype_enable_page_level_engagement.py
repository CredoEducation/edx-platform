# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2018-11-08 10:04
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('credo_modules', '0014_auto_20181004_0618'),
    ]

    operations = [
        migrations.AddField(
            model_name='organizationtype',
            name='enable_page_level_engagement',
            field=models.BooleanField(default=False,
                                      verbose_name='Enable Page Level for Engagement Statistic in Insights'),
        ),
    ]
