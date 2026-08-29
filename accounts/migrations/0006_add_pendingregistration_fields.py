from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_add_public_id"),
    ]

    operations = [
        migrations.AddField(
            model_name='pendingregistration',
            name='session_key',
            field=models.CharField(max_length=40, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='pendingregistration',
            name='status',
            field=models.CharField(default='pending', max_length=32),
        ),
        migrations.AddField(
            model_name='pendingregistration',
            name='verification_token',
            field=models.CharField(max_length=128, null=True, blank=True, unique=True),
        ),
        migrations.AddField(
            model_name='pendingregistration',
            name='verification_token_hash',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='pendingregistration',
            name='verified_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='pendingregistration',
            name='used_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='pendingregistration',
            name='expires_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
