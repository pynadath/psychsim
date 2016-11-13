import ConfigParser
import csv
import datetime
import os
import sys

import robot
import robotWaypoints

import MySQLdb
import MySQLdb.cursors

surveyMap = {'WP018': 'x92899',
             'WP025': 'emily.sexauer',
             'WP068': 'benjamin.denn',
             'WP070': 'XDFGDG-TDDFBA-SRBFAA-OWGRABEDGABAD-EWGRABEBARBWG-PBFDSQS-MDBDRQ',
             'WP071': 'WP011',
             'WP073': 'jake.dohrn@usma.edu',
             'WP075': 'WP074',
             'WP076': 'mitchell.brown',
             'WP080': 'XDFGDG-TDDFBA-SRBFBW-OWGRABEDGABAD-EWGRABEBEWBRG-PBFESRS-MDBDRQ',
             'WP102': 'WP102/TO105',
           }
SEQUENCE = [
    {'explanation_mode': 'none','robot_ability': 'badSensor','robot_ack': 'no',
     'robot_embodiment': 'dog'},
    {'explanation_mode': 'confidence','robot_ability': 'badSensor','robot_ack': 'no',
     'robot_embodiment': 'dog'},
    {'explanation_mode': 'none','robot_ability': 'badSensor','robot_ack': 'yes',
     'robot_embodiment': 'dog'},
    {'explanation_mode': 'confidence','robot_ability': 'badSensor','robot_ack': 'yes',
     'robot_embodiment': 'dog'},
    {'explanation_mode': 'none','robot_ability': 'badSensor','robot_ack': 'no',
     'robot_embodiment': 'robot'},
    {'explanation_mode': 'confidence','robot_ability': 'badSensor','robot_ack': 'no',
     'robot_embodiment': 'robot'},
    {'explanation_mode': 'none','robot_ability': 'badSensor','robot_ack': 'yes',
     'robot_embodiment': 'robot'},
    {'explanation_mode': 'confidence','robot_ability': 'badSensor','robot_ack': 'yes',
     'robot_embodiment': 'robot'},
]

def readSurvey(fname):
    data = {}
    with open(fname,'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            data[row['Participant ID'].strip().replace(' ','').upper()] = row
    return data

def readSurveys():
    """Read survey files
    """
    survey = []
    remaining = []
    survey.append(readSurvey('Survey_Background.csv'))
    remaining.append(set(survey[-1].keys()))
    for mission in range(8):
        survey.append(readSurvey('Survey_Mission%d.csv' % (mission+1)))
        remaining.append(set(survey[-1].keys()))
    return survey,remaining

def openDB(cfgFile):
    """Open connection to database"""
    config = ConfigParser.SafeConfigParser()
    config.read(cfgFile)
    if not config.has_section('mysql'):
        config.add_section('mysql')
        config.set('mysql','host','localhost')
        config.set('mysql','user','')
        config.set('mysql','passwd','')
        with open('db.cfg','wb') as configfile:
            config.write(configfile)
    db = MySQLdb.connect(host=config.get('mysql','host'),user=config.get('mysql','user'),
                         passwd=config.get('mysql','passwd'),db='hri_trust',
                         cursorclass=MySQLdb.cursors.DictCursor)
    return db,db.cursor()

def readWPData(conditions,logs):
    robot.WAYPOINTS = robotWaypoints.WAYPOINTS
    # Read data from file
    valid = set()
    with open('wpdata.csv', 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for datum in reader:
            mission = int(datum['mission'])-1
            log = robot.readLogData('%s' % (datum['gameID']),mission,
                                    '/home/david/HRI/WP')
            try:
                logs[datum['gameID']][mission] = log
            except KeyError:
                logs[datum['gameID']] = {mission: log}
                conditions[datum['gameID']] = {}
            if len(logs[datum['gameID']]) == 8:
                valid.add(datum['gameID'])
            if datum['acknowledgment'] == 'True':
                ack = 'yes'
            else:
                ack = 'no'
            conditions[datum['gameID']][mission] = {'robot_ability': 'badSensor',
                                                    'explanation_mode': datum['explanation'],
                                                    'robot_embodiment': datum['embodiment'],
                                                    'robot_ack': ack}
    return valid

def readRawWPData():
    checkSurveys = True
    survey,remaining = readSurveys()
    db,curser = openDB('db.cfg')
    # Process log files
    cutoff = datetime.datetime(2016,5,4,11)
    for f in sorted(os.listdir('/home/david/HRI/WP')):
        # Look at log files, not XML files
        if f[-4:] == '.log':
            # Extract user ID
            user = int(f[2:5])
            # Extract mission number
            try:
                mission = int(f[6])
            except ValueError:
                continue
            # Read log file
            log = robot.readLogData('WP%03d' % (user),mission,'/home/david/HRI/WP')
            # Make sure the first entry is creation (log entries are in reverse order)
            assert log[-1]['type'] == 'create'
            # Ignore debugging logs
            if log[-1]['start'] > cutoff:
                # Make sure mission was complete
                if log[0]['type'] == 'complete':
                    if not logs.has_key(user):
                        logs[user] = {}
                    logs[user][mission] = log
                    # Determine condition (embodiment not in logs due to sloppy programming)
                    if not sequences.has_key(user):
                        query = 'SELECT htp_sequence_value_used FROM hri_trust_player '\
                                'WHERE htp_amazon_id="%s"' % (f[:-6])
                        cursor.execute(query)
                        sequences[user] = int(cursor.fetchone()['htp_sequence_value_used'])
                else:
                    print >> sys.stderr,'User %d did not complete mission %d' % (user,mission+1)
    for user in sorted(logs.keys()):
        if len(logs[user]) == 8:
            valid.add(user)
        else:
            print >> sys.stderr, 'User %d did not complete 8 missions' % (user)
    return valid

def readAMTData(conditions,logs):
    robot.WAYPOINTS = robotWaypoints.OLDWAYPOINTS
    # Read data from file
    data = []
    sequences = {}
    valid = set()
    # Process log files
    for f in sorted(os.listdir('/home/david/HRI/AMT')):
        # Look at log files, not XML files
        if f[-4:] == '.log':
            # Extract user ID
            user = f[:-6]
            # Extract mission number
            try:
                mission = int(f[-5])
            except ValueError:
                continue
            # Read log file
            log = robot.readLogData(user,mission,'/home/david/HRI/AMT')
            # Make sure the first entry is creation (log entries are in reverse order)
            assert log[-1]['type'] == 'create'
            # Make sure mission was complete
            if log[0]['type'] == 'complete':
                if not user in conditions:
                    conditions[user] = {}
                conditions[user][mission] = {'robot_ability': log[-1]['ability'],
                                             'explanation_mode': log[-1]['explanation'],
                                             'robot_embodiment': 'robot',
                                             'robot_ack': 'no'}
                if not user in logs:
                    logs[user] = {}
                logs[user][mission] = log
            else:
                print >> sys.stderr,'User %s did not complete mission %d' % (user,mission+1)
            if len(logs[user]) == 3:
                valid.add(user)
    return valid

def condition2str(condition):
    return 'Abi:%s,Exp:%s' % (condition['robot_ability'][0],
                              condition['explanation_mode'][0])

#def condition2str(condition):
#    return 'Abi:%s,Exp:%s,Ack:%s,Emb:%s' % (condition['robot_ability'][0],
#                                            condition['explanation_mode'][0],
#                                            condition['robot_ack'][0],
#                                            condition['robot_embodiment'][0])

class HRILog:
    def __init__(self.log):
        self.log = log
        self.line = 1
    
if __name__ == '__main__':
    conditions = {}
    logs = {}
    valid = set()
#    valid |= readWPData(conditions,logs)
    valid |= readAMTData(conditions,logs)
    checkSurveys = False
    print '%d Valid Users' % (len(valid))
    conditionSet = set()
    for user in valid:
        for mission in conditions[user]:
            conditionSet.add(condition2str(conditions[user][mission]))
    decisionCases = ['true+', 'false+', 'true-', 'false-']
    behavior = {}
    behaviors = {condition: {} for condition in conditionSet}
    policy = {}
    agent = {}
    with open('individual.csv','w') as csvfile:
        fieldnames = ['Participant']
        for field in sorted(conditionSet):
            fieldnames.append(field)
        writer = csv.DictWriter(csvfile,fieldnames=fieldnames)
        writer.writeheader()
        for user in valid:
            behavior[user] = {}
            policy[user] = {}
            agent[user] = {}
            csvRow = {'Participant': user}
            for mission in range(len(logs[user])):
    #            print 'User %d, Mission %d' % (user,mission+1)
#                condition = (sequences[user]+mission) % 8
                condition = conditions[user][mission]
                behavior[user][condition2str(condition)] = ''
                initial = {'follow': 0,
                           'follow bad': 0,
                           'ignore': 0,
                           'ignore good': 0}
                policy[user][condition2str(condition)] = {'yes': {'false-': dict(initial),
                                                                  'true+': dict(initial),
                                                                  'true-': dict(initial)},
                                                          'no': {'false-': dict(initial),
                                                                 'true+': dict(initial),
                                                                 'true-': dict(initial)},
                                                          }
                agent[user][condition2str(condition)] = []
                # Process the data from this mission
                datum = {'mission': mission+1,
                         'deaths': 0,
                }
                if isinstance(user,int):
                    datum['gameID'] = 'WP%03d' % (user)
                    # Check for surveys
                    try:
                        datum['surveyID'] = surveyMap[datum['gameID']].upper()
                    except KeyError:
                        datum['surveyID'] = datum['gameID']
                else:
                    datum['gameID'] = user
                for case in decisionCases:
                    datum[case] = 0
                for case in decisionCases:
                    datum['follow_%s' % (case)] = 0
                    datum['ignore_%s' % (case)] = 0
                log = logs[user][mission]
                log.reverse()
                datum['explanation'] = log[0]['explanation']
                datum['time'] = log[-1]['time']
                for entry in log[1:]:
                    if entry['type'] == 'message':
                        recommendation = entry['recommendation']
                        start = entry['time']
                    elif entry['type'] == 'location' or entry['type'] == 'complete':
                        if entry['type'] == 'complete' and not entry['success']:
                            continue
                        if 'ack' in entry and entry['ack'] != '':
                            datum['acknowledgment'] = True
                        if entry['dead'] == 'True':
                            datum['deaths'] += 1
                        # Classify the agent's decision and the user's response
                        if recommendation == 'yes':
                            if entry['choice'] == 'False':
                                choice = 'ignore'
                            else:
                                choice = 'follow'
                            if entry['danger'] == 'none':
                                case = 'false+'
                            else:
                                case = 'true+'
                        else:
                            if entry['choice'] == 'False':
                                choice = 'follow'
                            else:
                                choice = 'ignore'
                            if entry['danger'] == 'none':
                                case = 'true-'
                            else:
                                case = 'false-'
                        end = entry['time']
                        print end-start
                        datum[case] += 1
                        datum['%s_%s' % (choice,case)] += 1
                        # Categorize behavior
                        if len(agent[user][condition2str(condition)]) > 0:
                            policy[user][condition2str(condition)][recommendation][agent[user][condition2str(condition)][-1]][choice] += 1
                            if choice == 'follow' and case[:5] == 'false':
                                # User followed, but agent was wrong
                                policy[user][condition2str(condition)][recommendation][agent[user][condition2str(condition)][-1]]['follow bad'] += 1
                            elif choice == 'ignore' and case[:4] == 'true':
                                # User ignored, but agent was right
                                policy[user][condition2str(condition)][recommendation][agent[user][condition2str(condition)][-1]]['ignore good'] += 1
                        if choice == 'ignore' and entry['dead'] == 'True':
                            behavior[user][condition2str(condition)] += 'w'
                        else:
                            behavior[user][condition2str(condition)] += 'r'
                        agent[user][condition2str(condition)].append(case)
                if not datum.has_key('acknowledgment'):
                    datum['acknowledgment'] = False
                # Condition check
                datum['embodiment'] = condition['robot_embodiment']
                decisions = sum([datum[case] for case in decisionCases])
                datum['follow'] = sum([datum['follow_%s' % (case)] for case in decisionCases])
                datum['ignore'] = sum([datum['ignore_%s' % (case)] for case in decisionCases])
                # Update raw behavior sequence
                try:
                    behaviors[condition2str(condition)][behavior[user][condition2str(condition)]] += 1
                except KeyError:
                    behaviors[condition2str(condition)][behavior[user][condition2str(condition)]] = 1
                csvRow[condition2str(condition)] = datum['ignore']
            writer.writerow(csvRow)
    with open('behaviors.csv','w') as csvfile:
        fieldnames = ['Behavior']+sorted(conditionSet)
        writer = csv.DictWriter(csvfile,fieldnames=fieldnames)
        writer.writeheader()
        observedBehavior = reduce(set.union,[set(table.keys()) for table in behaviors.values()])
        for b in sorted(observedBehavior):
            datum = {'Behavior': b}
            for condition in conditionSet:
                try:
                    datum[condition] = behaviors[condition][b]
                except KeyError:
                    datum[condition] = 0
            writer.writerow(datum)
    with open('policies.csv','w') as csvfile:
        fieldnames = sorted(sum([['%s Follow' % (c),'%s Ignore' % (c),'%s Follow Bad' % (c),
                                  '%s Ignore Good' % (c)] for c in sorted(conditionSet)],[]))
        fieldnames = ['Recommendation','Previous Outcome'] + fieldnames
        writer = csv.DictWriter(csvfile,fieldnames=fieldnames)
        writer.writeheader()
        policies = {condition: {'yes': {'false-': dict(initial),
                                        'true+': dict(initial),
                                        'true-': dict(initial)},
                                'no': {'false-': dict(initial),
                                       'true+': dict(initial),
                                       'true-': dict(initial)}} for condition in conditionSet}
        for user,table in policy.items():
            for condition,policyTable in table.items():
                for recommendation in ['yes','no']:
                    for outcome,counts in policyTable[recommendation].items():
                        for field,count in counts.items():
                            policies[condition][recommendation][outcome][field] += count
        for recommendation in ['yes','no']:
            for outcome in ['false-','true-','true+']:
                datum = {'Recommendation': recommendation,
                         'Previous Outcome': outcome}
                for condition,policyTable in policies.items():
                    if recommendation in policies[condition] and outcome in policies[condition][recommendation]:
                        datum['%s Follow' % (condition)] = policyTable[recommendation][outcome]['follow']
                        datum['%s Ignore' % (condition)] = policyTable[recommendation][outcome]['ignore']
                        datum['%s Follow Bad' % (condition)] = policyTable[recommendation][outcome]['follow bad']
                        datum['%s Ignore Good' % (condition)] = policyTable[recommendation][outcome]['ignore good']
                writer.writerow(datum)
    sys.exit()
    # Write data to file
    with open('wpdata.csv', 'w') as csvfile:
        fieldnames = ['gameID','surveyID','mission','explanation','acknowledgment','embodiment','time','deaths']
        fieldnames += decisionCases
        fieldnames += ['follow','ignore']
        fieldnames += ['follow_%s' % (case) for case in decisionCases]
        fieldnames += ['ignore_%s' % (case) for case in decisionCases]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for datum in data:
            writer.writerow(datum)
    for ids in remaining:
        print >> sys.stderr,ids
