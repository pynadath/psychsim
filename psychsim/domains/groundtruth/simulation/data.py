# -*- coding: utf-8 -*-
import csv
import os.path
import random

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
