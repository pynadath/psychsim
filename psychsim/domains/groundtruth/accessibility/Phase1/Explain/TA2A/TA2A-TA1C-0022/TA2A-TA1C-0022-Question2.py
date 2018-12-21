from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
	parser = accessibility.createParser(output='TA2A-TA1C-0022-Question2.tsv')
	args = accessibility.parseArgs(parser)
	data = accessibility.loadFromArgs(args,actions=True)
	fields = ['Timestep','Region']
	output = [{'Timestep': t+1, 'Region': data['actions'][t]['System']['object']} for t in range(len(data['actions'])) if 'System' in data['actions'][t]]
	accessibility.writeOutput(args,output,fields)
