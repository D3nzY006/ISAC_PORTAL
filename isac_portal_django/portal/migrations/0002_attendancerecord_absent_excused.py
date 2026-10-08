from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portal", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="attendancerecord",
            name="status",
            field=models.CharField(
                choices=[
                    ("present", "Present"),
                    ("absent", "Absent"),
                    ("excused", "Excused"),
                    ("corrected", "Corrected"),
                ],
                default="present",
                max_length=20,
            ),
        ),
    ]
