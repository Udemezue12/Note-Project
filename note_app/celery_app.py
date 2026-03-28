from __future__ import absolute_import, unicode_literals

import os
import sys
from celery import Celery
from dotenv import load_dotenv
from celery.schedules import crontab
import django

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "note_app.settings")


django.setup()

app = Celery("note_app")

app.config_from_object("django.conf:settings", namespace="CELERY")


app.autodiscover_tasks()

app.conf.update(
    task_always_eager=False,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    worker_prefetch_multiplier=1,
    worker_concurrency=1,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "delete_blacklisted_tokens": {
            "task": "delete_blackisted_tokens",
            "schedule": crontab(hour=1, minute=0)
        }
    },
)



import notes.tasks.verify_email_tasks
import notes.tasks.sync_notes_tasks
import notes.tasks.sync_all_notes_tasks
import  notes.tasks.delete_blackisted_tokens_tasks
