from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0002_userbase_activation_key"),
    ]

    operations = [
        migrations.AddField(
            model_name="userbase",
            name="activation_created_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
