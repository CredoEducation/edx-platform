# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2020-07-10 11:59
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('block_structure', '0009_apicoursestructuretags_is_parent'),
    ]

    operations = [
        migrations.AddField(
            model_name='apicoursestructuretags',
            name='ts',
            field=models.IntegerField(null=True),
        ),
    ]
