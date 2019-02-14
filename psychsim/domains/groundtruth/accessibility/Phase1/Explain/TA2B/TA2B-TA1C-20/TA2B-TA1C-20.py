"""
**Research method category**: Survey


**Specific question**:
We would like to request a post-hurricane survey for the original area that fills out the variables present in the new area Post Survey: Property Damage. For convenience we have included the survey of the area. Either this survey can be re-deployed on the old and new seasons for the original area, or simply the question pertaining to property damage could be asked to the original area post-hurricane survey respondents. 

5
. ActorPostTable: Actor-level survey, conducted after a hurricane has passed:
a. Participant: ID for participant.
b. Hurricane: Identifying number of hurricane (see numbering notes in HurricaneTable).
c. Demographics: gender, age, ethnicity (either majority or minority), religion (either
majority, minority, or none), number of children, wealth (on a 0-5 scale, increasing
from 0 to 5), pet owned or not, fulltime job or not, region of residence
d. Survey questions:
i. At shelter: Did you stay at a public shelter at any point during the previous
hurricane?
ii. Evacuated: Did you evacuate the area at any point during the previous hurricane? (If you were already evacuated due to a previous hurricane, answer no)
iii. Assistance: I received government assistance during or after this past hurricane in response to that hurricane. (Response on a 1-5 scale, ranging from “strongly disagree” to “strongly agree”)
iv. Risk: The previous hurricane posed a significant risk to myself and my family.
(Response on a 1-5 scale, ranging from “strongly disagree” to “strongly agree”)
v. Dissatisfaction: The government response was *not* fair and adequate. (Response on a
1-5 scale, ranging from “strongly disagree” to “strongly agree”)
vi. Property: In the last hurricane, did your primary residence suffer significant property damage?
(Response on a 1-5 scale, ranging from “strongly disagree” to “strongly agree”)
vii. InjuryAdults: In the last hurricane, how many adults in your household over the age of 18 suffered from a significant physical injury?
viii. InjuryChildren: In the last hurricane, how many children in your household under the age of 18 suffered from a significant physical injury?


**Sampling strategy**: Same as for new area post actor survey, included below for convenience.
For each of the surveys conducted either before or after a hurricane, sample 10% of the total population. Use an approach where respondents are revisited for the following hurricane. For example in the post-hurricane surveys, after hurricane 2 we resample the same respondents as for hurricane 1. After we have two _consecutive_ post-hurricane surveys from the same household, we move on to the not yet surveyed potential respondents in the population, in each case trying to create a pairing of a post-hurricane response in hurricane N and N+1. Once all households have been surveyed in 2 consecutive surveys, start over with a fully random sample.




**Other applicable detail**: Either this survey can be re-deployed on the old and new seasons for the original area, or simply the question pertaining to property damage could be asked to the original area post-hurricane survey respondents. 


**Research request identifier**: 20propdamageinoldarea
"""
import csv
import os.path
from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

def getDamage(record,hurricane,population,data):
    matches = accessibility.findMatches(record,population=population)
    assert len(matches) == 1
    name = next(iter(matches))
    region = record['Residence']
    damage = [float(data[region][stateKey(region,'risk')][t]) for t in range(hurricane['Start'],hurricane['End']+1)]
    return max(damage)

if __name__ == '__main__':
    parser = accessibility.createParser(output='TA2B-TA1C-20propdamageinoldarea.tsv')
    args = accessibility.parseArgs(parser,'%s.log' % (os.path.splitext(__file__)[0]))
    hurricanes = accessibility.loadFromArgs(args,hurricanes=True)['hurricanes']
    runData = accessibility.loadRunData(args['instance'],args['run'])
    demos = accessibility.readDemographics(runData)
    output = []
    with accessibility.openFile(args,'ActorPostTable.tsv') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            if row['Timestep'] == '82' and row['Participant'] == '1':
                break
            damage = getDamage(row,hurricanes[int(row['Hurricane'])-1],demos,runData)
            row['Table'] = 'ActorPostTable'
            row['Property Previous Hurricane'] = accessibility.toLikert(damage)
            output.append(row)
    with accessibility.openFile(args,'ActorPostNewTable.tsv') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            if int(row['Hurricane']) > 6:
                damage = getDamage(row,hurricanes[int(row['Hurricane'])-1],demos,runData)
                row['Table'] = 'ActorPostNewTable'
                row['Property Previous Hurricane'] = accessibility.toLikert(damage)
                output.append(row)
    output.sort(key=lambda r: (int(r['Timestep']),int(r['Participant'])))
    fields = ['Timestep','Participant','Property Previous Hurricane']
    accessibility.writeOutput(args,output,fields)

