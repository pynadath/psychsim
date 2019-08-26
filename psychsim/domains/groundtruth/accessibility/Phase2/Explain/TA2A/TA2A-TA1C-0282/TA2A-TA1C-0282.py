from argparse import ArgumentParser
import logging
import os.path
import random

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from TA2A_TA1C_0252 import aidWillingnessEtc

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    cmd = vars(parser.parse_args())
    random.seed(int(os.path.splitext(os.path.basename(__file__))[0].split('-')[2]))
    defined = False
    variables = accessibility.boilerPlate[:]
    for instance,args in accessibility.allArgs():
        if cmd['debug']:
            print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        world = accessibility.unpickle(instance)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run'],'Input' if 3 <= instance <= 14 else None)
            if h['End'] <= args['span']]
        if accessibility.instancePhase(instance) == 1:
            states = accessibility.loadRunData(args['instance'],args['run'],args['span'],subs=['Input'] if 3 <= instance <= 14 else [None])
        else:
            states = {}
        actors = accessibility.getLivePopulation(args,world,states,args['span'])
        pool = {name for name,death in actors.items() if death is None}
        demos = {name: accessibility.getCurrentDemographics(args,name,world,states,config,args['span']) for name in pool}
        participants = random.sample(pool,len(pool)//10)
        output = []
        for partID in range(len(participants)):
            if not defined:
                variables.insert(0,{'Name': 'Participant','Values': '[1+]','VarType': 'fixed','DataType': 'Integer'})
            record = {'Participant': partID+1}
            output.append(record)
            name = participants[partID]
            logging.info('Participant %d: %s' % (record['Participant'],name))
            agent = world.agents[name]
            # 0.i.1-9
            record.update(demos[name])
            # 0.i.10
            record['Timestep'] = args['span']
            # 0.i.11
            if not defined:
                aidVars = []
            else:
                aidVars = None
            aidWillingnessEtc(args,agent,record,world,states,demos,hurricanes,pool,aidVars)
            if not defined:
                for j in range(len(aidVars)):
                    if j < 3:
                        aidVars[j]['Notes'] = '0.i.%d' % (11+j)
                    else:
                        aidVars[j]['Notes'] = '0.ii.%d' % (j-2)
                variables += aidVars
            # 1. Questions on crime
            tmpVars = ['Witnessed Crime','Heard Crime Friends','Heard Crime Acquaintances','Heard Crime Strangers','Heard Crime Social Media',
                'Heard Crime Govt Broadcast','Heard Crime Govt Officials']
            if not defined:
                for j in range(len(tmpVars)):
                    variables.append({'Name': tmpVars[j],'Values': '[0+]','DataType': 'Integer','Notes': '1.%d' % (j+1)})
            for var in tmpVars:
                record[var] = 0
            # 1. Questions on awareness on crime
            tmpVars = ['Aware Family Crime','Aware Acquaintance Crime','Aware Friend Crime','Aware Stranger Crime']
            if not defined:
                for j in range(len(tmpVars)):
                    variables.append({'Name': '%s Frequency' % (tmpVars[j]),'Values': '[0-6]','DataType': 'Integer','Notes': '1.%d' % (j+1)})
                for j in range(len(tmpVars)):
                    variables.append({'Name': '%s Severity' % (tmpVars[j]),'Values': '[0-6]','DataType': 'Integer','Notes': '1.%d' % (j+5)})
            for j in range(len(tmpVars)):
                record['%s Frequency' % (tmpVars[j])] = 6 if j == 0 else 0
                record['%s Severity' % (tmpVars[j])] = 6 if j == 0 else 0
            if cmd['debug']:
                print(record)
            if not defined:
                if not cmd['debug']:
                    accessibility.writeVarDef(os.path.dirname(__file__),variables)
                defined = True
        if not cmd['debug']:
            accessibility.writeOutput(args,output,[var['Name'] for var in variables],'%s.tsv' % (os.path.splitext(os.path.basename(__file__))[0]),
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
