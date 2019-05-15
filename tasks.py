from __future__ import absolute_import, unicode_literals
from celery import Celery
from zipfilehandle import handleAll,mvtonfs
from tinyCsvMerge import mergefile_all
from multiprocessing import current_process
from celery.utils.log import get_task_logger
from kombu import Queue
import os,psycopg2
from datetime import datetime

PG_CONN_TEXT = 'host=10.XXX.XXX.2 dbname=XXXX user=XXXX password=XXXX'

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

@app.task(queue='main')
def handleBigZipfile(filename,nid):
	current_process()._config['daemon'] = False

	logger.info('{} begin handle!'.format(filename))
	recordtime(filename,nid,'taskbegin')

	filelist=handleAll(filename,nid)

	for csvfile in filelist:
		maintodb(csvfile)
	
	recordtime(filename,nid,'taskend')
	logger.info('{} is done!'.format(filename))

def recordtime(filename,nid,timename):
	conn = psycopg2.connect(PG_CONN_TEXT)
	cur = conn.cursor()
	try :
		cur.execute("update filelist set {} = '{}' where filename='{}' and nid = {};".format(timename,datetime.now(),filename,nid))
		conn.commit()
	except Exception as e :
		cur.close()
		conn.close()
		raise e		
	cur.close()
	conn.close()		

def maintodb(filename):
	conn = psycopg2.connect(PG_CONN_TEXT)
	cur = conn.cursor()
	tablename = filetype(filename)	
	try :	
		cur.execute("copy {} from '{}' WITH DELIMITER AS ',' NULL AS 'NIL' CSV;".format(tablename,filename) )
		conn.commit()
	except Exception as e:
		cur.close()
		conn.close()	
		raise e
	cur.close()
	conn.close()	
	os.remove(filename)


def filetype(filename):
	return os.path.splitext(os.path.splitext(filename)[0])[1].replace('.','').replace('.','')
