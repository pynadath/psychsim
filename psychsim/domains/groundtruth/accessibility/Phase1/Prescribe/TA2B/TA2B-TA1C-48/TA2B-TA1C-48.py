import csv
import logging
import os.path
import random

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.action import *

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename=os.path.join(os.path.dirname(__file__),'TA2B-TA1C-48.log'))
    random.seed(48)
    responses = {1: 'I would be strongly satisfied',
        2: 'I would be somewhat satisfied',
        3: 'I would be neutral',
        4: 'I would be somewhat dissatisfied',
        5: 'I would be strongly dissatisfied'}
    fields = ['Timestep','Participant','Sheltered']+sorted(accessibility.demographics.keys())+['Condition 1 Satisfaction']+\
        sum([['Condition 1 Category %d Evacuate' % (category+1),'Condition 1 Category %d Stayed Home' % (category+1),
            'Condition 1 Category %d Sheltered' % (category+1)] for category in range(5)],[])+['Original Conditions Satisfaction']+\
        sum([['Original Conditions Category %d Evacuate' % (category+1),'Original Conditions Category %d Stayed Home' % (category+1),
            'Original Conditions Category %d Sheltered' % (category+1)] for category in range(5)],[])
    for instance in range(9,15):
        logging.info('Instance %d' % (instance))
        args = accessibility.instances[instance-1]
        config = accessibility.getConfig(args['instance'])
        data = accessibility.loadRunData(args['instance'],args['run'],args['span'],subs=['Input'] if instance > 2 else [None])
        world = accessibility.loadPickle(args['instance'],args['run'],args['span']+1,sub='Input' if instance > 2 else None)
        demos = accessibility.readDemographics(data,last=args['span'])
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run'],'Input' if instance > 2 else None) 
            if h['End'] < args['span']]
        hurricane = hurricanes[-1]
        if instance > 2:
            participants = accessibility.readParticipants(args['instance'],args['run'],os.path.join('Input','psychsim.log'))['ActorPostTable']
        else:
            participants = accessibility.readParticipants(args['instance'],args['run'])['ActorPostTable']
        population = [name for name in accessibility.getPopulation(data) if name in participants.values()]
        shelterers = {name for name in population if len([t for t,loc in data[name][stateKey(name,'location')].items()
            if loc[:7] == 'shelter']) > 0}
        size = 6
        if len(shelterers) > 10:
            pool = random.sample(shelterers,10)
        else:
            pool = list(shelterers)
            size += 10-len(shelterers) 
        pool += random.sample([name for name in population if name not in shelterers],size)
        output = []
        for name in pool:
            participantID = accessibility.getParticipantID(name,participants)
            logging.info('Participant %d: %s' % (participantID,name))
            record = {'Timestep': args['span'],'Sheltered': 'yes' if name in shelterers else 'no',
                'Participant': participantID}
            record.update(demos[name])
            # 1
            oldGrievance = data[name][stateKey(name,'grievance')][1 if args['span'] < 365 else 365]
            try:
                newGrievance = data[name][stateKey(name,'grievance')][args['span']]
            except KeyError:
                newGrievance = data[name][stateKey(name,'grievance')][args['span']-1]
            tax = accessibility.likert[5][config.getint('Actors','grievance_delta')-1] / len([r for r in data if r[:6] == 'Region'])
            response = newGrievance+tax*(1.-newGrievance)
            if newGrievance > oldGrievance:
                # Grievance went up
                delta = (newGrievance-oldGrievance)/(1.-oldGrievance)
                response += delta*(1.-response)
            else:
                # Grievance went down
                delta = (newGrievance-oldGrievance)/oldGrievance
                response += delta*response
            record['Condition 1 Satisfaction'] = responses[accessibility.toLikert(response)]
            # 2-6
            allocate = ActionSet([Action({'subject': 'System','verb': 'allocate','object': demos[name]['Residence']})])
            risk = stateKey(demos[name]['Residence'],'risk')
            oldTree = world.dynamics[risk][allocate]
            impact = accessibility.likert[5][config.getint('System','system_impact')-1]
            assert impact < 0.5
            impact *= 1.5
            newTree = makeTree(approachMatrix(risk,impact,0.))
            world.dynamics[risk][allocate] = newTree
            for category in range(5):
                locations = []
                belief = accessibility.setHurricane(world,category+1,hurricane['Actual Location'][0],name,locations=locations,myStart=demos[name]['Residence'],debug=True)
                locations = set(locations)
                record['Condition 1 Category %d Evacuate' % (category+1)] = 'yes' if 'evacuated' in locations else 'no'
                record['Condition 1 Category %d Stayed Home' % (category+1)] = 'yes' if demos[name]['Residence'] in locations else 'no'
                record['Condition 1 Category %d Sheltered' % (category+1)] = 'yes' if {loc for loc in locations if loc[:7] == 'shelter'} else 'no'
            world.dynamics[risk][allocate] = oldTree
            # 7
            if newGrievance > oldGrievance:
                # Grievance went up
                delta = (newGrievance-oldGrievance)/(1.-oldGrievance)
                response = newGrievance+delta*(1.-newGrievance)
            else:
                # Grievance went down
                delta = (newGrievance-oldGrievance)/oldGrievance
                response = newGrievance+delta*newGrievance
            record['Original Conditions Satisfaction'] = responses[accessibility.toLikert(response)]
            # 8-12
            for category in range(5):
                locations = []
                belief = accessibility.setHurricane(world,category+1,hurricane['Actual Location'][0],name,locations=locations,myStart=demos[name]['Residence'],debug=True)
                locations = set(locations)
                record['Original Conditions Category %d Evacuate' % (category+1)] = 'yes' if 'evacuated' in locations else 'no'
                record['Original Conditions Category %d Stayed Home' % (category+1)] = 'yes' if demos[name]['Residence'] in locations else 'no'
                record['Original Conditions Category %d Sheltered' % (category+1)] = 'yes' if {loc for loc in locations if loc[:7] == 'shelter'} else 'no'
                if record['Original Conditions Category %d Evacuate' % (category+1)] != record['Condition 1 Category %d Evacuate' % (category+1)] or \
                    record['Original Conditions Category %d Stayed Home' % (category+1)] != record['Condition 1 Category %d Stayed Home' % (category+1)] or \
                    record['Original Conditions Category %d Sheltered' % (category+1)] != record['Condition 1 Category %d Sheltered' % (category+1)] or \
                    record['Original Conditions Satisfaction'] != record['Condition 1 Satisfaction']:
                    print('difference!')
            output.append(record)
        accessibility.writeOutput(args,output,fields,'TA2B-TA1C-48WhatIfSurvey.tsv',
            os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))