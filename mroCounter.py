import os 

SC_COUNTER_LIST = ['sc_rsrp_valid_counter',
				   'sc_rsrp_counter',
				   'sc_ rsrp_ numerator',
				   'sc_overlapcoverage_counter',
				   'sc_rsrp_invalid_counter']

NC_COUNTER_LIST = ['nc_rsrp_ numerator',
				   'nc_rsrp_ counter',
				   'nc_rsrpdiff_numerator',
				   'nc_rsrp_diff3_counter',
				   'nc_rsrp_diff6_counter',
				   'nc_rsrp_diff12_counter',
				   'nc_rsrp_diff6_valid_counter']

class counter(dict):
	def sumField(self,fieldname,value=1):
		if self.has_key(fieldname):
			self[fieldname] = self[fieldname]+value
		else :
			self[fieldname] = value

class mroCounter(object):
	
	def __init__(self,mro):
		self.mro = mro
		self.EnodebId = mro.EnodebId
		self.scCounters = []
		self.ncCounters = []
		self.Counter()

	def _ValueNil(self,s,nil = False):
		try: 
			return float(s)-140
		except ValueError :
			return nil


	def Counter(self):
		self.scCounters = {}
		self.ncCounters = {}
		for v in self.mro.samples.itervalues() :
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
				self.scCounters[v.id].sumField('sc_ rsrp_ numerator',scrsrp)
			overlapcoverage = 0
			for ncinfo in v.NcInfo_list:
				key = '%s,%s,%s' % (v.id , ncinfo['LteNcEarfcn'], ncinfo['LteNcPci'])
				try:
					self.ncCounters[key].sumField('nc_rsrp_ counter')
				except KeyError:
					self.ncCounters[key] = counter()
					self.ncCounters[key].sumField('nc_rsrp_ counter')
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
			if overlapcoverage> 3 :
				self.scCounters[v.id].sumField('sc_overlapcoverage_counter')

	def to_csv_sccounter(self,dir):
		if dir == '' : 
			filename = self.mro.filename + '.sccounter.csv'
		else :
			filename = os.path.join(dir,os.path.basename(self.mro.filename)+ '.sccounter.csv')
		with open(filename,'w') as f:
			for k ,v in self.scCounters.iteritems():
				line = "%s,%s,%s," % (self.mro.startTime, self.mro.EnodebId, k)
				line = line + ','.join([str(v[counter]) \
					if v.has_key(counter) else 'NIL' for counter in SC_COUNTER_LIST])
				f.write(line+'\n')
		return filename

	def to_csv_nccounter(self,dir):
		if dir == '' : 
			filename = self.mro.filename + '.nccounter.csv'
		else :
			filename = os.path.join(dir,os.path.basename(self.mro.filename)+ '.nccounter.csv')
		with open(filename,'w') as f:
			for k ,v in self.ncCounters.iteritems():
				line = "%s,%s,%s," % (self.mro.startTime, self.mro.EnodebId, k)
				line = line + ','.join([str(v[counter]) \
					if v.has_key(counter) else 'NIL' for counter in NC_COUNTER_LIST])
				f.write(line+'\n')
		return filename

if __name__ == '__main__':
	a = counter()
	a.sumField('a')
	print a['a']
	a.sumField('a')
	print a['a']
	a.sumField('a',100)
	print a['a']