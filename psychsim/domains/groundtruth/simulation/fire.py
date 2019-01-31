import random
from psychsim.probability import Distribution
from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
	parser = accessibility.createParser(output='JoGT.tsv',seed=True,day=True)
	args = accessibility.parseArgs(parser)
	world = accessibility.loadFromArgs(args,world=True)['world']
	population = [name for name in world.agents if name[:5] == 'Actor']
	shelters = {name for name in world.agents if stateKey(name,'shelterPets') in world.variables}
	data = []
	samples = 40
	while len(data) < samples:
		# Choose participant
		name = random.choice(population)
		population.remove(name)
		agent = world.agents[name]
		record = {'Participant': len(data)+1}
		record.update(accessibility.getDemographics(agent))
		# Choose condition
		allowsPets = len(data) < samples//2
		record['Allows Pets'] = allowsPets
		model,belief = next(iter(agent.getBelief().items()))
		world.setState('Nature','category',3,belief)
		world.setState('Nature','phase','active',belief)
		world.setState('Nature','location',agent.home,belief)
		for shelter in shelters:
			key = stateKey(shelter,'shelterPets')
			assert key in belief
			world.setFeature(key,allowsPets,belief)
		# Get decision
		result = agent.decide(selection='distribution')
		V = {}
		for action in agent.getActions(belief):
			if action['verb'] in {'evacuate','stayInLocation'}:
				V[action['verb']] = agent.value(belief,action,model)['__EV__']
		action = Distribution(V,agent.getAttribute('rationality',model))
		record['Evacuate'] = accessibility.toLikert(action['evacuate'])
		data.append(record)
	accessibility.writeOutput(args,data,['Participant']+sorted(accessibility.demographics)+['Allows Pets','Evacuate'])