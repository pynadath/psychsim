import csv
import os
import random
import sys

from psychsim.pwl.keys import *
from psychsim.world import World

def countAntisocial(world):
    newState = world.step(select=True)
    joint = world.explainAction(newState,level=1)
    count = 0
    for name,action in joint.items():
        assert len(action) == 1
        if action.first()['verb'] in ['takeResources','increaseRisk']:
            count += 1
    return count
    
instance = int(sys.argv[1])
inFile = os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),
                      'Runs','run-0','scenario.psy')
world = World(inFile)
actors = [actor for actor in world.agents.values() if actor.name[:5] == 'Actor' and
          actor.getState('alive').first()]
regions = [name for name in world.agents if name[:6] == 'Region']

preCount = countAntisocial(world)

world.step()

region = random.choice(regions)
residents = {actor for actor in actors if actor.getState('region') == region}
remove = set()
while len(remove) < len(residents) / 2:
    actor = random.choice(list(residents-remove))
    remove.add(actor.name)
    print(actor.getState(TURN))
    actor.setState('alive',False)

postCount = countAntisocial(world)
print(preCount,postCount)
