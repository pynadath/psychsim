from argparse import ArgumentParser
import csv
import os.path
import random

from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    # Read in ground truth
    parser = ArgumentParser()
    parser.add_argument('-l','--last',type=int,default=0,help='Last timestep to include in output files')
    parser.add_argument('-i','--instance',type=int,default=22,help='Instance to be processed')
    parser.add_argument('-t','--target',action='store_true',help='Whether to pick a target actor')
    parser.add_argument('-r','--run',type=int,default=0,help='Run to be processed')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--short',action='store_true',help='Short-term instance')
    group.add_argument('--long',action='store_true',help='Long-term instance')
    cmd = vars(parser.parse_args())
    print('Instance %d (Run %d)' % (cmd['instance'],cmd['run']))
    if cmd['short']:
        hurricanes = accessibility.readHurricanes(cmd['instance'],cmd['run'])
    behaviors = {}
    for table in ['RunData','RelationshipData']:
        output = []
        for record in accessibility.loadMultiCSV('%sTable_full.tsv' % (table),cmd['instance'],cmd['run'],grabFields=False):
            try:
                t = int(record['Timestep'])
                if t < cmd['last']:
                    output.append(record)
            except ValueError:
                output.append(record)
                t = None
            if table == 'RunData':
                if cmd['short'] and record['VariableName'] == 'Actor-evacuate':
                    if record['EntityIdx'] not in behaviors:
                        behaviors[record['EntityIdx']] = {}
                    behaviors[record['EntityIdx']][t] = record['Value'] == 'yes'
                elif cmd['long'] and t == cmd['last'] - 1 and record['VariableName'] == 'Actor\'s health':
                    behaviors[record['EntityIdx']] = True
        if table == 'RunData':
            if cmd['short']:
                data = {}
                prediction = {name: False for name in behaviors}
                for name,timeline in behaviors.items():
                    data[name] = set()
                    for h in hurricanes:
                        if name in data:
                            for t in range(h['Start'],h['End']):
                                if t not in timeline:
                                    # Died
                                    del data[name]
                                    break
                                if timeline[t]:
                                    # Evacuated
                                    if h['Hurricane'] < len(hurricanes):
                                        data[name].add(h['Hurricane'])
                                    elif cmd['short']:
                                        prediction[name] = True
                                    else:
                                        data[name].add(h['Hurricane'])
                                    break
                candidates = [name for name,times in data.items() if len(times) == 2 and 6 not in times and prediction[name]]
                for name in candidates:
                    print(name,data[name],prediction[name])
            elif cmd['long']:
                candidates = list(behaviors.keys())

            if cmd['target']:
                name = random.choice(candidates)
                print(name)
                output.append({'VariableName': 'TargetActor','EntityIdx': name,'Value': 'yes'})
        accessibility.writeOutput({'instance': cmd['instance'],'run': cmd['run']},output,accessibility.fields[table],'%sTable.tsv' % (table))
