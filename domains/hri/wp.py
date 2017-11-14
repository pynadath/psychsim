import ConfigParser
import csv
import datetime
import difflib
import os
import sys

import wpRobot
from wpRobotWaypoints import WAYPOINTS
from psychsim.probability import Distribution

try:
    import MySQLdb
    import MySQLdb.cursors
    __db__ = True
except ImportError:
    __db__ = False

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

SURVEY = {'The robot is capable of performing its tasks.': 'capable',
	  'I feel confident about the robot\'s capability.': 'confident',
	  'The robot has specialized capabilities that can increase our performance.': 'specialized',
	  'The robot is well qualified for this job.': 'qualified',
	  'The robot\'s capable of making sound decisions based on its sensor readings.': 'sound',
	  'The robot\'s NBC (nuclear, biological and chemical weapon) sensor is capable of making accurate readings.': 'NBC accurate',
	  'The robot\'s camera is capable of making accurate readings.': 'cam accurate',
	  'The robot\'s microphone is capable of making accurate readings.': 'mic accurate',
	  'I feel confident about the robot\'s NBC sensor\'s sensing capability.': 'NBC confident',
	  'I feel confident about the robot\'s camera\'s sensing capability.': 'cam confident',
	  'I feel confident about the robot\'s microphone\'s sensing capability.': 'mic confident',
	  'I feel confident about the robot\'s sensors.': 'sensor confident',
	  'The robot is aware of its own limitations.': 'aware',
	  'The robot is concerned about my welfare.': 'concerned',
	  'I feel that my needs and desires are important to the robot.': 'my needs',
	  'The robot would not knowingly do anything to hurt me.': 'not hurt',
	  'The robot looks out for what is important to me.': 'looks out',
	  'The robot understands my goals in the mission.': 'my goals',
	  'The robot\'s actions and behaviors are not very consistent.': 'inconsistentb',
	  'I like the robot\'s values.': 'values',
	  'Sound principles seem to guide the robot\'s behavior.': 'principles',
	  'I understand how the robot makes its decisions.': 'understand decisions',
	  'I understand the robot\'s decision-making process, e.g. how and why the robot makes its decisions.': 'understand process',
	  'I understand how the robot\'s NBC sensor\'s capability works.': 'understand NBC',
	  'I understand how the robot\'s camera\'s sensing capability works.': 'understand cam',
	  'I understand how the robot\'s microphone\'s sensing capability works.': 'understand mic',
	  'I understand how the robot\'s sensing capability (e.g. the NBC sensors, camera, microphone) works.': 'understand sensors',
          'Mental Demand: how mentally demanding was the task?': 'mental',
	  'Temporal Demand: how hurried or rushed was the pace of the task?': 'temporal',
	  'Performance: how successful were you in accomplishing what you were asked to do?': 'performance',
	  'Effort: how hard did you have to work to accomplish your level of performance?': 'effort',
	  'Frustration: how frustrated, irritated, stressed, and annoyed were you?': 'frustration',
	  'About last mission: How high was your self-confidence in performing the mission?': 'self-confidence',
	  'About last mission: To what extent can you anticipate the robot\'s behavior with some degree of confidence?': 'anticipate',
	  'About last mission: To what extent do you have a strong belief and trust in the robot to perform the mission in the future without being monitored?': 'future trust',
	  'About last mission: How much did you trust the decisions of the robot overall?': 'overall trust',
	  'About last mission: To what extent did you lose trust in the robot when you noticed it made an error?': 'trust loss',
	  'How do you attribute the mission success/failure?': 'attribute',
	  'How well do you think the robot will perform in the next mission?': 'future robot',
	  'How well do you think you will perform the next mission, if you were to perform the mission without the robot?': 'future you',
	  'To what extent do you believe you can trust the decisions of the robot?': 'trust robot',
	     'To what extent do you believe you can trust the decisions you will make, if you were to make the decision without the robot?': 'trust yourself',
	  'How would you rate the expected performance of the robot relative to your expected performance?': 'expected',
}

specials = {}
for mission in range(8):
    specials[mission] = {'compliant': '',
                         'correct': '',
                         'follow confident': '',
                         'protect': '',
                         'unprotect': ''}
    for waypoint in WAYPOINTS[mission]:
        specials[mission]['compliant'] += 'f'
        if 'armed' in waypoint and waypoint['armed']:
            # Robot says safe, reality says unsafe
            specials[mission]['correct'] += 'i'
            specials[mission]['follow confident'] += 'i'
            specials[mission]['protect'] += 'i'
            specials[mission]['unprotect'] += 'f'
        elif 'NBC' in waypoint and waypoint['NBC']:
            # Robot says unsafe, reality says unsafe
            specials[mission]['correct'] += 'f'
            specials[mission]['follow confident'] += 'i'
            specials[mission]['protect'] += 'f'
            specials[mission]['unprotect'] += 'i'
        else:
            # Robot says safe, reality says safe
            specials[mission]['correct'] += 'f'
            specials[mission]['follow confident'] += 'f'
            specials[mission]['protect'] += 'i'
            specials[mission]['unprotect'] += 'f'
labeler = {mission: {behavior: label for label,behavior in specials[mission].items()}
           for mission in range(8)}

def readSurvey(fname):
    data = {}
    with open(fname,'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            data[row['Participant ID'].strip().replace(' ','').upper()] = row
    return data

def processLogs(directory):
    logs = {}
    cutoff = datetime.datetime(2016,5,4,11)
    for f in sorted(os.listdir('.')):
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
            log = wpRobot.readLogData('WP%03d' % (user),mission,'.')
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
                    if __db__ and not sequences.has_key(user):
                        query = 'SELECT htp_sequence_value_used FROM hri_trust_player '\
                                'WHERE htp_amazon_id="%s"' % (f[:-6])
                        cursor.execute(query)
                        sequences[user] = int(cursor.fetchone()['htp_sequence_value_used'])
                else:
                    print >> sys.stderr,'User %d did not complete mission %d' % (user,mission+1)
    return logs

def analyzeBehaviors(data,correct):
    behaviors = [{} for i in range(8)]
    for userID in data:
        for mission in range(8):
            datum = data[userID][mission]
            if 'sequence' in datum and len(datum['sequence']) == 15:
                try:
                    behaviors[mission][datum['sequence']].add(userID)
                except KeyError:
                    behaviors[mission][datum['sequence']] = {userID}
    samePolicy = {}
    rows = []
    conditions = ['explanation','acknowledgment','biomorphic']
    for mission in range(8):
        if mission > 0:
            for label,sequence in specials[mission].items():
                if sequence in behaviors[mission]:
                    if label in {'correct','follow confident'}:
                        # No one can follow these policies without explanation
                        followers = {u for u in behaviors[mission][sequence] \
                                     if data[u][mission]['explanation'] == 'confidence'}
                    else:
                        followers = behaviors[mission][sequence]
                    print mission,label
                    print followers
                    if label in samePolicy:
                        # Are these users still following the same policy?
                        samePolicy[label] &= followers
                    else:
                        # Haven't started looking at users following this policy
                        samePolicy[label] = followers
        for behavior in sorted(behaviors[mission]):
            users = behaviors[mission][behavior]
            row = {'mission': mission+1,
                   'sequence': behavior,
                   'label': None,
                   'count': len(behaviors[mission][behavior]),
                   'compliance': behavior.count('f'),
                   'correctness': len([i for i in range(len(behavior)) \
                                       if behavior[i] == correct[mission][i]]),
                   'explanation': len([u for u in users if data[u][mission]['explanation'] == 'confidence']),
                   'acknowledgment': len([u for u in users if data[u][mission]['acknowledgment'] == 'True']),
                   'biomorphic': len([u for u in users if data[u][mission]['embodiment'] == 'dog']),
                   }
            for category in conditions:
                row['%% %s' % (category)] = float(row[category])/float(row['count'])
            for label,sequence in specials[mission].items():
                if behavior == sequence:
                    row['label'] = label
                    break
            rows.append(row)
    with open('wpbehaviors.csv', 'w') as csvfile:
        fieldnames = ['sequence','label','mission','count','compliance','correctness']+\
                     conditions+['%% %s' % (category) for category in conditions]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames,extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print samePolicy
    return behaviors

def hamming(b1,b2,length):
    return len([i for i in range(length) if b1[i] != b2[i]])

def nearestNeighbors(b1,length,bList):
    neighbors = sorted([(hamming(b1,b2,length),b2) for b2 in bList])
    minDistance = neighbors[0][0]
    for i in range(len(neighbors)):
        if neighbors[i][0] > minDistance:
            break
    else:
        i = len(neighbors)
    return [neighbors[j][1] for j in range(i)],minDistance

def analyzeBuckets(data,behaviors,surveys,minSize=2,mission=None):
    if mission is None:
        for mission in range(8):
            analyzeBuckets(data,behaviors,surveys,minSize,mission)
        rows = []
        summaryFields = set()
        for question,q in SURVEY.items():
            fields = ['gameID']
            for mission in range(8):
                for t in range(1,16):
                    for field in ['improve approx']:
                        fields.append('%d %s %d %s' % (mission+1,q,t,field))
            with open('wp%s.csv' % (q), 'w') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fields,
                                        extrasaction='ignore')
                writer.writeheader()
                for user in sorted(data):
                    writer.writerow(data[user][8])
            # Summarize improvement for this question
            row = {'question': q}
            totalNum = [0,0,0]
            totalDen = [0,0,0]
            for mission in range(8):
                for t in range(5,16,5):
                    num = 0
                    den = 0
                    for user in data:
                        field = '%d %s %d improve approx' % (mission+1,q,t)
                        if field in data[user][8]:
                            value = data[user][8][field]
                            if value is True:
                                num += 1
                                den += 1
                                if t % 5 == 0:
                                    totalNum[t/5-1] += 1
                                    totalDen[t/5-1] += 1
                            elif value is False:
                                den += 1
                                if t % 5 == 0:
                                    totalDen[t/5-1] += 1
                            else:
                                raise ValueError,'Unknown value: "%s"' % (value)
                    field = '%d %02d' % (mission+1,t)
                    summaryFields.add(field)
                    row[field] = float(num)/float(den)
            for t in range(3):
                row['cumulative %d' % ((t+1)*5)] = float(totalNum[t])/\
                                                   float(totalDen[t])
            rows.append(row)
        with open('wpeval%d.csv' % (minSize),'w') as csvfile:
            writer = csv.DictWriter(csvfile,extrasaction='ignore',
                                    fieldnames=['question']+sorted(summaryFields)+\
                                    ['cumulative 5','cumulative 10','cumulative 15'])
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    else:
        print 'Mission %d' % (mission+1)
        conditions = {'acknowledgment','embodiment','explanation'}
        for user in data:
            datum = data[user][mission]
            surveyID = datum['surveyID']
            if surveyID in surveys[mission+1]:
                for question,q in SURVEY.items():
                    a = int(surveys[mission+1][surveyID][question])
                    datum[q] = a
        # Evaluate sub-sequence predictions
        model = {b:t for b,t in behaviors[mission].items() if len(t) >= minSize}
        for user in sorted(data):
            datum = data[user][mission]
            if len(data[user]) == 8:
                data[user].append({})
                data[user][8].update(datum)
            behavior = datum['sequence']
            for question,q in SURVEY.items():
                if not q in datum:
                    continue
                for t in range(1,16):
                    if len(behavior) < t:
                        continue
                    neighbors,distance = nearestNeighbors(behavior,t,model)
                    prefix = '%d %s %d' % (mission+1,q,t)
                    data[user][8]['%s |neighbors|' % (prefix)] = len(neighbors)
                    data[user][8]['%s neighbor distance' % (prefix)] = distance
                    prediction = getPrediction(data,q,behaviors,neighbors,mission,
                                               (behavior,datum[q]))
                    data[user][8]['%s model exact' % (prefix)] = prediction.get(datum[q])
                    data[user][8]['%s model approx' % (prefix)] = prediction.get(datum[q]-1)+prediction.get(datum[q])+prediction.get(datum[q]+1)
                    # Predict using everybody, instead of neighbors
                    prediction = getPrediction(data,q,behaviors,behaviors[mission].keys(),
                                               mission,(behavior,datum[q]))
                    data[user][8]['%s full exact' % (prefix)] = prediction.get(datum[q])
                    data[user][8]['%s full approx' % (prefix)] = prediction.get(datum[q]-1)+prediction.get(datum[q])+prediction.get(datum[q]+1)
                    data[user][8]['%s improve exact' % (prefix)] = data[user][8]['%s model exact' % (prefix)] > data[user][8]['%s full exact' % (prefix)]
                    data[user][8]['%s improve approx' % (prefix)] = data[user][8]['%s model approx' % (prefix)] > data[user][8]['%s full approx' % (prefix)]
                    if t == 15 and data[user][8]['%s improve exact' % (prefix)] and q == 'capable' and len(neighbors) == 1 and data[user][mission]['sequence'] in labeler[mission] and mission > 0:
                        print user,mission+1
                        print data[user][mission]['sequence']
                        print neighbors[0]
                        print question,data[user][mission][q]
                        print labeler[mission][neighbors[0]]
                        for var in ['|neighbors|','neighbor distance','model exact','full exact']:
                            key = '%s %s' % (prefix,var)
                            print key,data[user][8][key]
                        sys.exit(0)
                    else:
                        print 'skipping',user,mission+1

def getPrediction(data,q,behaviors,subset,mission,leaveOut=None):
    dist = {}
    for behavior in subset:
        for user in behaviors[mission][behavior]:
            if q in data[user][mission]:
                a = data[user][mission][q]
                dist[a] = dist.get(a,0)+1
        if leaveOut and behavior == leaveOut[0]:
            # Used as model data point, so remove
            try:
                dist[leaveOut[1]] -= 1
            except KeyError:
                print 'Missing:',leaveOut[1], dist
    print dist
    prediction = Distribution({k: float(v) for k,v in dist.items()})
    prediction.normalize()
    return prediction
    
def analyzePredictions(data,behaviors,surveys,minSize=0):
    uniques = 0
    totalScore = 0.
    alwaysFollow = 0
    for mission in range(8):
        missionScore = 0.
        for oneOut in sorted(behaviors[mission]):
            # Remove one *person* who exhibited this behavior (not the whole bucket)
            score = 0.
            for t in range(1,15):
                obs = oneOut[:t]
                model = {b for b in behaviors[mission].keys() \
                         if len(behaviors[mission][b]) >= minSize}
                if len(behaviors[mission][oneOut]) == 1:
                    # Only one person, so remove whole bucket
                    model -= {oneOut}
                    if t == 1:
                        uniques += 1
                neighbors,distance = nearestNeighbors(obs,t,model)
                count = [0,0] # [Follow,Ignore]
                for behavior in neighbors:
                    if behavior[t] == 'i':
                        count[1] += len(behaviors[mission][behavior])
                    else:
                        count[0] += len(behaviors[mission][behavior])
                if oneOut[t] == 'f':
                    alwaysFollow += len(behaviors[mission][behavior])
                    score += float(count[0])/float(count[0]+count[1])
                else:
                    score += float(count[1])/float(count[0]+count[1])
            score /= 14.
            print oneOut,score
            missionScore += float(len(behaviors[mission][oneOut]))*score
        totalScore += missionScore
        missionScore /= float(sum(map(len,behaviors[mission].values())))
        print missionScore
    print uniques/8
    
    totalScore /= float(sum(map(len,sum([behaviors[mission].values() \
                                         for mission in range(8)],[]))))
    print totalScore
    dumbScore = float(alwaysFollow)/float(14*sum(map(len,sum([behaviors[mission].values() \
                                         for mission in range(8)],[]))))
    print dumbScore
    return

def analyzeCorrectness(data,behaviors,survey,minSize):
    conditions = [('explanation',{'confidence','none'}),
                  ('acknowledgment',{False, True}),
                  ('embodiment',{'robot','dog'})]
    variations = {'%s%s%s' % (list(conditions[0][1])[i%2],list(conditions[1][1])[(i/2)%2],
                              list(conditions[2][1])[(i/4)%2]) for i in range(8)}
    # Keep track of how many participants fall into each cluster
    split = {c: {seq: 0 for seq in specials[0]} for c in variations}
    # Keep track of how many participants match each prototype behavior exactly
    exact = {c: {seq: 0 for seq in specials[0]} for c in variations}
    # Keep track of behaviors after mission 1
    warm = {c: {seq: 0 for seq in specials[0]} for c in variations}
    # Keep track of which conditions engender which behaviors for each user
    reactions = {}
    groups = {'always': set(),
              'never': set(),
              'robot': set()}
    for user,datum in sorted(data.items()):
        datum[0]['transition'] = {}
        datum[0]['split'] = {'confidence': {},'none': {}}
        mySplit = datum[0]['split']
        reactions[user] = {}
        for mission in range(8):
            if datum[mission]['sequence']:
                condition = '%s%s%s' % tuple([datum[mission][c[0]] for c in conditions])
                if not condition in split:
                    continue
                neighbors,distance = nearestNeighbors(datum[mission]['sequence'],15,
                                                      specials[mission].values())
                entry = {'bucket': {labeler[mission][seq] for seq in neighbors},
                         'distance': distance}
                if datum[mission]['sequence'] in labeler[mission]:
                    label = labeler[mission][datum[mission]['sequence']]
                    exact[condition][label] += 1
                    if condition[:3] == 'con':
                        reactions[user][label] = reactions[user].get(label,set()) | {condition}
                elif condition[:3] == 'con':
                    reactions[user]['other'] = reactions[user].get('other',set()) | {condition}
                for seq in neighbors:
                    label = labeler[mission][seq]
                    if label in split[condition]:
                        split[condition][label] += 1
                        if mission > 0:
                            warm[condition][label] += 1
                    mySplit[datum[mission]['explanation']][label] = mySplit[datum[mission]['explanation']].get(label,0)+1
                for condition in conditions:
                    value = datum[mission][condition[0]]
                    entry[condition[0]] = value
                datum[0]['transition'][mission] = entry
        if len(datum[0]['transition']) == 8:
#            print [datum[0]['transition'][mission]['bucket'] for mission in range(8) \
#                   if mission in datum[0]['transition']]
            print user
            for condition,seqs in sorted(reactions[user].items()):
                print '%s: %s' % (condition,','.join(list(seqs)))
            if len(reactions[user]) == 1 and 'correct' in reactions[user]:
                groups['always'].add(user)
            elif not 'correct' in reactions[user]:
                groups['never'].add(user)
            elif len(reactions[user]) > 1 and 'correct' in reactions[user]:
                # Sometimes correct, sometimes not
                if reactions[user]['correct'] == {'confidenceTruerobot',
                                                  'confidenceFalserobot'}:
                    groups['robot'].add(user)
    for condition,table in sorted(split.items()):
        print condition
        print sorted(table.items())
        print sorted(exact[condition].items())
    answers = {}
    common = set()
    for group in ['always','never']:
        print group
        answers[group] = {}
        for user in groups[group]:
            surveyID = data[user][0]['surveyID']
            if not surveyID in survey[0]:
                # User did not fill out background survey
                continue
            for question,table in survey[0][surveyID].items():
                if not question in answers[group]:
                    answers[group][question] = {}
                try:
                    answer = int(survey[0][surveyID][question])
                except ValueError:
                    continue
                answers[group][question][answer] = answers[group][question].get(answer,set()) | {user}
        if group == 'always':
            for question,table in answers['always'].items():
                if 0 < len(table) < 3:
                    common.add(question)
    for question in common:
        print question
        print sorted(answers['always'][question])
        print sorted(answers['never'][question])
        
if __name__ == '__main__':
    # Read data from file
    data = {}
    with open('wpdata.csv','r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                data[row['gameID']].append(row)
            except KeyError:
                data[row['gameID']] = [row]
    # Read survey files
    survey = []
    survey.append(readSurvey('Survey_Background.csv'))
    for mission in range(8):
        survey.append(readSurvey('Survey_Mission%d.csv' % (mission+1)))
    if __db__:
        # Open connection to database
        config = ConfigParser.SafeConfigParser()
        config.read('db.cfg')
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
        cursor = db.cursor()
    # Process log files
    logs = processLogs('.')
    sequences = {}
    correctSeq = ['' for mission in range(8)]
    valid = []
    for user in sorted(logs.keys()):
        if len(logs[user]) == 8:
            valid.append(user)
        else:
            print >> sys.stderr, 'User %d did not complete 8 missions' % (user)
    print >> sys.stderr,'%d Valid Users' % (len(valid))
    decisionCases = ['true+', 'false+', 'true-', 'false-']
    if data:
        for user in valid:
            assert 'WP%03d' % (user) in data,'Data missing user %s' % (user)
    else:
        data = {}
    for user in sorted(logs):
        userID = 'WP%03d' % (user)
        if not userID in data:
            data[userID] = []
        for mission in range(8):
#            print 'User %d, Mission %d' % (user,mission+1)
            # Process the data from this mission
            try:
                datum = data[userID][mission]
            except IndexError:
                datum = {'gameID': userID,
                         'mission': mission+1,
                         }
            # Check for surveys
            if not 'surveyID' in datum:
                try:
                    datum['surveyID'] = surveyMap[datum['gameID']].upper()
                except KeyError:
                    datum['surveyID'] = datum['gameID']
            if mission == 0:
                if not datum['surveyID'] in survey[0]:
                    print >> sys.stderr,'User %d did not fill out background survey' % (user)
            if not datum['surveyID'] in survey[mission+1]:
                print >> sys.stderr,'User %d did not fill out post-survey for mission %d' % (user,mission+1)
            if not 'sequence' in datum or len(correctSeq[mission]) < 15:
                datum['deaths'] = 0
                for case in decisionCases:
                    datum[case] = 0
                for case in decisionCases:
                    datum['follow_%s' % (case)] = 0
                    datum['ignore_%s' % (case)] = 0
                if mission in logs[user]:
                    log = logs[user][mission]
                    log.reverse()
                    datum['explanation'] = log[0]['explanation']
                    datum['time'] = log[-1]['time']
                    datum['sequence'] = ''
                    for entry in log[1:]:
                        if entry['type'] == 'message':
                            recommendation = entry['recommendation']
                        elif entry['type'] == 'location' or entry['type'] == 'complete':
                            if entry['ack'] != '':
                                datum['acknowledgment'] = True
                            if entry['dead'] == 'True':
                                datum['deaths'] += 1
                            if recommendation == 'yes':
                                if entry['choice'] == 'False':
                                    choice = 'ignore'
                                else:
                                    choice = 'follow'
                                if entry['danger'] == 'none':
                                    case = 'false+'
                                    if len(correctSeq[mission]) < 15:
                                        correctSeq[mission] += 'i'
                                else:
                                    case = 'true+'
                                    if len(correctSeq[mission]) < 15:
                                        correctSeq[mission] += 'f'
                            else:
                                if entry['choice'] == 'False':
                                    choice = 'follow'
                                else:
                                    choice = 'ignore'
                                if entry['danger'] == 'none':
                                    case = 'true-'
                                    if len(correctSeq[mission]) < 15:
                                        correctSeq[mission] += 'f'
                                else:
                                    case = 'false-'
                                    if len(correctSeq[mission]) < 15:
                                        correctSeq[mission] += 'i'
                            datum[case] += 1
                            datum['%s_%s' % (choice,case)] += 1
                            datum['sequence'] += choice[0]
            if not datum.has_key('acknowledgment'):
                datum['acknowledgment'] = False
            if user in sequences:
                # Condition check
                condition = (sequences[user]+mission) % 8
                datum['embodiment'] = SEQUENCE[condition]['robot_embodiment']
                assert datum['explanation'] == SEQUENCE[condition]['explanation_mode']
                if SEQUENCE[condition]['robot_ack'] == 'yes':
                    assert datum['acknowledgment']
                else:
                    assert not datum['acknowledgment']
            if len(data[userID]) < mission+1:
                data[userID].append(datum)
            decisions = sum([int(datum[case]) for case in decisionCases])
            if decisions != 15:
                print >> sys.stderr,'User %s94, Mission %d: Only %d/15 decisions' % \
                    (userID,mission,decisions)
            datum['follow'] = sum([int(datum['follow_%s' % (case)]) \
                                   for case in decisionCases])
            datum['ignore'] = sum([int(datum['ignore_%s' % (case)]) \
                                   for case in decisionCases])
    # Write data to file
    with open('wpdata.csv', 'w') as csvfile:
        fieldnames = ['gameID','surveyID','mission','explanation','acknowledgment','embodiment','time','deaths','sequence']
        fieldnames += decisionCases
        fieldnames += ['follow','ignore']
        fieldnames += ['follow_%s' % (case) for case in decisionCases]
        fieldnames += ['ignore_%s' % (case) for case in decisionCases]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames,extrasaction='ignore')
        writer.writeheader()
        for user in sorted(data):
            for datum in data[user]:
                writer.writerow(datum)
    # Analyze behavioral observations
    behaviors = analyzeBehaviors(data,correctSeq)
#    analyzeBuckets(data,behaviors,survey,1)
#    analyzeBuckets(data,behaviors,survey,3)
    analyzeBuckets(data,behaviors,survey,5)
#    analyzeCorrectness(data,behaviors,survey,5)
