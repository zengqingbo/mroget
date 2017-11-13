import os , shutil
import time
from datetime import datetime , timedelta

CUR_DIR = os.path.split(os.path.realpath(__file__))[0]
CSV_DIR = os.path.join(CUR_DIR,'csv')
MERG_DIR = os.path.join(CUR_DIR,'merge')


def mergefile(src,dst):
	#print (src,dst)
	if os.path.isfile(src) :
		with open(dst,'a') as fdst:
			with open(src,'r') as fsrc:
				shutil.copyfileobj(fsrc, fdst)
		os.remove(src)

def mergefile_all(zipname = ''):
	zipname = os.path.basename(zipname)
	fldict = {}
	result = []
	for dirpath, dirnames, filenames in os.walk(CSV_DIR):
		for filename in filenames:
			if os.path.splitext(filename)[1]=='.csv':
				ftype = os.path.splitext(os.path.splitext(filename)[0])[1].replace('.','')
				if ftype not in fldict : fldict[ftype] = []
				fldict[ftype].append(filename)
	for ftype,flist in fldict.items() :
		fdst = os.path.join(MERG_DIR,'.'.join(filter(None,[zipname,ftype,'csv'])))
		result.append(fdst)
		for f in flist:
			fsrc = os.path.join(CSV_DIR,f)
			mergefile(fsrc,fdst)
	return result	

if __name__ == '__main__':
	t1 = datetime.now()
	mergefile_all()
	print('used time : {}'.format(datetime.now()-t1))