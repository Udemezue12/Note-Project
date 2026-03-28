
from datetime import datetime, timedelta, timezone

import httpx
from celery import shared_task
from ..auth_utils import delete_expired_blacklisted_tokens


@shared_task(
    name="delete_blackisted_tokens",
    autoretry_for=(httpx.HTTPError, ConnectionError, RuntimeError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def delete_blaclisted_tokens_tasks():

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    return delete_expired_blacklisted_tokens(cutoff)
