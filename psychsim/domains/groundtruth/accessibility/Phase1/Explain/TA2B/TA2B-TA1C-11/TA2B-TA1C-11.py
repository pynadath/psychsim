"""


**Research method category**: Survey revision


**Specific question**:


We’d like to ask for a revision of the IDP package where the same respondents answer questions only about the previous hurricane in their post-hurricane survey. That is to say, could the IDP set be revised such that questions d are now:


d. Survey questions:
i. At shelter: Did you move to stay at a public shelter at any point during the previous
hurricane as a result of the previous hurricane? (Which should be interpreted as going to the shelter due to this past hurricane. If the person was already in the shelter due to a hurricane prior to the previous hurricane, then the person should only answer yes if they would have gone to the shelter because of this past hurricane as well, and should answer no if they would not have gone to the shelter and were simply on their way out of the shelter when the next hurricane hit. If the respondent was already in sheltered state and cannot answer what they would have done, then use the response: AlreadySheltered. So the 3 choices in that case would be Yes, No, and AlreadySheltered)
ii. Evacuated: Did you evacuate the area at any point during the previous hurricane as a result of the previous hurricane? (Which should be interpreted as evacuating due to this past hurricane. If the person was already evacuated due to a hurricane prior to the last hurricane, then the person should only answer yes if they would have evacuated because of this past hurricane as well, and should answer no if they would not have evacuated and were simply on their way back but not yet arrived when the next hurricane hit. If the respondent was already in an evacuated state and cannot answer what they would have done, then use the response: AlreadyEvacuated. So the 3 choices in that case would be Yes, No, and AlreadyEvacuated)
iii. Injured: Did you suffer any injuries during the previous hurricane (do not count injuries that were due to hurricanes prior to the previous one)?
iv. Risk: The previous hurricane posed a significant risk to myself and my family. (Refer only to the most recent hurricane)
(Response on a 1-5 scale, ranging from “strongly disagree” to “strongly agree”)
v. Dissatisfaction: The government response was unfair and inadequate. (Refer only to the most recent hurricane) (Response on a 1-5 scale, ranging from “strongly disagree” to “strongly agree”)


**Sampling strategy**: We’d like the responses to be updated from the people of the initial data package (IDP) post-hurricane surveys. 


**Other applicable detail**: This is a revision request to the set of surveys included in the IDP to clarify the meaning of evacuated and sheltered so that responses are more usable to us for causal analysis. 


**Research request identifier**: 11reviseIDP

"""
import csv
import os.path

from psychsim.pwl.keys import ACTION
from psychsim.domains.groundtruth import accessibility


if __name__ == '__main__':
    parser = accessibility.createParser(output='TA2B-TA1C-11.tsv',day=True)
    parser.add_argument('-f','--first',type=int,default=0,help='First day to consider')
    parser.add_argument('-l','--last',type=int,default=None,help='Last day to consider')
    parser.add_argument('-t','--table',default='ActorPostTable',help='Table to get participants from')
    parser.add_argument('--locationonly',action='store_true',help='Generate only shelter and evacuation responses')
    args = accessibility.parseArgs(parser)
    data = accessibility.loadFromArgs(args,hurricanes=True,participants=True)
#    data['hurricanes'] = data['hurricanes'][:6]
    data['run'] = accessibility.loadRunData(args['instance'],args['run'],args['last'])
    output = []
    with open(os.path.join(data['directory'],'%s.tsv' % (args['table'])),'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            if int(row['Timestep']) < args['first']:
                continue
            elif args['last'] and int(row['Timestep']) > args['last']:
                break
            output.append(row)
            name = data['participants'][args['table']][int(row['Participant'])]
            hurricane = data['hurricanes'][int(row['Hurricane'])-1]
            assert hurricane['Hurricane'] == int(row['Hurricane'])
            # d.i
            series = [data['run'][name]['%s\'s location' % (name)][t] for t in range(hurricane['Start'],hurricane['End']+1)]
            unsheltered = series[0] != 'shelter11'
            for t in range(1,len(series)):
                if series[t] == 'shelter11':
                    if unsheltered:
                        # Sheltered after not
                        row['At Shelter Previous Hurricane'] = 'Yes'
                        break
                else:
                    # Was somewhere other than shelter
                    unsheltered = True
            else:
                if unsheltered:
                    row['At Shelter Previous Hurricane'] = 'No'
                else:
                    row['At Shelter Previous Hurricane'] = 'AlreadySheltered'
            # d.ii
            series = [data['run'][name]['%s\'s location' % (name)][t] for t in range(hurricane['Start'],hurricane['End']+1)]
            unevacuated = series[0] != 'evacuated'
            for t in range(1,len(series)):
                if series[t] == 'evacuated':
                    if unevacuated:
                        # Evacuated after not
                        row['Evacuated Previous Hurricane'] = 'Yes'
                        break
                else:
                    # Was somewhere other than evacuated
                    unevacuated = True
            else:
                if unevacuated:
                    row['Evacuated Previous Hurricane'] = 'No'
                else:
                    row['Evacuated Previous Hurricane'] = 'AlreadyEvacuated'
            # Verify
            move = False
            for t in range(hurricane['Start'],hurricane['End']):
                if data['run'][name]['%s\'s %s' % (name,ACTION)][t]['verb'] == 'evacuate':
                    assert row['Evacuated Previous Hurricane'] == 'Yes'
                    break
                elif data['run'][name]['%s\'s %s' % (name,ACTION)][t]['verb'] == 'moveTo':
                    move = True                    
            else:
                if move or series[0] != 'evacuated':
                    assert row['Evacuated Previous Hurricane'] == 'No'
                else:
                    assert row['Evacuated Previous Hurricane'] == 'AlreadyEvacuated','%s (%s) was already evacuated' % (name,row['Participant'])
            move = False
            for t in range(hurricane['Start'],hurricane['End']):
                if data['run'][name]['%s\'s %s' % (name,ACTION)][t]['verb'] == 'moveTo' and data['run'][name]['%s\'s %s' % (name,ACTION)][t]['object'][:7] == 'shelter':
                    assert row['At Shelter Previous Hurricane'] == 'Yes'
                    break
                elif data['run'][name]['%s\'s %s' % (name,ACTION)][t]['verb'] == 'moveTo':
                    move = True                    
            else:
                if move or series[0] != 'shelter11':
                    assert row['At Shelter Previous Hurricane'] == 'No'
                else:
                    assert row['At Shelter Previous Hurricane'] == 'AlreadySheltered'
            if not args['locationonly']:
                # d.iii
                series = [data['run'][name]['%s\'s health' % (name)][t] for t in range(hurricane['Start'],hurricane['End']+1)]
                uninjured = series[0] >= 0.2
                for t in range(1,len(series)):
                    if series[t] < 0.2:
                        if uninjured:
                            # Got injured after being uninjured
                            row['Injured Previous Hurricane'] = 'Yes'
                            break
                    else:
                        # Was uninjured at some point
                        uninjured = True
                else:
                    row['Injured Previous Hurricane'] = 'No'
                # d.iv
                series = [data['run'][name]['%s\'s risk' % (name)][t] for t in range(hurricane['Start'],hurricane['End']+1)]
                row['Risk Previous Hurricane'] = accessibility.toLikert(max(series))
                # d.v
                series = [data['run'][name]['%s\'s grievance' % (name)][t] for t in range(hurricane['Start'],hurricane['End']+1)]
                row['Grievance Previous Hurricane'] = accessibility.toLikert(5*(series[-1] - series[0]) + 0.5)
    fields = ['Timestep','Participant','Hurricane','At Shelter Previous Hurricane','Evacuated Previous Hurricane']
    if not args['locationonly']:
        fields += ['Injured Previous Hurricane','Risk Previous Hurricane','Grievance Previous Hurricane']
    accessibility.writeOutput(args,output,fields)
