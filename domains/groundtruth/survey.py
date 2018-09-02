import csv
import os
import random
import sys

from psychsim.pwl.keys import *
from psychsim.world import World
from psychsim.domains.disaster.groundtruth.data import toLikert

instance = int(sys.argv[1])
inFile = os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),
                      'Runs','run-0','scenario.psy')
world = World(inFile)
actors = [actor for actor in world.agents.values() if actor.name[:5] == 'Actor' and \
          actor.getState('alive').first()]


outFile = os.path.join(os.path.dirname(__file__),'Instances','Instance100001',
                       'Runs','run-0','AccessibilityDemo05Table')
fields = ['Actor','Cat 5 Shelter','Cat 3 Shelter','Cat 1 Shelter']
with open(outFile,'w') as csvfile:
    writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
    writer.writeheader()
    samples = []
    while len(samples) < 10:
        actor = random.choice(actors)
        samples.append({'Actor': actor.name})
        actors.remove(actor)
        model = world.getModel(actor.name,world.state)
        assert len(model) == 1
        model = model.first()
        for category in [5,3,1]:
            actor.setBelief(stateKey('Nature','category'),category,model)
            actor.setBelief(stateKey('Nature','phase'),'approaching',model)
            actor.setBelief(stateKey('Nature','days'),5,model)
            actor.setBelief(stateKey('Nature','location'),'Region01',model)
            actor.setBelief(stateKey(actor.name,'location'),
                            actor.getState('region').first(),model)
            result = actor.decide(selection='distribution')
            for key in result:
                if key != 'policy':
                    result = result[key]
                    break
            total = 0.
            for action in result['action'].domain():
                if action['verb'] == 'moveTo':
                    if action['object'][:7] == 'shelter':
                        total += result['action'][action]
            samples[-1]['Cat %d Shelter' % (category)] = toLikert(total)
        writer.writerow(samples[-1])
