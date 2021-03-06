# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2020-09-11 09:14
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('credo_modules', '0048_auto_20200717_1015'),
    ]

    operations = [
        migrations.CreateModel(
            name='UsageLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('course_id', models.CharField(max_length=255)),
                ('org_id', models.CharField(max_length=80)),
                ('course', models.CharField(max_length=255)),
                ('run', models.CharField(max_length=80)),
                ('term', models.CharField(blank=True, max_length=20, null=True)),
                ('block_id', models.CharField(db_index=True, max_length=255)),
                ('block_type', models.CharField(max_length=80)),
                ('parent_path', models.CharField(blank=True, max_length=6000, null=True)),
                ('display_name', models.CharField(blank=True, max_length=2048, null=True)),
                ('user_id', models.IntegerField(db_index=True)),
                ('ts', models.IntegerField()),
                ('is_staff', models.SmallIntegerField(default=0)),
                ('course_user_id', models.CharField(max_length=255, null=True)),
                ('update_ts', models.IntegerField()),
                ('update_process_num', models.IntegerField(db_index=True, null=True)),
            ],
        ),
        migrations.AlterIndexTogether(
            name='usagelog',
            index_together=set([('org_id', 'ts')]),
        ),
    ]
