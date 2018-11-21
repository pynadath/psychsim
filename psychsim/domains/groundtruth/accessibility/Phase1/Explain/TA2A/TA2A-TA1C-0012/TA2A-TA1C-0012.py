"""
Research method category:
Survey
 
Specific question:
We will send a team of trained survey professionals across all 16 regions, to homes, shelters and hospitals and ask the following questions:
 
1. Unique ID corresponding to IDs in the ActorPostTable.tsv if possible.
  
2. Ask the following details if NOT able to link IDs (following question 1) or the respondent was NOT present in the original survey (as answered in the PostSurvey):
a. Age?
b. Children?
c. Ethnicity?
d. Religion?
e. Fulltime Job?
f. Gender?
g. Pets?
h. Residence?
i. If went to shelter; wealth at shelter?
j. How many hurricanes struck region this season?
k. How severe was the most severe hurricane this season?
 
3. Residency:
a. Are you a short-term resident, long-term resident, or a visitor to the overall area?
b. Are you a short-term resident, long-term resident, or a visitor to the specific region you in which you are currently residing?

4. Additional personal information:
a. Highest grade of schooling completed
b. Occupation
c. What is the size of your family and close interpersonal network — people whom you could call upon for significant support — within your region?
d. What are the number of your acquaintances within your region?
 
5. Prior season experience:
a. Have you experienced one or more hurricanes in prior seasons?
b. Were deaths involved in any previously experienced hurricanes in your region?
c. Were deaths involved in any previously experienced hurricanes among your family members or close interpersonal ties?
d. Were deaths involved in any previously experienced hurricanes among your acquaintances?
e. Were casualties involved in any previously experienced hurricanes in your region?
f. Were casualties involved in any previously experienced hurricanes among your family members or close interpersonal ties?
g. Were casualties involved in any previously experienced hurricanes among your acquaintances?
h. Did any experienced hurricanes from previous seasons pose a significant risk to myself and my family? (Response on a 1-5 scale, ranging from “strongly disagree” to “strongly agree”)
i. How many experienced hurricanes posed a significant risk to myself and my family?
j. Has any other natural disaster posed a significant risk to myself or my family? (Response on a 1-5 scale, ranging from “strongly disagree” to “strongly agree”)
k. Has any other circumstance posed a significant risk to myself or my family? (Response on a 1-5 scale, ranging from “strongly disagree” to “strongly agree”)
l. In your experience, has the government previously tended to over-or under-evacuate the regional population from hurricanes in previous seasons? (Response on a 1-5 scale, ranging from “under-evacuate” to “over-evacuate”)

6. Current experience:
a. Were casualties involved in any experienced hurricanes this season among your family members or close interpersonal ties?
b. Were casualties involved in any experienced hurricanes this season among your acquaintances?
 
7. Attitudes:
a. Should the government should intervene on behalf of my health and safety? (Response on a 1-5 scale, ranging from “I strongly do believe that the government should not intervene” to “I strongly believe that the government should intervene”)
b. When would I evacuate a hurricane? (Multiple choice / multiple answer: answer “Yes” as many as are applicable: “If there is a potential threat of some property damage”; “If there is a strong threat of some property damage”; “If there is a potential threat of some widespread property damage”; “If there is a strong threat of widespread property damage”; “If there is a potential threat of some injury (“casualty”)”; “If there is a strong threat of some injury(“casualty”)”; “If there is a potential threat of widespread injury (“casualty”)”; “If there is a strong threat of widespread injury(“casualty”)”;“If there is a potential threat of some death”; “If there is a strong threat of some death”; “If there is a potential threat of widespread death”; “If there is a strong threat of widespread death”)  
 
7. Description:
a. How does a hurricane pose a significant risk to myself and my family? [short answer, e.g., damage house and indirectly kill or injure; directly kill or injure; cut off from water and food that can inconvenience and passively injure; etc.]
b. If the government’s effort to evacuate the regional population were unsatisfying, why? [multiple choice: “They should have evacuated, but did not”; “they did not evaluate, but should have”; “their information about the hurricane was insufficient for them to make an effective evacuation decision”.]
 
8. Media:
a. Who reports deaths and casualties? (e.g., government, private news service).
b. Do you trust these reports?
 
Sampling strategy:
We seek this information on a paired sample with existing pre- and post-surveys. If these links are unavailable, then we seek a random sample of the population, of maximal size that we can afford.
 
Other applicable detail:
Not applicable
 
Research request identifier:
TA2A-TA1C-0012-RR
"""

from argparse import ArgumentParser
import csv
import logging
import os.path
import pickle
import random
import sys

from psychsim.pwl import *

from psychsim.domains.groundtruth.simulation.create import loadPickle
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
    parser.add_argument('-o','--output',default='TA2A-TA1C-0012.tsv',help='Output filename')
    parser.add_argument('-d','--debug',default='INFO',help='Level of logging detail')
    args = vars(parser.parse_args())
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logfile = '%s.log' % (os.path.splitext(__file__)[0])
    logging.basicConfig(level=level,filename=logfile)
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
                data[name][row['VariableName'][6:]] = row['Value']
            if row['VariableName'] == 'Actor alive' and row['Value'] == 'False' and row['EntityIdx'] not in dead:
                dead.add(name)
            elif row['VariableName'] == 'Actor health' and float(row['Value']) < 0.2:
                casualties.add(row['EntityIdx'])
            elif row['VariableName'] == 'Actor location' and row['Value'] == 'evacuated':
                evacuees.add(row['EntityIdx'])
            elif row['VariableName'] == 'Actor action':
                action = row['Value'].split('-')
                try:
                    actions[row['EntityIdx']][row['Timestep']] = action[1]
                except KeyError:
                    actions[row['EntityIdx']] = {row['Timestep']: action[1]}
            elif row['VariableName'] == 'Actor childrenHealth' and float(row['Value']) < 0.2:
                casualties.add('%s children' % (row['EntityIdx']))
            elif row['VariableName'] == 'ActorBeliefOfNature category':
                value = value2dist(row['Value'],row['Notes'],int)
                data[name]['Most Severe'] = max(value,data[name].get('Most Severe',0))
            elif row['VariableName'] == 'ActorBeliefOfRegion risk':
                try:
                    data[name]['B(region risk)'][row['Timestep']] = value2dist(row['Value'],row['Notes'],float)
                except KeyError:
                    data[name]['B(region risk)'] = {row['Timestep']: value2dist(row['Value'],row['Notes'],float)}
            elif row['VariableName'] == 'ActorBeliefOfActor risk':
                try:
                    data[name]['B(actor risk)'][row['Timestep']] = value2dist(row['Value'],row['Notes'],float)
                except KeyError:
                    data[name]['B(actor risk)'] = {row['Timestep']: value2dist(row['Value'],row['Notes'],float)}
            elif row['VariableName'] == 'ActorBeliefOfActor location':
                try:
                    data[name]['location'][row['Timestep']] = row['Value']
                except KeyError:
                    data[name]['location'] = {row['Timestep']: row['Value']}
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
        # 2a-i. Add demographics
        if not fieldSet:
            fields = list(record.keys())+sorted(demographics.keys())
        for label,feature in demographics.items():
            if feature in {'employed','pet'}:
                record[label] = {'False': 'no','True': 'yes'}[data[actor][feature]]
            elif feature == 'resources':
                record[label] = toLikert(float(data[actor][feature]))
            else:
                record[label] = data[actor][feature]
        # Survey items
        # 2j
        record['Hurricanes'] = len(hurricanes)
        if not fieldSet: fields.append('Hurricanes')
        # 2k
        record['Most Severe'] = data[actor]['Most Severe']
        if not fieldSet: fields.append('Most Severe')
        # 3a
        record['Area Residency'] = 'long-term resident'
        if not fieldSet: fields.append('Area Residency')
        # 3b
        record['Regional Residency'] = 'long-term resident'
        if not fieldSet: fields.append('Regional Residency')
        # 4c
        count = 1
        count += agent.kids
        friends = network['friendOf'].get(actor,set())
        neighbors = network['neighbor'].get(actor,set())
        count += len(friends & neighbors)
        field = 'Family & Network Size'
        record[field] = count
        if not fieldSet: fields.append(field)
        # 4d
        field = 'Acquaintances'
        record[field] = len(neighbors)
        if not fieldSet: fields.append(field)
        # 6a
        field = 'Family & Network Casualties'
        for name in {actor} | friends:
            if name in casualties or '%s children' in casualties:
                record[field] = 'yes'
                break
        else:
            record[field] = 'no'
        if not fieldSet: fields.append(field)
        # 6b
        field = 'Acquaintances Casualties'
        for name in neighbors:
            if name in casualties or '%s children' in casualties:
                record[field] = 'yes'
                break
        else:
            record[field] = 'no'
        if not fieldSet: fields.append(field)
        # 7a
        field = 'Government Intervention'
        record[field] = 5
        if not fieldSet: fields.append(field)
        # 7b
        answers = {
            'If there is a potential threat of some property damage': (2,True),
            'If there is a strong threat of some property damage': (2,False),
            'If there is a potential threat of some widespread property damage': (5,True),
            'If there is a strong threat of widespread property damage': (5,False),
            'If there is a potential threat of widespread injury ("casualty")': (2,True),
            'If there is a strong threat of widespread injury("casualty")': (2,False),
            'If there is a potential threat of some death': (4,True),
            'If there is a strong threat of some death': (4,False),
            'If there is a potential threat of widespread death': (5,True),
            'If there is a strong threat of widespread death': (5,False)
            }
        histogram = [{False: 0,True: 0} for value in range(5)]
        for t in actions[actor]:
            if int(t) > 1:
                prior = '%d' % (int(t)-1)
                if data[actor]['location'][prior] == agent.home:
                    # Only care when deciding from home
                    property = toLikert(data[actor]['B(region risk)'][prior])
                    injury = toLikert(data[actor]['B(actor risk)'][prior])
                    assert property == injury
                    histogram[property-1][actions[actor][t] == 'evacuate'] += 1
        alwaysEvac = None
        alwaysStay = None
        someEvac = None
        for level in range(len(histogram)):
            if histogram[level][False] == 0:
                if histogram[level][True] > 0 and alwaysEvac is None:
                    # Always evacuate
                    alwaysEvac = level
            elif histogram[level][True] == 0:
                # Always stay
                alwaysStay = level
            else:
                # Sometimes evacuate
                if someEvac is None:
                    someEvac = level
        print(histogram)
        print(alwaysStay,someEvac,alwaysEvac)
        for condition,threshold in answers.items():
            field = 'Evacuate: %s' % (condition)
            level,always = threshold
            if alwaysEvac is not None and alwaysEvac < level:
                record[field] = 'yes'
            elif not always and someEvac is not None and someEvac < level:
                record[field] = 'yes'
            else:
                record[field] = 'no'
            print(record[field],condition)
            if not fieldSet: fields.append(field)
        # 8a
        field = 'Media'
        record[field] = 'none'
        if not fieldSet: fields.append(field)
        # 8b
        field = 'Media Trust'
        record[field] = 'n/a'
        if not fieldSet: fields.append(field)
        if not fieldSet:
            fieldSet = True
        samples.append(record)
    with open(os.path.join(root,args['output']),'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for record in samples:
            writer.writerow(record)