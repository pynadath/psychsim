from argparse import ArgumentParser
import logging
import os.path
import random

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility

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
        config = accessibility.getConfig(args['instance'])
        world = accessibility.unpickle(instance)
        states = {}
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run'],'Input' if 3 <= instance <= 14 else None)
            if h['End'] <= args['span']]
        actors = accessibility.getLivePopulation(args,world,states,args['span'])
        demos = {name: accessibility.getCurrentDemographics(args,name,world,states,config,death) for name,death in actors.items() if death is not None}
        output = []
        for name,record in demos.items():
            if not defined:
                variables += accessibility.boilerPlate[1:] # Skip timestep
            output.append(record)
            # 0
            record.update(demos[name])
            # 1
            record['Timestep'] = actors[name]
            if not defined:
                variables.append({'Name': 'Timestep','Values':'[1-365]','VarType': 'static','DataType': 'Integer','Notes': '1'})
            # 2
            var = 'Location'
            if not defined:
                variables.append({'Name': var,'Values':'shelter,evacuated,home','DataType': 'String','Notes': '2'})
            location = accessibility.getInitialState(args,name,'location',world,states,actors[name])
            if isinstance(location,Distribution):
                location = location.first()
            if location[:6] == 'Region':
                record[var] = 'home'
            elif location[:7] == 'shelter':
                record[var] = 'shelter'
            else:
                record[var] = location
            # 3
            last = accessibility.findHurricane(actors[name],hurricanes,True)
            assert last is not None
            locations = [{loc.first() for loc in accessibility.getInitialState(args,name,'location',world,states,(hurricane['Start'],hurricane['End']+1))}
                for hurricane in hurricanes[:last['Hurricane']]]
            var = 'Stayed Home Last Hurricane'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '3'})
            record[var] = 'yes' if len(locations[last['Hurricane']-1]) == 1 and record['Residence'] in locations[last['Hurricane']-1] else 'no'
            var = 'Evacuated Last Hurricane'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '3'})
            record[var] = 'yes' if 'evacuated' in locations[last['Hurricane']-1] else 'no'
            var = 'Sheltered Last Hurricane'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '3'})
            record[var] = 'yes' if [loc for loc in locations[last['Hurricane']-1] if loc[:7] == 'shelter'] else 'no'
            # 4
            var = 'Injured'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '4'})
            health = accessibility.getInitialState(args,name,'health',world,states,last['Start'])
            record[var] = 'yes' if float(health) < 0.2 else 'no'
            # 5
            var = 'Category'
            if not defined:
                variables.append({'Name': var,'Values':'[1-5]','DataType': 'Integer','Notes': '5'})
            centers = [s.first() for s in accessibility.getInitialState(args,'Nature','location',world,states,(last['Landfall'],last['End']))]
            categories = [s.first() for s in accessibility.getInitialState(args,'Nature','category',world,states,(last['Landfall'],last['End']))]
            # Pair distance between hurricane and home, with hurricane category
            distCat = [(world.agents[centers[t]].distance(record['Residence']),categories[t]) for t in range(len(centers))]
            record[var] = min(distCat)[1]
            # 6
            var = 'Stayed Home Previous Hurricanes'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '6'})
            record[var] = ','.join(['yes' if len(locs) == 1 and record['Residence'] in locs else 'no' for locs in locations[:-1]])
            var = 'Evacuated Previous Hurricanes'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '6'})
            record[var] = ','.join(['yes' if 'evacuated' in locs else 'no' for locs in locations[:-1]])
            var = 'Sheltered Previous Hurricanes'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '6'})
            record[var] = ','.join(['yes' if [loc for loc in locs if loc[:7] == 'shelter'] else 'no' for locs in locations[:-1]])
            # 7
            var = 'Injured Previous Hurricanes'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '7'})
            health = [float(accessibility.getInitialState(args,name,'health',world,states,h['End'])) for h in hurricanes[:last['Hurricane']-1]]
            record[var] = ','.join(['yes' if value < 0.2 else 'no' for value in health])
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
