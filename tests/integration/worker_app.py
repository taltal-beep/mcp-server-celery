import os

from celery import Celery

app = Celery("integration", broker=os.environ["CELERY_BROKER_URL"])
app.conf.worker_hijack_root_logger = False


@app.task(name="integration.add")
def add(x, y):
    return x + y
