from argparse import ArgumentParser
import logging
import os.path
import random
import sys

from psychsim.probability import Distribution
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
        random.seed(int(os.path.splitext(os.path.basename(__file__))[0].split('-')[2])+instance)
        config = accessibility.getConfig(args['instance'])
        world = accessibility.unpickle(instance)
        states = {}
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        hurricane = hurricanes[-1]
        actors = accessibility.getLivePopulation(args,world,states,args['span'])
        demos = {name: accessibility.getCurrentDemographics(args,name,world,states,config,args['span']) for name,death in actors.items() if death is None}
        sample = random.sample(demos.keys(),len(demos)//10)
        output = []
        for name in sample:
            agent = world.agents[name]
            record = {}
            output.append(record)
            var = 'Participant'
            if not defined:
                variables.append({'Name': var,'Values':'[1+]','VarType': 'fixed','DataType': 'Integer'})
            record[var] = len(output)
            logging.info('Participant %d: %s' % (record[var],name))
            if not defined:
                variables += accessibility.boilerPlate
            record.update(demos[name])
            record['Timestep'] = args['span']
            # 1
            var = 'Physical Health'
            if not defined:
                variables.append({'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q1'})
            health = accessibility.getInitialState(args,name,'health',world,states,args['span'])
            record[var] = accessibility.toLikert(float(health),7)
            # 6
            var = 'Relative Property Value'
            if not defined:
                variables.append({'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q6'})
            # How does my wealth compare to my neighbors'?
            wealth = float(accessibility.getInitialState(args,name,'resources',world,states,args['span']))
            others = [float(accessibility.getInitialState(args,other,'resources',world,states,args['span'])) for other in agent.getNeighbors()]
            record[var] = accessibility.toLikert(len([value for value in others if value < wealth])/len(others),7)
            # 9
            var = 'Landfall Certainty'
            if not defined:
                variables.append({'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q9'})
            model,belief = copy.deepcopy(next(iter(states[hurricane['Start']]['Nature'][name].items())))
            locDist = {}
            stepDist = {}
            catDist = {}
            step = 1
            phase = stateKey('Nature','phase')
            location = stateKey('Nature','location')
            category = stateKey('Nature','category')
            mass = 1.
            while mass > 0.01:
                prob = 0.
                world.step(state=belief,keySubset=belief.keys())
                dist = belief.distributions[belief.keyMap[phase]]
                for vector in dist.domain():
                    if world.float2value(phase,vector[phase]) == 'active': 
                        loc = world.float2value(location,vector[location])
                        locDist[loc] = locDist.get(loc,0.) + dist[vector]*mass
                        cat = world.float2value(category,vector[category])
                        catDist[cat] = catDist.get(cat,0.) + dist[vector]*mass
                        stepDist[step//3] = stepDist.get(step//3,0.) + dist[vector]*mass
                        prob += dist[vector]*mass
                        del dist[vector]
                dist.normalize()
                mass -= prob
                step += 1
            record[var] = accessibility.toLikert(min(max(locDist.values()),max(stepDist.values())),7)
            # 10
            var = 'Category Certainty'
            if not defined:
                variables.append({'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q10'})
            record[var] = accessibility.toLikert(max(catDist.values()),7)
            if cmd['debug']:
                print(record)
            if not defined:
                if not cmd['debug']:
                    accessibility.writeVarDef(os.path.dirname(__file__),variables)
                defined = True
        output.sort(key=lambda rec: rec['Timestep'])
        if not cmd['debug']:
            accessibility.writeOutput(args,output,[var['Name'] for var in variables],'%s.tsv' % (os.path.splitext(os.path.basename(__file__))[0]),
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
