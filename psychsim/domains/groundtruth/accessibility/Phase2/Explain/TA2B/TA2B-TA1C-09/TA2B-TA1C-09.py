from argparse import ArgumentParser
import csv
import logging
import os.path
import sys

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.domains.groundtruth.simulation import survey

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    cmd = vars(parser.parse_args())
    defined = False
    variables = []
    for instance,args in accessibility.instanceArgs('Phase2','Explain'):
        if cmd['debug']:
            print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        world = accessibility.unpickle(instance)
        states = {}
        participants = accessibility.readParticipants(args['instance'],args['run'],splitHurricanes=True)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        actors = accessibility.getLivePopulation(args,world,states,args['span'])
        output = []
        # Grab timesteps from previous paired survey
        timesteps = {}
        with open(os.path.join(os.path.dirname(__file__),'..','TA2B-TA1C-02','Instances','Instance%d' % (instance),'Runs','run-0',
            'TA2B-TA1C-2-Post.tsv'),'r') as csvfile:
            reader = csv.DictReader(csvfile,delimiter='\t')
            for row in reader:
                partID = int(row['Participant'])
                if partID not in timesteps:
                    timesteps[partID] = {}
                hurricane = int(row['Hurricane'])
                timesteps[partID][hurricane] = int(row['Timestep'])
        for partID in timesteps:
            name = participants['Post-survey %d' % (min(timesteps[partID]))][partID]
            health = [value.first() for value in accessibility.getInitialState(args,name,'health',world,states,
                (1,actors[name] if actors[name] else args['span']))]
            for hurricaneID,t in timesteps[partID].items():
                hurricane = hurricanes[hurricaneID-1]
                assert hurricane['Hurricane'] == hurricaneID
                logging.info('Participant %d Hurricane %d: %s' % (partID,hurricane['Hurricane'],name))
                agent = world.agents[name]
                record = {}
                output.append(record)
                var = 'Participant'
                if not defined:
                    variables.append({'Name': var,'Values':'[1+]','VarType': 'fixed','DataType': 'Integer'})
                record[var] = partID
                var = 'Hurricane'
                if not defined:
                    variables.append({'Name': var,'Values':'[1+]','DataType': 'Integer'})
                record[var] = hurricane['Hurricane']
                var = 'Timestep'
                if not defined:
                    variables.append({'Name': var,'Values':'[1+]','DataType': 'Integer'})
                record[var] = t
                var = 'Last Poor Health Began'
                if not defined:
                    variables.append({'Name': var,'Values':'[1+]','DataType': 'Integer','Notes': 'Q1. NA if no such episode occurred'})
                injuries = [i+1 for i in range(len(health)) if health[i] < 0.2 and i < t]
                if injuries:
                    index = len(injuries) - 1
                    record[var] = injuries[index]
                    while injuries[index-1] == record[var]-1:
                        # Find beginning of this episode
                        index -= 1
                        record[var] = injuries[index]
                    assert record[var] <= t
                else:
                    record[var] = 'NA'
                var = 'Last Poor Health at Shelter'
                if not defined:
                    variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': 'Q3. NA if no such episode occurred'})
                if injuries:
                    location = accessibility.getInitialState(args,name,'location',world,states,record['Last Poor Health Began']).first()
                    record[var] = 'yes' if location[:7] == 'shelter' else 'no'
                else:
                    record[var] = 'NA'
                var = 'Last Poor Health Ended'
                if not defined:
                    variables.append({'Name': var,'Values':'[1+],ongoing','DataType': 'Integer','Notes': 'Q4. NA if no such episode occurred'})
                if injuries:
                    if injuries[-1] == t:
                        record[var] = 'ongoing'
                    else:
                        record[var] = injuries[-1] + 1
                        assert record[var] <= t
                else:
                    record[var] = 'NA'
                if cmd['debug']:
                    print(record)
                if not defined:
                    if not cmd['debug']:
                        accessibility.writeVarDef(os.path.dirname(__file__),variables)
                    defined = True
        if not cmd['debug']:
            accessibility.writeOutput(args,output,[var['Name'] for var in variables],'%s.tsv' % (os.path.splitext(os.path.basename(__file__))[0]),
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
