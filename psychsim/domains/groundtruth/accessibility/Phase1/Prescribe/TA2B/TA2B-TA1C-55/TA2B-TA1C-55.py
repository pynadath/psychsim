import csv
import logging
import os.path
import random

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.action import *

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename=os.path.join(os.path.dirname(__file__),'TA2B-TA1C-55.log'))
    responses = {1: 'I would be strongly satisfied',
        2: 'I would be somewhat satisfied',
        3: 'I would be neutral',
        4: 'I would be somewhat dissatisfied',
        5: 'I would be strongly dissatisfied'}
    items = ['Condition 1 Satisfaction']+sum([['Condition 1 Category %d Evacuate' % (category+1),'Condition 1 Category %d Stayed Home' % (category+1),
            'Condition 1 Category %d Sheltered' % (category+1)] for category in range(5)],[])
    fields = ['Name','LongName','Values','VarType','DataType','Notes']
    output = []
    for i in range(len(items)):
        if items[i] == 'Condition 1 Satisfaction':
            output.append({'Name': items[i],'LongName': items[i],
                'Values': ','.join(['I would be strongly dissatisfied','I would be somewhat dissatisfied',
                'I would be neutral','I would be somewhat satisfied','I would be strongly satisfied']),'VarType': 'dynamic','DataType': 'String',
                'Notes': 'Q%d' % (i+1)})
        else:
            output.append({'Name': items[i],'LongName': items[i],'Values': 'yes,no','VarType': 'dynamic','DataType': 'Boolean',
                'Notes': 'Q%d' % (i+1)})
    with open(os.path.join(os.path.dirname(__file__),'SimulationDefinition','VariableDefTable.tsv'),'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for record in output:
            writer.writerow(record)
    fields = ['Timestep','Participant','Sheltered']+sorted(accessibility.demographics.keys())+items
    for instance in range(1,15):
        random.seed(55)
        logging.info('Instance %d' % (instance))
        args = accessibility.instances[instance-1]
        config = accessibility.getConfig(args['instance'])
        data = accessibility.loadRunData(args['instance'],args['run'],args['span'],subs=['Input'] if instance > 2 else [None])
        print('Unpickling',instance)
        world = accessibility.loadPickle(args['instance'],args['run'],args['span']+(1 if instance == 2 or instance > 8 else 0),
            sub='Input' if instance > 2 else None)
        print('done')
        demos = accessibility.readDemographics(data,last=args['span'])
        residents = {}
        for name,demo in demos.items():
            residents[demo['Residence']] = residents.get(demo['Residence'],set()) | {name}
        for name in world.agents:
            if name[:5] == 'Actor':
                accessibility.backwardDemographics(world.agents[name],demos)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run'],'Input' if instance > 2 else None) 
            if h['End'] < args['span']]
        hurricane = hurricanes[-1]
        if instance > 2:
            participants = accessibility.readParticipants(args['instance'],args['run'],os.path.join('Input','psychsim.log'))['ActorPostTable']
        else:
            participants = accessibility.readParticipants(args['instance'],args['run'])['ActorPostTable']
        population = [name for name in accessibility.getPopulation(data) if name in participants.values()]
        shelters = {name for name in world.agents if name[:6] == 'Region' and stateKey('Region','shelterRisk') in world.variables}
        shelterers = {name for name in population if len([t for t,loc in data[name][stateKey(name,'location')].items()
            if loc[:7] == 'shelter']) > 0}
        size = 6
        if len(shelterers) > 10:
            pool = random.sample(shelterers,10)
        else:
            pool = list(shelterers)
            size += 10-len(shelterers) 
        pool += random.sample([name for name in population if name not in shelterers],size)
        world.agents['System'].TA2BTA1C54 = False
        world.agents['System'].TA2BTA1C52 = False
        output = []
        for name in pool:
            participantID = accessibility.getParticipantID(name,participants)
            logging.info('Participant %d: %s' % (participantID,name))
            record = {'Timestep': args['span'],'Sheltered': 'yes' if name in shelterers else 'no',
                'Participant': participantID}
            record.update(demos[name])
            output.append(record)
            # 1 (This already is the government aid policy)
            try:
                record['Condition 1 Satisfaction'] = responses[accessibility.toLikert(data[name][stateKey(name,'grievance')][args['span']])]
            except KeyError:
                record['Condition 1 Satisfaction'] = responses[accessibility.toLikert(data[name][stateKey(name,'grievance')][args['span']-1])]
            logging.info('Grievance %f' % (data[name][stateKey(name,'grievance')][args['span']-1]))
            # 2-6
            for category in range(5):
                locations = []
                print(instance,name,category)
                belief = accessibility.setHurricane(world,category+1,hurricane['Actual Location'][0],name,locations=locations,myStart=demos[name]['Residence'],debug=True)
                locations = set(locations)
                record['Condition 1 Category %d Evacuate' % (category+1)] = 'yes' if 'evacuated' in locations else 'no'
                record['Condition 1 Category %d Stayed Home' % (category+1)] = 'yes' if demos[name]['Residence'] in locations else 'no'
                record['Condition 1 Category %d Sheltered' % (category+1)] = 'yes' if {loc for loc in locations if loc[:7] == 'shelter'} else 'no'
        accessibility.writeOutput(args,output,fields,'TA2B-TA1C-55AidRedistribution.tsv',
            os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
