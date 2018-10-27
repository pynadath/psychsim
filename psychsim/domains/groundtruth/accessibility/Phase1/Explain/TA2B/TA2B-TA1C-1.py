"""


Research method category: Survey
Specific questions:

For the last 6 hurricanes, broken down by hurricane, if you stayed, could you list the major reason you stayed (freeform response); if you evacuated, could you list the major reason you evacuated?
For the last 6 hurricanes, broken down by hurricane, if you took shelter, could you list the major reason you took shelter (and vice versa)?
For the last 6 hurricanes, broken down by hurricane, did the government compensate you for losses incurred due to hurricane damage
How risk averse are you (broken down by ethnicity, other demo vars)?
When facing a hurricane, are you more concerned about short-term effects (personal safety) or long-term effects (rebuilding your household after the disaster)?
For the last 6 hurricanes, was there a case when you wanted to evacuate but were not able to? If yes, broken down by case (and listing which hurricane): could you list up to the top 3 reasons you were not able to evacuate?

Sampling strategy: uniform random sampling from regions 1-16

Other applicable detail:
Research request identifier: TA2B-TA1C-1
Research request priority: 1

"""
from argparse import ArgumentParser
import csv
import logging
import os
import os.path
import pickle
import random
from psychsim.probability import Distribution

from psychsim.domains.groundtruth.simulation.data import toLikert
from psychsim.domains.groundtruth.simulation.create import *
from psychsim.domains.groundtruth.simulation.execute import getDemographics

reasonMapping = {'resources': 'financial',
                 }
    

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-i','--instance',type=int,default=24,help='Instance to query')
    parser.add_argument('-r','--run',type=int,default=1,help='Run to query')
    parser.add_argument('--seed',type=int,default=1,help='Random number generator seed')
    parser.add_argument('-d','--debug',default='WARNING',help='Level of logging detail')
    parser.add_argument('--sampling',type=float,default=0.1,help='% of actors to sample')
    args = vars(parser.parse_args())
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logfile = '%s.log' % (os.path.splitext(__file__)[0])
    os.remove(logfile)
    logging.basicConfig(level=level,filename=logfile)
    random.seed(args['seed'])
    hurricanes = loadHurricanes(args['instance'],args['run'])
    world = loadPickle(args['instance'],0)
    data = loadRunData(args['instance'],args['run'])
    
    actors = [name for name in data if name[:5] == 'Actor' and
              data[name][-1]['Actor alive']['Value'] == 'True']
    survey = []
    size = int(args['sampling']*len(actors))
    while actors and len(survey) < size:
        actor = random.choice(actors)
        actors.remove(actor)
        model = next(iter(world.getModel(actor,world.state).domain()))
        Rtree = world.agents[actor].getReward(model)
        assert Rtree.isLeaf(),'Cannot currently handle branching reward functions'
        R = Rtree.getLeaf()[rewardKey(actor,True)]
        Rkeys = R.keys() - {CONSTANT}
        survey.append(getDemographics(world.agents[actor]))
        survey[-1]['Participant'] = len(survey)
        logging.info('TA2B-TA1C-1, Participant %d: %s' % (survey[-1]['Participant'],actor))
        for hurricane in hurricanes:
            evacuate = []
            whyEvacuate = []
            whyNotEvacuate = []
            shelter = []
            whyShelter = []
            whyNotShelter = []
            compensation = []
            start = hurricane['Start']
#            if hurricane['Hurricane'] == 1:
#                start = 1
#            else:
#                start = hurricanes[hurricane['Hurricane']-1]['End']+1
            for day in range(start,hurricane['End']):
                if data[actor][day-1]['Actor location']['Value'] == 'evacuated':
                    # This actor evacuated at some point
                    evacuate.append(day)
                elif data[actor][day-1]['Actor location']['Value'][:7] == 'shelter':
                    # This actor went to the shelter at some point
                    shelter.append(day)
                # Evaluate action choice
                verb = data[actor][day-1]['Actor action']['Value'].split('-')[1]
                # Set current beliefs
                state = world.agents[actor].getBelief(model=model)
                if day < hurricane['Landfall']:
                    world.setState('Nature','phase','approaching')
                else:
                    world.setState('Nature','phase','active')
                beliefs = set()
                for belief in data[actor][day-1]:
                    if belief[:13] == 'ActorBeliefOf':
                        if ' ' in belief[13:]:
                            agent,feature = belief[13:].split()
                        else:
                            agent = WORLD
                            feature = belief[13:]
                        if agent == 'Actor':
                            agent = actor
                        elif agent == 'Region':
                            if feature == 'shelterRisk':
                                for action in world.agents[actor].actions:
                                    if action['verb'] == 'moveTo' and \
                                       action['object'][:7] == 'shelter':
                                        agent = 'Region%s' % (action['object'][7:])
                            else:
                                agent = world.agents[actor].home
                        key = stateKey(agent,feature)
                        probs = data[actor][day-1][belief]['Value'].split(',')
                        if len(probs) == 1:
                            values = probs
                            probs = [1.]
                        else:
                            values = data[actor][day-1][belief]['Notes'].split(',')
                            values = [v[6:-1] for v in values]
                            probs = [float(p) for p in probs]
                        if world.variables[key]['domain'] is int:
                            values = [int(v) for v in values]
                        elif world.variables[key]['domain'] is float:
                            values = [float(v) for v in values]
                        elif world.variables[key]['domain'] is bool:
                            values = [True if v == 'True' else False for v in values]
                        value = Distribution({values[i]: probs[i] for i in range(len(values))})
                        world.agents[actor].setBelief(key,value)
                        beliefs.add(key)
                for key in state.keys():
                    if key not in beliefs:
                        world.agents[actor].setBelief(key,world.getFeature(key))
                decision = world.agents[actor].decide()
                Vtable = sorted([(decision['V'][action]['__EV__'],action)
                                 for action in decision['V']])
                Vtable.reverse()
                V = {action: {key: sum([s[key].expectation() for s in decision['V'][action]['__S__']])
                              for key in Rkeys} for action in decision['V']}
                for action in V:
                    if action['verb'] == 'evacuate':
                        # Compare evacuation against alternative
                        delta = dict(V[action])
                        if verb == action['verb']:
                            # Evacuate was best action. Why?
                            for lowerV,alternative in Vtable[1:]:
                                if alternative['verb'] == 'stayInLocation' or \
                                   alternative['verb'] == 'moveTo':
                                    break
                            else:
                                raise ValueError('I\'ve got nowhere else to go!')
                        else:
                            # Evacuate was suboptimal. Why?
                            alternative = Vtable[0][1]
                        for key in delta:
                            delta[key] -= V[alternative][key]
                        motivation = sorted([(abs(delta[key]*R[key]),key) for key in delta])
                        if verb == action['verb']:
                            whyEvacuate.append(motivation[-1][1])
                        else:
                            whyNotEvacuate.append(motivation[-1])
                    elif action['verb'] == 'moveTo' and action['object'][:7] == 'shelter':
                        # Compare sheltering against alternative
                        delta = dict(V[action])
                        if verb == action['verb']:
                            # Sheltering was best action. Why?
                            for lowerV,alternative in Vtable[1:]:
                                if alternative['verb'] == 'stayInLocation' or \
                                   alternative['verb'] == 'moveTo':
                                    break
                            else:
                                raise ValueError('I\'ve got nowhere else to go!')
                        else:
                            # Sheltering was suboptimal. Why?
                            alternative = Vtable[0][1]
                        for key in delta:
                            delta[key] -= V[alternative][key]
                        motivation = sorted([(abs(delta[key]*R[key]),key) for key in delta])
                        if verb == action['verb']:
                            whyShelter.append(motivation[-1][1])
                        else:
                            whyNotShelter.append(motivation[-1])
            if evacuate:
                survey[-1]['Hurricane %d: Evacuated?' % (hurricane['Hurricane'])] = 'yes'
                reasons = set()
                for motivation in whyEvacuate:
                    if isinstance(motivation,str):
                        reasons.add(motivation)
                    else:
                        reasons.add(motivation[1])
                if reasons:
                    reasons = [state2feature(reason) for reason in reasons]
                    reasons = ','.join([reasonMapping.get(reason,reason) for reason in reasons])
                else:
                    reasons = 'don\'t know'
                survey[-1]['Hurricane %d: Why/Why Not Evacuate?' % (hurricane['Hurricane'])] = reasons
            else:
                survey[-1]['Hurricane %d: Evacuated?' % (hurricane['Hurricane'])] = 'no'
                reasons = set()
                for motivation in whyNotEvacuate:
                    if isinstance(motivation,str):
                        reasons.add(motivation)
                    else:
                        reasons.add(motivation[1])
                if reasons:
                    reasons = [state2feature(reason) for reason in reasons]
                    reasons = ','.join([reasonMapping.get(reason,reason) for reason in reasons])
                else:
                    reasons = 'don\'t know'
                survey[-1]['Hurricane %d: Why/Why Not Evacuate?' % (hurricane['Hurricane'])] = reasons
            if shelter:
                survey[-1]['Hurricane %d: Went to Shelter?' % (hurricane['Hurricane'])] = 'yes'
                reasons = set()
                for motivation in whyShelter:
                    if isinstance(motivation,str):
                        reasons.add(motivation)
                    else:
                        reasons.add(motivation[1])
                if reasons:
                    reasons = [state2feature(reason) for reason in reasons]
                    reasons = ','.join([reasonMapping.get(reason,reason) for reason in reasons])
                else:
                    reasons = 'don\'t know'
                survey[-1]['Hurricane %d: Why/Why Not Shelter?' % (hurricane['Hurricane'])] = reasons
            else:
                survey[-1]['Hurricane %d: Went to Shelter?' % (hurricane['Hurricane'])] = 'no'
                reasons = set()
                for motivation in whyNotShelter:
                    if isinstance(motivation,str):
                        reasons.add(motivation)
                    else:
                        reasons.add(motivation[1])
                if reasons:
                    reasons = [state2feature(reason) for reason in reasons]
                    reasons = ','.join([reasonMapping.get(reason,reason) for reason in reasons])
                else:
                    reasons = 'don\'t know'
                survey[-1]['Hurricane %d: Why/Why Not Shelter?' % (hurricane['Hurricane'])] = reasons
            survey[-1]['Hurricane %d: Government Compensation?' % (hurricane['Hurricane'])] = 'no'
            
        survey[-1]['Risk Aversion'] = 'n/a'
        survey[-1]['Importance Short-Term'] = toLikert(R[stateKey(actor,'health')])
        survey[-1]['Importance Long-Term'] = toLikert(0)
        survey[-1]['Wanted to Evacuate But Unable'] = 'no'
    fields = ['Participant', 'Gender', 'Age', 'Ethnicity', 'Religion', 'Children', 'Fulltime Job', 'Pets', 'Wealth', 'Residence', 'Hurricane 1: Evacuated?', 'Hurricane 1: Why/Why Not Evacuate?', 'Hurricane 1: Went to Shelter?', 'Hurricane 1: Why/Why Not Shelter?', 'Hurricane 1: Government Compensation?', 'Hurricane 2: Evacuated?', 'Hurricane 2: Why/Why Not Evacuate?', 'Hurricane 2: Went to Shelter?', 'Hurricane 2: Why/Why Not Shelter?', 'Hurricane 2: Government Compensation?', 'Hurricane 3: Evacuated?', 'Hurricane 3: Why/Why Not Evacuate?', 'Hurricane 3: Went to Shelter?', 'Hurricane 3: Government Compensation?', 'Hurricane 4: Evacuated?', 'Hurricane 4: Why/Why Not Evacuate?', 'Hurricane 4: Went to Shelter?', 'Hurricane 4: Government Compensation?', 'Hurricane 5: Evacuated?', 'Hurricane 5: Why/Why Not Evacuate?', 'Hurricane 5: Went to Shelter?', 'Hurricane 5: Why/Why Not Shelter?', 'Hurricane 5: Government Compensation?', 'Hurricane 6: Evacuated?', 'Hurricane 6: Went to Shelter?', 'Hurricane 6: Government Compensation?', 'Risk Aversion', 'Wanted to Evacuate But Unable', 'Importance Short-Term', 'Importance Long-Term']
    with open('TA2B-TA1C-1.tsv','w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for record in survey:
            writer.writerow(record)
