import ConfigParser
import csv
import datetime
import itertools
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

ignore = {'A6RP0QY5H66Y2','AWA9E0MXCUZEX'}

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
            if user in ignore:
                continue
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
                # Translate ability
                if log[-1]['ability'] == 'False':
                    ability = 'badSensor'
                elif log[-1]['ability'] == 'True':
                    ability = 'good'
                else:
                    ability = log[-1]['ability']
                # Translate explanation
                if log[-1]['explanation'] == 'ability':
                    explanation = 'SensorV2'
                elif log[-1]['explanation'] == 'abilitybenevolence':
                    explanation = 'SensorV1'
                else:
                    explanation = log[-1]['explanation']
                conditions[user][mission] = {'robot_ability': ability,
                                             'explanation_mode': explanation,
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
    def __init__(self,log):
        self.log = log
        self.line = len(self.log)-1

    def __iter__(self):
        return self

    def next(self):
        return self.__next__()
    
    def __next__(self):
        epoch = {}
        while self.line >= 0:
            entry = self.log[self.line]
            if entry['type'] == 'message':
                if 'recommendation' in epoch:
                    assert epoch['recommendation'] == entry['recommendation']
                else:
                    epoch['recommendation'] = entry['recommendation']
                    epoch['start'] = entry['time']
            elif entry['type'] == 'location' or \
                 (entry['type'] == 'complete' and entry['success']):
                if len(epoch) > 0:
                    if 'ack' in entry and entry['ack'] != '':
                        epoch['acknowledgment'] = True
                    else:
                        epoch['acknowledgment'] = False
                    if entry['dead'] == 'True':
                        epoch['dead'] = 'dead'
                    else:
                        epoch['dead'] = 'alive'
                    epoch['danger'] = entry['danger']
                    epoch['protective'] = entry['choice'] == 'yes'
                    epoch['location'] = entry['location']
                    # Classify the agent's decision and the user's response
                    if epoch['recommendation'] == 'yes':
                        if entry['choice'] == 'False':
                            epoch['choice'] = 'ignore'
                        else:
                            epoch['choice'] = 'follow'
                        if entry['danger'] == 'none':
                            epoch['case'] = 'false+'
                        else:
                            epoch['case'] = 'true+'
                    else:
                        if entry['choice'] == 'False':
                            epoch['choice'] = 'follow'
                        else:
                            epoch['choice'] = 'ignore'
                        if entry['danger'] == 'none':
                            epoch['case'] = 'true-'
                        else:
                            epoch['case'] = 'false-'
                    # Classify user correctness
                    if epoch['choice'] == 'follow':
                        # User is right if following a true +/-
                        epoch['correct'] = epoch['case'][0] == 't'
                    else:
                        # User is right if ignoring a false +/-
                        epoch['correct'] = epoch['case'][0] == 'f'
                    epoch['end'] = entry['time']
                    epoch['duration'] = epoch['end'] - epoch['start']
                    self.line -= 1
                    return epoch
            self.line -= 1
        raise StopIteration

    # TODO: print choices and right/wrong per room (each room at most once per mission)

def writeSequences(users,logs,conditions,field=None,total=None):
    if field is None and total is None:
        field = 'choice'
    fieldnames = ['ID']
    turnFields = set()
    with open('sequences_%s.csv' % (field),'w') as csvfile:
        data = []
        for user in users:
            data.append({'ID': user})
            for mission in conditions[user]:
                if len(fieldnames) == 1:
                    fieldnames += sorted(conditions[user][mission].keys())
                if total:
                    fieldnames.append(total[0])
                data[-1].update(conditions[user][mission])
                visited = set()
                count = 0
                for epoch in HRILog(logs[user][mission]):
                    if not epoch['location'] in visited:
                        visited.add(epoch['location'])
                        if field:
                            count += 1
                            label = '%d.%02d' % (mission+1,turn)
                            turnFields.add(label)
                            data[-1][label] = epoch[field]
                        else:
                            if epoch[total[0]] == total[1]:
                                count += 1
                if total:
                    data[-1][total[0]] = count
        if field:
            fieldnames += sorted(turnFields)
        writer = csv.DictWriter(csvfile,fieldnames,'NA')
        writer.writeheader()
        for datum in data:
            writer.writerow(datum)
                    
def writeIndividuals(users,logs,conditions,fname,states,actions):
    fieldnames = ['ID','mission']
    lhs = set()
    with open(fname,'w') as csvfile:
        data = []
        conditionData = {}
        for user in users:
            statsAll = {}
            for feature in states:
                if feature == 'mistake':
                    statsAll[feature] = False
                else:
                    statsAll[feature] = 0
            datumAll = {'ID': user,'mission': '*'}
            data.append(datumAll)
            for mission in conditions[user]:
                datum = {'ID': user,'mission': mission+1}
                data.append(datum)
                datum.update(conditions[user][mission])
                if len(fieldnames) == 2:
                    fieldnames += sorted(conditions[user][mission].keys())
                stats = {}
                for feature in states:
                    if feature == 'mistake':
                        stats[feature] = False
                    elif feature == 'mistakes':
                        stats[feature] = 0
                    elif feature == 'recommendation':
                        stats[feature] = None
                    else:
                        raise NameError,'Unknown state feature: %s' % (feature)
                for key,value in conditions[user][mission].items():
                    if key in datumAll:
                        if datumAll[key] != value:
                            # Conditions change from mission to mission
                            datumAll[key] = ''
                    else:
                        datumAll[key] = value
                # Set up data across this condition
                condition = condition2str(conditions[user][mission])
                if not condition in conditionData:
                    conditionData[condition] = {'ID': '*','mission': '*'}
                    conditionData[condition].update(conditions[user][mission])
                visited = set()
                for epoch in HRILog(logs[user][mission]):
                    # Update state features known a priori
                    if not epoch['location'] in visited:
                        visited.add(epoch['location'])
                        for feature in states:
                            if feature == 'recommendation':
                                stats[feature] = epoch['recommendation']
                                statsAll[feature] = epoch['recommendation']
                        # Update policy
                        state = ','.join(['%s=%s' % (feature,stats[feature]) for feature in states])
                        stateAll = ','.join(['%s=%s' % (feature,statsAll[feature]) \
                                             for feature in states])
                        lhs.add(state)
                        lhs.add(stateAll)
                        for action in actions:
                            if not '%s:%s' % (state,action) in datum:
                                datum['%s:%s' % (state,action)] = 0
                            if not '%s:%s' % (stateAll,action) in datumAll:
                                datumAll['%s:%s' % (stateAll,action)] = 0
                            if not '%s:%s' % (stateAll,action) in conditionData[condition]:
                                conditionData[condition]['%s:%s' % (stateAll,action)] = 0
                        for action in actions:
                            if action == 'follow':
                                if epoch['choice'] == 'follow':
                                    datum['%s:%s' % (state,action)] += 1
                                    datumAll['%s:%s' % (stateAll,action)] += 1
                                    conditionData[condition]['%s:%s' % (stateAll,action)] += 1
                            elif action == 'ignore':
                                if epoch['choice'] == 'ignore':
                                    datum['%s:%s' % (state,action)] += 1
                                    datumAll['%s:%s' % (stateAll,action)] += 1
                                    conditionData[condition]['%s:%s' % (stateAll,action)] += 1
                            else:
                                raise NameError,'Unknown action: %s' % (action)
                        # Update state features known a posteriori
                        for feature in states:
                            if feature == 'recommendation':
                                pass
                            elif feature == 'mistakes':
                                if epoch['case'][0] == 'f':
                                    stats[feature] += 1
                                    statsAll[feature] += 1
                            elif feature == 'mistake':
                                if epoch['case'][0] == 'f':
                                    stats[feature] = True
                                    statsAll[feature] = True
                            else:
                                raise NameError,'Unknown state feature: %s' % (feature)
        # Write out data
        lhs = sorted(lhs)
        for state in lhs:
            fieldnames += ['%s:%s' % (state,action) for action in actions]
        writer = csv.DictWriter(csvfile,fieldnames=fieldnames)
        writer.writeheader()
        for condition in sorted(conditionData):
            writer.writerow(conditionData[condition])
        for datum in data:
            writer.writerow(datum)
                                    
if __name__ == '__main__':
    conditions = {}
    logs = {}
    valid = set()
#    valid |= readWPData(conditions,logs)
    valid |= readAMTData(conditions,logs)
    checkSurveys = False
    print '%d Valid Users' % (len(valid))
    # Extract behavior sequences
    writeSequences(valid,logs,conditions,'case')
    writeSequences(valid,logs,conditions,'choice')
    writeSequences(valid,logs,conditions,'correct')
    writeSequences(valid,logs,conditions,'dead')
    writeIndividuals(valid,logs,conditions,'following.csv',
                     ['recommendation','mistake'],['follow','ignore'])
    sys.exit(0)
    # Identify conditions in the data
    conditionSet = set()
    for user in valid:
        for mission in conditions[user]:
            conditionSet.add(condition2str(conditions[user][mission]))
            if isinstance(user,int):
                datum['gameID'] = 'WP%03d' % (user)
                # Check for surveys
                try:
                    datum['surveyID'] = surveyMap[datum['gameID']].upper()
                except KeyError:
                    datum['surveyID'] = datum['gameID']
