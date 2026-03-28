from .cache_deps import cache_deps

from .crud_deps import crud_actions
from .models import SyncQueue
from .tasks.sync_notes_tasks import sync_notes_tasks


def add_to_sync_queue(note, action):
    obj, created = crud_actions.get_or_create(SyncQueue, note=note)

    obj.action = action
    obj.synced = False
    obj.retry_count = 0
    obj.save()
    user_id = str(note.user.id)
    cache_key = f"sync_running_user_{user_id}"
    if not cache_deps.get_from_cache(cache_key):
        cache_deps.set_from_cache(cache_key, True, timeout=10)
        sync_notes_tasks.delay(user_id)
