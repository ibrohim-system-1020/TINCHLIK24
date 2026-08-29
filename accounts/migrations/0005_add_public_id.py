from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_telegramoutmessage"),
    ]

    operations = [
        migrations.AddField(
            model_name="pendingregistration",
            name="public_id",
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
    ]
