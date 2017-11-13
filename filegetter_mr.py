#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ftpext
import csv
import re
import time
import os , shutil
from multiprocessing import Pool
from datetime import date, datetime, timedelta
from tasks import handleBigZipfile
import psycopg2

PG_CONN_TEXT = 'host=10.25.226.2 dbname=qc user=postgres password=r00t'

debuglevel = 0
CUR_DIR = os.path.split(os.path.realpath(__file__))[0]
FTP_DL_DIR = '/gpdir/mro'
DELTA_HOURS = 4

subfoldernor = {
	'HUAWEI' : {'dateDirformat':'%Y%m%d','layer':1,'ext':'.zip'},
	'ZTE' : {'dateDirformat':'%Y-%m-%d','layer':1,'ext':'.zip'},
	'POTEVO' : {'dateDirformat':'%Y-%m-%d','layer':1,'ext':'.zip'},
	'ERICSSON' : {'dateDirformat':'%Y%m%d','layer':2,'ext':'.zip'},
	'NSN' : {'dateDirformat':'%Y%m%d','layer':2,'ext':'.gz'},
	'DATANG' : {'dateDirformat':'%Y-%m-%d','layer':2,'ext':'.gz'}
	}

def mroFileCheck(localdir,filename,):
	dstfilename = os.path.join(localdir,filename)
	conn = psycopg2.connect(PG_CONN_TEXT)
	cur = conn.cursor()
	cur.execute("select filename from filelist where filename = '{}' ;".format(dstfilename))
	rs = cur.fetchall()
	filelist = [r[0] for r in rs]
	cur.close()
	conn.close()
	return dstfilename in filelist

def mroFileCheckHour(localdir,filename,):
	dstfilename = os.path.join(localdir,filename)
	try: 
		return dstfilename in FILE_LIST
	except:
		conn = psycopg2.connect(PG_CONN_TEXT)
		cur = conn.cursor()
		hours = getHours()
		cur.execute("select filename from filelist where filetime > '{}' ;".format(datetime.now()-timedelta(hours=DELTA_HOURS+12)))
		rs = cur.fetchall()
		FILE_LIST = [r[0] for r in rs]
		cur.close()
		conn.close()
		return dstfilename in FILE_LIST

def mroFileRecord(filename,nid):
	conn = psycopg2.connect(PG_CONN_TEXT)
	cur = conn.cursor()
	try:
		m = rg.search(filename)
	except:
		rg_txt = '.+_(\d{14})[_\.].+'
		rg = re.compile(rg_txt, re.DOTALL) 
		m = rg.search(filename)
	if not m : return False
	d = m.group(1)
	fileDateHour = datetime(int(d[:4]),int(d[4:6]),int(d[6:8]),int(d[8:10]))
	cur.execute("insert into filelist(filename,nid,filetime,tasksend) values('{}',{},'{}','{}');".format(filename,nid,fileDateHour,datetime.now()))
	conn.commit()
	cur.close()
	conn.close()


def isValidMroFile(filename,omcinfo,hour=False):
	if filename.find('MRO') == -1 : return False
	if os.path.splitext(filename)[1] != subfoldernor[omcinfo['vendor']]['ext'] : return False
	try:
		m = rg.search(filename)
	except:
		rg_txt = '.+_(\d{14})[_\.].+'
		rg = re.compile(rg_txt, re.DOTALL) 
		m = rg.search(filename)
	if not m : return False
	d = m.group(1)
	fileDateTime = datetime(int(d[:4]),int(d[4:6]),int(d[6:8]),int(d[8:10]),int(d[10:12]))
	fileDateHour = datetime(int(d[:4]),int(d[4:6]),int(d[6:8]),int(d[8:10]))
	timedeltaHour = timedelta(hours = DELTA_HOURS)
	if debuglevel >= 2 : print(fileDateTime)
	if hour :
		if hour == fileDateHour : return True
	else :
		if datetime.now() - fileDateTime <= timedeltaHour : return True
	return False	

def ftpPush(localdir,filename,mirrorlevel):
	ftp = ftpext.FTPExt('10.30.173.73','21','mroPusher','1qaz@WSX')
	subdir = 'MRO'
	if subdir not in ftp.nlst() : ftp.mkd(subdir)
	ftp.cwd('MRO')
	dirlist = localdir.split(os.sep)
	for i in range(mirrorlevel):
		subdir = dirlist[i-mirrorlevel]
		print(subdir)
		if subdir not in ftp.nlst() : ftp.mkd(subdir)
		ftp.cwd(subdir)
	f = open(os.path.join(localdir,filename), 'rb')
	f_done = open(os.path.join(localdir,filename+'.done'), 'rb')
	print('%s push is begin' % filename)
	if filename not in ftp.nlst() : 
		ftp.storbinary('STOR '+filename,f)
		ftp.storbinary('STOR '+filename+'.done',f_done)
	print('%s push is done' % filename)
	f.close()
	ftp.close()
	delayRemove(localdir,filename)


def delayRemove(localdir,filename):
	delaytime = 0
	print(filename ,'will be deleted in %d second' % delaytime)
	for i in range(delaytime):
		time.sleep(1)
		print(delaytime - i)
	os.remove(os.path.join(localdir, filename))


def ftpDL(ftp,localdir,filename,nid):
	print(filename , 'is downloading')
	dstname = os.path.join(localdir, filename)
	f = open(dstname,'wb')
	ftp.retrbinary('RETR ' + filename , f.write , 1024)
	f.close()
	print(dstname, 'is done')
	#ftpPush(localdir,filename,2)
	handleBigZipfile.delay(dstname,nid)
	mroFileRecord(dstname,nid)


def getValidDate():
	#return list ,include valid date. from now, [ValidDateNum] days
	ValidDateNum = 2
	validDate = []
	for i in range(ValidDateNum):
		validDate.append(datetime.now()-timedelta(days=i))
	return validDate

def niGetter(omcinfo):
	print('nbi id%s ip(%s) is scan' % (omcinfo['id'],omcinfo['ip']))
	ftp = ftpext.FTPExt(omcinfo['ip'],omcinfo['port'],omcinfo['user'],omcinfo['password'])
	ftp.cwd(omcinfo['path'])
	if debuglevel >= 1 : print(os.path.join(omcinfo['path']))
	for k,v in ftp.ls().items():
		for validDate in getValidDate():
			localdir = os.path.join(FTP_DL_DIR,validDate.strftime('%Y%m%d'))
			if not os.path.isdir(localdir) : os.mkdir(localdir)
			localdir = os.path.join(localdir,omcinfo['id'])
			if not os.path.isdir(localdir) : os.mkdir(localdir)
			print(validDate.strftime(subfoldernor[omcinfo['vendor']]['dateDirformat']),v['dir'],k,v)
			if v['dir'] and \
			k.find(validDate.strftime(subfoldernor[omcinfo['vendor']]['dateDirformat'])) != -1 :
				if debuglevel >= 1 : print(omcinfo['path']+'/'+k)
				ftp.cwd(omcinfo['path']+'/'+k)
				for k1,v1 in ftp.ls().items():
					if subfoldernor[omcinfo['vendor']]['layer'] == 1 :
						if debuglevel >= 2 : print(k1)
						if v1['file'] and isValidMroFile(k1,omcinfo) and not mroFileCheck(localdir,k1):
							ftpDL(ftp,localdir,k1,omcinfo['id'])
					elif v1['dir'] and subfoldernor[omcinfo['vendor']]['layer'] == 2 :
						if debuglevel >= 2 : print(omcinfo['path']+'/'+k+'/'+k1)
						ftp.cwd(omcinfo['path']+'/'+k+'/'+k1)
						for k2,v2 in ftp.ls().items():
							if isValidMroFile(k2,omcinfo) and not mroFileCheck(localdir,k2):
								ftpDL(ftp,localdir,k2,omcinfo['id'])
	ftp.close()

def niHourGetter(omcinfo,hour):
	print('nbi id%s ip(%s) is scan' % (omcinfo['id'],omcinfo['ip']))
	ftp = ftpext.FTPExt(omcinfo['ip'],omcinfo['port'],omcinfo['user'],omcinfo['password'])
	ftp.cwd(omcinfo['path'])
	if debuglevel >= 1 : print(os.path.join(omcinfo['path']))
	for k,v in ftp.ls().items():
		localdir = os.path.join(FTP_DL_DIR,hour.strftime('%Y%m%d'))
		if not os.path.isdir(localdir) : os.mkdir(localdir)
		localdir = os.path.join(localdir,omcinfo['id'])
		if not os.path.isdir(localdir) : os.mkdir(localdir)
		if v['dir'] and \
		k.find(hour.strftime(subfoldernor[omcinfo['vendor']]['dateDirformat'])) != -1 :
			if debuglevel >= 1 : print(omcinfo['path']+'/'+k)
			ftp.cwd(omcinfo['path']+'/'+k)
			for k1,v1 in ftp.ls().items():
				if subfoldernor[omcinfo['vendor']]['layer'] == 1 :
					if debuglevel >= 2 : print(k1)
					if v1['file'] and isValidMroFile(k1,omcinfo,hour) and not mroFileCheck(localdir,k1):
						ftpDL(ftp,localdir,k1,omcinfo['id'])
				elif v1['dir'] and subfoldernor[omcinfo['vendor']]['layer'] == 2 :
					if debuglevel >= 2 : print(omcinfo['path']+'/'+k+'/'+k1)
					ftp.cwd(omcinfo['path']+'/'+k+'/'+k1)
					for k2,v2 in ftp.ls().items():
						if isValidMroFile(k2,omcinfo,hour) and not mroFileCheck(localdir,k2):
							ftpDL(ftp,localdir,k2,omcinfo['id'])
	ftp.close()

def getmrnicfg():
	mrnicfg =[]
	with open(os.path.join(CUR_DIR,'mrnicfg.csv'),mode='r',encoding='gbk') as csvfile:
		cfgreader = csv.reader(csvfile)
		for row in cfgreader:
			omcinfo = {
				'id' : row[0],
				'vendor'	:	row[2],
				'ip' : row[4],
				'user' : row[5],
				'password' : row[6],
				'port' : row[7],
				'type' : row[8],
				'path' : row[9],
				'mode' : row[10]
			}
			mrnicfg.append(omcinfo)
	return(mrnicfg)

def mroFilegetter():
	mrnicfg = getmrnicfg()
	print('loaded mrnbicfg %d rows' % len(mrnicfg))
	p = Pool(8)
	for mrni in mrnicfg:
		print(mrni['id'],mrni['ip'])
		if debuglevel == 0 :p.apply_async(niGetter,args=(mrni,))
		else: niGetter(mrni)
	print('waiting all omc connection returns')
	p.close()
	p.join()
	print('finish all %d connections' % len(mrnicfg))

def getHours(delta = DELTA_HOURS):
	hours = []
	d = datetime.now()
	n = datetime(d.year,d.month,d.day,d.hour)
	for i in range(delta):
		hours.append(n-timedelta(hours=i))
	return hours

def getDay(y,m,d):
	hours = []
	return [datetime(y,m,d,h) for h in range(24)]

def mroHourFilegetter(hours = None , omcids = None):
	mrnicfg = getmrnicfg()
	if type(omcids) == list : mrnicfg = [omcinfo for omcinfo in mrnicfg if omcinfo['id'] in omcids]
	print('loaded mrnbicfg %d rows' % len(mrnicfg))
	p = Pool(8)
	if hours == None: hours = getHours()
	print(hours)
	for hour in hours : 
		for omcinfo in mrnicfg:
			print(omcinfo['id'],omcinfo['ip'])
			if debuglevel == 0 :p.apply_async(niHourGetter,args=(omcinfo,hour))
			else: niHourGetter(omcinfo,hour)
		print('waiting all omc connection returns')
	p.close()
	p.join()
	print('finish all %d connections' % len(mrnicfg))


def getDiskFreeGB(drive):
	total, used , free = shutil.disk_usage(drive)
	return free/1024/1024/1024

def mrgetter_main():
	if getDiskFreeGB(FTP_DL_DIR) > 500 :
		mroHourFilegetter(getDay(2017,11,8))
		mroHourFilegetter(getDay(2017,11,10))
		mroHourFilegetter(getDay(2017,11,6))
		mroHourFilegetter(getDay(2017,11,4))			

if __name__ == '__main__':
	mrgetter_main()
