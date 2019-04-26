import csv
import logging
import os.path
import random

from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename=os.path.join(__file__,'..','TA2A-TA1C-0132.log'))
    random.seed(132)
    args = accessibility.instances[0]

    world = accessibility.loadPickle(args['instance'],args['run'],args['span'])

    hurricanes = accessibility.readHurricanes(args['instance'],args['run'])
    hurricane = hurricanes[6]
    assert hurricane['Hurricane'] == 7
    dayFirst = hurricane['Start']
    dayLast = hurricanes[7]['Start']-1

    data = accessibility.loadRunData(args['instance'],args['run'],dayLast+1)

    population = accessibility.readDemographics(data,last=dayFirst)
    residents = [name for name,record in population.items() if record['Residence'] == 'Region05']
    aid = {day: {name for name in residents if data[name][stateKey(name,'alive')][day] and 
        data[name][actionKey(name)][day]['verb'] == 'decreaseRisk'}
        for day in range(dayFirst,dayLast+1)}

    pool =  [name for name in residents if data[name][stateKey(name,'alive')][dayFirst]]
    pool = random.sample(pool,8)

    network = accessibility.readNetwork(args['instance'],args['run'])
    output = []
    fields = ['Participant']+sorted(accessibility.demographics.keys())+['Vulnerable','# of Friends',
        'Aid if Wealth Loss','Aid if Injury','Aid if Evacuate','New Friends']

    journal = []

    for name in pool:
        agent = world.agents[name]
        output.append(population[name])
        output[-1]['Participant'] = len(output)
        logging.info('Participant %d: %s' % (output[-1]['Participant'],name))
        # b
        value = float(data[name]['__beliefs__'][stateKey(name,'risk')][dayFirst])
        output[-1]['Vulnerable'] = accessibility.toLikert(value)
        # c
        friends = network['friendOf'].get(name,set())
        output[-1]['# of Friends'] = len(friends)
        # d
        value = sum([agent.Rweights[k] for k in ['health','childrenHealth','neighbors']])/sum(agent.Rweights.values())
        response = accessibility.toLikert(value,7)-1
        output[-1]['Aid if Wealth Loss'] = response
        # e
        output[-1]['Aid if Injury'] = response
        # f
        output[-1]['Aid if Evacuate'] = response
        # g
        output[-1]['New Friends'] = 'no'

        # Journal
        for day in range(dayFirst,dayLast+1):
            record = {'Participant': output[-1]['Participant'], 'Timestep': day}
            journal.append(record)
            # 0
            value = float(data[name]['__beliefs__'][stateKey(name,'resources')][day])
            record['Wealth'] = accessibility.toLikert(value)
            # 1
            value = float(data[name]['__beliefs__'][stateKey('Nature','category')][day])
            record['Hurricane Category'] = int(round(float(value)))
            if record['Hurricane Category'] == 0:
                record['Hurricane Category'] = 'N/A'
            # 2
            record['Hurricane Location'] = data[name]['__beliefs__'][stateKey('Nature','location')][day]
            if record['Hurricane Location'] == 'none':
                record['Hurricane Location'] = 'N/A'
            # 3
            value = float(data[name]['__beliefs__'][stateKey('Region','risk')][day])
            record['Regional Damage'] = accessibility.toLikert(value)
            # 4
            record['Regional Aid'] = data['System'][actionKey('System')][day]['object']
            # 5
            value = float(data[name]['__beliefs__'][stateKey(name,'risk')][day])
            record['Injury Likelihood'] = accessibility.toLikert(value,7)-1
            # 6
            if population[name]['Children'] == 0:
                record['Children Injury Likelihood'] = 'N/A'
            else:
                record['Children Injury Likelihood'] = record['Injury Likelihood']
            # 7
            record['Wealth Loss Likelihood'] = 3
            # 8
            if data[name][stateKey(name,'location')][day][:7] == 'shelter':
                record['Shelter Likelihood'] = 'N/A'
            else:
                action = data[name][actionKey(name)][day]
                if action['verb'] == 'moveTo' and action['object'][:7] == 'shelter':
                    record['Shelter Likelihood'] = 6
                else:
                    record['Shelter Likelihood'] = 0
            # 9 & 10
            value = data[name][stateKey(name,'health')][day]
            if value < 0.2:
                record['Severe Injury'] = 'yes'
                record['Minor Injury'] = 'no'
            elif value < 0.5:
                record['Minor Injury'] = 'yes'
                record['Severe Injury'] = 'no'
            else:
                record['Minor Injury'] = 'no'
                record['Severe Injury'] = 'no'
            # 11 & 12
            if population[name]['Children'] == 0:
                record['Severe Child Injury'] = 'N/A'
                record['Minor Child Injury'] = 'N/A'
            else:
                value = data[name][stateKey(name,'childrenHealth')][day]
                if value < 0.2:
                    record['Severe Child Injury'] = 'yes'
                    record['Minor Child Injury'] = 'no'
                elif value < 0.5:
                    record['Minor Child Injury'] = 'yes'
                    record['Severe Child Injury'] = 'no'
                else:
                    record['Minor Child Injury'] = 'no'
                    record['Severe Child Injury'] = 'no'
            # 13
            record['Dissatisfaction'] = accessibility.toLikert(data[name][stateKey(name,'grievance')][day])
            # 14
            record['Location'] = data[name][stateKey(name,'location')][day]
            if record['Location'][:7] == 'shelter':
                record['Location'] = 'shelter'
            elif record['Location'] == population[name]['Residence']:
                record['Location'] = 'home'
            # 15
            record['Severity'] = record['Hurricane Category']
            # 16
            value = float(data[name]['__beliefs__'][stateKey(name,'risk')][day])
            record['Risk'] = accessibility.toLikert(value)  
            # 17.1
            record['Received Govt Aid'] = 'yes' if record['Regional Aid'] == population[name]['Residence'] else 'no'
            # 18
            delta = data[name][stateKey(name,'grievance')][day-1] - data[name][stateKey(name,'grievance')][day]
            record['Satisfied Aid Decision'] = accessibility.toLikert(40*delta+0.5)
            # 19
            if record['Received Govt Aid']:
                record['Satisfied Aid Distribution'] = 3
            else:
                record['Satisfied Aid Distribution'] = 'N/A'
            # 20.1
            record['Received Acquaintance Aid'] = 'yes' if len(aid[day]) > 0 else 'no'
            # 21
            record['Know Shelter Policy'] = 'yes'
            # 22
            assert record['Shelter Likelihood'] != 6
    accessibility.writeOutput(args,output,fields,'TA2A-TA1C-0132-Initial.tsv')
    fields = ['Participant','Timestep','Wealth','Hurricane Category','Hurricane Location','Regional Damage','Regional Aid',
        'Injury Likelihood','Children Injury Likelihood','Wealth Loss Likelihood','Shelter Likelihood','Minor Injury',
        'Severe Injury','Minor Child Injury','Severe Child Injury','Dissatisfaction','Location','Severity','Risk','Received Govt Aid',
        'Satisfied Aid Decision','Satisfied Aid Distribution','Received Acquaintance Aid','Know Shelter Policy']
    accessibility.writeOutput(args,journal,fields,'TA2A-TA1C-0132-Journal.tsv')