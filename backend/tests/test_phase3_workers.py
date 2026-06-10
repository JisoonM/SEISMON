from celery.schedules import crontab

from celery_app import celery_app


def test_celery_beat_schedule_contains_phase3_jobs() -> None:
    schedule = celery_app.conf.beat_schedule

    assert schedule["ingest-all-sources"]["task"] == "app.workers.tasks.ingest_all_sources"
    assert schedule["ingest-all-sources"]["schedule"] == 60.0
    assert schedule["cleanup-old-events"]["task"] == "app.workers.tasks.cleanup_old_events"
    assert isinstance(schedule["cleanup-old-events"]["schedule"], crontab)

