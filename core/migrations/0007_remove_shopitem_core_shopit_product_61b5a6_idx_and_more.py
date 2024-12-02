# Generated by Django 5.0 on 2024-12-02 17:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_fix_quest_difficulty_values'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='shopitem',
            name='core_shopit_product_61b5a6_idx',
        ),
        migrations.RemoveIndex(
            model_name='shopitem',
            name='core_shopit_points__fc3d0c_idx',
        ),
        migrations.RenameField(
            model_name='shopitem',
            old_name='points_required',
            new_name='price',
        ),
        migrations.RemoveField(
            model_name='shopitem',
            name='ad_required',
        ),
        migrations.RemoveField(
            model_name='shopitem',
            name='digital_file',
        ),
        migrations.RemoveField(
            model_name='shopitem',
            name='product_type',
        ),
        migrations.AddField(
            model_name='shopitem',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='shopitem',
            name='effect',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='shopitem',
            name='item_type',
            field=models.CharField(choices=[('CONSUMABLE', 'Consumable'), ('EQUIPMENT', 'Equipment'), ('WEAPON', 'Weapon')], default='CONSUMABLE', max_length=20),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='inventory',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
