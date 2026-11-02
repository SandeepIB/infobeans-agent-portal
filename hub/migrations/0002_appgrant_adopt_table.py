import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # No SQL needed: the table and its rows already exist.
            database_operations=[],
            # Informing Django's model state that AppGrant owns that table.
            state_operations=[
                migrations.CreateModel(
                    name="AppGrant",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("app", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                  related_name="grants", to="hub.app")),
                        ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                   related_name="app_grants", to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        "db_table": "hub_app_allowed_users",
                        "unique_together": {("app", "user")},
                    },
                ),
                migrations.AlterField(
                    model_name="app",
                    name="allowed_users",
                    field=models.ManyToManyField(blank=True, related_name="granted_apps",
                                                 through="hub.AppGrant", through_fields=("app", "user"), to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
    ]