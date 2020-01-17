from argparse import ArgumentParser
import logging
import os.path
import pickle
import random
import sys

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    reqNum = int(os.path.splitext(os.path.basename(__file__))[0].split('-')[2])
    team = os.path.splitext(os.path.basename(__file__))[0].split('-')[0]
    random.seed(reqNum)
    cmd = vars(parser.parse_args())
    variables = {}
    for instance,args in accessibility.instanceArgs('Phase3','Explain'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        states = {}
        # Load world
        world = accessibility.unpickle(instance)
        accessibility.loadState(args,states,args['span']-1,'Nature',world)
        participants = accessibility.readParticipants(args['instance'],args['run'])
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        regions = [name for name in world.agents if name[:6] == 'Region']
        probs = {h['Hurricane']: {} for h in hurricanes}
        key = stateKey('Nature','location')
        tree = world.dynamics[key][world.agents['Nature'].evolution].children[1].children[False]
        for h in hurricanes:
            accessibility.loadState(args,states,h['Landfall']-1,'Nature')
            location = states[h['Landfall']-1]['Nature']['__state__'][key].first()
            probs[h['Hurricane']][world.float2value(key,location)] = 1.
            active = [(location,1.)]
            while len(active) > 0:
                oldLoc,prob = active.pop()
                vector = KeyedVector({key: oldLoc,CONSTANT: 1.})
                dist = tree[vector]*vector
                if not isinstance(dist,KeyedVector):
                    for vector in dist.domain():
                        newLoc = vector[makeFuture(key)]
                        if newLoc != oldLoc:
                            region = world.float2value(key,newLoc)
                            if region != 'none':
                                probs[h['Hurricane']][region] = probs[h['Hurricane']].get(region,0)+prob*dist[vector]
                                active.append((newLoc,prob*dist[vector]))
        actors = [name for name in world.agents if name[:5] == 'Actor' and stateKey(name,'health') in world.state]
        sample = random.sample(actors,len(actors)//5)
        output = []
        partID = 0
        for name in sample:
            partID += 1
            agent = world.agents[name]
            logging.info('Participant %d: %s' % (partID,name))

            root = {'Timestep': args['span'],'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID)}

            surveyID = accessibility.participantMatch(name,participants)
            if surveyID is not None:
                var = '%s %d Survey ID' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'Actor[Pre,Post] [1+] Hurricane [1+]','DataType': 'String'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = surveyID
                output.append(record)

            var = '%s %d Residence' % (team,reqNum)
            region = world.agents[name].demographics['home']
            if var not in variables:
                variables[var] = {'Name': var,'Values':'Region[01-16]','DataType': 'String','Notes': 'Q1'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = region
            output.append(record)

            for hurricane in hurricanes:
                t = hurricane['Landfall'] - 1

                var = '%s %d Hurricane %d Hit Region Likelihood' % (team,reqNum,hurricane['Hurricane'])
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q2'}
                record = dict(root)
                record['Timestep'] = t
                record['VariableName'] = var
                record['Value'] = accessibility.toLikert(probs[hurricane['Hurricane']].get(region,0),7)
                output.append(record)

                var = '%s %d Hurricane %d Hit Region Category' % (team,reqNum,hurricane['Hurricane'])
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[0-5]','DataType': 'Integer','Notes': 'Q3'}
                record = dict(root)
                record['Timestep'] = t
                record['VariableName'] = var
                if region in probs[hurricane['Hurricane']]:
                    record['Value'] = accessibility.getInitialState(args,'Nature','category',world,states,t,name).max()
                else:
                    record['Value'] = 0
                output.append(record)

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),sorted(variables.values(),key=lambda v: v['Name']))
