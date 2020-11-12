# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-10-14 10:00
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('credo_modules', '0025_customuserrole_edit_library_content'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuserrole',
            name='update_library_content',
            field=models.BooleanField(default=False,
                                      verbose_name='Unit: Access to "Update Now" button for Library Content'),
        ),
    ]
