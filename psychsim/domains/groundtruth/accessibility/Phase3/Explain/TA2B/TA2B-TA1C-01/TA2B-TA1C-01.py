from argparse import ArgumentParser
import logging
import os.path
import sys

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.domains.groundtruth.simulation import survey

def loc2value(location,agent):
    if len(location) == 1 and agent.demographics['home'] in location:
        return 'home'
    elif 'evacuated' in location:
        if [loc for loc in location if loc[:7] == 'shelter']:
            return 'evacuatedAndSheltered'
        else:
            return 'evacuated'
    elif [loc for loc in location if loc[:7] == 'shelter']:
        return 'sheltered'
    else:
        raise ValueError('Unable to determine behavior: %s' % (location))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    reqNum = int(os.path.splitext(os.path.basename(__file__))[0].split('-')[2])
    team = os.path.splitext(os.path.basename(__file__))[0].split('-')[0]
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    cmd = vars(parser.parse_args())
    demos = ['Gender','Children','Religion','Ethnicity']
    variables = {field: accessibility.boilerDict[field] for field in demos}
    for instance,args in accessibility.instanceArgs('Phase3'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        world = accessibility.unpickle(instance)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        states = {}
        actors = {name: t for name,t in accessibility.getLivePopulation(args,world,states,args['span']).items() if t is not None}
        participants = accessibility.readParticipants(args['instance'],args['run'])

        locations = {name: [] for name in actors}
        healths = {name: [] for name in actors}
        aid = {}
        for hurricane in hurricanes:
            for name in actors:
                location = set()
                for t in range(hurricane['Start'],hurricane['End']+1):
                    try:
                        location.add(accessibility.getInitialState(args,name,'location',world,states,t,unique=True))
                    except KeyError:
                        if location:
                            locations[name].append(location)
                        break
                else:
                    locations[name].append(location)
                if len(locations[name]) < hurricane['Hurricane']:
                    # Died before this hurricane
                    continue
                try:
                    healths[name].append(accessibility.getInitialState(args,name,'health',world,states,hurricane['End'],unique=True))
                except KeyError:
                    pass
                for friend in world.agents[name].getFriends():
                    if friend in actors:
                        continue
                    if friend not in locations:
                        locations[friend] = []
                    location = set()
                    for t in range(hurricane['Start'],hurricane['End']+1):
                        try:
                            location.add(accessibility.getInitialState(args,friend,'location',world,states,t,unique=True))
                        except KeyError:
                            # Dead, don't keep going
                            if location:
                                locations[friend].append(location)
                            break
                    else:
                        locations[friend].append(location)
                for t in range(hurricane['Start'],hurricane['End']+1):
                    aid[t] = accessibility.getAction(args,'System',world,states,t)['object']
            states.clear()

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
            location = accessibility.getInitialState(args,name,'location',world,states,t-1).first()
            if location[:6] == 'Region':
                record['Value'] = 'home'
            elif location[:7] == 'shelter':
                record['Value'] = 'shelter'
            else:
                record['Value'] = location
            output.append(record)

            last = accessibility.findHurricane(t,hurricanes,True)
            centers = [s.first() for s in accessibility.getInitialState(args,'Nature','location',world,states,(last['Landfall'],last['End']))]
            distance = [(world.agents[centers[t]].distance(agent.demographics['home']),t) for t in range(len(centers))]
            closestT = last['Landfall']+min(distance)[1]

            var = '%s %d Injured' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': 'yes,no','DataType': 'Boolean','Notes': 'Q3'}
            record = dict(root)
            record['VariableName'] = var
            record['Timestep'] = last['Start']-1
            health = accessibility.getInitialState(args,name,'health',world,states,last['Start']-1)
            record['Value'] = 'yes' if float(health) < 0.2 else 'no'
            output.append(record)

            var = '%s %d Category' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': '[1-5]','DataType': 'Integer','Notes': 'Q4'}
            record = dict(root)
            record['VariableName'] = var
            value = accessibility.getInitialState(args,'Nature','category',world,states,closestT)
            assert len(value) == 1,'Uncertain hurricane category on day %d' % (closestT)
            record['Value'] = value.first()
            record['Timestep'] = closestT
            output.append(record)

            var = '%s %d Action Previous Hurricanes' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': 'home,evacuated,sheltered,evacuatedAndSheltered','DataType': 'String','Notes': 'Q5: Comma-separated list from first to last hurricane'}
            record = dict(root)
            record['VariableName'] = var
            myActions = [loc2value(loc,agent) for loc in locations[name]]
            record['Value'] = ','.join(myActions)
            output.append(record)

            var = '%s %d Friends Same Previous Hurricanes' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': '[0+]','DataType': 'Integer','Notes': 'Q6: Comma-separated list from first to last hurricane'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = ','.join(['%d' % (len([friend for friend in agent.getFriends() 
                if len(locations[friend]) > h+1 and loc2value(locations[friend][h],world.agents[friend]) == myActions[h]]))
                for h in range(len(myActions))])
            output.append(record)

            var = '%s %d Injured Previous Hurricanes' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': 'yes,no','DataType': 'Boolean','Notes': 'Q7: Comma-separated list from first to last hurricane'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = ','.join(['yes' if value < 0.2 else 'no' for value in healths[name]])
            output.append(record)

            surveyID = accessibility.participantMatch(name,participants)
            if surveyID is not None:
                var = '%s %d Survey ID' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'Actor[Pre,Post] [1+] Hurricane [1+]','DataType': 'String'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = surveyID
                output.append(record)

        for t in range(1,args['span']):
            var = '%s %d Aid Region' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': 'Region[01-16]','DataType': 'String','Notes': 'Q8'}
            try:
                output.append({'Timestep': t,'VariableName': var,'EntityIdx': 'Government', 'Value': aid[t]})
            except KeyError:
                output.append({'Timestep': t,'VariableName': var,'EntityIdx': 'Government', 
                    'Value':accessibility.getAction(args,'System',world,states,t)['object']})
                states.clear()

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
