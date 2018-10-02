# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import openedx.core.djangoapps.xmodule_django.models
import credo_modules.models


class Migration(migrations.Migration):

    dependencies = [
        ('credo_modules', '0003_registrationpropertiespermicrosite'),
    ]

    operations = [
        migrations.CreateModel(
            name='EnrollmentPropertiesPerCourse',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('course_id', openedx.core.djangoapps.xmodule_django.models.CourseKeyField(max_length=255, db_index=True)),
                ('data', models.TextField(help_text=b'Config in JSON format', verbose_name=b'Enrollment Properties', validators=[credo_modules.models.validate_json_props])),
            ],
            options={
                'db_table': 'credo_enrollment_properties',
                'verbose_name': 'enrollment properties item',
                'verbose_name_plural': 'enrollment properties per course',
            },
        ),
        migrations.AlterField(
            model_name='registrationpropertiespermicrosite',
            name='data',
            field=models.TextField(help_text=b'Config in JSON format', verbose_name=b'Registration Properties', validators=[credo_modules.models.validate_json_props]),
        ),
    ]

