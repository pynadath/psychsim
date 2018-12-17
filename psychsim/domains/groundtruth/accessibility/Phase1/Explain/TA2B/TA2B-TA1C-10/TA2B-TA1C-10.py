"""


**Research method category**: Survey, Observational Data


**Specific question**:
We would like to collect observational data and survey data on the current population for the remainder of the current hurricane season and the entirety of the upcoming hurricane season. 


Observational Data:


1. PopulationTable: These are statistics aggregated over the entire urban area, broken down by
“Timstep”.
a. Deaths: cumulative number of deaths as of the given day
b. Casualties: current number of residents who are either injured (requiring hospitalization)
or dead on the given day
c. Evacuated: number of residents who have left the area completely and have not returned
by the given day
d. Sheltered: number of residents at a public shelter on the given day


2. RegionalTable: These are statistics for each day broken down by each region and day
(“Timestep”).
a. Deaths: cumulative number of region’s residents who have died this season as of the
given day
b. Casualties: number of region’s residents who are either injured (requiring hospitalization)
or dead on the given day
c. Sheltered: number of region’s residents at a public shelter on the given day.


3. HurricaneTable: Entries made for only those days (i.e., “Timestep”) when a hurricane is present:
a. Hurricane: Identifying number of hurricane (first hurricane of the first season is 1, if the last hurricane of the first season is N then the first hurricane of the second season is N+1).
b. Category: The category of the current hurricane (1-5 scale, with 5 being the most severe)
c. Location: The region where the hurricane is projected to make landfall (if it has not yet
landed) or where it is currently centered (if it has). If the hurricane has moved out of the
area, the location will be given as “leaving”.
d. Landed: Whether or not (“yes” or “no”) this hurricane has made landfall.


Survey Data: We expect the firm conducting the pre- and post- hurricane surveys to use a consistent set of linked participant ID’s. We want the recruitment for these surveys to follow the pairing approach described in Sampling Strategy. 


4. ActorPreTable: Actor-level survey, conducted when a hurricane is approaching:
a. Participant: ID for participant.
b. Hurricane: Identifying number of hurricane (see numbering notes in HurricaneTable).
c. Demographics: gender, age, ethnicity (either majority or minority), religion (either
majority, minority, or none), number of children, wealth (on a 0-5 scale, increasing
from 0 to 5), pet owned or not, fulltime job or not, region of residence
d. Survey questions:
i. At Shelter: Are you currently staying at a public shelter?
ii. Evacuated: Are you currently residing outside the area?
iii. Severity: The approaching hurricane poses a significant risk to the area.
(Response on a 1-5 scale, ranging from “strongly disagree” to “strongly agree”)
iv. LastSheltered: When did you last stay in the public shelter at any point in response to the previous hurricane (we are asking for the date you left for the shelter)?
v. LastEvacuated: When did you last evacuate in response to a hurricane (where evacuate is defined as leaving the area to reside elsewhere as a result of the hurricane and we are asking for the date you left)?


5. ActorPostTable: Actor-level survey, conducted after a hurricane has passed:
a. Participant: ID for participant.
b. Hurricane: Identifying number of hurricane (see numbering notes in HurricaneTable).
c. Demographics: gender, age, ethnicity (either majority or minority), religion (either
majority, minority, or none), number of children, wealth (on a 0-5 scale, increasing
from 0 to 5), pet owned or not, fulltime job or not, region of residence
d. Survey questions:
i. At shelter: Did you stay at a public shelter at any point during the previous
hurricane?
ii. Evacuated: Did you evacuate the area at any point during the previous hurricane?
iii. Injured: Did you suffer any injuries during the previous hurricane?
iv. Risk: The previous hurricane posed a significant risk to myself and my family.
(Response on a 1-5 scale, ranging from “strongly disagree” to “strongly agree”)
v. Dissatisfaction: The government response was fair and adequate. (Response on a
1-5 scale, ranging from “strongly disagree” to “strongly agree”)


**Sampling strategy**: For each of the surveys conducted either before or after a hurricane, sample 10% of the total population. Use an approach where respondents are revisited for the following hurricane. For example in the post-hurricane surveys, after hurricane 1 we first try to resample the same respondents for hurricane 2, if some of those respondents decline to respond for hurricane 2, we look for new respondents until we reach our percent of the population target. After we have two _consecutive_ post-hurricane surveys from the same household, we move on to the not yet surveyed potential respondents in the population, in each case trying to create a pairing of a post-hurricane response in hurricane N and N+1. Once all households that are willing to be surveyed have filled 2 consecutive surveys, start over with a fully random sample. 


**Other applicable detail**: None


**Research request identifier**: 10currentareamoretime

"""

from argparse import ArgumentParser
import csv
import logging
import os.path
import pickle
import random
import sys

from psychsim.probability import Distribution
from psychsim.pwl import *

from psychsim.domains.groundtruth.simulation.create import loadPickle,getConfig
from psychsim.domains.groundtruth.simulation.data import *
from psychsim.domains.groundtruth.simulation.execute import demographics

def verifySurveyData(instance,run,augment=False):
    root = os.path.join(os.path.dirname(__file__),'..','..','..','..','..',
        'Instances','Instance%d' % (instance),'Runs','run-%d' % (run))
    mapping = readParticipants(instance,run)
    actions = readActions(instance,run)
    hurricanes = readHurricanes(instance,run)
    deaths = readDeaths(instance,run)
    change = False
    inFile = os.path.join(root,'ActorPreNewTable.tsv')
    actors = {}
    data = []
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        fields = list(reader.fieldnames)
        for row in reader:
            data.append(row)
            name = mapping['ActorPreNewTable'][int(row['Participant'])]
            if name in deaths:
                # Make sure actor is alive
                assert deaths[name] >= int(row['Timestep'])
            actors[name] = actors.get(name,[])+[int(row['Hurricane'])]
            behavior = {t+1: actions[t][name] for t in range(int(row['Timestep'])-1) if name in actions[t]}
            location = 'home'
            for t in sorted(behavior):
                if behavior[t]['verb'] == 'evacuate':
                    location = 'evacuated'
                elif behavior[t]['verb'] == 'moveTo':
                    location = behavior[t]['object']
            if location == 'evacuated':
                assert row['Evacuated'] == 'yes'
            else:
                assert row['Evacuated'] == 'no'
            if location[:7] == 'shelter':
                assert row['At Shelter'] == 'yes'
            else:
                assert row['At Shelter'] == 'no'
            matches = [t for t in sorted(behavior) if behavior[t]['verb'] == 'moveTo' and behavior[t]['object'][:7] == 'shelter']
            if matches:
                last = max(matches)
                if int(row['LastSheltered']) == last + 1 and last <= 82:
                    # Hack to catch now-fixed bug in patching I24R1 pickle file
                    print('%s (%s) responded %s, despite sheltering %s' % (name,row['Participant'],row['LastSheltered'],matches))
                    row['LastSheltered'] = last
                    change = True
                else:
                    assert int(row['LastSheltered']) == max(matches)
            else:
                assert row['LastSheltered'] == 'NA'
            matches = [t for t in sorted(behavior) if behavior[t]['verb'] == 'evacuate']
            if matches:
                last = max(matches)
                if int(row['LastEvacuated']) == last + 1 and last <= 82:
                    # Hack to catch now-fixed bug in patching I24R1 pickle file
                    print('%s (%s) responded %s, despite evacuating %s' % (name,row['Participant'],row['LastEvacuated'],matches))
                    row['LastEvacuated'] = last
                    change = True
                else:
                    assert int(row['LastEvacuated']) == max(matches),'%s (%s) responded %s, despite behavior %s' % (name,row['Participant'],row['LastEvacuated'],matches)
            else:
                assert row['LastEvacuated'] == 'NA'
    if change:
        with open(inFile,'w') as csvfile:
            writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
            writer.writeheader()
            for row in data:
                writer.writerow(row)
#    for name in sorted(actors):
#        print(name,actors[name])
    actors.clear()
    runData = readRunData(instance,run)
    data = []
    change = False
    inFile = os.path.join(root,'ActorPostNewTable.tsv')
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        fields = list(reader.fieldnames)
        for row in reader:
            data.append(row)
            name = mapping['ActorPostNewTable'][int(row['Participant'])]
            actors[name] = actors.get(name,[])+[int(row['Hurricane'])]
            behavior = {t+1: actions[t][name] for t in range(int(row['Timestep'])-1) if name in actions[t]}
            evacuated = False
            sheltered = False
            hurricane = hurricanes[int(row['Hurricane'])-1]
            for t in range(hurricane['Start'],hurricane['End']):
                if t in behavior and behavior[t]['verb'] == 'evacuate':
                    assert row['Evacuated Previous Hurricane'] == 'yes'
                    evacuated = True
                    break
            for t in range(hurricane['Start'],hurricane['End']):
                if t in behavior and behavior[t]['verb'] == 'moveTo' and behavior[t]['object'][:7] == 'shelter':
                    assert row['At Shelter Previous Hurricane'] == 'yes'
                    sheltered = True
                    break
            location = 'home'
            for t in sorted(behavior):
                if behavior[t]['verb'] == 'evacuate':
                    location = 'evacuated'
                elif behavior[t]['verb'] == 'moveTo':
                    location = behavior[t]['object']
                if t in range(hurricane['Start'],hurricane['End']+1):
                    if location == 'evacuated':
                        evacuated = True
                        if row['Evacuated Previous Hurricane'] != 'yes':
                            print('%s (%s) was still evacuated on day %s (hurricane %d, %d-%d)' % \
                                (name,row['Participant'],t,hurricane['Hurricane'],hurricane['Start'],hurricane['End']))
                            change = True
                            row['Evacuated Previous Hurricane'] = 'yes'
                    elif location[:7] == 'shelter':
                        assert row['At Shelter Previous Hurricane'] == 'yes','%s (%s) was sheltered on day %s (hurricane %d, %d-%d)' % (name,row['Participant'],t,hurricane['Hurricane'],hurricane['Start'],hurricane['End'])
                        sheltered = True
                elif t > hurricane['End']:
                    break
            if not evacuated:
                assert row['Evacuated Previous Hurricane'] == 'no','%s (T%s, P%s) never evacuated during hurricane %d (%d-%d)' \
                    % (name,row['Timestep'],row['Participant'],hurricane['Hurricane'],hurricane['Start'],hurricane['End'])
            if not sheltered:
                assert row['At Shelter Previous Hurricane'] == 'no','%s (T%s, P%s) never sheltered during hurricane %d (%d-%d)' \
                    % (name,row['Timestep'],row['Participant'],hurricane['Hurricane'],hurricane['Start'],hurricane['End'])
            if augment:
                if 'Assistance Previous Hurricane' not in row:
                    change = True
                    if 'Assistance Previous Hurricane' not in fields:
                        fields.append('Assistance Previous Hurricane')
                    govt = [actions[t]['System'] for t in range(hurricane['Start'],hurricane['End'])]
                    count = len([a for a in govt if a['object'] == row['Residence']])
                    row['Assistance Previous Hurricane'] = toLikert(float(count)/float(len(govt)))
                if 'Injury Child Previous Hurricane' not in row:
                    change = True
                    if 'Injury Child Previous Hurricane' not in fields:
                        fields.append('Injury Child Previous Hurricane')
                    values = [float(rec['Value']) for rec in runData 
                        if rec['VariableName'] == 'Actor childrenHealth' and rec['EntityIdx'] == name and 
                            int(rec['Timestep']) >= hurricane['Start'] and int(rec['Timestep']) <= hurricane['End']]
                    if values:
                        if min(values) < 0.2:
                            row['Injury Child Previous Hurricane'] = 1
                        else:
                            row['Injury Child Previous Hurricane'] = 0
                    else:
                        row['Injury Child Previous Hurricane'] = 0
                if 'Property Previous Hurricane' not in row:
                    change = True
                    if 'Property Previous Hurricane' not in fields:
                        fields.append('Property Previous Hurricane')
                    values = [float(rec['Value']) for rec in runData 
                        if rec['VariableName'] == 'Region risk' and rec['EntityIdx'] == row['Residence'] and 
                            int(rec['Timestep']) >= hurricane['Start'] and int(rec['Timestep']) <= hurricane['End']]
                    row['Property Previous Hurricane'] = toLikert(max(values))
    if change:
        with open(inFile,'w') as csvfile:
            writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
            writer.writeheader()
            for row in data:
                writer.writerow(row)
#    for name in sorted(actors):
#        print(name,actors[name])

def value2dist(value,notes,cls):
    try:
        return cls(value)
    except ValueError:
        probs = [float(v) for v in value.split(',')]
        domain = [cls(el[6:-1]) for el in notes.split(',')]
        value = Distribution({domain[i]: probs[i] for i in range(len(domain))})
        return value
#        return sum([domain[i]*probs[i] for i in range(len(domain))])

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-i','--instance',type=int,default=24,help='Instance to query')
    parser.add_argument('-r','--run',type=int,default=1,help='Run to query')
    parser.add_argument('-t','--test',action='store_true',help='Run in verification mode')
    parser.add_argument('-d','--debug',default='INFO',help='Level of logging detail')
    args = vars(parser.parse_args())
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logfile = '%s.log' % (os.path.splitext(__file__)[0])
    logging.basicConfig(level=level,filename=logfile,filemode='w')

    if args['test']:
        verifySurveyData(args['instance'],args['run'])
    else:
        root = os.path.join(os.path.dirname(__file__),'..','..','..','..','..',
            'Instances','Instance%d' % (args['instance']),
            'Runs','run-%d' % (args['run']))
        world = loadPickle(args['instance'],args['run'])
        world.history = {}
        timestep = None
        inFile = os.path.join(root,'RunDataTable.tsv')
        with open(inFile,'r') as csvfile:
            reader = csv.DictReader(csvfile,delimiter='\t')
            for row in reversed(list(reader)):
                name = row['EntityIdx']
                var = row['VariableName']
                elements = var.split()
                if timestep is None:
                    timestep = row['Timestep']
                elif row['Timestep'] != timestep:
                    if len(elements) == 2 and elements[1] == 'action':
                        t = int(row['Timestep']) - 1
                        if t > 0 and t not in world.history:
                            world.history[t] = {} 
                        world.history[t][name] = Action(row['Value'])
                    continue
                if len(elements) == 1:
                    if elements[0][:13] == 'ActorBeliefOf':
                        cls = '%s%s' % (elements[0][:13],WORLD)
                        feature = elements[0][13:]
                    else:
                        cls = WORLD
                        name = WORLD
                        feature = elements[0]
                else:
                    assert len(elements) == 2,var
                    cls,feature = elements
                if cls[:13] == 'ActorBeliefOf':
                    agent = world.agents[name]
                    model = world.getModel(name,world.state).first()
                    beliefs = agent.models[model]['beliefs']
                    cls = cls[13:]
                    if cls == 'Actor':
                        cls = name
                    elif cls == 'Region':
                        if feature == 'risk':
                            cls = agent.home
                        else:
                            # Assumes only one shelter!
                            assert feature == 'shelterRisk'
                            for cls in [n for n in world.agents if n[:6] == 'Region']:
                                if stateKey(cls,feature) in world.variables:
                                    break
                    else:
                        assert cls in {WORLD,'System','Nature'},'Unknown agent type: %s' %(cls)
                    key = stateKey(cls,feature)
                    assert key in world.variables,'Unknown variable: %s' % (key)
                    if ',' in row['Value']:
                        assert world.variables[key]['domain'] in [float,int]
                        value = value2dist(row['Value'],row['Notes'],world.variables[key]['domain'])
                    elif world.variables[key]['domain'] is bool:
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
                    world.setFeature(key,value,beliefs)
                else:
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
                        world.setFeature(key,value)
                    else:
                        assert feature == 'action','Unknown variable: %s' % (var)
        with open(os.path.join(root,'scenario%s.pkl' % (timestep)),'wb') as outfile:
            pickle.dump(world,outfile)