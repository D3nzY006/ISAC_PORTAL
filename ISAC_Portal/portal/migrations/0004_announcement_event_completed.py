from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0003_profile_requested_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="announcement",
            name="event_completed",
            field=models.BooleanField(default=False),
        ),
    ]
