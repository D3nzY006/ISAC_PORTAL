from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0002_attendancerecord_absent_excused"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="requested_role",
            field=models.CharField(blank=True, choices=[("student", "Student"), ("officer", "CSBO Officer"), ("admin", "Administrator")], default="", max_length=20),
        ),
    ]
