#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ftpext
import csv
from config import *
import re
import time
import os
from multiprocessing import Pool
from datetime import date, datetime, timedelta

debuglevel = 0

subfoldernor = {
	'HUAWEI' : {'dateDirformat':'%Y%m%d','layer':1,'ext':'.zip'},
	'ZTE' : {'dateDirformat':'%Y-%m-%d','layer':1,'ext':'.zip'},
	'POTEVO' : {'dateDirformat':'%Y-%m-%d','layer':1,'ext':'.zip'},
	'ERICSSON' : {'dateDirformat':'%Y%m%d','layer':2,'ext':'.zip'},
	'NSN' : {'dateDirformat':'%Y%m%d','layer':2,'ext':'.gz'},
	'DATANG' : {'dateDirformat':'%Y-%m-%d','layer':2,'ext':'.gz'}
	}

def mroFileCheck(localdir,filename):
	return os.path.isfile(os.path.join(localdir,filename+'.done'))

def ftpPush(localdir,filename,mirrorlevel):
	ftp = ftpext.FTPExt('10.30.173.73','21','mroPusher','1qaz@WSX')
	subdir = 'MRO'
	if subdir not in ftp.nlst() : ftp.mkd(subdir)
	ftp.cwd('MRO')
	dirlist = localdir.split(os.sep)
	for i in range(mirrorlevel):
		subdir = dirlist[i-mirrorlevel]
		print subdir
		if subdir not in ftp.nlst() : ftp.mkd(subdir)
		ftp.cwd(subdir)
	f = open(os.path.join(localdir,filename), 'rb')
	f_done = open(os.path.join(localdir,filename+'.done'), 'rb')
	print '%s push is begin' % filename
	if filename not in ftp.nlst() : 
		ftp.storbinary('STOR '+filename,f)
		ftp.storbinary('STOR '+filename+'.done',f_done)
	print '%s push is done' % filename
	f.close()
	ftp.close()
	delayRemove(localdir,filename)


def delayRemove(localdir,filename):
	delaytime = 0
	print filename ,'will be deleted in %d second' % delaytime
	for i in range(delaytime):
		time.sleep(1)
		print delaytime - i
	os.remove(os.path.join(localdir, filename))


def ftpDL(ftp,localdir,filename):
	print filename , 'is downloading'
	f_done = open(os.path.join(localdir, filename + '.done'),'w')
	f = open(os.path.join(localdir, filename),'wb')
	ftp.retrbinary('RETR ' + filename , f.write , 1024)
	f.close()
	f_done.write('OK')
	f_done.close()
	print filename, 'is done'
	#ftpPush(localdir,filename,2)

def isValidMroFile(filename,omcinfo):
	if filename.find('MRO') == -1 : return False
	if os.path.splitext(filename)[1] <> subfoldernor[omcinfo['vendor']]['ext'] : return False
	try:
		m = rg.search(filename)
	except:
		rg_txt = '.+_(\d{14})[_\.].+'
		rg = re.compile(rg_txt, re.DOTALL) 
		m = rg.search(filename)
	if not m : return False
	d = m.group(1)
	fileDateTime = datetime(int(d[:4]),int(d[4:6]),int(d[6:8]),int(d[8:10]),int(d[10:12]))
	timedeltaHour = timedelta(hours = DELTA_HOURS)
	if debuglevel >= 2 : print fileDateTime
	if datetime.now() - fileDateTime > timedeltaHour : return False
	return True	

def getValidDate():
	#return list ,include valid date. from now, [ValidDateNum] days
	ValidDateNum = 2
	validDate = []
	for i in range(ValidDateNum):
		validDate.append(datetime.now()-timedelta(days=i))
	return validDate

def niGetter(omcinfo):
	print 'nbi id%s ip(%s) is scan' % (omcinfo['id'],omcinfo['ip'])
	ftp = ftpext.FTPExt(omcinfo['ip'],omcinfo['port'],omcinfo['user'],omcinfo['password'])
	ftp.cwd(omcinfo['path'])
	if debuglevel >= 1 : print os.path.join(omcinfo['path'])
	for k,v in ftp.ls().iteritems():
		for validDate in getValidDate():
			localdir = os.path.join(os.getcwd(),'Nfile',validDate.strftime('%Y%m%d'))
			if not os.path.isdir(localdir) : os.mkdir(localdir)
			localdir = os.path.join(localdir,omcinfo['id'])
			if not os.path.isdir(localdir) : os.mkdir(localdir)
			if v['dir'] and \
			k.find(validDate.strftime(subfoldernor[omcinfo['vendor']]['dateDirformat'])) <> -1 :
				if debuglevel >= 1 : print omcinfo['path']+'/'+k
				ftp.cwd(omcinfo['path']+'/'+k)
				for k1,v1 in ftp.ls().iteritems():
					if subfoldernor[omcinfo['vendor']]['layer'] == 1 :
						if debuglevel >= 2 : print k1
						if v1['file'] and isValidMroFile(k1,omcinfo) and not mroFileCheck(localdir,k1):
							ftpDL(ftp,localdir,k1)
					elif v1['dir'] and subfoldernor[omcinfo['vendor']]['layer'] == 2 :
						if debuglevel >= 2 : print omcinfo['path']+'/'+k+'/'+k1
						ftp.cwd(omcinfo['path']+'/'+k+'/'+k1)
						for k2,v2 in ftp.ls().iteritems():
							if isValidMroFile(k2,omcinfo) and not mroFileCheck(localdir,k2):
								ftpDL(ftp,localdir,k2)
	ftp.close()

def getmrnicfg():
	mrnicfg =[]
	with open('mrnicfg.csv','rb') as csvfile:
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

def mroFilegetter():
	mrnicfg = getmrnicfg()
	print 'loaded mrnbicfg %d rows' % len(mrnicfg)
	p = Pool(2)
	for mrni in mrnicfg:
		print mrni['id'],mrni['ip']
		if debuglevel == 0 :p.apply_async(niGetter,args=(mrni,))
		else: niGetter(mrni)
	print 'waiting all omc connection returns'
	p.close()
	p.join()
	print 'finish all %d connections' % len(mrnicfg)

def main():
	d = date.today()
	dd = datetime(d.year,d.month,d.day,23,30)
	drive = os.path.splitdrive(CSV_PATH)[0]
	i=1
	while datetime.now() - dd < timedelta(0) :
		if getDiskFreeGB(drive) > 40 :
			print 'begin %d' % i
			mroFilegetter()
			time.sleep(120)
			i = i + 1
		else:
			print 'disk freeSpace < 40GB'

if __name__ == '__main__':
	main()