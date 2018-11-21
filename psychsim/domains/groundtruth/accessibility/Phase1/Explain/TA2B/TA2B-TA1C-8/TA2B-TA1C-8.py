"""
Research method category: Survey

Specific questions to be answered by the sampled households:
0. Ask the post hurricane demographics questions (age, children, ethnicity, fulltime job, gender, pets, region, religion)
For each hurricane "N" :
With regard to the decision to evacuate or seek shelter, do you agree or disagree with the following (please respond on a 0-5 scale, 0 is Strongly Disagree, 5 is Strongly Agree. If the question does not apply to you, e.g. if you do not have any pets, please answer NA):
1. I had access to transportation to evacuate.
2. I had access to transportation to a shelter.
3. My pet(s) would be accommodated at a shelter.
4. My pets(s) could accompany me if I evacuated.
5. I am aware of a shelter available in my region.
6. I did not have enough money to afford to evacuate.
7. My family would be safer at home than at a shelter.
8. Shelters in my area are too crowded to shelter everyone who needs it.

Sampling strategy:
50% random sample of all households in the area.

Other applicable detail:
Hypothesis: Our general hypothesis about this scenario right now is: The decision to evacuate is a cost benefit calculation conducted by the individual household. Benefits are reduced risk of injury. Costs are lost wages, logistical cost, lost property, and inability to shelter/transport pets. We hypothesize that families with children bear more logistical costs and are more risk averse to lost wages as well as injury. Sheltering is an alternate option to evacuation that has lower logistical cost. However, inadequate capacity or distance may be limiting the use of shelters. The outcome of interest is: casualties. This research request helps us test the part of the hypothesis related to pets, financial costs of evacuation, and perceived shelter availability. 

Research request identifier: 8shelter_finance_pet_survey
"""

from argparse import ArgumentParser
import csv
import logging
import os.path
import pickle
import random
import sys

from psychsim.pwl import *

from psychsim.domains.groundtruth.simulation.create import loadPickle,getConfig
from psychsim.domains.groundtruth.simulation.data import *
from psychsim.domains.groundtruth.simulation.execute import demographics

def value2dist(value,notes,cls):
    try:
        return cls(value)
    except ValueError:
        probs = [float(v) for v in value.split(',')]
        domain = [cls(el[6:-1]) for el in notes.split(',')]
        return sum([domain[i]*probs[i] for i in range(len(domain))])

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-i','--instance',type=int,default=24,help='Instance to query')
    parser.add_argument('-r','--run',type=int,default=1,help='Run to query')
    parser.add_argument('--sampling',type=float,default=0.1,help='% of actors to sample')
    parser.add_argument('--seed',type=int,default=1,help='Random number generator seed')
    parser.add_argument('-o','--output',default='TA2B-TA1C-8.tsv',help='Output filename')
    parser.add_argument('-d','--debug',default='INFO',help='Level of logging detail')
    args = vars(parser.parse_args())
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logfile = '%s.log' % (os.path.splitext(__file__)[0])
    logging.basicConfig(level=level,filename=logfile,filemode='w')
    random.seed(args['seed'])
    root = os.path.join(os.path.dirname(__file__),'..','..','..','..','..',
        'Instances','Instance%d' % (args['instance']),
        'Runs','run-%d' % (args['run']))
    hurricanes = readHurricanes(args['instance'],args['run'])
    network = readNetwork(args['instance'],args['run'])
    population = set()
    dead = set()
    casualties = set()
    childCasualties = set()
    evacuees = set()
    actions = {}
    beliefs = {}

    config = getConfig(args['instance'])
    world = loadPickle(args['instance'],args['run'])

    data = {}
    inFile = os.path.join(root,'RunDataTable.tsv')
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            name = row['EntityIdx']
            if row['VariableName'][:5] == 'Actor' and row['VariableName'][6:] in demographics.values():
                if name not in population:
                    population.add(name)
                    data[name] = {}
                    beliefs[name] = {}
            if row['VariableName'] == 'Actor alive' and row['Value'] == 'False' and row['EntityIdx'] not in dead:
                dead.add(name)
            elif row['VariableName'][:6] == 'Actor ':
                feature = row['VariableName'][6:]
                key = stateKey(name,feature)
                if key in world.variables:
                    if world.variables[key]['domain'] is bool:
                        if row['Value'] == 'True':
                            value = True
                        else:
                            value = False
                    elif world.variables[key]['domain'] is float:
                        value = float(row['Value'])
                    elif world.variables[key]['domain'] is int:
                        value = int(row['Value'])
                    else:
                        value = row['Value']
                    try:
                        data[name][feature][int(row['Timestep'])] = value
                    except KeyError:
                        data[name][feature] = {int(row['Timestep']): value}
            elif row['VariableName'][:13] == 'ActorBeliefOf':
                if ',' in row['Value']:
                    value = value2dist(row['Value'],row['Notes'],float)
                else:
                    value = row['Value']
                try:
                    beliefs[name][row['VariableName'][13:]][int(row['Timestep'])] = value
                except KeyError:
                    beliefs[name][row['VariableName'][13:]] = {int(row['Timestep']): value}
    pool = population - dead
    samples = []
    numSamples = args['sampling']*len(pool)
    fieldSet = False

    while len(samples) < numSamples:
        # Choose survey participant
        actor = random.choice(list(pool))
        pool.remove(actor)
        record = {'Participant ID': len(samples)+1}
        logging.info('Participant %d: %s' %(record['Participant ID'],actor))
        agent = world.agents[actor]
        # 20. Add demographics
        if not fieldSet:
            fields = list(record.keys())+sorted(demographics.keys())
        for label,feature in demographics.items():
            if feature in {'employed','pet'}:
                record[label] = {False: 'no',True: 'yes'}[data[actor][feature][1]]
            elif feature == 'resources':
                record[label] = toLikert(float(data[actor][feature][1]))
            else:
                record[label] = data[actor][feature][1]
        # Survey items
        for hurricane in hurricanes:
            # 1. I had access to transportation to evacuate.
            field = 'Hurricane %d: Evacuation Transport' % (hurricane['Hurricane'])
            for action in agent.actions:
                if action['verb'] == 'evacuate':
                    record[field] = 5
                    evacuation = action
                    break
            else:
                evacuation = None
                record[field] = 1
            if not fieldSet: fields.append(field)
            # 2. I had access to transportation to a shelter.
            field = 'Hurricane %d: Shelter Transport' % (hurricane['Hurricane'])
            shelters = set()
            for action in agent.actions:
                if action['verb'] == 'moveTo' and action['object'][:7] == 'shelter':
                    shelters.add('Region%s' % (action['object'][7:]))
            if shelters:
                record[field] = 5
            else:
                record[field] = 1
            if not fieldSet: fields.append(field)
            # 3. My pet(s) would be accommodated at a shelter.
            field = 'Hurricane %d: Shelter Pets' % (hurricane['Hurricane'])
            for region in shelters:
                if world.getState(region,'shelterPets').first():
                    # An available shelter accommodates pets
                    record[field] = 5
                    break
            else:
                record[field] = 1
            if not fieldSet: fields.append(field)
            # 4. My pets(s) could accompany me if I evacuated.
            field = 'Hurricane %d: Evacuate Pets' % (hurricane['Hurricane'])
            record[field] = 5
            if not fieldSet: fields.append(field)
            # 5. I am aware of a shelter available in my region.
            field = 'Hurricane %d: Shelter Available' % (hurricane['Hurricane'])
            if shelters:
                record[field] = 5
            else:
                record[field] = 1
            if not fieldSet: fields.append(field)
            # 6. I did not have enough money to afford to evacuate.
            field = 'Hurricane %d: Evacuation Unaffordable' % (hurricane['Hurricane'])
            if evacuation:
                cost = config.getint('Actors','evacuation_cost')
                if cost > 0:
                    cost = likert[5][cost-1]
                    for day in range(hurricane['Start'],hurricane['End']+1):
                        try:
                            value = toLikert(cost/float(beliefs[actor]['Actor resources'][day]))
                        except ZeroDivisionError:
                            value = 1
                        record[field] = min(value,record.get(field,6))
                    record[field] = max(1,record[field]-1)
                else:
                    record[field] = 1
            else:
                record[field] = 3
            if not fieldSet: fields.append(field)
            # 7. My family would be safer at home than at a shelter.
            field = 'Hurricane %d: Safer at home' % (hurricane['Hurricane'])
            if shelters:
                home = sum([float(beliefs[actor]['Region risk'][day]) for day in range(hurricane['Start'],hurricane['End']+1)])
                shelter = sum([float(beliefs[actor]['Region shelterRisk'][day]) for day in range(hurricane['Start'],hurricane['End']+1)])
                record[field] = toLikert(shelter/(home+shelter))
            else:
                record[field] = 3
            if not fieldSet: fields.append(field)
            # 8. Shelters in my area are too crowded to shelter everyone who needs it.
            field = 'Hurricane %d: Shelters crowded' % (hurricane['Hurricane'])
            record[field] = 1
            if not fieldSet: fields.append(field)
        if not fieldSet:
            fieldSet = True
        samples.append(record)
    with open(os.path.join(root,args['output']),'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for record in samples:
            writer.writerow(record)