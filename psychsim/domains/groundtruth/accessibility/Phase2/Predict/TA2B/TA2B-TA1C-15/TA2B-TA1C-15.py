from argparse import ArgumentParser
import logging
import os.path
import random
import sys

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.domains.groundtruth.simulation import survey

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    reqNum = int(os.path.splitext(os.path.basename(__file__))[0].split('-')[2])
    team = os.path.splitext(os.path.basename(__file__))[0].split('-')[0]
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    cmd = vars(parser.parse_args())
    variables = accessibility.boilerDict
    for instance,args in accessibility.instanceArgs('Phase2'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        challenge = accessibility.instanceChallenge(instance)[1]
        participants = accessibility.readParticipants(args['instance'],args['run'],splitHurricanes=challenge=='Predict',
            duplicates=challenge=='Predict')
        config = accessibility.getConfig(args['instance'])
        world = accessibility.unpickle(instance)
        states = {}
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        actors = {name: t for name,t in accessibility.getLivePopulation(args,world,states,args['span']).items() if t is not None}
        output = []
        deaths = {}
        for name,t in sorted(actors.items(),key=lambda tup: tup[1]):
            agent = world.agents[name]
            deaths[t] = deaths.get(t,0)+1
            demos = accessibility.getCurrentDemographics(args,name,world,states,config,t)

            root = {'Timestep': t,'EntityIdx': 'D%d-%d' % (t,deaths[t])}
            for var,value in demos.items():
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = value
                output.append(record)

            var = '%s %d Participant ID' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': 'Actor','DataType': 'String','Notes': 'Map to pre/post-survey ID'}
            record = dict(root)
            record['VariableName'] = var
            for label,table in participants.items():
                for partID in table:
                    if name == table[partID]:
                        if challenge == 'Predict':
                            record['Timestep'] = accessibility.getSurveyTime(args,label[:3] == 'Pre',int(label.split()[1]),partID)
                        record['Value'] = '%s %d' % (label,partID)
                        output.append(record)
                        logging.info('%s: %s and %s %d' % (name,root['EntityIdx'],label,partID))
                        break
                if 'Value' in record:
                    break
            else:
                logging.warning('%s never filled out survey' % (name))

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
