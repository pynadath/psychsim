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
    preVars = []
    postVars = []
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
        for hurricane in hurricanes[1:]:
            pool = participants['Pre-survey %d' % (hurricane['Hurricane']-1)]
            for partID,name in sorted(pool.items()):
                t = random.choice(list(range(hurricane['Start'],hurricane['Landfall'])))
                if actors[name] is None or actors[name] > t:
                    record = survey.preSurvey(args,name,world,states,config,t,hurricane,preVars if len(preVars) == 0 else None)
                    record['Participant'] = partID
                    output.append(record)
                    logging.info('Participant %d (%s) answered paired pre-survey %d' % (partID,name,hurricane['Hurricane']))
                    if cmd['debug']:
                        print(record)
                    if not defined:
                        defined = True
                else:
                    logging.warning('Participant %d (%s) not available for pre-survey %d' % (partID,name,hurricane['Hurricane']))
        output.sort(key=lambda e: (e['Participant'],e['Timestep']))
        if not cmd['debug']:
            accessibility.writeOutput(args,output,[var['Name'] for var in preVars],'%s-Pre.tsv' % (os.path.splitext(os.path.basename(__file__))[0]),
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
        continue
        defined = False
        oldSurvey = {int(entry['Participant']): entry for entry in accessibility.loadMultiCSV('ActorPostTable.tsv',args['instance'],args['run'],['Backup'],False)}
        output = []
        for hurricane in hurricanes[:-1]:
            aid = accessibility.getAction(args,'System',world,states,(hurricane['Start'],hurricane['End']+1))
            pool = participants['Post-survey %d' % (hurricane['Hurricane'])]
            for partID,name in sorted(pool.items()):
                agent = world.agents[name]
                record = oldSurvey[partID]
                partID = record['Participant'] = int(record['Participant'])
                t = record['Timestep'] = int(record['Timestep'])
                output.append(record)
                damage = accessibility.getInitialState(args,record['Residence'],'risk',world,states,(hurricane['Start'],hurricane['End']+1))
                record['Property'] = accessibility.toLikert(max(map(float,damage)),7)
                count = len([act for act in aid if act['object'] == record['Residence']])
                record['Assistance'] = accessibility.toLikert(float(count)/float(len(aid)),7)
                # How many friends still alive
                friends = [friend for friend in agent.getFriends() if actors[friend] is None or actors[friend] > t]
                record['Number of Friends'] = len(friends)
                record['Number of Friends Evacuated'] = 0
                record['Number of Friends Sheltered'] = 0
                for friend in friends:
                    locations = {loc.first() for loc in accessibility.getInitialState(args,friend,'location',world,states,
                        (hurricane['Landfall'],hurricane['End']+1))}
                    if 'evacuated' in locations:
                        record['Number of Friends Evacuated'] += 1
                    for loc in locations:
                        if loc[:7] == 'shelter':
                            record['Number of Friends Sheltered'] += 1
                            break
                employed = [emp.first() for emp in accessibility.getInitialState(args,name,'employed',world,states,(hurricane['Landfall'],hurricane['End']+1))]
                if config.getboolean('Shelter','job'):
                    sheltered = [False for t in range(len(employed))]
                else:
                    sheltered = [loc.first()[:7] == 'shelter' for loc in accessibility.getInitialState(args,name,'location',world,states,
                        (hurricane['Landfall'],hurricane['End']))]
                possible = employed.count(True)
                worked = [employed[t] and not sheltered[t] for t in range(len(employed))].count(True)
                if possible == 0:
                    # Unemployed
                    record['Days Worked'] = 'N/A'
                    record['Missed Work'] = 'N/A'
                else:
                    record['Days Worked'] = worked
                    record['Missed Work'] = possible - worked
        for hurricane in hurricanes[1:]:
            pool = participants['Post-survey %d' % (hurricane['Hurricane']-1)]
            for partID,name in sorted(pool.items()):
                t = random.choice(list(range(hurricane['End']+1,
                    hurricanes[hurricane['Hurricane']]['Start'] if hurricane['Hurricane'] < len(hurricanes) else args['span'])))
                if actors[name] is None or actors[name] > t:
                    agent = world.agents[name]
                    record = survey.postSurvey(args,name,world,states,config,t,hurricane,postVars if len(postVars) == 0 else None)
                    record['Participant'] = partID
                    assert isinstance(record['Participant'],int)
                    assert isinstance(record['Timestep'],int)
                    output.append(record)
                    logging.info('Participant %d (%s) answered paired post-survey %d' % (partID,name,hurricane['Hurricane']))
                    var = 'Property'
                    if not defined:
                        postVars.append({'Name': var,'Values': '[1-7]','DataType': 'Integer','Notes': '5.vi'})
                    damage = accessibility.getInitialState(args,record['Residence'],'risk',world,states,(hurricane['Start'],hurricane['End']+1))
                    record[var] = accessibility.toLikert(max(map(float,damage)),7)
                    var = 'Assistance'
                    count = len([act for act in aid if act['object'] == record['Residence']])
                    if not defined:
                        postVars.append({'Name': var,'Values': '[1-7]','DataType': 'Integer','Notes': '5.vii'})
                    record[var] = accessibility.toLikert(float(count)/float(len(aid)),7)
                    # How many friends still alive
                    var = 'Number of Friends'
                    if not defined:
                        postVars.append({'Name': var,'Values': '[1-999]','DataType': 'Integer','Notes': '5.viii'})
                    friends = [friend for friend in agent.getFriends() if actors[friend] is None or actors[friend] > t]
                    record[var] = len(friends)
                    var = 'Number of Friends Evacuated'
                    if not defined:
                        postVars.append({'Name': var,'Values': '[1-999]','DataType': 'Integer','Notes': '5.ix'})
                    record[var] = 0
                    var = 'Number of Friends Sheltered'
                    if not defined:
                        postVars.append({'Name': var,'Values': '[1-999]','DataType': 'Integer','Notes': '5.x'})
                    record[var] = 0
                    for friend in friends:
                        locations = {loc.first() for loc in accessibility.getInitialState(args,friend,'location',world,states,
                            (hurricane['Landfall'],hurricane['End']+1))}
                        if 'evacuated' in locations:
                            record['Number of Friends Evacuated'] += 1
                        for loc in locations:
                            if loc[:7] == 'shelter':
                                record['Number of Friends Sheltered'] += 1
                                break
                    if not defined:
                        postVars.append({'Name': 'Missed Work','Values': '[1-365]','DataType': 'Integer','Notes': '5.xi'})
                    if not defined:
                        postVars.append({'Name': 'Days Worked','Values': '[1-365]','DataType': 'Integer','Notes': '5.xi'})
                    employed = [emp.first() for emp in accessibility.getInitialState(args,name,'employed',world,states,(hurricane['Landfall'],hurricane['End']+1))]
                    if config.getboolean('Shelter','job'):
                        sheltered = [False for t in range(len(employed))]
                    else:
                        sheltered = [loc.first()[:7] == 'shelter' for loc in accessibility.getInitialState(args,name,'location',world,states,
                            (hurricane['Landfall'],hurricane['End']))]
                    possible = employed.count(True)
                    worked = [employed[t] and not sheltered[t] for t in range(len(employed))].count(True)
                    if possible == 0:
                        # Unemployed
                        record['Days Worked'] = 'N/A'
                        record['Missed Work'] = 'N/A'
                    else:
                        record['Days Worked'] = worked
                        record['Missed Work'] = possible - worked
                    if cmd['debug']:
                        print(record)
                    if not defined:
#                        if not cmd['debug']:
#                            accessibility.writeVarDef(os.path.dirname(__file__),preVars+[var for var in postVars if var not in preVars])
                        defined = True
                else:
                    logging.warning('Participant %d (%s) not available for post-survey %d' % (partID,name,hurricane['Hurricane']))
        output.sort(key=lambda e: (e['Participant'],e['Timestep']))
        if not cmd['debug']:
            accessibility.writeOutput(args,output,[var['Name'] for var in postVars],'%s-Post.tsv' % (os.path.splitext(os.path.basename(__file__))[0]),
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
