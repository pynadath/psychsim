import csv
import os
import random
import sys

from psychsim.world import World

instance = int(sys.argv[1])
inFile = os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),
                      'Runs','run-0','scenario.psy')


samples = []
world = World(inFile)
actors = [actor for actor in world.agents.values() if actor.name[:5] == 'Actor' and \
          actor.getState('alive').first() and actor.getState('location').first()[:7] == 'shelter']
outFile = os.path.join(os.path.dirname(__file__),'Instances','Instance100001',
                       'Runs','run-0','AccessibilityDemo06Table')
fields = ['Actor','Shelter','Alive','Dead']
with open(outFile,'w') as csvfile:
    writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
    writer.writeheader()
    while len(samples) < 2:
        actor = random.choice(actors)
        actors.remove(actor)
        shelter = actor.getState('location').first()
        samples.append({'Actor': actor.name,
                        'Shelter': shelter})
        fellows = [actor for actor in world.agents.values() if actor.name[:5] == 'Actor' and \
                   actor.getState('location').first() == shelter]

        samples[-1]['Alive'] = len([actor for actor in fellows if \
                                    actor.getState('alive').first()])
        samples[-1]['Dead'] = len([actor for actor in fellows if \
                                   not actor.getState('alive').first()])
        writer.writerow(samples[-1])
