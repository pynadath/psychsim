import csv
import os
import random
import sys

from psychsim.pwl.keys import *

from psychsim.world import World

instance = int(sys.argv[1])
inFile = os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),
                      'Runs','run-0','scenario.psy')


mapping = {'childrenHealth': 'children',
           'resources': 'finances'}

samples = []
world = World(inFile)
actors = [actor for actor in world.agents.values() if actor.name[:5] == 'Actor' and \
          actor.getState('alive').first()]
outFile = os.path.join(os.path.dirname(__file__),'Instances','Instance100001',
                       'Runs','run-0','AccessibilityDemo07Table')
fields = ['Actor','Factor1','Factor2','Factor3']
with open(outFile,'w') as csvfile:
    writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
    writer.writeheader()
    while len(samples) < 10:
        actor = random.choice(actors)
        actors.remove(actor)
        samples.append({'Actor': actor.name})
        model = world.getModel(actor.name).first()
        R = actor.getAttribute('R',model)
        assert R.isLeaf()
        R = R.children[None][makeFuture(rewardKey(actor.name))]
        weights = [(R[key],key) for key in R.keys() if key != CONSTANT]
        weights.sort()
        weights.reverse()
        for index in range(min(len(weights),3)):
            feature = state2feature(weights[index][1])
            samples[-1]['Factor%d' % (index+1)] = 'my %s' % (mapping.get(feature,feature))
        writer.writerow(samples[-1])
