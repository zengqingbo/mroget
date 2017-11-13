#from __future__ import absolute_import, unicode_literals
import os , time , shutil , gzip  , psycopg2
from zipfile import ZipFile , BadZipfile
from multiprocessing.pool import Pool as Pool
import billiard 
from multiprocessing.util import Finalize
from io import BytesIO as StringIO
from datetime import datetime

from mroparser5 import mro 
from mroCounter import mroCounter
from tinyCsvMerge import mergefile_all , MERG_DIR
from celery import Celery

DEBUG_LEVEL = 0
CSV_DIR = './csv/'
ZIP_DIR = './zip/'

PG_CONN_TEXT = 'host=10.XXX.XXX.2 dbname=qc user=postgres password=r00t'


def getZipobj(filename):
	t1 = time.time()
	try:
		zipobj = ZipFile(filename,'r')
	except BadZipfile as e:
		print('zipfile.BadZipfile' , e )
		zipobj = None
	return zipobj


def getSubFobj(zipobj,subname):
	if os.path.splitext(subname)[1].lower() == '.zip' :
		fzip = ZipFile(StringIO(zipobj.read(subname)))
		try:
			fobj = StringIO(fzip.read(fzip.namelist()[0]))
		except : 
			return None
		setattr(fobj,'filename',subname)			
	elif os.path.splitext(subname)[1].lower() == '.gz' :
		gz_fobj = StringIO(zipobj.read(subname))
		try : 
			fobj = StringIO(gzip.GzipFile(filename= subname , mode = 'rb', fileobj = gz_fobj).read())
		except : 
			return None
		setattr(fobj,'filename',subname)
	else :
		return None
	return fobj

def handleSub(fobj,nid):
	#print(fobj.filename)
	m = mro(fobj)
	c = mroCounter(m)
	fn_sccounter = c.to_csv_sccounter(CSV_DIR)
	fn_nccounter = c.to_csv_nccounter(CSV_DIR)
	fn_cmpcounter = c.to_csv_cmpcounter(CSV_DIR)
	fn_nccmpcounter= c.to_csv_nccmpcounter(CSV_DIR)
	fn_freqcounter = c.to_csv_freqcounter(CSV_DIR)
	#scfilename = m.toCsvScInfo(CSV_DIR)
	#ncfilename = m.toCsvNcInfo(CSV_DIR)
	fobj.close()
	del(c)
	del(m)

_finalizers = []

def poolHandle(zip,nid):
	if DEBUG_LEVEL ==0 : 	
		p = Pool(80)
		for sub in zip.namelist():
			fobj = getSubFobj(zip,sub)
			if fobj != None : p.apply_async(handleSub,args=(fobj,nid))
		p.close()  
		p.join()
	elif DEBUG_LEVEL ==1 :
		p = billiard.Pool()
		_finalizers.append(Finalize(p, p.terminate))
		try:
			p.map_async(handleSub, [(getSubFobj(zip,sub),nid) for sub in zip.namelist()])
			p.close()
			p.join()
		finally:
			p.terminate()
	else :
		for sub in zip.namelist():
			fobj = getSubFobj(zip,sub)
			if fobj != None : handleSub(fobj,nid)
	zip.close()

def todb(filelist,nid):
	conn = psycopg2.connect(PG_CONN_TEXT)
	cur = conn.cursor()
	for filename in filelist:
		if filetype(filename) == 'cmpcounter' :
			cur.execute("copy cmpcounter from '{}' WITH DELIMITER AS ',' NULL AS 'NIL' CSV;".format(filename) )
			conn.commit()
		if filetype(filename) == 'nccmpcounter' :
			cur.execute("copy nccmpcounter from '{}' WITH DELIMITER AS ',' NULL AS 'NIL' CSV;".format(filename) )
			conn.commit()
	cur.close()
	conn.close()
	os.remove(filename)

def filetype(filename):
	return os.path.splitext(os.path.splitext(filename)[0])[1].replace('.','').replace('.','')

def mvtonfs(nfsfile,mergefilelist):
	filelist = []
	for filename in mergefilelist:
		d, fn = os.path.split(nfsfile)
		d, nid = os.path.split(d)
		d , date = os.path.split(d)
		targetfile = shutil.move(filename,os.path.join(d,'{}_{}_{}'.format(date,nid,os.path.basename(filename))))
		os.chmod(targetfile,0o664)
		filelist.append(targetfile)
	return filelist	

def handleAll(filename,nid):
	init()
	if DEBUG_LEVEL != 0 :
		tmpfile = shutil.copy(filename,ZIP_DIR)
	else:
		tmpfile = shutil.move(filename,ZIP_DIR)
	myzip = getZipobj(tmpfile)
	if myzip != None : 
		poolHandle(myzip,nid)
	os.remove(tmpfile)
	mergefilelist = mergefile_all(filename)
	targetfilelist = mvtonfs(filename,mergefilelist)
	return targetfilelist

def init():
	tg_dir = [ZIP_DIR, CSV_DIR, MERG_DIR ]
	for d in tg_dir:
		for root, dirs, files in os.walk(d):
			for f in files:
				os.remove(os.path.join(root,f))


if __name__ == '__main__':
	t1 = datetime.now()
	handleAll('',1)
	print('used time : {}'.format(datetime.now()-t1))



