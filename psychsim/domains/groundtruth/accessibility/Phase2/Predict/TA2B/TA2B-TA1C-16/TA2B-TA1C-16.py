from argparse import ArgumentParser
import logging
import os.path
import pickle
import random
import sys

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.domains.groundtruth.simulation import survey

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    parser.add_argument('-1',action='store_true',help='Run Condition 1 only')
    reqNum = int(os.path.splitext(os.path.basename(__file__))[0].split('-')[2])
    team = os.path.splitext(os.path.basename(__file__))[0].split('-')[0]
    random.seed(reqNum)
    cmd = vars(parser.parse_args())
    variables = dict(accessibility.boilerDict)
    for instance,args in accessibility.instanceArgs('Phase2','Predict'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        challenge = accessibility.instanceChallenge(instance)[1]
        config = accessibility.getConfig(args['instance'])
        states = {}
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        # Load world
        if challenge == 'Explain':
            yearLength = config.getint('Disaster','year_length',fallback=365)
            day1 = (args['span']//yearLength + 1)*yearLength+1
            world = accessibility.unpickle(instance,day=day1)
        else:
            world = accessibility.unpickle(instance)
            day1 = hurricanes[-1]['Start']-2
            accessibility.loadState(args,states,day1,'Nature',world)
        participants = accessibility.readParticipants(args['instance'],args['run'],splitHurricanes=challenge=='Predict',
            duplicates=challenge=='Predict')
        actors = {name for name in world.agents if name[:5] == 'Actor' and world.getState(name,'alive').first()}
        sample = random.sample(actors,len(actors)//20)
        output = {1: [], 2: [], 3: []}
        # Condition 0
        for partID in range(len(sample)):
            name = sample[partID]
            logging.info('Participant %d: %s' % (partID+1,name))
            agent = world.agents[name]
            root = {'Timestep': day1,'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID+1)}
            for field,value in accessibility.getCurrentDemographics(args,name,world,states,config).items():
                record = dict(root)
                record['VariableName'] = field
                record['Value'] = value
                output[2].append(record)

            var = '%s %d Participant ID' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': 'Actor','DataType': 'String','Notes': 'Map to pre/post-survey ID'}
            record = dict(root)
            record['VariableName'] = var
            for label,table in participants.items():
                for partID in table:
                    if name == table[partID]:
                        if challenge == 'Predict':
                            h = int(label.split()[1])
                            if h > hurricanes[-1]['Hurricane']:
                                continue
                            record['Timestep'] = accessibility.getSurveyTime(args,label[:3] == 'Pre',h,partID)
                        record['Value'] = '%s %d' % (label,partID)
                        output[1].append(record)
                        output[2].append(record)
                        output[3].append(record)
                        logging.info('%s: %s and %s %d' % (name,root['EntityIdx'],label,partID))
                        break
                if 'Value' in record:
                    break
            else:
                logging.warning('%s never filled out survey' % (name))

            var = '%s %d Friends' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = len([friend for friend in agent.getFriends() if world.getState(friend,'alive').first()])
            output[2].append(record)
        # Trigger hurricane
        logging.info('Condition 0')
        if challenge == 'Explain':
            history = accessibility.holoCane(world,config,set(sample),1,True,{'System': None},'seasons',None,True)
        else:
            history = accessibility.holoCane(world,config,set(sample),1,True,{'System': None},'hurricanes',hurricanes[-1],True)
        for name in sample:
            print(name,sum([world.getState(name,'risk',step['__state__']).expectation() for step in history]))
        if not cmd['debug']:
            for partID in range(len(sample)):
                name = sample[partID]
                root = {'Timestep': day1,'EntityIdx': '%s %d Participant %d Condition 0' % (team,reqNum,partID+1)}
                if challenge == 'Explain':
                    exit()
                else:
                    # Presurvey
                    t = random.randint(hurricanes[-1]['Start'],hurricanes[-1]['Landfall']-1)
                    output[3] += survey.preSurvey(args,name,world,{t-1: {'Nature': history[(t-day1-1)*3]}},config,t,hurricanes[-1],variables,
                        '%s %d Participant %d' % (team,reqNum,partID+1),'%s %d Pt3 Condition 0' % (team,reqNum),False)
                    # Postsurvey
                    responses = survey.postSurvey(args,name,world,
                        {t-1: {'Nature': history[(t-day1-1)*3]} for t in range(hurricanes[-1]['Start'],hurricanes[-1]['End']+1)},config,hurricanes[-1]['End'],
                        hurricanes[-1],variables,'%s %d Participant %d' % (team,reqNum,partID+1),'%s %d Pt1 Condition 0' % (team,reqNum),False,False)
                    output[1] += responses
        # Condition 1
        # Load world
        if challenge == 'Explain':
            yearLength = config.getint('Disaster','year_length',fallback=365)
            day1 = (args['span']//yearLength + 1)*yearLength+1
            world = accessibility.unpickle(instance,day=day1)
        else:
            world = accessibility.unpickle(instance)
            day1 = hurricanes[-1]['Start']-2
            accessibility.loadState(args,states,day1,'Nature',world)
        if world.agents['System'].resources > 0:
            world.agents['System'].resources *= 2
        else:
            world.agents['System'].resources = 1
        world.agents['System'].setAidDynamics(sample)
        # Trigger hurricane
        logging.info('Condition 1')
        if challenge == 'Explain':
            history = accessibility.holoCane(world,config,set(sample),1,True,{'System': None},'seasons',None,True)
        else:
            history = accessibility.holoCane(world,config,set(sample),1,True,{'System': None},'hurricanes',hurricanes[-1],True)
        for name in sample:
            print(name,sum([world.getState(name,'risk',step['__state__']).expectation() for step in history]))
        if not cmd['debug']:
            for partID in range(len(sample)):
                name = sample[partID]
                root = {'Timestep': day1,'EntityIdx': '%s %d Participant %d Condition 1' % (team,reqNum,partID+1)}
                if challenge == 'Explain':
                    exit()
                else:
                    # Presurvey
                    t = random.randint(hurricanes[-1]['Start'],hurricanes[-1]['Landfall']-1)
                    responses = survey.preSurvey(args,name,world,{t-1: {'Nature': history[(t-day1-1)*3]}},config,t,hurricanes[-1],variables,
                        '%s %d Participant %d' % (team,reqNum,partID+1),'%s %d Pt3 Condition 1' % (team,reqNum),False)
                    for value in responses:
                        for previous in output[3]:
                            if value['VariableName'].replace('Condition 1','Condition 0') == previous['VariableName']:
                                if value['Value'] != previous['Value']:
                                    logging.info('Value of %s changed for %s on day %d' % (value['VariableName'],value['EntityIdx'],value['Timestep']))
                    output[3] += responses
                    # Postsurvey
                    responses = survey.postSurvey(args,name,world,
                        {t-1: {'Nature': history[(t-day1-1)*3]} for t in range(hurricanes[-1]['Start'],hurricanes[-1]['End']+1)},config,hurricanes[-1]['End'],
                        hurricanes[-1],variables,'%s %d Participant %d' % (team,reqNum,partID+1),'%s %d Pt1 Condition 1' % (team,reqNum),False,False)
                    for value in responses:
                        for previous in output[3]:
                            if value['VariableName'].replace('Condition 1','Condition 0') == previous['VariableName']:
                                if value['Value'] != previous['Value']:
                                    logging.info('Value of %s changed for %s on day %d' % (value['VariableName'],value['EntityIdx'],value['Timestep']))
                    output[1] += responses
        if not cmd['debug']:
            for part in range(3):
                accessibility.writeOutput(args,output[part+1],accessibility.fields['RunData'],'RunDataTable%d.tsv' % (part+1),
                    os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
