from argparse import ArgumentParser
import logging
import os.path
import random

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility

rewardLabels = {'resources': 'my wealth','childrenHealth': 'my children\'s wellbeing','health': 'my wellbeing',
    'neighbors': 'my neighborhood\'s wellbeing','pet': 'my pet\'s wellbeing'}
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    cmd = vars(parser.parse_args())
    random.seed(int(os.path.splitext(os.path.basename(__file__))[0].split('-')[2]))
    defined = False
    variables = accessibility.boilerPlate[:]
    for instance,args in accessibility.instanceArgs('Phase2','Explain'):
        if cmd['debug']:
            print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        world = accessibility.unpickle(instance)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run'],'Input' if 3 <= instance <= 14 else None)
            if h['End'] <= args['span']]
        if accessibility.instancePhase(instance) == 1:
            states = accessibility.loadRunData(args['instance'],args['run'],args['span'],subs=['Input'] if 3 <= instance <= 14 else [None])
            network = accessibility.readNetwork(args['instance'],args['run'],'Input' if 3 <= instance <= 14 else None)
        else:
            states = {}
            network = None
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
            record.update(demos[name])
            record['Timestep'] = args['span']
            var = 'Information Channels'
            if not defined:
                variables.append({'Name': var,'Values':'social,friends','DataType': 'String','Notes': 'Q1'})
            if agent.getFriends(network):
                record[var] = 'social,friends'
            else:
                record[var] = 'social'
            var = 'Shelter Policy'
            if not defined:
                variables.append({'Name': var,'Values':'*','DataType': 'String','Notes': 'Q2'})
            if record['Pets'] == 'no':
                record[var] = 'none'
            elif config.getboolean('Shelter','pets'):
                record[var] = 'none'
            else:
                record[var] = 'no pets'
            var = 'Facilities'
            if not defined:
                variables.append({'Name': var,'Values':'*','DataType': 'String','Notes': 'Q3'})
            record[var] = 'none'            
            var = 'Reasons to not Evacuate'
            if not defined:
                variables.append({'Name': var,'Values':'*','DataType': 'String','Notes': 'Q4'})
            # Find most recent non-evacuation decision
            evac = ActionSet([Action({'subject': name,'verb': 'evacuate'})])
            t = args['span'] - 1
            while evac not in agent.getActions(next(iter(states[t-1]['Nature'][name].values()))):
                t -= 1
            model,belief = copy.deepcopy(next(iter(states[t-1]['Nature'][name].items())))
            real = accessibility.getAction(args,name,world,states,t-1)
            Vreal = agent.value(belief,real,model,updateBeliefs=False)
            Vevac = agent.value(belief,evac,model,updateBeliefs=False)
            keyMap = {feature: stateKey(record['Residence'],'risk') if feature == 'neighbors' else stateKey(name,feature) for feature in agent.Rweights}
            delta = {feature: sum([world.getFeature(keyMap[feature],s).expectation() for s in Vreal['__S__']])-
                sum([world.getFeature(keyMap[feature],s).expectation() for s in Vevac['__S__']]) for feature in agent.Rweights 
                if keyMap[feature] in world.variables}
            reasons = sorted([(diff*agent.Rweights[feature],rewardLabels[feature]) for feature,diff in delta.items() if diff > 0.])
            record[var] =','.join([reason[1] for reason in reasons])
            if cmd['debug']:
                print(record)
            if not defined:
                if not cmd['debug']:
                    accessibility.writeVarDef(os.path.dirname(__file__),variables)
                defined = True
        if not cmd['debug']:
            accessibility.writeOutput(args,output,[var['Name'] for var in variables],'%s.tsv' % (os.path.splitext(os.path.basename(__file__))[0]),
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
