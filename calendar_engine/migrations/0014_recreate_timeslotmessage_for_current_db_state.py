import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("calendar_engine", "0013_remove_timeslot_comment_timeslotcomment"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # Что реально делаем в БД:
            # старой таблицы calendar_engine_timeslotcomment уже нет,
            # поэтому просто создаем новую таблицу timeslotmessage с нуля.
            database_operations=[
                migrations.CreateModel(
                    name="TimeSlotMessage",
                    fields=[
                        ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
                        ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Дата обновления")),
                        ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ("message", models.TextField(help_text="Укажите текст сообщения участника встречи", verbose_name="Текст сообщения")),
                        ("is_rewrited", models.BooleanField(default=False, help_text="Флаг нужен, чтобы на UI показывать, что автор уже менял текст сообщения", verbose_name="Сообщение отредактировано")),
                        (
                            "creator",
                            models.ForeignKey(
                                help_text="Укажите пользователя, который оставил сообщение внутри встречи",
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="authored_slot_messages",
                                to=settings.AUTH_USER_MODEL,
                                verbose_name="Автор сообщения",
                            ),
                        ),
                        (
                            "slot",
                            models.ForeignKey(
                                help_text="Укажите встречу, к которой относится сообщение",
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="messages",
                                to="calendar_engine.timeslot",
                                verbose_name="Слот встречи",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "Сообщение встречи",
                        "verbose_name_plural": "Сообщения встреч",
                        "ordering": ["-created_at"],
                    },
                ),
            ],

            # Как меняем migration state Django:
            # в истории была TimeSlotComment, а в коде уже TimeSlotMessage.
            state_operations=[
                migrations.DeleteModel(
                    name="TimeSlotComment",
                ),
                migrations.CreateModel(
                    name="TimeSlotMessage",
                    fields=[
                        ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
                        ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Дата обновления")),
                        ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ("message", models.TextField(help_text="Укажите текст сообщения участника встречи", verbose_name="Текст сообщения")),
                        ("is_rewrited", models.BooleanField(default=False, help_text="Флаг нужен, чтобы на UI показывать, что автор уже менял текст сообщения", verbose_name="Сообщение отредактировано")),
                        (
                            "creator",
                            models.ForeignKey(
                                help_text="Укажите пользователя, который оставил сообщение внутри встречи",
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="authored_slot_messages",
                                to=settings.AUTH_USER_MODEL,
                                verbose_name="Автор сообщения",
                            ),
                        ),
                        (
                            "slot",
                            models.ForeignKey(
                                help_text="Укажите встречу, к которой относится сообщение",
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="messages",
                                to="calendar_engine.timeslot",
                                verbose_name="Слот встречи",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "Сообщение встречи",
                        "verbose_name_plural": "Сообщения встреч",
                        "ordering": ["-created_at"],
                    },
                ),
            ],
        ),
    ]
