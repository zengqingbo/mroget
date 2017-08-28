#!/usr/bin/env python
# -*- coding: utf-8 -*-
import psycopg2
from mroparser5 import mro
from config import *
import os
import time
import socket
import mroCounter

DEBUG_LEVEL = 0

def mrofilehandle(fobj,nid):
	run_server_name=socket.gethostname()
	if run_server_name == 'USER-GKJ0PB6D7E':run_server_name = 'boco1240'
	t1 = time.time()
	dir = os.path.join(CSV_PATH,getMrofileDate(fobj.filename))
	if not os.path.isdir(dir) : os.mkdir(dir)
	dir = os.path.join(dir,str(nid))
	if not os.path.isdir(dir) : os.mkdir(dir)
	m = mro(fobj)
	c = mroCounter.mroCounter(m)
	fn_sccounter = c.to_csv_sccounter(dir)
	print fn_sccounter
	fn_nccounter = c.to_csv_nccounter(dir)
	scfilename = m.toCsvScInfo(dir)
	ncfilename = m.toCsvNcInfo(dir)
	conn = psycopg2.connect(PG_CONN_TEXT)
	cur = conn.cursor()
	cur.execute("insert into filelist_68(run_server_name,filename,nid,date_num) values('%s','%s',%d,'%s');" % (run_server_name,scfilename,nid,getMrofileDate(fobj.filename)))
	cur.execute("insert into filelist_68(run_server_name,filename,nid,date_num) values('%s','%s',%d,'%s');" % (run_server_name,ncfilename,nid,getMrofileDate(fobj.filename)))
	conn.commit()
	cur.close()
	conn.close()	
	print 'handle sub file:%s samples: %d , used time : %.2f' % (fobj.filename, len(m.samples), time.time()-t1)

def getMrofileDate(filename):
	return filename.split('_')[5][:8]