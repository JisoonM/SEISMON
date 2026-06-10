from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ph_earthquake_monitor",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {
    "ingest-all-sources": {
        "task": "app.workers.tasks.ingest_all_sources",
        "schedule": 60.0,
    },
    "cleanup-old-events": {
        "task": "app.workers.tasks.cleanup_old_events",
        "schedule": crontab(hour=0, minute=0),
    },
}
