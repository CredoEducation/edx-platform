# Generated by Django 2.2.13 on 2020-12-30 12:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('credo_modules', '0061_usersettings'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usersettings',
            name='my_skills_access',
            field=models.BooleanField(default=None, null=True),
        ),
    ]
