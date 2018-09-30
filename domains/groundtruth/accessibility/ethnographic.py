from argparse import ArgumentParser
import csv
import os
import pickle
import random
import sys

from psychsim.pwl.keys import *
from psychsim.world import World

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('instance',type=int,help='Instance to query')
    parser.add_argument('-o','--output',default='RequestEthnographic.tsv',help='Output filename')
    parser.add_argument('-r','--run',type=int,default=0,help='Run to query')
    parser.add_argument('-s','--samples',type=int,default=2,help='Number of people to survey')
    args = vars(parser.parse_args())

    root = os.path.join(os.path.dirname(__file__),'..')
    inFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                          'Runs','run-%d' % (args['run']),'RunDataTable.tsv')
    shelters = {}
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            if row['VariableName'] == 'Actor location':
                if row['Value'][:7] == 'shelter':
                    if not row['Value'] in shelters:
                        shelters[row['Value']] = {}
                    if not row['Timestep'] in shelters[row['Value']]:
                        shelters[row['Value']][row['Timestep']] = []
                    shelters[row['Value']][row['Timestep']].append(row['EntityIdx'])

    samples = []
    while len(samples) < args['samples'] and shelters:
        shelter = random.choice(list(shelters.keys()))
        day,occupants = random.choice(list(shelters[shelter].items()))
        samples.append({'Timestep': day,
                        'ParticipantID': len(samples)+1,
                        'Shelter': 'Region%s' % (shelter[-2:]),
                        'Alive': len(occupants),
                        'Dead': 0})
        del shelters[shelter]
    outFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                           'Runs','run-%d' % (args['run']),args['output'])
    fields = ['Timestep','ParticipantID','Shelter','Alive','Dead']
    with open(outFile,'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for record in samples:
            writer.writerow(record)
