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
    random.seed(reqNum)
    team = os.path.splitext(os.path.basename(__file__))[0].split('-')[0]
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    cmd = vars(parser.parse_args())
    participants = accessibility.readRRParticipants(os.path.join(os.path.dirname(__file__),'..','TA2A-TA1C-0462','TA2A-TA1C-0462.log'))
    variables = {}
    for instance,args in accessibility.instanceArgs('Phase2'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        world = accessibility.unpickle(instance)
        states = {}
        accessibility.loadState(args,states,args['span']-1,'Nature',world)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        actors = {name for name in world.agents if name[:5] == 'Actor' and world.getState(name,'alive').first()}
        sample = random.sample(actors,len(actors)//5)
        output = []

        for hurricane in hurricanes[-5:]:
            for partID,name in sorted(participants[instance].items()):
                logging.info('Participant %d: %s' % (partID,name))
                agent = world.agents[name]
                root = {'Timestep': args['span'],'EntityIdx': '%s %d Participant %d' % (team,reqNum-10,partID)}

                var = '%s %d Hurricane %d Evacuation Incentive' % (team,reqNum,hurricane['Hurricane'])
                if var not in variables:
                    variables[var] = {'Name': var,'Values': '[0-6]', 'DataType': 'Integer','Notes': 'Q1'}
                record = dict(root)
                record['VariableName'] = var
                actions = accessibility.getAction(args,name,world,states,(hurricane['Start'],hurricane['End']+1))
                verbs = {act['verb'] for act in actions}
                if 'evacuate' in verbs:
                    record['Value'] = 0
                else:
                    values = []
                    for t in range(hurricane['Start'],hurricane['End']+1):
                        real = actions[t-hurricane['Start']]
                        model = agent.world.getModel(name)
                        assert len(model) == 1
                        model = model.first()
                        belief = accessibility.loadState(args,states,t-1,'Nature')[name][model]
                        Vreal = agent.value(belief,real,model,keySet=belief.keys(),updateBeliefs=False)
                        Vevac = agent.value(belief,ActionSet([Action({'subject': name,'verb': 'evacuate'})]),model,
                            keySet=belief.keys(),updateBeliefs=False)
                        delta = Vreal['__EV__']-Vevac['__EV__']
                        assert delta >= 0.
                        values.append(delta/agent.Rweights['resources'])
                    record['Value'] = min(6,accessibility.toLikert(min(values),7))
                    print(delta,record['Value'])
                output.append(record)

                var = '%s %d Hurricane %d Dissatisfaction' % (team,reqNum,hurricane['Hurricane'])
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': 'Q2'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = accessibility.toLikert(accessibility.getInitialState(args,name,'grievance',world,states,
                    hurricane['End']).expectation(),7)-1
                output.append(record)
            states.clear()
        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
