import csv
import logging
import os.path

from psychsim.pwl.keys import *
from psychsim.probability import Distribution
from psychsim.domains.groundtruth import accessibility

labels = {'Output': 'Actual',
    'OutputMax': 'Most Likely',
    'Counterfactual': 'Counterfactual',
    'CounterfactualMax': 'Most Likely Counterfactual'}

fields = {False: ['Instance','Outcome','Probability','Global Deaths','Global Evacuees','Local Min Deaths %','Local Max Deaths %',
                'Local Min Evacuees %','Local Max Evacuees %','Individual Death','Individual Evacuations'],
        True: ['Instance','Outcome','Probability','Global Casualties','Global Evacuees','Local Min Casualties %','Local Max Casualties %',
                'Local Min Evacuees %','Local Max Evacuees %','Individual Casualty','Individual Evacuation']}

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename=os.path.join(os.path.dirname(__file__),'predict.log'))
    for instance in range(3,9):
        logging.info('Instance %d' % (instance))
        output = []
        short = (instance < 6)
        args = accessibility.instances[instance-1]
        targetID = accessibility.getTarget(args['instance'],args['run'])
        participants = accessibility.readParticipants(args['instance'],args['run'],os.path.join('Input','psychsim.log'))
        target = participants['ActorPostTable'][targetID]
        logging.info('Target: %s' % (target))
        run = args['run']
        runs = {'Output': [],'Counterfactual': []}
        while run < 30:
            conditions = ['Output','Counterfactual']
            if run == args['run']:
                conditions += ['OutputMax','CounterfactualMax']
            for query in conditions:
                try:
                    data = accessibility.loadRunData(args['instance'],run,
                        subs=[query] if query == 'OutputMax' else [(args['run'],'Input'),query])
                except ValueError:
                    data = accessibility.loadRunData(args['instance'],run,subs=[query])
                except FileNotFoundError:
                    logging.error('Missing outcome %s on run %d for Instance%d' % (query,run,args['instance']))
                    continue
                demos = accessibility.readDemographics(data,last=True)
                hurricanes = accessibility.readHurricanes(args['instance'],run,query)
                population = sorted([name for name in data if name[:5] == 'Actor'])
                if short:
                    logging.info('Short-term Predictions')
                else:
                    logging.info('Long-term Predictions')
                record = {'Instance': instance,
                    'Run': run,
                    'Outcome': labels[query],
                    'Count': 1,
                    'Probability': 100,
                    'Global Casualties': 0,
                    'Global Evacuees': 0,
                    'Global Deaths': 0,
                    'Individual Casualty': 'no',
                    'Individual Death': 'no',
                    'Individual Evacuation': 'no',
                    'Individual Evacuations': 0}
                regional = {name: {'Casualties': 0,'Evacuees': 0, 'Deaths': 0,'Population': 0} for name in data if name[:6] == 'Region'}
                if run == args['run']:
                    output.append(record)
                if query in runs:
                    runs[query].append(record)
                else:
                    runs[query[:-3]].append(record)
                if short:
                    hurricane = hurricanes[-1]
                    if hurricane['Hurricane'] != 7:
                        logging.error('Incomplete run? Instance %d, Run %d' % (args['instance'],run))
                        hurricane = accessibility.readHurricanes(args['instance'],args['run'],query)[-1]
                    start = hurricane['Start']
                    end = hurricane['End']
                else:
                    start = 365
                    end = max(data['Region01'][stateKey('Region01','risk')].keys())
                for name in population:
                    if not data[name][stateKey(name,'alive')][start - (1 if short else 0)]:
                        logging.info('Prior death: %s' % (name))
                        continue
                    regional[demos[name]['Residence']]['Population'] += 1
                    healthy = data[name][stateKey(name,'health')][start-(1 if short else 0)] < 0.2
                    casualty = False
                    death = False
                    evacuee = False
                    for t in range(start,end):
                        if not data[name][stateKey(name,'alive')][t]:
                            logging.info('Died on %d: %s' % (t,name))
                            assert data[name][stateKey(name,'health')][t] < 0.2
                            death = True
                        if data[name][stateKey(name,'health')][t] < 0.2:
                            if healthy:
                                # Was healthy, now injured
                                logging.info('Casualty on %d: %s' % (t,name))
                                casualty = True
                                healthy = False
                        elif not casualty and not healthy:
                            healthy = True
                        if data[name][stateKey(name,'location')][t] == 'evacuated':
                            if not evacuee: logging.info('Evacuated on %d: %s' % (t,name))
                            evacuee = True
                        if name == target:
                            if data[name][actionKey(name)][t]['verb'] == 'evacuate':
                                record['Individual Evacuations'] += 1
                    if casualty:
                        record['Global Casualties'] += 1
                        regional[demos[name]['Residence']]['Casualties'] += 1
                        if name == target:
                            record['Individual Casualty'] = 'yes'
                    if death:
                        record['Global Deaths'] += 1
                        regional[demos[name]['Residence']]['Deaths'] += 1
                        if name == target:
                            record['Individual Death'] = 'yes'
                    if evacuee:
                        record['Global Evacuees'] += 1
                        regional[demos[name]['Residence']]['Evacuees'] += 1
                        if name == target:
                            record['Individual Evacuation'] = 'yes'
                for name,stats in regional.items():
                    for field in ['Casualties','Deaths','Evacuees']:
                        regional[name]['%% %s' % (field)] = stats[field]/stats['Population']
                for field in ['Casualties','Deaths','Evacuees']:
                    if sum([regional[name][field] for name in regional]) != record['Global %s' % (field)]:
                        print(field)
                        print(record['Global %s' % (field)])
                        print([regional[name][field] for name in regional])
                        raise RuntimeError
                    stats = [regional[name]['%% %s' % (field)] for name in regional]
                    value = min(stats)
                    record['Local Min %s %%' % (field)] = ','.join(sorted([name for name in regional if regional[name]['%% %s' % (field)] == value]))
                    value = max(stats)
                    record['Local Max %s %%' % (field)] = ','.join(sorted([name for name in regional if regional[name]['%% %s' % (field)] == value]))
                print(record)
            run += 1
        # Compute distribution
        for query in ['Output','Counterfactual']:
            for field in fields[short]:
                if field not in {'Instance','Outcome','Probability'}:
                    hist = {}
                    for record in runs[query]:
                        hist[record[field]] = hist.get(record[field],0) + 1
                    dist = Distribution(hist)
                    dist.normalize()
                    for value in sorted(dist.domain(),key=lambda v: -dist[v]):
                        record ={'Instance': instance,'Outcome': labels[query],field: value,
                            'Count': hist[value],'Probability': int(round(100*dist[value]))}
                        output.append(record)
        with open(os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0',
            '%sTermPredictionAnswer.tsv' % ('Short' if short else 'Long')),'w') as csvfile:
            writer = csv.DictWriter(csvfile,fields[short],delimiter='\t',extrasaction='ignore')
            writer.writeheader()
            for record in output:
                writer.writerow(record)
