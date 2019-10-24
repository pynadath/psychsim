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
    variables = {}
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
            root = {'Timestep': t,'EntityIdx': 'D%d-%d' % (t,deaths[t])}

            var = '%s %d Location' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': 'home,shelter,evacuated','DataType': 'String','Notes': 'Q2'}
            record = dict(root)
            record['VariableName'] = var
            location = accessibility.getInitialState(args,name,'location',world,states,t).first()
            if location[:6] == 'Region':
                record['Value'] = 'home'
            elif location[:7] == 'shelter':
                record['Value'] = 'shelter'
            else:
                record['Value'] = location
            output.append(record)

            var = '%s %d Last Hurricane' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': 'home,evacuated,sheltered,evacuatedAndSheltered','DataType': 'String','Notes': 'Q3'}
            last = accessibility.findHurricane(t,hurricanes,True)
            assert last is not None
            locations = [{loc.first() for loc in accessibility.getInitialState(args,name,'location',world,states,(hurricane['Start'],hurricane['End']+1))}
                for hurricane in hurricanes[:last['Hurricane']]]
            record = dict(root)
            record['VariableName'] = var
            if len(locations[last['Hurricane']-1]) == 1 and agent.demographics['home'] in locations[last['Hurricane']-1]:
                record['Value'] = 'home'
            elif 'evacuated' in locations[last['Hurricane']-1]:
                if [loc for loc in locations[last['Hurricane']-1] if loc[:7] == 'shelter']:
                    record['Value'] = 'evacuatedAndSheltered'
                else:
                    record['Value'] = 'evacuated'
            elif [loc for loc in locations[last['Hurricane']-1] if loc[:7] == 'shelter']:
                record['Value'] = 'sheltered'
            else:
                raise ValueError('Unable to determine behavior: %s' % (locations[last['Hurricane']-1]))
            output.append(record)

            var = '%s %d Injured' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': 'yes,no','DataType': 'Boolean','Notes': 'Q4'}
            record = dict(root)
            record['VariableName'] = var
            record['Timestep'] = last['Start']
            health = accessibility.getInitialState(args,name,'health',world,states,last['Start'])
            record['Value'] = 'yes' if float(health) < 0.2 else 'no'
            output.append(record)

            var = '%s %d Category' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': '[1-5]','DataType': 'Integer','Notes': 'Q5'}
            record = dict(root)
            record['VariableName'] = var
            centers = [s.first() for s in accessibility.getInitialState(args,'Nature','location',world,states,(last['Landfall'],last['End']))]
            categories = [s.first() for s in accessibility.getInitialState(args,'Nature','category',world,states,(last['Landfall'],last['End']))]
            # Pair distance between hurricane and home, with hurricane category
            distCat = [(world.agents[centers[t]].distance(agent.demographics['home']),categories[t],t) for t in range(len(centers))]
            record['Value'] = min(distCat)[1]
            record['Timestep'] = last['Landfall']+min(distCat)[2]
            output.append(record)

            var = '%s %d Previous Hurricanes' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': 'home,evacuated,sheltered,evacuatedAndSheltered','DataType': 'String','Notes': 'Q6: Comma-separated list from first to next-to-last hurricane'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = []
            for location in locations[:-1]:
                if len(location) == 1 and agent.demographics['home'] in location:
                    record['Value'].append('home')
                elif 'evacuated' in location:
                    if [loc for loc in location if loc[:7] == 'shelter']:
                        record['Value'].append('evacuatedAndSheltered')
                    else:
                        record['Value'].append('evacuated')
                elif [loc for loc in location if loc[:7] == 'shelter']:
                    record['Value'].append('sheltered')
                else:
                    raise ValueError('Unable to determine behavior: %s' % (location))
            record['Value'] = ','.join(record['Value'])
            output.append(record)

            var = '%s %d Injured Previous Hurricanes' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': 'yes,no','DataType': 'Boolean','Notes': 'Q7: Comma-separated list from first to next-to-last hurricane'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = []
            health = [float(accessibility.getInitialState(args,name,'health',world,states,h['End'])) for h in hurricanes[:last['Hurricane']-1]]
            record['Value'] = ','.join(['yes' if value < 0.2 else 'no' for value in health])
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

        for t in range(1,args['span']):
            var = '%s %d Aid Region' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': 'Region[01-16]','DataType': 'String','Notes': 'Q8'}
            output.append({'Timestep': t,'VariableName': var,'EntityIdx': 'Government', 
                'Value':accessibility.getAction(args,'System',world,states,t)['object']})

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
