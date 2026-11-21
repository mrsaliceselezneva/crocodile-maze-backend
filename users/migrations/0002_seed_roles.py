from django.db import migrations


def create_roles(apps, schema_editor):
    Role = apps.get_model("users", "Role")
    roles = Role.objects.using(schema_editor.connection.alias)

    for code in ("ADMIN", "STUDENT"):
        roles.get_or_create(code=code)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_roles, reverse_code=migrations.RunPython.noop),
    ]
