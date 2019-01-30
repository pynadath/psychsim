"""
**Research method category**: Event Journal


**Specific question**:
We would like to compile an event journal, to be filled out every five days, around actor decision-making around evacuation. For a small number of actors, we would like to recruit participants to record:


1. The actor’s demographics (Age, Children, Ethnicity, Fulltime Job, Gender, Pets, Religion, Residence, and Wealth at the time of the hurricane)
2. Whether the hurricane affected the actor’s region even if its eye (per the Hurricanes table) was not in the actor’s region (and, if so, the region of the hurricane’s eye and the region where the actor was located)
3. Whether the actor was in a different region than their region of residence (and, if so, the region where the actor was located and their region of residence)
4. If the actor suffered property damage during the hurricane (how much on a 1-5 scale) , whether / how they were able to recoup that damage (government assistance? Neighbor / friend assistance? Crowdfunding?)
5. The status of the actor’s home (livable / not livable) during the course of the hurricane season, broken down by hurricane.
6. Whether the actor recently suffered any of the following events: a. property damage. b. injury. c. death of family members. d. death of pets.
7. Whether the actor a. evacuated, b. sought shelter. c. requested government assistance.


**Sampling strategy**: Recruit the following fifteen actors (by participant id) from the original area that were affected by hurricanes: 68, 43, 87, 84, 69, 172, 25, 103, 127, 92, 59, 72, 97, 18, 105


**Other applicable detail**: None


**Research request identifier**: 17evacjournalorigarea
"""
import logging
import random

from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility
from psychsim.domains.groundtruth.simulation.data import getDemographics,toLikert,demographics

numSamples = 8

if __name__ == '__main__':
    parser = accessibility.createParser(output='TA2B-TA1C-17evacjournalorigarea.tsv',seed=True)
    args = accessibility.parseArgs(parser)
    cache = accessibility.loadFromArgs(args,world=True,hurricanes=True)
    world = cache['world']
    hurricanes = cache['hurricanes']
    data = accessibility.loadRunData(args['instance'],args['run'])
    fields = ['Timestep','Participant'] + sorted(demographics) + \
        ['Location','Affected','Property Damage','Recoup','Livable','Injured','Family Death','Pet Death','Request']
    pool = random.sample([name for name in world.agents if name[:5] == 'Actor'],numSamples)
    participant = 0
    for name in pool:
        participant += 1
        logging.info('Participant %d: %s' % (participant,name))
        agent = world.agents[name]
        pet = agent.getState('pet')
        journal = []
        day = random.randint(1,5)
        while True:
            state = {key: data[name][key][day] for key in data[name] if day in data[name][key]}
            if state.get(stateKey(name,'alive'),True) == 'False':
                break
            if len(state) > 1:
                # 1
                record = getDemographics(agent)
                record['Wealth'] = int(state[stateKey(name,'resources')]*5.1)
                record['Timestep'] = day
                record['Participant'] = participant
                hurricane = accessibility.findHurricane(day,hurricanes)
                if hurricane:
                    # 4
                    effect = data[agent.home][stateKey(agent.home,'risk')][day]-data[agent.home][stateKey(agent.home,'risk')][hurricane['Start']-1]
                    record['Property Damage'] = toLikert(effect)
                    # 2
                    record['Affected'] = record['Property Damage'] > 1
                else:
                    record['Affected'] = 'NA'
                    record['Property Damage'] = 'NA'
                # 3
                record['Location'] = state[stateKey(name,'location')]
                if record['Location'][:7] == 'shelter':
                    record['Location'] = 'shelter'
                # 4
                record['Recoup'] = 'False'
                # 5
                record['Livable'] = 'True'
                # 6b
                health = min([data[name][stateKey(name,'health')][max(1,day-t)] for t in range(5) if day-t in data[name][stateKey(name,'health')]])
                record['Injured'] = health < 0.2
                # 6c
                record['Family Death'] = 'False'
                # 6d
                if pet and record['Location'] == 'shelter':
                    pet = False
                    record['Pet Death'] = 'True'
                else:
                    record['Pet Death'] = 'False'
                # 7
                record['Request'] = 'False'
                journal.append(record)
            day += 5    
            if day > max(data[name][stateKey(name,'alive')]):
                break
        accessibility.writeOutput(args,journal,fields,'TA2B-TA1C-17-%d.tsv' % (participant))
