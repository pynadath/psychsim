import csv

import psychsim.probability
from psychsim.keys import *
from psychsim.pwl import *
from psychsim.action import powerset
from psychsim.reward import *
from psychsim.world import *
from psychsim.agent import Agent
from psychsim.ui.diagram import Diagram

world = World()
world.diagram = Diagram()

# Main agent
agent0 = world.addAgent('Resident')
world.diagram.setColor(agent0.name,'lightsalmon')
agent1 = world.addAgent('friend')
world.diagram.setColor(agent1.name,'lightyellow')

# States
health = world.defineState(agent0.name,'health',bool)
world.setFeature(health,True)

pet = world.defineState(agent0.name,'pet',bool)
rich = world.defineState(agent0.name,'wealth',float)
kids = world.defineState(agent0.name,'kids',bool)

location = world.defineState(agent0.name,'neighborhood',list,['sw','nw','ne','se','shelter','gone'])

# Shelter
shelter = world.addAgent('shelter')
world.diagram.setColor(shelter.name,'cornflowerblue')
allowPets = world.defineState(shelter.name,'allowPets',bool)
world.setFeature(allowPets,False)

risk = world.defineState(agent0.name,'risk',bool)
friendRisk = world.defineState(agent1.name,'risk',bool)
tree = makeTree(setToFeatureMatrix(risk,friendRisk))
world.setDynamics(risk,True,tree)
friendLeave = agent1.addAction({'verb': 'leave'})
world.setDynamics(risk,friendLeave,makeTree(noChangeMatrix(risk)))

# Actions and Dynamics

# A: Go to a shelter
actShelter = agent0.addAction({'verb':'shelter'})
# Effect on location
tree = makeTree(setToConstantMatrix(location,'shelter'))
world.setDynamics(location,actShelter,tree)
# Effect on my health
tree = makeTree(noChangeMatrix(health))
world.setDynamics(health,actShelter,tree)
# Effect on kids' health
tree = makeTree(noChangeMatrix(kids))
world.setDynamics(kids,actShelter,tree)
# Effect on pets' health
tree = makeTree({'if': trueRow(allowPets),
                 True: setTrueMatrix(pet),
                 False: setFalseMatrix(pet)})
world.setDynamics(pet,actShelter,tree)
# Effect on wealth
tree = makeTree({'if': thresholdRow(rich,0.5),
                 True: noChangeMatrix(rich),
                 False: scaleMatrix(rich,0.5)})
world.setDynamics(rich,actShelter,tree)
# Effect on risk
tree = makeTree(setFalseMatrix(risk))
world.setDynamics(risk,actShelter,tree)

# # A: Leave city
# actEvacuate = agent0.addAction({'verb': 'leaveCity'})
# # Effect on location
# tree = makeTree(setToConstantMatrix(location,'gone'))
# world.setDynamics(location,actEvacuate,tree)
# # Effect on my health
# tree = makeTree(noChangeMatrix(health))
# world.setDynamics(health,actEvacuate,tree)
# # Effect on kids' health
# tree = makeTree(noChangeMatrix(kids))
# world.setDynamics(kids,actEvacuate,tree)
# # Effect on pets' health (no hotels take pets)
# tree = makeTree(setFalseMatrix(pet))
# world.setDynamics(pet,actEvacuate,tree)

# A: Shelter in place
actStay = agent0.addAction({'verb': 'stay'})
# Effect on location
tree = makeTree(noChangeMatrix(location))
world.setDynamics(location,actStay,tree)
# Effect on my health
tree = makeTree({'if': trueRow(risk),
                  True: {'if': trueRow(rich),
                         True: {'distribution': [(setTrueMatrix(health),0.75),
                                                 (setFalseMatrix(health),0.25)]},
                         False: {'distribution': [(setTrueMatrix(health),0.25),
                                                  (setFalseMatrix(health),0.75)]}},
                  False: setTrueMatrix(health)})
world.setDynamics(health,actStay,tree)
# Effect on kids' health
tree = makeTree({'if': trueRow(kids),
                 True: {'if': trueRow(risk),
                        True: {'if': trueRow(rich),
                               True: {'distribution': [(setTrueMatrix(kids),0.75),
                                                       (setFalseMatrix(kids),0.25)]},
                               False: {'distribution': [(setTrueMatrix(kids),0.25),
                                                        (setFalseMatrix(kids),0.75)]}},
                        False: setTrueMatrix(kids)},
                 False: setFalseMatrix(kids)})
world.setDynamics(kids,actStay,tree)
# Effect on pets' health
tree = makeTree({'if': trueRow(pet),
                 True: {'if': trueRow(risk),
                        True: {'if': trueRow(rich),
                               True: {'distribution': [(setTrueMatrix(pet),0.75),
                                                       (setFalseMatrix(pet),0.25)]},
                               False: {'distribution': [(setTrueMatrix(pet),0.25),
                                                        (setFalseMatrix(pet),0.75)]}},
                        False: setTrueMatrix(pet)},
                 False: setFalseMatrix(pet)})
world.setDynamics(pet,actStay,tree)

world.setOrder([agent0.name])

# Reward
agent0.setReward(maximizeFeature(health),1.)
agent0.setReward(maximizeFeature(pet),1.)
agent0.setReward(maximizeFeature(rich),1.)
agent0.setReward(maximizeFeature(kids),1.)
# Decision-making parameters
agent0.setAttribute('horizon',1)
#agent0.setAttribute('selection','distribution')
#agent0.setAttribute('rationality',1.)

data = []
shelter = 0
for valueRich in [0.25,0.75]:
    world.setFeature(rich,valueRich)
    for valuePet in [True,False]:
        world.setFeature(pet,valuePet)
        for valueKid in [True,False]:
            world.setFeature(kids,valueKid)
            for valueLoc in ['sw','nw','ne','se']:
                world.setFeature(location,valueLoc)
                for valueFriend in [False]:
                    world.setFeature(friendRisk,valueFriend)
                    for valueRisk in [True,False]:
                        world.setFeature(risk,valueRisk)
                        entry = {'Rich': int(valueRich*100),'Pet': valuePet,'Children': valueKid,
                                 'Neighborhood': valueLoc,'Risk Perception': valueRisk}

                        nop = agent0.addAction({'verb': 'nop'})
                        result = world.step({agent0.name: nop},select=True)
                        agent0.actions.remove(nop)
                        result = world.step(select=False)
                        decision = result[0]['actions'][agent0.name] == actShelter
                        entry['Go to Shelter'] = decision
                        if decision:
                            shelter += 1
                        data.append(entry)
fields = ['Children','Neighborhood','Pet','Rich','Risk Perception','Go to Shelter']
with open('output0.csv','w') as csvfile:
    writer = csv.DictWriter(csvfile,fields,extrasaction='ignore')
    writer.writeheader()
    for record in data:
        writer.writerow(record)

                          
print float(shelter)/float(len(data))

world.save('scenario.psy')
