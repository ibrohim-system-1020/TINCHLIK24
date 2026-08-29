"""Add STATUS_SOLD choice to Listing.status choices."""
from django.db import migrations, models


def add_status_choices(apps, schema_editor):
    Listing = apps.get_model('market', 'Listing')
    # No data migration required; choices change will be reflected in model. Leave as noop.
    return


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='listing',
            name='status',
            field=models.CharField(choices=[('pending', 'Tekshirilmoqda'), ('approved', 'Tasdiqlandi'), ('sold', 'Sotilgan'), ('rejected', 'Rad etildi')], default='pending', max_length=20),
        ),
    ]
