# Generated by Django 4.2.15 on 2024-09-03 05:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apiabstractor', '0011_remove_feedback_expected_response_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='runentry',
            name='usage_metrics',
            field=models.JSONField(blank=True, default=dict, help_text='Usage metrics for the run'),
        ),
    ]