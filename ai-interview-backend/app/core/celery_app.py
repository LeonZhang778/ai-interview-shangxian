import logging
from celery import Celery
from app.core.config import settings

# 配置 Celery
celery_app = Celery(
    "tasks",
    broker=settings.CELERY_BROKER_URL,
backend=settings.CELERY_RESULT_BACKEND,
    include=[
        'app.schedule.celery_job',  # 主注册模块
        'app.schedule.jobs.demo',   # 示例任务
        'app.schedule.jobs.email_tasks',  # 邮件任务
        'app.schedule.jobs.image_task',   # 图片生成任务
        'app.schedule.jobs.media_tasks',  # 媒体工具任务
    ]
)

# 配置 Celery Beat（定时任务）
celery_app.conf.beat_schedule = {
    'demo-every-minute': {
        'task': 'app.schedule.jobs.demo.execute',
        'schedule': 60.0,
        'options': {'queue': 'scheduled_tasks'}
    },
    'media-health-check': {
        'task': 'media.health_check',
        'schedule': 300.0,  # 每 5 分钟检查一次
        'options': {'queue': 'media_tasks'},
    },
}

celery_app.conf.timezone = 'UTC'
celery_app.conf.task_queues = {
    'scheduled_tasks': {
        'exchange': 'scheduled_tasks',
        'routing_key': 'scheduled_tasks',
    },
    'media_tasks': {
        'exchange': 'media_tasks',
        'routing_key': 'media_tasks',
    },
    'celery': {  # 默认队列
        'exchange': 'celery',
        'routing_key': 'celery',
    }
}

# 媒体任务路由：实际任务名为 media.process_media、media.health_check，统一投递到 media_tasks 队列
celery_app.conf.task_routes = {
    "media.*": {"queue": "media_tasks"},
}

# Optional: Configure other Celery settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    worker_concurrency=settings.MEDIA_WORKER_CONCURRENCY,
    task_time_limit=30 * 60,  # 30 minutes time limit
    task_soft_time_limit=15 * 60,  # 15 minutes soft time limit
)