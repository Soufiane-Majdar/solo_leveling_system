# Generated by Django 5.0 on 2024-12-02 17:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_remove_shopitem_core_shopit_product_61b5a6_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='agility',
            field=models.IntegerField(default=10),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='intelligence',
            field=models.IntegerField(default=10),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='sense',
            field=models.IntegerField(default=10),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='strength',
            field=models.IntegerField(default=10),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='vitality',
            field=models.IntegerField(default=10),
        ),
    ]
