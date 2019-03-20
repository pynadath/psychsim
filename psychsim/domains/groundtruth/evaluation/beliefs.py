from psychsim.domains.groundtruth import accessibility
from psychsim.pwl.keys import *

if __name__ == '__main__':
	parser = accessibility.createParser(day=True)
	args = accessibility.parseArgs(parser)
	data = accessibility.loadRunData(args['instance'],args['run'],args['day'],True)
	demos = accessibility.readDemographics(data)
	same = {}
	different = {}
	for name in data:
		for key in data[name].get('__beliefs__',{}):
			agent = state2agent(key)
			feature = state2feature(key)
			if agent == 'Region':
				if feature == 'shelterRisk':
					agent = 'Region11'
				else:
					agent = demos[name]['Residence']
				realKey = stateKey(agent,feature)
			else:
				realKey = key
			storeKey = stateKey(agent[0],feature)
			for t,belief in data[name]['__beliefs__'][key].items():
				real = data[agent][realKey][t]
				if real != belief:
					if storeKey not in different:
						different[storeKey] = set()
					different[storeKey].add(name)
					break
			else:
				if storeKey not in same:
					same[storeKey] = set()
				same[storeKey].add(name)
	print(sorted(different.keys()))
	print(sorted(same.keys()))
