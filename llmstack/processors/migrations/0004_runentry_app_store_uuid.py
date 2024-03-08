# Generated by Django 4.2.10 on 2024-03-08 00:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apiabstractor', '0003_rename_processor_slugs'),
    ]

    operations = [
        migrations.AddField(
            model_name='runentry',
            name='app_store_uuid',
            field=models.CharField(default=None, help_text='UUID of the app store', max_length=40, null=True),
        ),
    ]
