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
    variables = {}
    for instance,args in accessibility.instanceArgs('Phase3'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        world = accessibility.unpickle(instance)
        states = {}
        accessibility.loadState(args,states,args['span']-1,'Nature',world)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        participants = accessibility.readParticipants(args['instance'],args['run'])

        output = []
        for oldH in hurricanes[:-1]:
            for partID,name in participants['Post-survey %d' % (oldH['Hurricane'])].items():
                agent = world.agents[name]
                newH = hurricanes[oldH['Hurricane']]
                t = newH['End'] + 1
                root = {'Timestep': t,'EntityIdx': 'ActorPost %d Hurricane %d' % (partID,oldH['Hurricane'])}

                var = '%s %d Hurricane' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[1+]','DataType': 'Integer','Notes': '5b'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = newH['Hurricane']
                output.append(record)

                try:
                    accessibility.getInitialState(args,name,'health',world,states,t)
                except KeyError:
                    # Dead
                    var = '%s %d Deceased' % (team,reqNum)
                    if var not in variables:
                        variables[var] = {'Name': var,'Values':'deceased','DataType': 'String'}
                    record = dict(root)
                    record['VariableName'] = var
                    record['Value'] = 'deceased'
                    output.append(record)
                    continue

                locations = accessibility.getInitialState(args,name,'location',world,states,(newH['Start'],newH['End']+1),
                    unique=True)

                var = '%s %d At Shelter' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '5d.i'}
                record = dict(root)
                record['VariableName'] = var
                for loc in locations:
                    if loc[:7] == 'shelter':
                        sheltered = True
                        break
                else:
                    sheltered = False
                record['Value'] = 'yes' if sheltered else 'no'
                output.append(record)

                var = '%s %d Evacuated' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '5d.ii'}
                record = dict(root)
                record['VariableName'] = var
                for loc in locations:
                    if loc == 'evacuated':
                        evacuated = True
                        break
                else:
                    evacuated = False
                record['Value'] = 'yes' if evacuated else 'no'
                output.append(record)

                health = accessibility.getInitialState(args,name,'health',world,states,(newH['Start'],newH['End']+1),
                    unique=True)

                var = '%s %d Injured' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '5d.iii'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = 'yes' if min(health) < 0.2 else 'no'
                output.append(record)

                var = '%s %d Risk' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': '5d.iv'}
                risk = [float(dist) for dist in accessibility.getInitialState(args,name,'risk',world,states,
                    (newH['Start'],newH['End']+1),name)]
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = accessibility.toLikert(max(risk),7)
                output.append(record)

                var = '%s %d Dissatisfaction' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': '5d.v'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = accessibility.toLikert(accessibility.getInitialState(args,name,'grievance',world,states,t,unique=True),7)
                output.append(record)

                actions = accessibility.getAction(args,name,world,states,(newH['Start'],newH['End']+1))
                pShelter = []
                pEvac = []
                pHome = []
                for day in range(newH['Start'],newH['End']+1):
                    belief = states[day-1]['Nature'][name]
                    if isinstance(belief,dict):
                        model,belief = copy.deepcopy(next(iter(belief.items())))
                    else:
                        belief = copy.deepcopy(belief)
                        model = world.getFeature(modelKey(name),states[day-1]['Nature']['__state__']).first()
                    horizon = agent.getAttribute('horizon',model)
                    pEvac.append(0.)
                    pShelter.append(0.)
                    pHome.append(0.)
                    if config.getint('Simulation','phase',fallback=1) < 3:
                        V = {action: agent.value(belief,action,model,updateBeliefs=False)['__EV__'] for action in agent.getActions(belief)}
                    else:
                        V = {action: agent.chooseAction(copy.deepcopy(belief),horizon,action,model)[1] for action in agent.getActions(belief)}            
                    dist = Distribution(V,agent.getAttribute('rationality',model))
                    for action,prob in dist.items():
                        if action != actions[day-newH['Start']]:
                            if action['verb'] == 'evacuate':
                                pEvac.append(prob)
                            elif action['verb'] == 'moveTo' and action['object'][:7] == 'shelter':
                                pShelter[-1] = max(prob,pShelter[-1])
                            elif action['verb'] in {'decreaseRisk','takeResources'}:
                                # Must be at home
                                pHome[-1] += prob
                            elif action['verb'] == 'moveTo' and action['object'] == agent.demographics['home']:
                                # Must be away from home
                                pHome[-1] += prob
                            elif action['verb'] == 'stayInLocation' and world.getState(name,'location',belief).first() == agent.demographics['home']:
                                pHome[-1] += prob

                var = '%s %d Shelter Possibility' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': '5d.vi: N/A if already at shelter'}
                record = dict(root)
                record['VariableName'] = var
                if sheltered:
                    record['Value'] = 'N/A'
                else:
                    record['Value'] = accessibility.toLikert(max(pShelter),7)
                output.append(record)

                var = '%s %d Evacuation Possibility' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': '5d.vii: N/A if already evacuated'}
                record = dict(root)
                record['VariableName'] = var
                if evacuated:
                    record['Value'] = 'N/A'
                else:
                    record['Value'] = accessibility.toLikert(max(pEvac),7)
                output.append(record)

                var = '%s %d Stay at Home Possibility' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': '5d.viii: N/A if stayed home'}
                record = dict(root)
                record['VariableName'] = var
                if not sheltered and not evacuated:
                    record['Value'] = 'N/A'
                else:
                    record['Value'] = accessibility.toLikert(max(pHome),7)
                output.append(record)

            states.clear()

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
