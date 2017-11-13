import os 

SC_COUNTER_LIST = ['sc_rsrp_valid_counter',
				   'sc_rsrp_counter',
				   'sc_rsrp_numerator',
				   'sc_overlapcoverage_counter',
				   'sc_rsrp_invalid_counter',
				   ]

NC_COUNTER_LIST = ['nc_rsrp_numerator',
				   'nc_rsrp_counter',
				   'nc_rsrpdiff_numerator',
				   'nc_rsrp_diff3_counter',
				   'nc_rsrp_diff6_counter',
				   'nc_rsrp_diff12_counter',
				   'nc_rsrp_diff6_valid_counter']

CMP_COUNTER_LIST = ['rsrp_avg_cmcc',
					'rsrp_count_cmcc',
					'rsrp_avg_chun_nume',
					'rsrp_avg_chte_nume',
					'rsrp_count_chun',
					'rsrp_count_chte',
					'rsrp_weak_cmcc',
					'rsrp_weak_chun_110',
					'rsrp_weak_chte_110',
					'rsrp_weak_chun_113',
					'rsrp_weak_chte_113',
					'rsrp_avg_inter_cmcc_nume',
					'rsrp_count_inter_cmcc',
					'rsrp_weak_inter_cmcc',
					'arfcn_str',
					'rsrp_maxavg_cmcc',
					]

NC_CMPCOUNTER_LIST = ['nc_rsrp_count',
					'nc_rsrp_accumulate',
					'nc_weakcount_110',
					'nc_weakcount_113',
					'nc_operator'
					]

FREQ_COUNTER_LIST = ['freq_rsrp_count',
						'freq_rsrp_accumulate',
						'freq_weakcount_110',
						'freq_weakcount_113',
						'nc_operator'
						]

CMCC = [38400,38098,37900,38950,38544,39148,40936,39292,3660,36275,39150,39300,]
CMCC = [str(f) for f in CMCC]
CHUN = [1650,400,401,450,500,1500,3770,40340]
CHUN = [str(f) for f in CHUN]
CHTE = [1825,100,2452,2440,2446,41140]
CHTE = [str(f) for f in CHTE]

class counter(dict):
	def sumField(self,fieldname,value=1):
		if fieldname in self :
			self[fieldname] = self[fieldname]+value
		else :
			self[fieldname] = value
	def maxField(self,fieldname,value):
		if (fieldname in self and self[fieldname] < value) or fieldname not in self:
			self[fieldname] = value

class mroCounter(object):
	
	def __init__(self,mro):
		self.mro = mro
		self.EnodebId = mro.EnodebId
		self.scCounters = {}
		self.ncCounters = {}
		self.cmpCounters = {}
		self.cmpNcCounters = {}
		self.freqCounters = {}
		self.CounterAll()

	def _ValueNil(self,s,nil = False):
		try: 
			return float(s)-141
		except ValueError :
			return nil

	def getncArfcnComp(self,arfcn):
		if arfcn in CMCC : return 0
		if arfcn in CHUN : return 1
		if arfcn in CHTE : return 2
		return None

	def ctScInfo(self,v):
		try :
			self.scCounters[v.id].sumField('sc_rsrp_counter')
		except KeyError:
			self.scCounters[v.id] = counter()
			self.scCounters[v.id].sumField('sc_rsrp_counter')
		scrsrp = self._ValueNil(v.ScInfo['LteScRSRP'])
		if scrsrp :
			if scrsrp  >= -110 : 
				self.scCounters[v.id].sumField('sc_rsrp_valid_counter')
			else: 
				self.scCounters[v.id].sumField('sc_rsrp_invalid_counter')
			self.scCounters[v.id].sumField('sc_rsrp_numerator',scrsrp)

	def ctNcInfo(self,v):
		overlapcoverage = 0
		scrsrp = self._ValueNil(v.ScInfo['LteScRSRP'])
		for ncinfo in v.NcInfo_list:
			key = '%s,%s,%s' % (v.id , ncinfo['LteNcEarfcn'], ncinfo['LteNcPci'])
			try:
				self.ncCounters[key].sumField('nc_rsrp_counter')
			except KeyError:
				self.ncCounters[key] = counter()
				self.ncCounters[key].sumField('nc_rsrp_counter')
			ncrsrp = self._ValueNil(ncinfo['LteNcRSRP'])
			if ncrsrp :
				self.ncCounters[key].sumField('nc_rsrp_numerator',ncrsrp)
				self.ncCounters[key].sumField('nc_rsrpdiff_numerator',scrsrp-ncrsrp)
				if scrsrp-ncrsrp <=3 : 
					self.ncCounters[key].sumField('nc_rsrp_diff3_counter')
				if scrsrp-ncrsrp <=6 :
					self.ncCounters[key].sumField('nc_rsrp_diff6_counter')
					overlapcoverage = overlapcoverage + 1
					if scrsrp > -110:
						self.ncCounters[key].sumField('nc_rsrp_diff6_valid_counter')
				if scrsrp-ncrsrp <=12 :
					self.ncCounters[key].sumField('nc_rsrp_diff12_counter')
		return overlapcoverage 

	def ctCompInfo(self,v):
		try :
			self.cmpCounters[v.id].sumField('sample_counter')
		except KeyError:
			self.cmpCounters[v.id] = counter()
			self.cmpCounters[v.id]['arfcn']={}
			self.cmpCounters[v.id].sumField('sample_counter')
		scrsrp = self._ValueNil(v.ScInfo['LteScRSRP'])
		cmcc_rsrp = scrsrp
		chun_rsrp = False
		chte_rsrp = False
		for ncinfo in v.NcInfo_list:
			comp = self.getncArfcnComp(ncinfo['LteNcEarfcn'])
			try:
				self.cmpCounters[v.id]['arfcn'][str(comp)].add(ncinfo['LteNcEarfcn'])
			except KeyError:
				self.cmpCounters[v.id]['arfcn'][str(comp)]=set()
				self.cmpCounters[v.id]['arfcn'][str(comp)].add(ncinfo['LteNcEarfcn'])
			ncrsrp = self._ValueNil(ncinfo['LteNcRSRP'])
			if comp == 0 and ncrsrp > cmcc_rsrp : cmcc_rsrp = ncrsrp
			if comp == 1 and (not chun_rsrp or ncrsrp > chun_rsrp) : chun_rsrp = ncrsrp
			if comp == 2 and (not chte_rsrp or ncrsrp > chte_rsrp) : chte_rsrp = ncrsrp
		#print(v.MmeUeS1apId,v.TimeStamp,v.id,scrsrp,cmcc_rsrp,chun_rsrp,chte_rsrp,ncrsrp)
		if scrsrp : 
			self.cmpCounters[v.id].sumField('rsrp_count_cmcc')
			self.cmpCounters[v.id].sumField('rsrp_avg_cmcc',scrsrp)
			if scrsrp < -110: self.cmpCounters[v.id].sumField('rsrp_weak_cmcc')
		if cmcc_rsrp:
			self.cmpCounters[v.id].sumField('rsrp_maxavg_cmcc',cmcc_rsrp)
			if cmcc_rsrp>chun_rsrp and cmcc_rsrp>chte_rsrp : 
				self.cmpCounters[v.id].sumField('rsrp_count_inter_cmcc')
				self.cmpCounters[v.id].sumField('rsrp_avg_inter_cmcc_nume',cmcc_rsrp)
				if cmcc_rsrp < -110 : self.cmpCounters[v.id].sumField('rsrp_weak_inter_cmcc')
		if chun_rsrp:
			self.cmpCounters[v.id].sumField('rsrp_count_chun')
			self.cmpCounters[v.id].sumField('rsrp_avg_chun_nume',chun_rsrp)
			if chun_rsrp < -110 : self.cmpCounters[v.id].sumField('rsrp_weak_chun_110')
			if chun_rsrp < -113 : self.cmpCounters[v.id].sumField('rsrp_weak_chun_113')
		if chte_rsrp:
			self.cmpCounters[v.id].sumField('rsrp_count_chte')
			self.cmpCounters[v.id].sumField('rsrp_avg_chte_nume',chte_rsrp)
			if chte_rsrp < -110 : self.cmpCounters[v.id].sumField('rsrp_weak_chte_110')
			if chte_rsrp < -113 : self.cmpCounters[v.id].sumField('rsrp_weak_chte_113')

	def ctCompNcInfo(self,v):
		scrsrp = self._ValueNil(v.ScInfo['LteScRSRP'])
		if scrsrp :
			for ncinfo in v.NcInfo_list:
				key = '%s,%s,%s' % (v.id , ncinfo['LteNcEarfcn'], ncinfo['LteNcPci'])
				ncrsrp = self._ValueNil(ncinfo['LteNcRSRP'])
				if ncrsrp :
					try:
						self.cmpNcCounters[key].sumField('nc_rsrp_count')
					except KeyError:
						self.cmpNcCounters[key] = counter()
						self.cmpNcCounters[key].sumField('nc_rsrp_count')
					self.cmpNcCounters[key].sumField('nc_rsrp_accumulate',ncrsrp)
					if ncrsrp < -110: self.cmpNcCounters[key].sumField('nc_weakcount_110')
					if ncrsrp < -113: self.cmpNcCounters[key].sumField('nc_weakcount_113')

	def ctFreqInfo(self,v):
		scrsrp = self._ValueNil(v.ScInfo['LteScRSRP'])
		freqMax = counter()
		if scrsrp :
			for ncinfo in v.NcInfo_list:
				key = ncinfo['LteNcEarfcn']
				ncrsrp = self._ValueNil(ncinfo['LteNcRSRP'])
				if ncrsrp :
						freqMax.maxField(key,ncrsrp)
			for freq , ncrsrp in freqMax.items() :
				if ncrsrp :
					key = '%s,%s' % (v.id , freq)
					try:
						self.freqCounters[key].sumField('freq_rsrp_count')
					except KeyError:
						self.freqCounters[key] = counter()
						self.freqCounters[key].sumField('freq_rsrp_count')
					self.freqCounters[key].sumField('freq_rsrp_accumulate',ncrsrp)
					if ncrsrp < -110: self.freqCounters[key].sumField('freq_weakcount_110')
					if ncrsrp < -113: self.freqCounters[key].sumField('freq_weakcount_113')
	

	def CounterAll(self):
		for v in self.mro.samples.values() :
			self.ctScInfo(v)
			overlapcoverage = self.ctNcInfo(v)
			if overlapcoverage> 3 :
				self.scCounters[v.id].sumField('sc_overlapcoverage_counter')			
			self.ctCompInfo(v)
			self.ctCompNcInfo(v)
			self.ctFreqInfo(v)	
		for key in self.cmpCounters.keys() :	
			if 'arfcn' in self.cmpCounters[key] :	
				self.cmpCounters[key]['arfcn_str'] = '"{}"'.format(str(self.cmpCounters[key]['arfcn']))	
		for key in self.cmpNcCounters.keys() :
			arfcn = key.split(',')[1]
			self.cmpNcCounters[key]['nc_operator'] = self.getncArfcnComp(arfcn)
		for key in self.freqCounters.keys() :
			arfcn = key.split(',')[1]
			self.freqCounters[key]['nc_operator'] = self.getncArfcnComp(arfcn)			

	def to_csv_sccounter(self,dir):
		if dir == '' : 
			filename = self.mro.filename + '.sccounter'
		else :
			filename = os.path.join(dir,os.path.basename(self.mro.filename)+ '.sccounter')
		with open(filename,'w') as f:
			for k ,v in self.scCounters.items():
				line = "%s,%s,%s," % (self.mro.startTime, self.mro.EnodebId, k)
				line = line + ','.join([str(v[counter]) \
					if counter in  v else 'NIL' for counter in SC_COUNTER_LIST])
				line = line + ',' + self.mro.startTime[:self.mro.startTime.find('T')]
				f.write(line+'\n')
		if os.path.isfile(filename):
			os.rename(filename,filename+'.csv')
			filename=filename+'.csv'
		return filename

	def to_csv_nccounter(self,dir):
		if dir == '' : 
			filename = self.mro.filename + '.nccounter'
		else :
			filename = os.path.join(dir,os.path.basename(self.mro.filename)+ '.nccounter')
		with open(filename,'w') as f:
			for k ,v in self.ncCounters.items():
				line = "%s,%s,%s," % (self.mro.startTime, self.mro.EnodebId, k)
				line = line + ','.join([str(v[counter]) \
					if counter in v else 'NIL' for counter in NC_COUNTER_LIST])
				line = line + ',' + self.mro.startTime[:self.mro.startTime.find('T')]
				f.write(line+'\n')
		if os.path.isfile(filename):
			os.rename(filename,filename+'.csv')
			filename=filename+'.csv'
		return filename

	def to_csv_cmpcounter(self,dir):
		if dir == '' : 
			filename = self.mro.filename + '.cmpcounter'
		else :
			filename = os.path.join(dir,os.path.basename(self.mro.filename)+ '.cmpcounter')
		with open(filename,'w') as f:
			for k ,v in self.cmpCounters.items():
				line = "\"%s\",%s,%s," % (self.mro.startTime, self.mro.EnodebId, k)
				line = line + ','.join([str(v[counter]) \
					if counter in v else 'NIL' for counter in CMP_COUNTER_LIST])
				f.write(line+'\n')
		if os.path.isfile(filename):
			os.rename(filename,filename+'.csv')
			filename=filename+'.csv'
		return filename

	def to_csv_nccmpcounter(self,dir):
		if dir == '' : 
			filename = self.mro.filename + '.nccmpcounter'
		else :
			filename = os.path.join(dir,os.path.basename(self.mro.filename)+ '.nccmpcounter')
		with open(filename,'w') as f:
			for k ,v in self.cmpNcCounters.items():
				line = "%s,%s,%s," % (self.mro.startTime, self.mro.EnodebId, k)
				line = line + ','.join([str(v[counter]) \
					if counter in v else 'NIL' for counter in NC_CMPCOUNTER_LIST])
				f.write(line+'\n')
		if os.path.isfile(filename):
			os.rename(filename,filename+'.csv')
			filename=filename+'.csv'
		return filename


	def to_csv_freqcounter(self,dir):
		if dir == '' : 
			filename = self.mro.filename + '.freqcounter'
		else :
			filename = os.path.join(dir,os.path.basename(self.mro.filename)+ '.freqcounter')
		with open(filename,'w') as f:
			for k ,v in self.freqCounters.items():
				line = "%s,%s,%s," % (self.mro.startTime, self.mro.EnodebId, k)
				line = line + ','.join([str(v[counter]) \
					if counter in v else 'NIL' for counter in FREQ_COUNTER_LIST])
				f.write(line+'\n')
		if os.path.isfile(filename):
			os.rename(filename,filename+'.csv')
			filename=filename+'.csv'
		return filename

if __name__ == '__main__':
	a = counter()
	a.sumField('a')
	print(a['a'])
	a.sumField('a')
	print(a['a'])
	a.sumField('a',100)
	print(a['a'])
