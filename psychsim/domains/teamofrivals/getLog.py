from argparse import ArgumentParser
import ConfigParser

import csv

import MySQLdb
import MySQLdb.cursors

def readLog(gameID,cursor):
    for player in range(4):
        # Read in-game survey data from db
        cursor.execute('SELECT * FROM sim_in_game_survey WHERE '+
                       'sigs_game_id=%d ' % (gameID)+
                       'AND sigs_player_number=%d' % (player+1))
        results = cursor.fetchall()
        if results:
            fields = sorted(results[0].keys())
            with open('%d_%d_survey_db.csv' % (gameID,player+1),'w') as csvfile:
                writer = csv.DictWriter(csvfile,fields,extrasaction='ignore')
                writer.writeheader()
                for record in results:
                    writer.writerow(record)
        # Read game log data from db
        cursor.execute('SELECT spl_message FROM sim_project_log WHERE '+
                       'spl_game_id=%d ' % (gameID)+
                       'AND spl_player_number=%d' % (player+1))
        results = cursor.fetchall()
        if results:
            fields = sorted(results[0].keys())
            with open('%d_%d_logs.csv' % (gameID,player+1),'w') as csvfile:
                writer = csv.DictWriter(csvfile,fields,extrasaction='ignore')
                writer.writeheader()
                for record in results:
                    writer.writerow(record)
    
if __name__ == '__main__':
    config = ConfigParser.SafeConfigParser()
    config.read('db.cfg')
    if not config.has_section('mysql'):
        config.add_section('mysql')
        config.set('mysql','host','localhost')
        config.set('mysql','user','')
        config.set('mysql','passwd','')
        with open('db.cfg','wb') as configfile:
            config.write(configfile)
    parser = ArgumentParser()
    parser.add_argument('gameID',help='Game ID')
    args = vars(parser.parse_args())
        
    db = MySQLdb.connect(host=config.get('mysql','host'),user=config.get('mysql','user'),
                         passwd=config.get('mysql','passwd'),db='simproject',
                         cursorclass=MySQLdb.cursors.DictCursor)
    cursor = db.cursor()
    idList = args['gameID'].split(',')
    idList = [int(element) if isinstance(element,str) else map(int,element.split('-')) for element in idList]
    for gameId in idList:
        if isinstance(gameId,int):
            readLog(gameId,cursor)
        else:
            for subgameId in range(gameId[0],gameId[1]):
                readLog(subgameId,cursor)
    cursor.close()
    db.close()
