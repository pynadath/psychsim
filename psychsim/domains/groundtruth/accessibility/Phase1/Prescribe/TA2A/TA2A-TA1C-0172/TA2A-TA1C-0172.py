import csv
import logging
import os.path
import random

from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename=os.path.join(os.path.dirname(__file__),'TA2A-TA1C-0172.log'))
    random.seed(172)
    trustLevels = [(3,'a'),(1,'b'),(2,'d'),(4,'e')]
    for instance in [1,9,10,11,12,13,14]:
        args = accessibility.instances[instance-1]
        logging.info('Instance %d, run %d' % (args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        network = accessibility.readNetwork(args['instance'],args['run'],'Input' if instance > 2 else None)
        friendTrust = config.getint('Actors','friend_opt_trust')+config.getint('Actors','friend_opt_trust')
        world = accessibility.loadPickle(args['instance'],args['run'],args['span']+(1 if instance == 2 or instance > 8 else 0),
            sub='Input' if instance > 2 else None)
        data = accessibility.loadRunData(args['instance'],args['run'],args['span']+1,subs=['Input'] if instance > 2 else [None])
        population = accessibility.getPopulation(data)
        demos = accessibility.readDemographics(data,last=args['span'])
        pool = random.sample(population,16)
        output = []
        fields = ['Participant','Timestep']+sorted(accessibility.demographics.keys())+\
            ['Trusted Sources','Ever Evacuated','Post-Evacuation Income','Post-Evacuation Income Source']
        for name in pool:
            agent = world.agents[name]
            output.append(demos[name])
            output[-1]['Participant'] = len(output)
            output[-1]['Timestep'] = args['span']
            logging.info('Participant %d: %s' % (output[-1]['Participant'],name))
            # 5
            friends = {friend for friend in network['friendOf'].get(name,set()) if friend in population}
            trust = {'over': config.getint('Actors','friend_opt_trust'),
                'under': config.getint('Actors','friend_pess_trust')}
            trust['none'] = (trust['over']+trust['under'])/2
            myLevels = trustLevels[:]
            if friends:
                myLevels.append((sum([trust[world.agents[friend].distortion] for friend in friends])/len(friends),'c'))
            # Random tie-breaking, because c'mon
            myLevels.sort(reverse=True,key=lambda e: (e[0],random.random()))
            output[-1]['Trusted Sources'] = ','.join([entry[1] for entry in myLevels])
            # 7i
            evacuations = {t for t,action in data[name][actionKey(name)].items() if action['verb'] == 'evacuate'}
            output[-1]['Ever Evacuated'] = 'yes' if evacuations else 'no'
            # 7ii
            if output[-1]['Ever Evacuated'] == 'yes':
                delta = [data[name][stateKey(name,'resources')][t+1]-data[name][stateKey(name,'resources')][t] for t in evacuations]
                deltaBig = [d for d in delta if d>0.2]
                output[-1]['Post-Evacuation Income'] = 'yes' if deltaBig else 'no'
            else:
                output[-1]['Post-Evacuation Income'] = 'N/A'
            # 7iii
            if output[-1]['Post-Evacuation Income'] == 'yes':
                raise RuntimeError(deltaBig)
            else:
                output[-1]['Post-Evacuation Income Source'] = 'N/A'
        accessibility.writeOutput(args,output,fields,'TA2A-TA1C-0172.tsv',
            os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
