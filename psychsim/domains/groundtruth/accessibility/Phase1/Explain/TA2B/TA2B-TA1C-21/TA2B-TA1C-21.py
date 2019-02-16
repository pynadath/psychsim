"""
**Research method category**: Survey


**Specific question**:
Please collect this new post hurricane SEASON survey by retrospectively asking respondents these questions about the past hurricane season.


6. ActorShelterEvacPostTable: Actor-level survey, conducted after a hurricane has passed:
a. Participant: ID for participant.
b. Hurricane: Identifying number of last hurricane (see numbering notes in HurricaneTable).
c. Demographics: gender, age, ethnicity (either majority or minority), religion (either
majority, minority, or none), number of children, wealth (on a 0-5 scale, increasing
from 0 to 5), pet owned or not, fulltime job or not, region of residence
d. Survey questions:
i. EverUsedShelter: Did you stay at a public shelter at any point during any previous hurricane this season?
ii. WhichHurricanesSheltered: Which previous hurricanes this season caused you to go to a shelter?
iii. EverEvacuated: Did you stay at a public shelter at any point during any previous hurricane this season?
iv. WhichHurricanesEvacd: Which previous hurricanes this season caused you to evacuate your home?
v. OrderingForBoth: For the past hurricanes where you both evacuated and sought shelter, which action did you do first? Please list these orderings for all hurricanes where you did both.
vi. DaysSpentInShelter: For the past hurricanes where you sought shelter, how many days did you spend at the shelter before moving on? Please list the number of days spent in the shelter for all hurricanes where you sheltered.
vii. DaysSpentInEvacd: For the past hurricanes where you evacuated, how many days did you spend evacuated before either returning home or going to a shelter? Please list the number of days spent evacuated for all hurricanes where you evacuated.
viii. Dissatisfaction1: For the past hurricanes where you evacuated or sheltered, rate your dissatisfaction with the government after each evacuation or sheltering event.
ix. Dissatisfaction2: For the past hurricanes where you did not evacuate nor shelter, rate your dissatisfaction with the government after each such hurricane.


**Sampling strategy**: Collect data for the original area at the end of the first season and the original area at the end of the second season. One survey is administered at the end of season 1. One survey is administered at the end of season 2. Recruit 10% of the population to fill each of the surveys. If possible, please recruit from the set of people who did shelter in the past season, and if that does not reach the total of 10% of the population then fill in respondents with nonsheltering households. 


**Other applicable detail**: None


**Research request identifier**: 21shelterandevac
"""
import logging
import os.path
import random

from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    random.seed(21)
    parser = accessibility.createParser(output='ActorShelterEvacPostTable.tsv')
    args = accessibility.parseArgs(parser,'%s.log' % (os.path.splitext(__file__)[0]))
    hurricanes = accessibility.readHurricanes(args['instance'],args['run'])
    data = accessibility.loadRunData(args['instance'],args['run'])
    demos = accessibility.readDemographics(data,True)
    population = [name for name in demos if name[:5] == 'Actor']
    days = [181,551]
    hurricanes = [[h for h in hurricanes if h['Start'] < days[0]],
        [h for h in hurricanes if h['End'] > days[0]]]
    output = []
    fields = ['Participant','Hurricane']+sorted(accessibility.demographics)+\
        ['EverUsedShelter','WhichHurricanesSheltered','EverEvacuated','WhichHurricanesEvacd','OrderingForBoth',
        'DaysSpentInShelter','DaysSpentInEvacd','Dissatisfaction1','Dissatisfaction2']
    for season in range(len(days)):
        pool = random.sample([name for name in population if data[name][stateKey(name,'alive')][days[season]]],16)
        for name in pool:
            participant = len(output) + 1
            logging.info('Participant %d: %s'  % (participant,name))
            record = {'Hurricane': hurricanes[season][-1]['Hurricane'],'Participant': participant}
            record.update(demos[name])
            record['Wealth'] = int(data[name][stateKey(name,'resources')][days[season]]*5.1)
            sheltered = {}
            evacuated = {}
            for hurricane in hurricanes[season]:
                sheltered[hurricane['Hurricane']] = [t for t in range(hurricane['Start'],hurricane['End']+1) \
                    if data[name][stateKey(name,'location')][t] == 'shelter11']
                evacuated[hurricane['Hurricane']] = [t for t in range(hurricane['Start'],hurricane['End']+1) \
                    if data[name][stateKey(name,'location')][t] == 'evacuated']
            record['EverUsedShelter'] = 'yes' if max([len(days) for days in sheltered.values()]) else 'no'
            hurrShelter = [h for h,days in sheltered.items() if len(days) > 0]
            if hurrShelter:
                record['WhichHurricanesSheltered'] = ','.join(['%d' % (h) for h in hurrShelter])
            else:
                record['WhichHurricanesSheltered'] = 'N/A'
            record['EverEvacuated'] = 'yes' if max([len(days) for days in evacuated.values()]) else 'no'
            hurrEvac = [h for h,days in evacuated.items() if len(days) > 0]
            if hurrEvac:
                record['WhichHurricanesEvacd'] = ','.join(['%d' % (h) for h in hurrEvac])
            else:
                record['WhichHurricanesEvacd'] = 'N/A'
            seq = []
            for hurricane in hurricanes[season]:
                if evacuated[hurricane['Hurricane']] and sheltered[hurricane['Hurricane']]:
                    if min(evacuated[hurricane['Hurricane']]) < min(sheltered[hurricane['Hurricane']]):
                        seq.append('Evacuated')
                    else:
                        seq.append('Sheltered')
            if seq:
                record['OrderingForBoth'] = ','.join(seq)
            else:
                record['OrderingForBoth'] = 'N/A'
            if hurrShelter:
                record['DaysSpentInShelter'] = ','.join(['%d' % (len(sheltered[h])) for h in hurrShelter])
            else:
                record['DaysSpentInShelter'] = 'N/A'
            if hurrEvac:
                record['DaysSpentInEvacd'] = ','.join(['%d' % (len(evacuated[h])) for h in hurrEvac])
            else:
                record['DaysSpentInEvacd'] = 'N/A'
            values = [data[name][stateKey(name,'grievance')][hurricane['End']] for hurricane in hurricanes[season] \
                if hurricane['Hurricane'] in hurrEvac or hurricane['Hurricane'] in hurrShelter]
            if values:
                record['Dissatisfaction1'] = ','.join(['%d' % (accessibility.toLikert(v)) for v in values])
            else:
                record['Dissatisfaction1'] = 'N/A'
            values = [data[name][stateKey(name,'grievance')][hurricane['End']] for hurricane in hurricanes[season] \
                if hurricane['Hurricane'] not in hurrEvac and hurricane['Hurricane'] not in hurrShelter]
            if values:
                record['Dissatisfaction2'] = ','.join(['%d' % (accessibility.toLikert(v)) for v in values])
            else:
                record['Dissatisfaction2'] = 'N/A'
            output.append(record)
    accessibility.writeOutput(args,output,fields)
