from django.db import migrations, models


def clear_placeholder_telegram_ids(apps, schema_editor):
    TelegramUser = apps.get_model("telegram_bot", "TelegramUser")
    TelegramUser.objects.filter(telegram_id=0).update(telegram_id=None)


def restore_placeholder_telegram_ids(apps, schema_editor):
    TelegramUser = apps.get_model("telegram_bot", "TelegramUser")
    TelegramUser.objects.filter(telegram_id__isnull=True).update(telegram_id=0)


class Migration(migrations.Migration):

    dependencies = [
        ("telegram_bot", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="telegramuser",
            name="telegram_id",
            field=models.BigIntegerField(
                blank=True,
                db_index=True,
                help_text="Null until the user completes /start linking in Telegram.",
                null=True,
                unique=True,
            ),
        ),
        migrations.RunPython(
            clear_placeholder_telegram_ids,
            restore_placeholder_telegram_ids,
        ),
    ]
