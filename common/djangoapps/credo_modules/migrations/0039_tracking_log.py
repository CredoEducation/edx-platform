# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2020-05-30 23:04
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('credo_modules', '0038_attemptcoursemigration_attemptusermigration'),
    ]

    operations = [
        migrations.CreateModel(
            name='TrackingLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('course_id', models.CharField(db_index=True, max_length=255)),
                ('org_id', models.CharField(db_index=True, max_length=80)),
                ('course', models.CharField(max_length=255)),
                ('run', models.CharField(max_length=80)),
                ('term', models.CharField(blank=True, max_length=20, null=True)),
                ('block_id', models.CharField(db_index=True, max_length=255)),
                ('user_id', models.IntegerField(db_index=True)),
                ('is_view', models.BooleanField(default=True)),
                ('answer_id', models.CharField(max_length=255, unique=True)),
                ('ts', models.IntegerField()),
                ('display_name', models.CharField(blank=True, max_length=2048, null=True)),
                ('question_name', models.CharField(blank=True, max_length=2048, null=True)),
                ('question_hash', models.CharField(max_length=80, null=True)),
                ('is_ora_block', models.BooleanField(default=False)),
                ('is_ora_empty_rubrics', models.BooleanField(default=False)),
                ('ora_criterion_name', models.CharField(blank=True, max_length=255, null=True)),
                ('grade', models.FloatField(null=True)),
                ('max_grade', models.FloatField(null=True)),
                ('is_correct', models.SmallIntegerField(default=0)),
                ('is_incorrect', models.SmallIntegerField(default=0)),
                ('answer', models.TextField(blank=True, null=True)),
                ('answer_hash', models.CharField(max_length=80, null=True)),
                ('correctness', models.CharField(blank=True, max_length=20, null=True)),
                ('sequential_name', models.CharField(max_length=255, null=True)),
                ('sequential_id', models.CharField(db_index=True, max_length=255, null=True)),
                ('sequential_graded', models.SmallIntegerField(default=0)),
                ('is_staff', models.SmallIntegerField(default=0)),
                ('attempt_ts', models.IntegerField()),
                ('is_last_attempt', models.SmallIntegerField(default=1)),
                ('properties_data', models.CharField(blank=True, max_length=4096, null=True)),
                ('course_user_id', models.CharField(max_length=255, null=True)),
                ('update_ts', models.IntegerField(db_index=True)),
            ],
        ),
        migrations.CreateModel(
            name='TrackingLogFile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('log_filename', models.CharField(db_index=True, max_length=255)),
                ('status', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='TrackingLogProp',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('course_user_id', models.CharField(db_index=True, max_length=255)),
                ('prop_name', models.CharField(max_length=255)),
                ('prop_value', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='TrackingLogUserInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('org_id', models.CharField(db_index=True, max_length=255)),
                ('user_id', models.IntegerField(db_index=True)),
                ('email', models.CharField(max_length=255, null=True)),
                ('full_name', models.CharField(max_length=255, null=True)),
                ('search_token', models.CharField(db_index=True, max_length=255, null=True)),
            ],
        ),
        migrations.AlterIndexTogether(
            name='trackinglog',
            index_together=set([('org_id', 'ts')]),
        ),
    ]
