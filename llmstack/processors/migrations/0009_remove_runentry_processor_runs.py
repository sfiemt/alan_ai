# Generated by Django 4.2.14 on 2024-08-08 22:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('apiabstractor', '0008_runentry_processor_runs_objref_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='runentry',
            name='processor_runs',
        ),
    ]
