import uuid

import httpx
from celery import shared_task
from django.utils.timezone import now

from ..cache_deps import cache_deps
from ..crud_deps import crud_actions
from ..models import Note, SyncQueue


@shared_task(
    name="sync_notes",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def sync_notes_tasks(user_id: str):
    user_uuid = uuid.UUID(user_id)
    user_lock_key = f"sync_running_user_{user_uuid}"

    try:
        unsynced = crud_actions.filter_by_select_related(
            model=SyncQueue,
            fields=["note"],
            synced=False,
            note__user_id=user_uuid
        )

        results = []
        current_time = now()  

        for item in unsynced:
            queue_key = f"sync_queue_{item.id}"

            if cache_deps.get_from_cache(queue_key):
                continue

            cache_deps.set_from_cache(queue_key, True, timeout=60)

            try:
                note = item.note
                existing = crud_actions.first(model=Note, id=note.id)

                if item.action == "delete":
                    if existing:
                        existing.is_deleted = True
                        existing.last_synced = current_time  
                        existing.save()

                elif existing:
                    if note.version > existing.version:
                        existing.title = note.title
                        existing.content = note.content
                        existing.version = note.version
                        existing.is_deleted = note.is_deleted
                        existing.last_synced = current_time  
                        existing.save()

                else:
                    crud_actions.create_object(
                        model=Note,
                        id=note.id,
                        user=note.user,
                        title=note.title,
                        content=note.content,
                        version=note.version,
                        last_synced=current_time  
                    )

                
                if not note.last_synced or note.last_synced < current_time:
                    note.last_synced = current_time
                    note.save(update_fields=["last_synced"])

                item.synced = True
                item.save(update_fields=["synced"])

                results.append({
                    "note_id": str(note.id),
                    "status": "synced"
                })

            finally:
                cache_deps.delete_from_cache(queue_key)

        return {
            "results": results,
            "synced_at": str(current_time)
        }

    finally:
        cache_deps.delete_from_cache(user_lock_key)
