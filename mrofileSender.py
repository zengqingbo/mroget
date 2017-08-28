#!/usr/bin/env python
# -*- coding: utf-8 -*-
import psycopg2
import os
from czipfile import ZipFile
import czipfile
import time 
from multiprocessing import Pool
import threadpool
from datetime import date,datetime,timedelta
from config import *
from mroHandler import mrofilehandle
import socket
import gzip
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO


DEBUG_LEVEL = 1

def isMroFile(filename):
	if not os.path.isfile(filename) : return False
	basename = os.path.splitext(os.path.basename(filename))
	fs = basename[0].split('_')
	if len(fs) < 4 or fs[1].lower() <> 'mro' : return False
	if len(basename) < 2 or basename[1].lower() not in ['.gz','.zip'] : return False
	return True

def isFileDone(filename):
	fnDone = filename + '.done'
	return os.path.isfile(fnDone) and os.path.getsize(fnDone)

def filelistRecord(path):
	run_server_name=socket.gethostname()
	if run_server_name == 'USER-GKJ0PB6D7E':run_server_name = 'boco1240'
	commitCount = 1000
	i = 0
	if os.path.isdir(path):		
		conn = psycopg2.connect(PG_CONN_TEXT)
		cur = conn.cursor()
		cur.execute('create temp table filelist_tmp (like filelist_68_all);' )
		conn.commit()
		for root , dir , files in os.walk(path):
			dir = os.path.basename(root)
			print 'scan %s %s' %(root,dir)
			for fn in files:
				root_fn = os.path.join(root,fn)
				if  isFileDone(root_fn) and isMroFile(root_fn) : #Done and Correct	
					cur.execute("insert into filelist_tmp(filename,nid) values('%s',%s);" % (root_fn,dir))
					i = i + 1
					if i > commitCount: 
						conn.commit()
						i = 0
		if i > 0 : conn.commit()
		sql = """  insert into filelist_68_all(run_server_name,filename,nid)
		select '%s',a.filename,a.nid from filelist_tmp a left join filelist_68_all b
		on a.filename = b.filename 
		where b.filename is null;
		"""%run_server_name
		cur.execute(sql)
		conn.commit()
		cur.close()
		conn.close()

def getValidFilelist():
	conn = psycopg2.connect(PG_CONN_TEXT)
	cur = conn.cursor()
	run_server_name=socket.gethostname()
	if run_server_name == 'USER-GKJ0PB6D7E':run_server_name = 'boco1240'
	cur.execute("select filename,nid from filelist_68_all where status is null and run_server_name='%s';"%run_server_name)
	rs = cur.fetchall()
	cur.close()
	conn.close()	
	return rs

class fileobj():
	def __init__(self,fobj ,filename = ''):
		self._fobj = fobj
		self._filename = filename

	@property
	def fobj(self):
		return self._fobj
	
	@property
	def filename(self):
		return self._filename

def handleSubZip(myzip,subname,nid):
	#print subname
	if os.path.splitext(subname)[1].lower() == '.zip' :
		fzip = ZipFile(StringIO(myzip.read(subname)))
		fobj = StringIO(fzip.read(fzip.namelist()[0]))			
	elif os.path.splitext(subname)[1].lower() == '.gz' :
		gz_fobj = StringIO(myzip.read(subname))
		fobj = gzip.GzipFile(filename= subname , mode = 'rb', fileobj = gz_fobj)
	else :
		return None
	fnobj = fileobj(fobj,subname)
	handleMrofile(fnobj, nid)

def handleMrofile(fobj,nid):
	mrofilehandle(fobj,nid)
	del fobj


def handleZipfile(filename,nid):
	t1 = time.time()
	try:
		myzip = ZipFile(filename,'r')
	except czipfile.BadZipfile , e:
		print 'czipfile.BadZipfile' , e 
		myzip = None
	if myzip <> None :
		p = Pool()
		for subname in myzip.namelist():
			if DEBUG_LEVEL == 0 : 
				p.apply_async(handleSubZip,args = (myzip,subname,nid,))
			else:
				handleSubZip(myzip,subname,nid)
		print 'begin!! mutliprocessing file:%s' % os.path.basename(filename)
		p.close()
		p.join() 
		myzip.close()
	print 'complete!! file:%s , used time: %.2f' % (os.path.basename(filename),time.time()-t1)
	try:
		os.remove(filename)
	except WindowsError , e:
		print 'WindowsError:',e

	

def handleFile(filename,nid):
	print 'handleFile %s begin' % filename
	if os.path.splitext(filename)[1].lower() == '.zip' :
		handleZipfile(filename,nid)
	elif os.path.splitext(filename)[1].lower() == '.gz': 
		#print 'handleMrofile error!!', os.path.splitext(filename)[1].lower
		#fobj = fileobj(gzip.open(filename,'rb'),os.path.basename(filename))
		#handleMrofile(fobj,nid)
		#fobj.close()
		return None
	else :
		return None
	conn = psycopg2.connect(PG_CONN_TEXT)
	cur = conn.cursor()
	cur.execute("update filelist_68_all set status = true where filename = '%s';" % filename)
	conn.commit()
	cur.close()
	conn.close()
	print 'handleFile %s complete' % filename

def fileSender(path):
	t1 = time.time()
	filelistRecord(path)
	for r in getValidFilelist():
		handleFile(r[0],r[1])
	t2 = time.time()
	print 'usetime : %.1fs' % (t2-t1)


def getDiskFreeGB(drive):
	if os.name == 'nt' :
		try :
			sectorsPerCluster, bytesPerSector, numFreeClusters, totalNumClusters = \
					win32file.GetDiskFreeSpace(os.path.splitdrive(CSV_PATH)[0])
			return (numFreeClusters * sectorsPerCluster * bytesPerSector) /(1024 * 1024 * 1024)#get free space
		except :
			import win32file
			sectorsPerCluster, bytesPerSector, numFreeClusters, totalNumClusters = \
					win32file.GetDiskFreeSpace(os.path.splitdrive(CSV_PATH)[0])
			return (numFreeClusters * sectorsPerCluster * bytesPerSector) /(1024 * 1024 * 1024)#get free space
	else :
		try :
			vfs = os.statvfs(CSV_PATH)
			return vfs[statvfs.F_BAVAIL]*vfs[statvfs.F_BSIZE]/(1024*1024*1024)
		except :
			import statvfs
			vfs = os.statvfs(CSV_PATH)
			return vfs[statvfs.F_BAVAIL]*vfs[statvfs.F_BSIZE]/(1024*1024*1024)


def main():
	d = date.today()
	dd = datetime(d.year,d.month,d.day,23,30)
	drive = os.path.splitdrive(CSV_PATH)[0]
	i = 1
	while datetime.now() - dd < timedelta(0) :
		if getDiskFreeGB(drive) > 30 :
			print 'begin %d' % i
			fileSender(MRO_PATH)
			time.sleep(120)
			i = i+1
		else :
			print 'disk freeSpace < 30GB'

if __name__ == '__main__':
	#main()
	handleFile('C:\\TD-LTE_MRO_HUAWEI_010030226002-010025089111_20170227090000_001.zip',61)