from celery import Celery
from celery.schedules import crontab
from celery.utils.log import get_task_logger
from filegetter_mr import mrgetter_main


app = Celery('tasks',
             broker='pyamqp://guest:guest@10.XXX.XXX.2',
             backend='db+postgresql://gpadmin:boco1234!@10.XXX.XXX.7/qc')

# Optional configuration, see the application user guide.
app.conf.update(
    result_expires=3600,
    worker_concurrency = 1,
    timezone = 'Asia/Chongqing',
)

logger = get_task_logger(__name__)

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Calls test('hello') every 10 seconds.
    sender.add_periodic_task(3600, mrogetter.s(), expires = 3600)

@app.task
def mrogetter(arg):
    mrgetter_main()
