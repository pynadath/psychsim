from argparse import ArgumentParser
import csv
import logging
import os.path
import random
import sys

from psychsim.pwl import *
from psychsim.action import makeActionSet
from psychsim.domains.groundtruth import accessibility
from psychsim.domains.groundtruth.simulation import survey

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    reqNum = int(os.path.splitext(os.path.basename(__file__))[0].split('-')[2])
    team = os.path.splitext(os.path.basename(__file__))[0].split('-')[0]
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    cmd = vars(parser.parse_args())
    variables = {}
    for instance,args in accessibility.instanceArgs('Phase2','Explain'):
        if args['instance'] < 101: continue
        if cmd['debug']:
            print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        world = accessibility.unpickle(instance)
        states = {}
        participants = accessibility.readParticipants(args['instance'],args['run'],splitHurricanes=True)
        if len(participants) == 0:
            with open(os.path.join(os.path.dirname(__file__),'participant.log'),'r') as csvfile:
                for line in csvfile:
                    if line[:4] == 'INFO':
                        elements = line.split()
                        participants[int(elements[1])] = elements[2][1:-1]
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
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
            try:
                name = participants['Post-survey %d' % (min(timesteps[partID]))][partID]
            except KeyError:
                try:
                    name = participants[partID]
                except KeyError:
                    continue
            for hurricaneID,t in timesteps[partID].items():
                hurricane = hurricanes[hurricaneID-1]
                assert hurricane['Hurricane'] == hurricaneID
                logging.info('Participant %d Hurricane %d: %s' % (partID,hurricane['Hurricane'],name))
                agent = world.agents[name]
                records = survey.preSurvey(args,name,world,states,config,random.randint(hurricane['Start'],hurricane['Landfall']-1),
                    hurricane,variables,partID)
                output += records
        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
