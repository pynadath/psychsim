from argparse import ArgumentParser
import logging
import os.path

from psychsim.probability import Distribution
from psychsim.domains.groundtruth import accessibility

def p2answer(p):
    return min(int(10*p)+1,10)

def shelterp(action):
    return action['object'] is not None and 'shelter' in action['object']

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    reqNum = int(os.path.splitext(os.path.basename(__file__))[0].split('-')[2])
    team = os.path.splitext(os.path.basename(__file__))[0].split('-')[0]
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    cmd = vars(parser.parse_args())
    variables = {}
    for instance,args in accessibility.instanceArgs('Phase3','Prescribe'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        world = accessibility.unpickle(instance)
        simLog = accessibility.readLog(args)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        states = {}
        actors = {name for name in world.agents if name[:5] == 'Actor'}
        output = []
        for h in hurricanes:
            V = {}
            actions = {}
            shelter = set()
            wantShelter = set()
            for name in actors:
                V[name] = {}
                for t in range(h['Start'],h['End']+1):
                    if name in simLog[t]:
                        V[name][t-h['Start']] = {a: v for a,v in simLog[t][name].items() if a != '__horizon__'}
                    else:
                        del V[name]
                        break
            for name,values in V.items():
                actions[name] = accessibility.getAction(args,name,world,states,(h['Start'],h['End']+1))
                for action in actions[name]:
                    if shelterp(action):
                        shelter.add(name)
                        break
                for t,values in V[name].items():
                    for action,ER in values.items():
                        if shelterp(action):
                            if ER == max(values.values()):
                                wantShelter.add(name)
                            break
            for name,values in sorted(V.items()):
                agent = world.agents[name]
                pFalse = {'neutral': 1.,'incentive': 1.,'disincentive': 1.,'pets': 1.}
                root = {'Timestep': h['End'],'EntityIdx': name}
                resources = accessibility.getInitialState(args,name,'resources',world,states,(h['Start'],h['End']+1),unique=True)

                decider = False
                for t,action in enumerate(actions[name]):
                    if len(values[t]) == 1 and isinstance(next(iter(values[t].values())),str):
                        # No value available
                        continue
                    decider = True
                    dist = {'neutral': Distribution(values[t],1)}
                    assert dist['neutral'][action] == max(dist['neutral'].values())

                    valuesPlus = {}
                    for a,V in values[t].items():
                        if shelterp(a):
                            valuesPlus[a] = V+0.2*agent.Rweights['resources']*resources[t]
                        else:
                            valuesPlus[a] = V
                    dist['incentive'] = Distribution(valuesPlus,1)

                    valuesMinus = {}
                    for a,V in values[t].items():
                        if shelterp(a):
                            valuesMinus[a] = V-0.2*agent.Rweights['resources']*resources[t]
                        else:
                            valuesMinus[a] = V
                    dist['disincentive'] = Distribution(valuesMinus,1)

                    if agent.demographics['pet']:
                        valuesPets = {}
                        for a,V in values[t].items():
                            if shelterp(a):
                                valuesPets[a] = V+agent.Rweights['pet']
                            else:
                                valuesPets[a] = V
                        dist['pets'] = Distribution(valuesPets,1)
                    else:
                        dist['pets'] = dist['neutral']

#                    print(agent.Rweights['resources'],agent.demographics['pet'],agent.Rweights['pet'])
#                    for a in sorted(dist['neutral'].domain()):
#                        print('%32s: %5.2f\t%5.2f\t%5.2f\t%5.2f' % (a,100*dist['neutral'][a],100*dist['incentive'][a],100*dist['disincentive'][a],100*dist['pets'][a]))

                    prob = {condition: 0 for condition in pFalse}
                    for a in dist['neutral'].domain():
                        if not shelterp(a):
                            for condition in prob:
                                prob[condition] += dist[condition][a]
                    for condition in prob:
                        pFalse[condition] *= prob[condition]

                if decider:
                    myShelter = {condition: 1-p for condition,p in pFalse.items()}
                else:
                    myShelter = {condition: 1 if name in shelter else 0 for condition in pFalse}

                var = '%s %d Spouse Shelter' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'1-10,N/A','DataType': 'Integer','Notes': 'Q1'}
                record = dict(root)
                record['VariableName'] = var
                if agent.spouse is None:
                    record['Value'] = 'N/A'
                else:
                    record['Value'] = p2answer((1+myShelter['neutral'])/2)
                output.append(record)

                var = '%s %d Friends Shelter' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'1-10,N/A','DataType': 'Integer','Notes': 'Q2'}
                record = dict(root)
                record['VariableName'] = var
                if agent.getFriends():
                    record['Value'] = p2answer(myShelter['neutral'])
                else:
                    record['Value'] = 'N/A'
                output.append(record)

                var = '%s %d Neighbors Shelter' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'1-10,N/A','DataType': 'Integer','Notes': 'Q3'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = p2answer(myShelter['neutral'])
                output.append(record)

                var = '%s %d Incentive Shelter' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'1-10','DataType': 'Integer','Notes': 'Q4'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = p2answer(myShelter['incentive'])
                output.append(record)

                var = '%s %d Spouse No Shelter' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'1-10,N/A','DataType': 'Integer','Notes': 'Q5'}
                record = dict(root)
                record['VariableName'] = var
                if agent.spouse is None:
                    record['Value'] = 'N/A'
                else:
                    record['Value'] = p2answer(myShelter['neutral']/2)
                output.append(record)

                var = '%s %d Friends No Shelter' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'1-10,N/A','DataType': 'Integer','Notes': 'Q6'}
                record = dict(root)
                record['VariableName'] = var
                if agent.getFriends():
                    record['Value'] = p2answer(myShelter['neutral'])
                else:
                    record['Value'] = 'N/A'
                output.append(record)

                var = '%s %d Neighbors No Shelter' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'1-10,N/A','DataType': 'Integer','Notes': 'Q7'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = p2answer(myShelter['neutral'])
                output.append(record)

                var = '%s %d Cost Shelter' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'1-10','DataType': 'Integer','Notes': 'Q8'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = p2answer(myShelter['disincentive'])
                output.append(record)

                var = '%s %d Pets Shelter' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'1-10','DataType': 'Integer','Notes': 'Q9'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = p2answer(myShelter['pets'])
                output.append(record)

                var = '%s %d Shelter Tax' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'1-10','DataType': 'Integer','Notes': 'Q10'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = p2answer(myShelter['neutral'])
                output.append(record)

            states.clear()
        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
