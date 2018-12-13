# -*- coding: utf-8 -*-
import csv
import os.path
import random

from psychsim.action import Action

likert = {5: [0.2,0.4,0.6,0.8,1.],
          7: [0.14,0.28,0.42,0.56,0.70,0.84,1.],
          }
reverseLikert = {'0': '0','0.2': '1','0.4': '2','0.6': '3','0.8': '4','1': '5'}

def toLikert(value,scale=5):
    for index in range(len(likert[scale])):
        if value < likert[scale][index]:
            return index+1
    else:
        return scale

def sampleNormal(mean,sigma,scale=5):
    mean = min(max(1,mean),scale)
    realValue = random.gauss(likert[scale][mean-1],likert[scale][sigma])
    return likert[scale][toLikert(realValue,scale)-1]

mapFromTandE = {'Actor’s distribution over ethnicGroup\'': ('Actors','ethnic_majority',reverseLikert),
                'Actor’s distribution over religion probability of majority\'':
                ('Actors','religious_majority',reverseLikert),
                '\'Actor’s distribution over religion probability of none\'':
                ('Actors','atheists',reverseLikert),
                'Actor’s distribution over age\'': ('Actors','age_max',None),
                'Actor’s distribution over children\'': ('Actors','children_max',None),
                'Actor’s distribution over owning a pet\'': ('Actors','pet_prob',reverseLikert),
                '\'Actor’s distribution over employed job_majority \'':
                ('Actors','job_majority',reverseLikert),
                '\'Actor’s distribution over employed job_minority \'':
                ('Actors','job_minority',reverseLikert),
                'Actor’s distribution over number of friendOf links\'': ('Actors','friends',None),
                'System’s resources\'': ('System','resources',reverseLikert),
                'Region’s risk distribution\'': ('Regions','risk_value',None),
                'Region’s security distribution\'': ('Regions','security_value',None),
                }

def readHurricanes(instance,run=0):
    """
    :returns: A list of attributes about the hurricanes so far
    """
    inFile = os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (instance),
                          'Runs','run-%d' % (run),'HurricaneTable.tsv')
    hurricanes = []
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            hurricane = int(row['Name'])
            if len(hurricanes) < hurricane:
                hurricanes.append({'Hurricane': hurricane,
                                   'Predicted Location': row['Location'],
                                   'Media Coverage': 'yes',
                                   'Actual Track': [],
                                   'Official Announcements': 'none',
                                   'Start': int(row['Timestep']),
                                   })
            elif row['Landed'] == 'yes':
                if row['Location'] == 'leaving':
                    hurricanes[-1]['End'] = int(row['Timestep'])
                else:
                    if not 'Actual Severity' in hurricanes[-1]:
                        hurricanes[-1]['Actual Severity'] = row['Category']
                    if len(hurricanes[-1]['Actual Track']) == 0 or \
                       hurricanes[-1]['Actual Track'][-1] != row['Location']:
                        hurricanes[-1]['Actual Track'].append(row['Location'])
    for record in hurricanes:
        record['Actual Track'] = ','.join(record['Actual Track'])
    if 'End' not in hurricanes[-1]:
        # Ignore partial hurricane track
        return hurricanes[:-1]
    else:
        return hurricanes

def readNetwork(instance,run=0):
    """
    :returns: The social networks in the given run
    """
    networks = {}
    inFile = os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (instance),
                          'Runs','run-%d' % (run),'RelationshipDataTable.tsv')
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            link = row['RelationshipType']
            if link not in networks:
                networks[link] = {}
            assert row['Directed'] == 'yes'
            try:
                networks[link][row['FromEntityId']].add(row['ToEntityId'])
            except KeyError:
                networks[link][row['FromEntityId']] = {row['ToEntityId']}
    return networks

def readParticipants(instance,run=0):
    """
    :returns: Mapping from participants to actor names for each survey
    """
    tables = {}
    if isinstance(instance,int):
        inFile = os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (instance),
                              'Runs','run-%d' % (run),'psychsim.log')
    else:
        # Assume it's a directory
        inFile = os.path.join(instance,'psychsim.log')
    with open(inFile,'r') as logfile:
        for line in logfile:
            if 'Participant' in line:
                elements = line.split()
                survey = elements[0]
                if not survey in tables:
                    tables[survey] = {}
                hurricane = int(elements[1][:-1])
                participant = int(elements[3][:-1])
                name = elements[4]
                if participant in tables[survey]:
                    assert name == tables[survey][participant],'Mismatch on paticipant %s in %s' % (participant,survey)
                else:
                    tables[survey][participant] = name
    return tables

def readActions(instance,run=0):
    """
    :returns: List of tables of actions by all agents
    """
    series = []
    inFile = os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (instance),
                          'Runs','run-%d' % (run),'RunDataTable.tsv')
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            if row['VariableName'][-6:] == 'action':
                t = int(row['Timestep'])
                while len(series) < t:
                    series.append({})
                name = row['EntityIdx']
                action = Action(row['Value'])
                series[t-1][name] = action
    return series[1:]

def readDeaths(instance,run=0):
    """
    :returns: a table of who died and when
    """
    deaths = {}
    inFile = os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (instance),
                          'Runs','run-%d' % (run),'RunDataTable.tsv')
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            if row['VariableName'] == 'Actor alive' and row['Value'] == 'False':
                if row['EntityIdx'] not in deaths:
                    deaths[row['EntityIdx']] = int(row['Timestep'])
    return deaths  

def readRunData(instance,run=0):
    inFile = os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (instance),
                          'Runs','run-%d' % (run),'RunDataTable.tsv')
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        data = list(reader)
    return data
