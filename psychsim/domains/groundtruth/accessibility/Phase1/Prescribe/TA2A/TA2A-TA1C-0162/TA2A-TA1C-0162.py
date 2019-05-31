import csv
import logging
import os.path
import random

from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename=os.path.join(os.path.dirname(__file__),'TA2A-TA1C-0162.log'))
    random.seed(162)
    for instance in range(9,15):
        args = accessibility.instances[instance-1]
        world = accessibility.loadPickle(args['instance'],args['run'],args['span']+1,'Input')
        hurricanes = accessibility.readHurricanes(args['instance'],args['run'],'Input')
        hurricane = hurricanes[-1]
        assert hurricane['End'] < args['span']
        dayFirst = hurricane['Start']-2
        dayLast = args['span']

        data = accessibility.loadRunData(args['instance'],args['run'],args['span']+1,subs=['Input'])
        population = {name for name in data if name[:5] == 'Actor' and data[name][stateKey(name,'alive')][dayFirst]}
        demos = accessibility.readDemographics(data,last=dayFirst)
        pool = random.sample(population,8)

        aid = {day: {name for name in population if data[name][stateKey(name,'alive')][day] and 
            data[name][actionKey(name)][day]['verb'] == 'decreaseRisk'}
            for day in range(dayFirst,dayLast)}

        network = accessibility.readNetwork(args['instance'],args['run'],'Input')
        output = []
        fields = ['Participant','Timestep']+sorted(accessibility.demographics.keys())+['Vulnerable','# of Friends',
            'Aid if Wealth Loss','New Friends']

        journal = []

        for name in pool:
            agent = world.agents[name]
            output.append(demos[name])
            output[-1]['Participant'] = len(output)
            output[-1]['Timestep'] = hurricane['Start']
            logging.info('Participant %d: %s' % (output[-1]['Participant'],name))
            # b
            value = float(data[name]['__beliefs__'][stateKey(name,'risk')][hurricane['Start']])
            output[-1]['Vulnerable'] = accessibility.toLikert(value)
            # c
            friends = {friend for friend in network['friendOf'].get(name,set()) if data[friend][stateKey(friend,'alive')][hurricane['Start']]}
            output[-1]['# of Friends'] = len(friends)
            # d
            value = sum([agent.Rweights[k] for k in ['health','childrenHealth','neighbors']])/sum(agent.Rweights.values())
            response = accessibility.toLikert(value,7)-1
            output[-1]['Aid if Wealth Loss'] = response
            # e
            output[-1]['New Friends'] = 'no'

            # Journal
            for day in range(dayFirst,dayLast+1):
                record = {'Participant': output[-1]['Participant'], 'Timestep': day}
                journal.append(record)
                # 0
                value = float(data[name]['__beliefs__'][stateKey(name,'resources')][day])
                record['Wealth'] = accessibility.toLikert(value)
                # 1
                if friends:
                    msgs = ['%d' % (int(round(float(data[friend]['__beliefs__'][stateKey('Nature','category')][day])))) for friend in friends]
                    record['Category from Friends'] = ','.join(msgs)
                else:
                    record['Category from Friends'] = 'N/A'
                # 7
                record['Location'] = data[name][stateKey(name,'location')][day]
                if record['Location'][:7] == 'shelter':
                    record['Location'] = 'shelter'
                elif record['Location'] == demos[name]['Residence']:
                    record['Location'] = 'home'
                # 8 & 9
                value = float(data[name]['__beliefs__'][stateKey(name,'risk')][day])
                record['Minor Injury Likelihood'] = accessibility.toLikert(value,7)-1
                record['Serious Injury Likelihood'] = accessibility.toLikert(value/2,7)-1
                # 10
                if data[name][stateKey(name,'location')][day][:7] == 'shelter':
                    record['Shelter Likelihood'] = 'N/A'
                else:
                    action = data[name][actionKey(name)].get(day,{'verb': 'stayInLocation'})
                    if action['verb'] == 'moveTo' and action['object'][:7] == 'shelter':
                        record['Shelter Likelihood'] = 6
                    else:
                        record['Shelter Likelihood'] = 0
                # 11
                record['Dissatisfaction'] = accessibility.toLikert(data[name][stateKey(name,'grievance')][day])
                # 12 & 13
                value = data[name][stateKey(name,'health')][day]
                if value < 0.2:
                    record['Serious Injury'] = 'yes'
                    record['Minor Injury'] = 'no'
                elif value < 0.5:
                    record['Minor Injury'] = 'yes'
                    record['Serious Injury'] = 'no'
                else:
                    record['Minor Injury'] = 'no'
                    record['Serious Injury'] = 'no'
                # 14 & 15
                if demos[name]['Children'] == 0:
                    record['Serious Child Injury'] = 'N/A'
                    record['Minor Child Injury'] = 'N/A'
                else:
                    value = data[name][stateKey(name,'childrenHealth')][day]
                    if value < 0.2:
                        record['Serious Child Injury'] = 'yes'
                        record['Minor Child Injury'] = 'no'
                    elif value < 0.5:
                        record['Minor Child Injury'] = 'yes'
                        record['Serious Child Injury'] = 'no'
                    else:
                        record['Minor Child Injury'] = 'no'
                        record['Serious Child Injury'] = 'no'
                # 16
                record['Received Govt Aid'] = 'yes' if data['System'][actionKey('System')].get(day,{'object':None}) == demos[name]['Residence'] else 'no'
                # 17
                record['Received Acquaintance Aid'] = 'yes' if len([friend for friend in aid.get(day,[]) if demos[friend]['Residence'] == demos[name]['Residence']]) > 0 else 'no'
                # 18
                record['Gave Aid'] = 'yes' if name in aid.get(day,[]) else 'no'
                # 19
                delta = data[name][stateKey(name,'resources')][day]-data[name][stateKey(name,'resources')][day-1]
                if delta < 0.:
                    record['Wealth Change'] = -accessibility.toLikert(-delta)
                else:
                    record['Wealth Change'] = accessibility.toLikert(delta)
        accessibility.writeOutput(args,output,fields,'TA2A-TA1C-0162-Initial.tsv',
            os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
        fields = ['Participant','Timestep','Wealth','Category from Friends','Location',
            'Minor Injury Likelihood','Serious Injury Likelihood','Shelter Likelihood','Dissatisfaction','Minor Injury','Serious Injury',
            'Minor Child Injury','Serious Child Injury','Received Govt Aid','Received Acquaintance Aid','Gave Aid','Wealth Change']
        accessibility.writeOutput(args,journal,fields,'TA2A-TA1C-0162-Journal.tsv',
            os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))