# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-10-21 15:06
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tagging', '0004_auto_20191021_0859'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tagorgtypes',
            name='org',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='org_types', to='tagging.TagCategories'),
        ),
        migrations.AlterField(
            model_name='tagorgtypes',
            name='org_type',
            field=models.IntegerField(verbose_name='Organization type ID'),
        ),
    ]
