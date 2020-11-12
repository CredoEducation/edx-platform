# Generated by Django 2.2.13 on 2020-10-21 09:38

from django.db import migrations, models


data = {
    'Rutgers-New Brunswick': [
        ['01', 'School of Arts and Sciences'],
        ['07', 'Mason Gross School of the Arts'],
        ['08', 'Graduate School Creative & Performing Arts'],
        ['10', 'Edward J. Bloustein School of Planning and Public Policy: Undergraduate'],
        ['11', 'School of Environmental and Biological Sciences'],
        ['14', 'School of Engineering'],
        ['15', 'Graduate School of Education'],
        ['16', 'Graduate School–New Brunswick'],
        ['17', 'School of Communication and Information'],
        ['18', 'Graduate School of Applied and Professional Psychology'],
        ['19', 'School of Social Work'],
        ['30', 'Ernest Mario School of Pharmacy'],
        ['31', 'Graduate School of Pharmacy'],
        ['33', 'School of Business'],
        ['34', 'Edward J. Bloustein School of Planning and Public Policy: Graduate'],
        ['37', 'School of Management and Labor Relations: Undergraduate'],
        ['38', 'School of Management and Labor Relations: Graduate'],
        ['77', 'School of Nursing'],
        ['80', 'Continuous Education'],
        ['81', 'Graduate Continuous Education']
    ],
    'Rutgers-Newark': [
        ['20', 'School of Public Affairs and Administration'],
        ['21', 'Newark College of Arts and Sciences'],
        ['22', 'Rutgers Business School–Newark'],
        ['23', 'Rutgers School of Law–Newark'],
        ['25', 'School of Nursing'],
        ['26', 'Graduate School–Newark'],
        ['27', 'School of Criminal Justice: Graduate'],
        ['29', 'School of Business'],
        ['40', 'Public Affairs'],
        ['45', 'College of Nursing: Graduate'],
        ['47', 'School of Criminal Justice'],
        ['62', 'University College–Newark']
    ],
    'Rutgers-Camden': [
        ['24', 'Rutgers School of Law–Camden'],
        ['50', 'Camden College of Arts and Sciences'],
        ['52', 'School of Business–Camden'],
        ['53', 'Graduate School of Business'],
        ['56', 'Graduate School–Camden'],
        ['57', 'School of Nursing–Camden'],
        ['58', 'Graduate School of Nursing'],
        ['64', 'University College–Camden']
    ],
    'RBHS': [
        ['rbhs', 'Other']
    ]
}


def add_rutgers_campus_values(apps, schema_editor):
    RutgersCampusMapping = apps.get_model("credo_modules", "RutgersCampusMapping")
    for campus, items in data.items():
        for item in items:
            obj = RutgersCampusMapping(
                num=item[0],
                school=item[1],
                campus=campus
            )
            obj.save()


class Migration(migrations.Migration):

    dependencies = [
        ('credo_modules', '0055_edx_api_token_255_symbols'),
    ]

    operations = [
        migrations.CreateModel(
            name='RutgersCampusMapping',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('num', models.CharField(db_index=True, max_length=255)),
                ('school', models.CharField(max_length=255)),
                ('campus', models.CharField(max_length=255)),
            ],
        ),
        migrations.RunPython(
            add_rutgers_campus_values,
        ),
    ]
