"""
Module for parsing CAMEO-encoded GDELT event databases (in CSV format)
Run with -h to get usage information
"""
import argparse
import calendar
from datetime import date,timedelta,MINYEAR,MAXYEAR
import fileinput 
import os.path
import sys
import time

from psychsim.world import World
from psychsim.action import Action
from psychsim.agent import Agent

def parseCAMEO():
    """
    Extracts mapping and reverse mapping of CAMEO codes to/from event labels
    @rtype: dict,dict
    """
    cameo = {}
    oemac = {}
    for line in fileinput.input(os.path.join(os.path.dirname(__file__),'cameo.txt')):
        elements = line.split(':')
        if len(elements) == 2:
            code = int(elements[0])
            event = elements[1].strip()
            cameo[code] = event
            oemac[event] = code
    return cameo,oemac

# Global variables for reference, CAMEO and GDELT formats
cameo,oemac = parseCAMEO()
headings = 'GLOBALEVENTID	SQLDATE	MonthYear	Year	FractionDate	Actor1Code	Actor1Name	Actor1CountryCode	Actor1KnownGroupCode	Actor1EthnicCode	Actor1Religion1Code	Actor1Religion2Code	Actor1Type1Code	Actor1Type2Code	Actor1Type3Code	Actor2Code	Actor2Name	Actor2CountryCode	Actor2KnownGroupCode	Actor2EthnicCode	Actor2Religion1Code	Actor2Religion2Code	Actor2Type1Code	Actor2Type2Code	Actor2Type3Code	IsRootEvent	EventCode	EventBaseCode	EventRootCode	QuadClass	GoldsteinScale	NumMentions	NumSources	NumArticles	AvgTone	Actor1Geo_Type	Actor1Geo_FullName	Actor1Geo_CountryCode	Actor1Geo_ADM1Code	Actor1Geo_Lat	Actor1Geo_Long	Actor1Geo_FeatureID	Actor2Geo_Type	Actor2Geo_FullName	Actor2Geo_CountryCode	Actor2Geo_ADM1Code	Actor2Geo_Lat	Actor2Geo_Long	Actor2Geo_FeatureID	ActionGeo_Type	ActionGeo_FullName	ActionGeo_CountryCode	ActionGeo_ADM1Code	ActionGeo_Lat	ActionGeo_Long	ActionGeo_FeatureID	DATEADDED'.split('\t')

intHeadings = {'GLOBALEVENTID','SQLDATE','MonthYear','Year',
               'IsRootEvent','EventCode','EventBaseCode','EventRootCode','QuadClass',
               'NumMentions','NumSources','NumArticles',
               'Actor1Geo_Type','Actor1Geo_FeatureID','Actor2Geo_Type','Actor2Geo_FeatureID',
               'ActionGeo_Type','ActionGeo_FeatureID','DATEADDED'}
floatHeadings = {'FractionDate','GoldsteinScale','AvgTone',
                 'Actor1Geo_Lat','Actor1Geo_Long','Actor2Geo_Lat','Actor2Geo_Long',
                 'ActionGeo_Lat','ActionGeo_Long'}

def matchActor(name,targets):
    """
    Determines whether a given actor name is one of a given list of targets
    @type name: str
    @type targets: str[]
    @rtype: bool
    """
    if len(targets) == 0:
        # Nobody given, assume everybody is a target
        return True
    if name is None:
        # There's nobody to match
        return False
    for actor in targets:
        if name[:len(actor)] == actor:
            return True
    else:
        return False

def parseGDELT(fname,targets=[]):
    """
    Extracts events from a single GDELT CSV file
    """
    # Parse filename
    root,ext = os.path.splitext(os.path.basename(fname))
    assert ext == '.csv','CSV file expected instead of %s' % (fname)
    if len(root) == 4:
        year = int(root)
        month = 0
    else:
        assert len(root) == 6,'Filename not in YYYY.csv or YYYYMM.csv format: %s' % (fname)
        year = int(root[:4])
        month = int(root[4:])
    # Initialize storage
    result = {'month': month,
              'year': year,
              'agents': {},
              'matrix': {},
              'calendar': {},
              }
    today = None
    start = time.time()
    lines = 0
    for line in fileinput.input(fname):
        lines += 1
        # Extract the event fields
        elements = map(lambda x: x.strip(),line.split('\t'))
        event = {}
        for index in range(len(elements)):
            if len(elements[index]) == 0:
                event[headings[index]] = None
            elif headings[index] in intHeadings:
                event[headings[index]] = int(elements[index])
            elif headings[index] in floatHeadings:
                event[headings[index]] = float(elements[index])
            else:
                event[headings[index]] = elements[index].strip()
        if event['SQLDATE'] != today:
            today = event['SQLDATE']
            events = []
            result['calendar'][event['SQLDATE']] = events
            print >> sys.stderr,today
        if event['Actor1Code'] is None: 
            # No actor?
            event['Actor1Code'] = 'Unknown'
        if lines%10000 == 0 and events:
            print >> sys.stderr,'\t%dK (%d events,%d agents)' % \
                (lines/1000,len(events),len(result['agents']))
        if matchActor(event['Actor1Code'],targets) or \
                matchActor(event['Actor2Code'],targets):
            # Event matching our target
            events.append(event)
            if not result['agents'].has_key(event['Actor1Code']):
                agent = Agent(event['Actor1Code'])
                result['agents'][agent.name] = agent
            event['action'] = Action({'subject': event['Actor1Code'],
                                      'verb': cameo[event['EventCode']]})
            if event['Actor2Code']:
                if not result['agents'].has_key(event['Actor2Code']):
                    agent = Agent(event['Actor2Code'])
                    result['agents'][agent.name] = agent
                event['action']['object'] = event['Actor2Code']
            # Update relationship matrix
            if event['Actor1Code'] < event['Actor2Code']:
                key = '%s,%s' % (event['Actor1Code'],event['Actor2Code'])
            else:
                key = '%s,%s' % (event['Actor2Code'],event['Actor1Code'])
            try:
                result['matrix'][key].append(event)
            except KeyError:
                result['matrix'][key] = [event]
    return result

if __name__ == '__main__':
    # Command-line arguments
    parser = argparse.ArgumentParser(description='Create a PsychSim World from GDELT database files')
    parser.add_argument('files',metavar='FILE',nargs='+',help='names of GDELT CSV files')
    parser.add_argument('--actor',metavar='ACTOR',action='append',help='KEDS actor codes to search for')
    args = parser.parse_args()
    # Initialization
    world = World()
    count = 0
    eventCalendar = {}
    events = []
    matrix = {}
    earliest = MAXYEAR
    latest = MINYEAR
    # Get cracking
    for fname in args.files:
        result = parseGDELT(fname,args.actor)
        assert result.has_key('calendar')
        earliest = min(earliest,result['year'])
        latest = max(latest,result['year'])
        # Add relationships to the matrix
        for key,actions in result['matrix'].items():
            try:
                matrix[key] += actions
            except KeyError:
                matrix[key] = actions
        # Add new agents to the world
        for agent in result['agents'].values():
            if not world.has_agent(agent):
                world.addAgent(agent)
        # Add events to the calendar
        for when,day in result['calendar'].items():
            try:
                eventCalendar[when] += day
            except KeyError:
                eventCalendar[when] = day
            events += day
                
    # Print summary
    print >> sys.stderr,format(len(world.agents),',d'),'agents'
    print >> sys.stderr,format(len(events),',d'),'events'
    print >> sys.stderr,len(eventCalendar),'days'

    # Print calendar
    pairs = matrix.keys()
    pairs.sort()
    for pair in pairs:
        today = None
        print pair
        for event in matrix[pair]:
            if event['SQLDATE'] != today:
                print '\t',event['SQLDATE']
                today = event['SQLDATE']
            print '\t\t%s %4.2f %d/%d/%d %4.2f' % (event['action'],event['GoldsteinScale'],event['NumMentions'],event['NumSources'],event['NumArticles'],event['AvgTone'])
