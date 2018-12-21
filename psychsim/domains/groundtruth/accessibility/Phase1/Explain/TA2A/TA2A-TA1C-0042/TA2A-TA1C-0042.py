"""
TA2A-TA1C-0042-RR.txt

Research method category:
Brief from expert observer / Interview of government experts

Specific question:
We would like to deploy a group of expert observers to collect data from the government and/or relevant insuring companies or agencies in each region, soliciting answers to the following:

1.How many hospitals are there in each region?

2.What is the maximum number of people hospitals can accommodate in each region?

3.What are the major facilities and resources in this coastal area? Please list all including but not limited to:
i.All transportation facilities (airports, harbors, train stations, etc)
ii.All power plants (hydroelectric, nuclear, thermal, solar etc.)
iii. All water purification/treatment plants

4.For each facility listed in Question 3, please provide the following information:
4a.Unique ID or name of the facility
4b.Location of the facility (which region[s] it is in)
4c.Description of this facility's functions
4d.What will happen to the facility during specific hurricanes and interim periods (e.g. the power plant NP138 will be shut down when category 2 hurricane hits the region, but remains open at other times)
4e.What is the maximum number of people this facility can serve (e.g., the power plant NP138 provides electricity for 20 individuals when in operation)

5. Please provide an official weather report for each region in the following format:
    5a) Pre_hurricane weather report (provided after hurricane has formed in the sea, but not yet landed):
        5a.i) Timestep 
        5a.ii) Predicted precipitation for the first day the hurricane would land (on a scale of 1 to 5, with 5 as maximum level of precipitation)
        5a.iii) Predicted average wind speed for the first day hurricane would land (on a scale of 1 to 5, with 5 as the maximum level of wind speed)
        5a.iv) Predicted severity of the first day hurricane landed
(on a scale of 1 to 5, with 5 as the maximum level of severity)
    5b. During hurricane weather document.
        5b.i) Timestep
        5b.ii) Actual precipitation on the day of the hurricane (collected at the end of the day, on a scale of 1 to 5, with 5 as the maximum level of precipitation)
        5b.iii) Actual average wind speed on the day of the hurricane (collected at the end of the day, on a scale of 1 to 5, with 5 as the maximum level of wind speed)
        5b.iv) Actual overall severity on the day of the hurricane (collected at the end of the day, on a scale of 1 to 5, with 5 as the maximum level of severity)

6. Please report the predicted hurricane movement for each hurricane. (e.g., Hurricane 5 will land at T32 in region 1, stay until T37 and move to region 2, eventually leaving the area at T39)
Please note that we desire to assess these predictions as generated before the specific hurricane hits. Please provide the timestep in which the prediction was originally generated.

7. Please report damage sustained in each region for each one of the six hurricanes. Specifically:
7a.How many people have lost assets
7b.The demographic information of the people who lost assets (gender, ethnicity, age, etc., as complete as possible)
7c.When did the asset loss happen, and what is the wealth before and after the asset loss? (e.g. Asset loss at 7, with wealth 5 at T6 and 3 at T7.

Sampling strategy:
We would like the team of researchers to visit the government and the hospitals to interview personnel who has access to the information we are soliciting.
Ideally we would like our researcher to get reports from all 16 regions. If this is not possible, we prefer to get report from regions
R2, R4, R16, R6 first.
If we can afford more, we would like to get the reports from
R3, R9, R14, R15 next.
If we can afford more, we would like to get the reports from
R1, R11, R7, R8 next.
If we can afford more, we would like to get the reports from
R5, R10, R12, R13 next.

Other applicable detail:
None.
 
Research request identifier:
TA2A-TA1C-0042-RR.txt
"""
import copy

from psychsim.pwl.keys import *
from psychsim.action import *
from psychsim.domains.groundtruth.simulation.data import toLikert
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    parser = accessibility.createParser(output='TA2A-TA1C-0042',day=True,seed=True)
    args = accessibility.parseArgs(parser)
    data = accessibility.loadFromArgs(args,world=True,hurricanes=True)
    data['hurricanes'] = data['hurricanes'][:6]
    data['run'] = accessibility.loadRunData(args['instance'],args['run'],82)
    # 7
    regions = {name for name in data['world'].agents if name[:6] == 'Region'}
    damage = []
    for hurricane in data['hurricanes']:
        start = int(hurricane['Landfall'])
        end = int(hurricane['End'])
        for name in sorted(regions):
            series = [data['run'][name]['%s\'s risk' % (name)][t-1] for t in range(start,end+1)]
            v0 = series[0]
            v1 = max(series)
            damage.append({'Hurricane': hurricane['Hurricane'],
                'Region': name,
                'Damage': toLikert(v1-v0)})
    accessibility.writeOutput(args,damage,['Hurricane','Region','Damage'],'%sDamage.tsv' % (args['output']))
    # 6
    predictions = []
    for hurricane in data['hurricanes']:
        state = copy.deepcopy(data['world'].state)
        data['world'].setState('Nature','phase','approaching',state)
        location = hurricane['Actual Location'][0]
        data['world'].setState('Nature','location',location,state)
        data['world'].setState('Nature','days',1,state)
        data['world'].setState(WORLD,'day',int(hurricane['Start']),state)
        action = ActionSet([Action({'subject': 'Nature','verb': 'evolve'})])
        while location != 'none':
            data['world'].rotateTurn('Nature',state)
            data['world'].step({'Nature': action},state,updateBeliefs=False,select='max')
            phase = data['world'].getState('Nature','phase',state).first()
            location = data['world'].getState('Nature','location',state).first()
            t = data['world'].getState(WORLD,'day',state).first()
            if phase != 'approaching':
                record = {'Timestep': int(hurricane['Start']),
                    'Hurricane': hurricane['Hurricane'],
                    'Predicted Timestep': t,
                    'Location': location}
                predictions.append(record)
    accessibility.writeOutput(args,predictions,['Timestep','Hurricane','Predicted Timestep','Location'],'%sPrediction.tsv' % (args['output']))
