import os

from celery import Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meiduo_mall.settings.dev")
app=Celery('meiduo',broker='redis://127.0.0.1/7')
app.autodiscover_tasks(['celery_tasks.sms','celery_tasks.email'])