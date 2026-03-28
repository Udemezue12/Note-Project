import uuid

import httpx
from celery import shared_task
from django.db import transaction
from django.utils.timezone import now

from ..cache_deps import cache_deps
from ..crud_deps import crud_actions
from ..models import Note, SyncQueue


@shared_task(
    name="sync_all_notes",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def sync_all_notes_tasks(user_id: str):
    user_uuid = uuid.UUID(user_id)
    user_lock_key = f"sync_running_user_{user_uuid}"

    if cache_deps.get_from_cache(user_lock_key):
        return {"message": "Sync already running"}

    cache_deps.set_from_cache(user_lock_key, True, timeout=60 * 5)

    try:
        unsynced_qs = crud_actions.filter_by_select_related(
            model=SyncQueue,
            fields=["note"],
            synced=False,
            note__user_id=user_uuid,
        )

        unsynced_items = list(unsynced_qs)

        if not unsynced_items:
            return {"message": "No notes to sync"}

        current_time = now()

        notes_to_update = []
        notes_to_create = []
        queue_items_to_update = []

        for item in unsynced_items:
            note = item.note

            existing = crud_actions.first(model=Note, id=note.id)
            # existing = {
            #     note.id: note
            #     for note in Note.objects.filter(id__in=[i.note.id for i in unsynced_items])
            # }

            if item.action == "delete":
                if existing:
                    existing.is_deleted = True
                    existing.last_synced = current_time
                    notes_to_update.append(existing)

            elif existing:
                if note.version > existing.version:
                    existing.title = note.title
                    existing.content = note.content
                    existing.version = note.version
                    existing.is_deleted = note.is_deleted
                    existing.last_synced = current_time
                    notes_to_update.append(existing)

            else:
                notes_to_create.append(
                    Note(
                        id=note.id,
                        user=note.user,
                        title=note.title,
                        content=note.content,
                        version=note.version,
                        is_deleted=note.is_deleted,
                        last_synced=current_time,
                    )
                )

            if not note.last_synced or note.last_synced < current_time:
                note.last_synced = current_time
                notes_to_update.append(note)

            item.synced = True
            queue_items_to_update.append(item)

        with transaction.atomic():

            if notes_to_create:
                Note.objects.bulk_create(
                    notes_to_create, ignore_conflicts=True)

            if notes_to_update:

                unique_notes = {
                    note.id: note for note in notes_to_update}.values()

                Note.objects.bulk_update(
                    unique_notes,
                    ["title", "content", "version", "is_deleted", "last_synced"],
                )

            if queue_items_to_update:
                SyncQueue.objects.bulk_update(
                    queue_items_to_update, ["synced"])

        return {
            "synced_notes": len(queue_items_to_update),
            "synced_at": str(current_time),
        }

    finally:

        cache_deps.delete_from_cache(user_lock_key)
