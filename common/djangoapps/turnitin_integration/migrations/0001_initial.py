# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-12-19 13:11
from __future__ import unicode_literals

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('credo_modules', '0033_org_default_order'),
    ]

    operations = [
        migrations.CreateModel(
            name='TurnitinApiKey',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_active', models.BooleanField(default=False)),
                ('key', models.CharField(max_length=255, verbose_name=b'Authorization token')),
                ('url_part', models.CharField(max_length=30, validators=[django.core.validators.RegexValidator(b'^[a-z]+$', b'Only a-z characters are allowed')], verbose_name=b'XXX url part in the "xxx.turnitin.com" hostname')),
                ('use_sandbox', models.BooleanField(default=False, verbose_name=b'Use xxx.tii-sandbox.com instead of xxx.turnitin.com')),
                ('webhook_id', models.CharField(blank=True, max_length=255, null=True, verbose_name=b'Webhook ID')),
                ('org', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='credo_modules.Organization')),
            ],
            options={
                'db_table': 'turnitin_api_key',
            },
        ),
        migrations.CreateModel(
            name='TurnitinSubmission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('block_id', models.CharField(db_index=True, max_length=255)),
                ('file_name', models.CharField(blank=True, max_length=255, null=True)),
                ('ora_submission_id', models.CharField(db_index=True, max_length=255)),
                ('turnitin_submission_id', models.CharField(blank=True, db_index=True, max_length=255, null=True)),
                ('status', models.CharField(max_length=30)),
                ('data', models.TextField(blank=True, null=True)),
                ('report_status', models.CharField(default=b'-', max_length=30)),
                ('creation_time', models.DateTimeField(auto_now_add=True, null=True)),
                ('update_time', models.DateTimeField(auto_now=True, null=True)),
                ('api_key', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='turnitin_integration.TurnitinApiKey')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'turnitin_submission',
            },
        ),
        migrations.CreateModel(
            name='TurnitinUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id_hash', models.CharField(db_index=True, max_length=255)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'turnitin_user',
            },
        ),
    ]
