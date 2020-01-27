import os.path
import pickle

from psychsim.domains.groundtruth import accessibility

def getStats(args,world,start,end,target,short):
    result = {'global': set()}
    fname = os.path.join(accessibility.getDirectory(args),'state%d%s.pkl' % (start-1,'Nature'))
    with open(fname,'rb') as f:
        state = pickle.load(f)['__state__']
    living = [name for name in world.agents if name[:5] == 'Actor' and world.getState(name,'alive',state).first()]
    assert target in living
    regions = {name: set() for name in world.agents if name[:6] == 'Region'}
    population = {region: len([name for name in living if world.agents[name].demographics['home'] == region]) for region in regions}
    for t in range(start if short else end,end+1 if short else start,1 if short else -1):
        fname = os.path.join(accessibility.getDirectory(args),'state%d%s.pkl' % (t,'Nature'))
        try:
            with open(fname,'rb') as f:
                state = pickle.load(f)['__state__']
        except FileNotFoundError:
            continue
        for name in list(living):
            if world.getState(name,'alive',state).first():
                if short and world.getState(name,'location',state).first() == 'evacuated':
                    result['global'].add(name)
                    regions[world.agents[name].demographics['home']].add(name)
            else:
                living.remove(name)
                if not short:
                    result['global'].add(name)
                    regions[world.agents[name].demographics['home']].add(name)
        if not short:
            print(t)
            break
    result['local'] = sorted([(len(evacuees)/population[region],region) for region,evacuees in regions.items()])
    result['individual'] = target in result['global']
    return result

if __name__ == '__main__':
    output = []
    for instance,args in accessibility.instanceArgs('Phase2','Predict'):
        print('Short-term' if instance == 18 else 'Long-term')
        record = {'Instance': instance}
        states = {}
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run'])]
        world = accessibility.unpickle(instance)
        try:
            target = accessibility.getTarget(args['instance'],args['run'])['Name']
        except KeyError:
            matches = accessibility.findMatches({'Gender': 'male','Age': 74,'Ethnicity': 'majority','Religion': 'minority','Children': 0,
                'Fulltime Job': 'yes','Pets': 'no','Wealth': 7,'Residence': 'Region10','Participant': 'ActorPost 93'},world)
            assert len(matches) == 1
            target = next(iter(matches))
        for run in range(args['run'],5):
            states.clear()
            stats = getStats({'instance': args['instance'],'run': run},world,hurricanes[6]['Start'] if instance==18 else 367,
                hurricanes[6]['End'] if instance == 18 else 500,target,instance==18)
            if run == args['run']:
                record['Q1 Best'] = len(stats['global'])
                record['Q2 Best'] = stats['local'][-1][1]
                record['Q3 Best'] = 'yes' if stats['individual'] else 'no'
            elif run == 4:
                record['Q4(1) Best'] = len(stats['global'])
                record['Q4(2) Best'] = stats['local'][-1][1]
                record['Q4(3) Best'] = 'yes' if stats['individual'] else 'no'
            print(run,len(stats['global']),stats['individual'])
            print(stats['local'])
        output.append(record)
