import ConfigParser
import csv
import datetime
import os
import sys

import robot

import MySQLdb
import MySQLdb.cursors

userMap = {71: 11,
           75: 74,
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
    
if __name__ == '__main__':
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
    logs = {}
    sequences = {}
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
            if user in userMap:
                user = userMap[user]
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
    valid = []
    for user in sorted(logs.keys()):
        if len(logs[user]) == 8:
            valid.append(user)
        else:
            print >> sys.stderr, 'User %d did not complete 8 missions' % (user)
    print '%d Valid Users' % (len(valid))
    data = []
    decisionCases = ['true+', 'false+', 'true-', 'false-']
    for user in valid:
        for mission in range(8):
            print 'User %d, Mission %d' % (user,mission+1)
            # Process the data from this mission
            datum = {'user': 'WP%03d' % (user),'mission': mission+1,'deaths': 0}
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
                elif entry['type'] == 'location' or entry['type'] == 'complete':
#                    print entry['location']
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
                    datum[case] += 1
                    datum['%s_%s' % (choice,case)] += 1
            if not datum.has_key('acknowledgment'):
                datum['acknowledgment'] = False
            # Condition check
            condition = (sequences[user]+mission) % 8
            datum['embodiment'] = SEQUENCE[condition]['robot_embodiment']
            assert datum['explanation'] == SEQUENCE[condition]['explanation_mode']
            if SEQUENCE[condition]['robot_ack'] == 'yes':
                assert datum['acknowledgment']
            else:
                assert not datum['acknowledgment']
            data.append(datum)
            decisions = sum([datum[case] for case in decisionCases])
            if decisions != 15:
                print '\n'.join(['%s\n%s' % (e['type'],str(e)) for e in log])
                raise ValueError,'\tOnly %d/15 decisions\n%s' % (decisions,datum)
    # Write data to file
    with open('wpdata.csv', 'w') as csvfile:
        fieldnames = ['user','mission','explanation','acknowledgment','embodiment','time','deaths']
        fieldnames += decisionCases
        fieldnames += ['follow_%s' % (case) for case in decisionCases]
        fieldnames += ['ignore_%s' % (case) for case in decisionCases]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for datum in data:
            writer.writerow(datum)
