import os
from celery import Celery, Task
import asyncio
import traceback
import uuid

broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

class ProspectForgeTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        from app.database import async_session_factory
        from app.models import FailedWorkItem

        async def _record_failure():
            async with async_session_factory() as session:
                failed_item = FailedWorkItem(
                    id=str(uuid.uuid4()),
                    original_work_item_id=task_id,
                    task_name=self.name,
                    payload={"args": args, "kwargs": kwargs},
                    error_message=str(exc),
                    traceback=traceback.format_exc() if einfo else None
                )
                session.add(failed_item)
                await session.commit()

        # Run synchronously since Celery workers are sync by default
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        loop.run_until_complete(_record_failure())
        super().on_failure(exc, task_id, args, kwargs, einfo)



celery_app = Celery(
    "prospectforge",
    broker=broker_url,
    backend=result_backend,
    include=["app.workers.tasks"],
    task_cls=ProspectForgeTask,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.workers.tasks.ingest_*": {"queue": "source-ingestion"},
        "app.workers.tasks.resolve_*": {"queue": "identity-domain"},
        "app.workers.tasks.extract_*": {"queue": "website-evidence"},
        "app.workers.tasks.contact_*": {"queue": "buyer-contact"},
        "app.workers.tasks.campaign_*": {"queue": "campaigns-notifications"},
    },
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

if __name__ == "__main__":
    celery_app.start()
