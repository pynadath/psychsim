from argparse import ArgumentParser
import csv
import logging
import os
import statistics

from psychsim.pwl.keys import stateKey
from psychsim.domains.groundtruth.simulation.data import demographics
from psychsim.domains.groundtruth import accessibility

def oldMetric():
    parser = ArgumentParser()
    parser.add_argument('instances',help='Instance to query')
    parser.add_argument('-r','--run',default=0,help='Run to query')
    parser.add_argument('--region',default=None,help='Region to single out')
    parser.add_argument('fields',nargs='+',help='Fields to include in report')
    args = vars(parser.parse_args())

    instances = args['instances'].split(',')
    instances = [instance.split('-') for instance in instances]
    instances = sum([list(range(int(instance[0]),int(instance[1])+1))
                     if len(instance) == 2 else [int(instance[0])]
                     for instance in instances],[])
    valid = {}
    root = os.path.join(os.path.dirname(__file__),'..')
    values = {instance: {} for instance in instances}
    for instance in instances:
        # Read in all potential QOIs
        if args['run'] == 'all':
            runs = os.listdir(os.path.join(root,'Instances','Instance%d' % (instance),'Runs'))
        else:
            runs = ['run-%s' % (args['run'])]
        for runFile in runs:
            values[instance][runFile] = {}
            label = '%s%s' % (instance,runFile)
            inFile = os.path.join(root,'Instances','Instance%d' % (instance),
                                  'Runs',runFile,'SummaryStatisticsDataTable.tsv')
            with open(inFile,'r') as csvfile:
                reader = csv.DictReader(csvfile,delimiter='\t')
                for row in reader:
                    if row['VariableName'][:8] == 'Regional' or 'all' in args['fields']:
                        if args['region'] is None or args['region'] == row['EntityIdx']:
                            if row['VariableName'][:8] == 'Regional':
                                feature = row['VariableName'][9:]
                            else:
                                feature = row['VariableName']
                            if 'all' in args['fields'] or feature in args['fields']:
                                if row['EntityIdx'][0] == '[':
                                    field = 'All %s' % (feature)
                                else:
                                    field = stateKey(row['EntityIdx'],feature)
                                if field not in values[instance][runFile]:
                                    values[instance][runFile][field] = []
                                if '.' in row['Value']:
                                    values[instance][runFile][field].append(float(row['Value']))
                                else:
                                    values[instance][runFile][field].append(int(row['Value']))
                                if instance == instances[0]:
                                    valid[field] = row
                # Analyze QOI time series. Filter out those with nonzero variance.
                for field in list(valid.keys()):
                    if statistics.pvariance(values[instance][runFile][field]) < 1e-8:
                        print(field,instance,runFile)
                        if field[:3] == 'All':
                            del valid[field]
                        else:
                            for other in [f for f in valid if f[:6] == 'Region' and f[8:] == field[8:]]:
                                del valid[other]
    for instance in instances:
        # Write QOI subset
        for runFile,table in values[instance].items():
            timespan = len(table[next(iter(valid))])
            with open(os.path.join(root,'Instances','Instance%d' % (instance),
                                   'Runs',runFile,'QOITable.tsv'),'w') as csvfile:
                fields = ['Timestep','VariableName','EntityIdx','Value','Metadata']
                writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
                writer.writeheader()
                for t in range(timespan):
                    for field,entry in valid.items():
                        assert len(table[field]) == timespan,\
                            'Instance %d has %d values for %s instead of %d' % \
                            (instance,len(table[field]),field,timespan)
                        record = dict(entry)
                        record['Timestep'] = t+1
                        record['Value'] = table[field][t]
                        writer.writerow(record)

dataFiles = {'RunDataTable','InstanceVariableTable','RelationshipDataTable','QualitativeDataTable','SummaryStatisticsDataTable'}
mapping = {'TA2B-TA1C-11': 'ActorPostTable', 'TA2B-TA1C-12_revise10': 'ActorPostTable'}
timestep = {'TA2B-TA1C-1': 82, 'TA2A-TA1C-0032': 82}
evacuate = {'Evacuated', 'Evacuated All Hurricanes', 'Evacuated Previous Hurricane','Hurricane 1: Evacuated?','Hurricane 2: Evacuated?', 'Hurricane 3: Evacuated?', 'Hurricane 4: Evacuated?', 'Hurricane 5: Evacuated?', 'Hurricane 6: Evacuated?', 'LastEvacuated'}
shelter = {'At Shelter', 'At Shelter All Hurricanes', 'At Shelter Previous Hurricane', 'Hurricane 1: Went to Shelter?', 'Hurricane 2: Went to Shelter?', 'Hurricane 3: Went to Shelter?', 'Hurricane 4: Went to Shelter?', 'Hurricane 5: Went to Shelter?', 'Hurricane 6: Went to Shelter?', 'LastSheltered'}


def findMatches(record,world):
    mismatch = {}
    matches = set()
    for name in sorted(world.agents.keys()):
        if name[:5] == 'Actor':
            for field,feature in sorted(demographics.items()):
                key = stateKey(name,feature)
                if world.variables[key]['domain'] is bool:
                    value = {True: 'yes',False: 'no'}[world.agents[name].getState(feature).first()]
                elif feature == 'resources':
                    # Wealth has changed since beginning
                    continue
                else:
                    value = str(world.agents[name].getState(feature).first())
                if record[field] != value:
                    try:
                        mismatch[field].append(name)
                    except KeyError:
                        mismatch[field] = [name]
                    break
            else:
                logging.info('Participant %s: %s' % (row['Participant'],name))
                matches.add(name)
    if matches:
        return matches
    else:
        raise ValueError('No match for %s (mismatches: %s)' % (row['Participant'],mismatch))

if __name__ == '__main__':
    parser = accessibility.createParser(output='metrics.tsv',day=True)
    args = accessibility.parseArgs(parser)
    loadData = accessibility.loadFromArgs(args,participants=True,world=True,hurricanes=True)
#    runData = accessibility.loadRunData(args['instance'],args['run'])
    names = os.listdir(loadData['directory'])
    fieldTable = {}
    agentTable = {}
    participants = {}
    time2hurricane = []
    for hurricane in loadData['hurricanes']:
        time2hurricane += [hurricane['Hurricane']-1 for t in range(len(time2hurricane),hurricane['Start'])]
    for filename in names:
        base,ext = os.path.splitext(filename)
        if ext == '.tsv' and filename != args['output']:
            with open(os.path.join(loadData['directory'],filename),'r') as csvfile:
                reader = csv.DictReader(csvfile,delimiter='\t')
                fields = set(reader.fieldnames)
                fieldTable[base] = fields
                if 'Participant' in fields:
                    agentTable[base] = {}
                    participants[base] = {}
                    for row in reader:
                        if 'Timestep' not in row:
                            row['Timestep'] = '%d' %(timestep[base])
                        if base in mapping:
                            # Participants are given by another table
                            agentTable[base][row['Participant']] = row
                        else:
                            matches = findMatches(row,loadData['world'])
                            assert len(matches) == 1
                            agent = next(iter(matches))
                            participants[base][row['Participant']] = agent
                            agentTable[base][agent] = agentTable[base].get(agent,[])+[row]
    for link,orig in mapping.items():
        for participant,row in list(agentTable[link].items()):
            del agentTable[link][participant]
            agent = participants[orig][participant]
            agentTable[link][agent] = agentTable[link].get(agent,[])+[row]
    history = {}
    responses = {}
    for base,table in agentTable.items():
        for agent,rows in sorted(table.items()):
            if agent not in history:
                history[agent] = {}
                responses[agent] = {}
            for row in rows:
                t = int(row['Timestep'])
                if t not in history[agent]:
                    history[agent][t] = set()
                history[agent][t] |= set(row.keys())
                for field in row:
                    if field[-1] == '?':
                        elements = field.split()
                        hurricane = int(elements[1][:-1])
                    else:
                        try:
                            hurricane = time2hurricane[t]
                        except IndexError:
                            hurricane = time2hurricane[-1]+1
                    if hurricane <= 6:
                        responses[agent][field] = responses[agent].get(field,set())|{hurricane}
    data = []
    for name in sorted(loadData['world'].agents):
        if name[:5] == 'Actor':
            assert name in responses
            row = {'Actor': name}
            for field in sorted(evacuate)+sorted(shelter):
                row[field] = ';'.join(['%d' % (t) for t in sorted(responses[name].get(field,set()))])
                row[field] = len((responses[name].get(field,set())))
            row['%'] = (len(responses[name].get('Evacuated',set())|responses[name].get('Evacuated Previous Hurricane',set()))/6)
            data.append(row)
    accessibility.writeOutput(args,data,['Actor','%']+sorted(evacuate)+sorted(shelter))