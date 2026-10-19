from celery import Celery
from kombu import Queue

app = Celery("sample", broker="redis://sample:6379/0", set_as_current=False)
app.conf.task_queues = [Queue("emails"), Queue("reports")]
