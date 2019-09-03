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
        participants = accessibility.readParticipants(args['instance'],args['run'],splitHurricanes=True)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        actors = accessibility.getLivePopulation(args,world,states,args['span'])
        output = []
        oldSurvey = {int(entry['Participant']): entry for entry in accessibility.loadMultiCSV('ActorPostTable.tsv',args['instance'],args['run'],['Backup'],False)}
        for original in hurricanes:
            pool = participants['Post-survey %d' % (original['Hurricane'])]
            for partID,name in sorted(pool.items()):
                for delta in range(2 if original['Hurricane'] < len(hurricanes) else 1):
                    hurricane = hurricanes[original['Hurricane']+delta-1]
                    if delta == 0:
                        t = int(oldSurvey[partID]['Timestep'])
                    else:
                        if actors[name] is not None and actors[name] <= hurricane['End']:
                            # Actor died during the subsequent hurricane
                            continue
                        if hurricane['Hurricane'] < len(hurricanes):
                            t = random.randint(hurricane['End']+1,hurricanes[hurricane['Hurricane']]['Start']-1)
                        else:
                            t = random.randint(hurricane['End']+1,args['span']-1)
                    logging.info('Participant %d Hurricane %d: %s' % (partID,hurricane['Hurricane'],name))
                    agent = world.agents[name]
                    record = {}
                    output.append(record)
                    var = 'Participant'
                    if not defined:
                        variables.append({'Name': var,'Values':'[1+]','VarType': 'fixed','DataType': 'Integer'})
                    record[var] = partID
                    var = 'Hurricane'
                    if not defined:
                        variables.append({'Name': var,'Values':'[1+]','DataType': 'Integer'})
                    record[var] = hurricane['Hurricane']
                    record['Timestep'] = t
                    if not defined:
                        variables += accessibility.boilerPlate
                    record.update(accessibility.getCurrentDemographics(args,name,world,states,config,t))
                    var = 'Number of Friends'
                    if not defined:
                        variables.append({'Name': var,'Values': '[1-999]','DataType': 'Integer','Notes': 'Q1'})
                    friends = [friend for friend in agent.getFriends() if actors[friend] is None or actors[friend] > t]
                    record[var] = len(friends)
                    var = 'Number of Friends Evacuated'
                    if not defined:
                        variables.append({'Name': var,'Values': '[1-999]','DataType': 'Integer','Notes': 'Q2'})
                    record[var] = 0
                    var = 'Number of Friends Sheltered'
                    if not defined:
                        variables.append({'Name': var,'Values': '[1-999]','DataType': 'Integer','Notes': 'Q3'})
                    record[var] = 0
                    var = 'Number of Friends Stayed Home'
                    if not defined:
                        variables.append({'Name': var,'Values': '[1-999]','DataType': 'Integer','Notes': 'Q4'})
                    record[var] = len(friends)
                    for friend in friends:
                        locations = {loc.first() for loc in accessibility.getInitialState(args,friend,'location',world,states,
                            (hurricane['Landfall'],hurricane['End']+1))}
                        if 'evacuated' in locations:
                            record['Number of Friends Evacuated'] += 1
                            record['Number of Friends Stayed Home'] -= 1
                        for loc in locations:
                            if loc[:7] == 'shelter':
                                record['Number of Friends Sheltered'] += 1
                                record['Number of Friends Stayed Home'] -= 1
                                break
                    var = 'Number of Friends Shared Category'
                    if not defined:
                        variables.append({'Name': var,'Values': '[1-999]','DataType': 'Integer','Notes': 'Q5'})
                    record[var] = len(friends) if config.getboolean('Actors','messages') else 0
                    inRegion = [day for day in range(hurricane['Landfall'],hurricane['End']) 
                        if hurricane['Actual Location'][day-hurricane['Start']] == agent.demographics['home']]
                    var = 'Expected Category in Region'
                    if not defined:
                        variables.append({'Name': var,'Values': '[1-5],does not apply','DataType': 'Integer','Notes': 'Q6'})
                    if inRegion:
                        record[var] = int(round(accessibility.getInitialState(args,'Nature','category',world,states,inRegion[0],name).expectation()))
                    else:
                        record[var] = 'does not apply'
                    var = 'Actual Category in Region'
                    if not defined:
                        variables.append({'Name': var,'Values': '[1-5],does not apply','DataType': 'Integer','Notes': 'Q7'})
                    if inRegion:
                        categories = [int(round(cat.expectation())) 
                            for cat in accessibility.getInitialState(args,'Nature','category',world,states,inRegion,name)]
                        record[var] = max(categories)
                    else:
                        record[var] = 'does not apply'
                    var = 'Expected Category'
                    if not defined:
                        variables.append({'Name': var,'Values': '[1-5],does not apply','DataType': 'Integer','Notes': 'Q8'})
                    record[var] = int(round(accessibility.getInitialState(args,'Nature','category',world,states,hurricane['Landfall'],name).expectation()))
                    var = 'Actual Category'
                    if not defined:
                        variables.append({'Name': var,'Values': '[1-5],does not apply','DataType': 'Integer','Notes': 'Q9'})
                    categories = [int(round(cat.expectation())) 
                        for cat in accessibility.getInitialState(args,'Nature','category',world,states,(hurricane['Landfall'],hurricane['End']),name)]
                    record[var] = max(categories)
                    for regionIndex in range(config.getint('Regions','regions')):
                        region = 'Region%02d' % (regionIndex+1)
                        var = 'Friends %s' % (region)
                        if not defined:
                            variables.append({'Name': var,'Values': '[1-999]','DataType': 'Integer','Notes': 'Q10'})
                        record[var] = len([friend for friend in friends if world.agents[friend].demographics['home'] == region])
                    var = 'Injured Friends'
                    if not defined:
                        variables.append({'Name': var,'Values': '[0+]','DataType': 'Integer','Notes': 'Q11'})
                    record[var] = 0
                    neighborFriends = set(friends) & agent.getNeighbors()
                    if neighborFriends:
                        assist = [day for day in range(hurricane['Start'],hurricane['End']) 
                            if accessibility.getAction(args,name,world,states,day)['verb'] == 'decreaseRisk']
                        if assist:
                            for friend in neighborFriends:
                                if min(map(float,accessibility.getInitialState(args,friend,'health',world,states,assist))) < 0.2:
                                    record[var] += 1
                                    logging.warning('%s "helped" %s somewhere in %s' % (name,friend,assist))
                                    break
                    var = 'Friends\' Loss'
                    if not defined:
                        variables.append({'Name': var,'Values': '[0-999]','DataType': 'Integer','Notes': 'Q12'})
                    record[var] = 0
                    var = 'Ethnicity of Friends'
                    if not defined:
                        variables.append({'Name': var,'Values': '[0-999]','DataType': 'Integer','Notes': 'Q13'})
                    record[var] = len([friend for friend in friends if world.agents[friend].demographics['ethnicGroup'] == 'majority'])
                    var = 'Gender of Friends'
                    if not defined:
                        variables.append({'Name': var,'Values': '[0-999]','DataType': 'Integer','Notes': 'Q14'})
                    record[var] = len([friend for friend in friends if world.agents[friend].demographics['gender'] == 'male'])
                    var = 'Age of Friends'
                    if not defined:
                        variables.append({'Name': var,'Values': '[0-999]','DataType': 'Integer','Notes': 'Q15'})
                    record[var] = len([friend for friend in friends if world.agents[friend].demographics['age'] > 50])
                    var = 'Religion of Friends'
                    if not defined:
                        variables.append({'Name': var,'Values': '[0-999]','DataType': 'Integer','Notes': 'Q16'})
                    record[var] = len([friend for friend in friends if world.agents[friend].demographics['religion'] == 'majority'])
                    if cmd['debug']:
                        print(record)
                    if not defined:
                        if not cmd['debug']:
                            accessibility.writeVarDef(os.path.dirname(__file__),variables)
                        defined = True
        if not cmd['debug']:
            accessibility.writeOutput(args,output,[var['Name'] for var in variables],'%s.tsv' % (os.path.splitext(os.path.basename(__file__))[0]),
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
