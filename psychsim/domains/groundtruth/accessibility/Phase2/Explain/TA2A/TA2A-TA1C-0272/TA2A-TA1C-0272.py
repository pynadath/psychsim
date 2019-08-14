import os.path

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    variables = [{'Name': '# Crimes', 'Values': '[0+]','DataType': 'Integer','Notes': '# of previous instances of misconduct by this individual'},
        {'Name': 'Severity of Crimes', 'Values': '[1-7]','DataType': 'Integer','Notes': 'Mean severity of misconduct'},
        ]
    accessibility.writeVarDef(os.path.dirname(__file__),variables)
    fields = sorted(accessibility.demographics.keys()) + ['Timestep'] + [var['Name'] for var in variables]
    for instance,args in accessibility.allArgs():
        print('Instance %d, Run %d' % (args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        if instance == 1:
            pickleDay = None
        elif instance < 9:
            pickleDay = args['span']
        elif instance < 15:
            pickleDay = args['span'] + 1
        else:
            pickleDay = 0
        world = accessibility.loadPickle(args['instance'],args['run'],pickleDay,'Input' if 3 <= instance <= 14 else None)
        hurricanes = accessibility.readHurricanes(args['instance'],args['run'],'Input' if 3 <= instance <= 14 else None)
        if accessibility.instancePhase(instance) == 1:
            data = accessibility.loadRunData(args['instance'],args['run'],args['span'],subs=['Input'] if 3 <= instance <= 14 else [None])
            population = accessibility.getPopulation(data)
            actors = {}
            # Find day of death
            for name in population:
                if data[name][stateKey(name,'alive')][len(data[name][stateKey(name,'alive')])-1]:
                    actors[name] = None
                else:
                    # Person died some time
                    for t,value in data[name][stateKey(name,'alive')].items():
                        if not value:
                            actors[name] = t
                            break
        else:
            states = {}
            actors = accessibility.getLivePopulation(args,world,states,args['span'])
        try:
            regions = {region: {name for name in actors if world.agents[name].demographics['home'] == region} 
                for region in world.agents if region[:6] == 'Region'}
        except AttributeError:
            regions = {region: {name for name in actors if world.agents[name].home == region} 
                for region in world.agents if region[:6] == 'Region'}
        severity = accessibility.likert[5][config.getint('Actors','antiresources_benefit')-1]
        crimes = {}
        epochs = {name: set() for name in actors}
        for name in actors:
            if accessibility.instancePhase(instance) == 1:
                actions = [data[name][actionKey(name)][t] for t in range(1,args['span']-1 if actors[name] is None else actors[name])]
            else:
                actions = accessibility.getAction(args,name,world,states,(1,args['span'] if actors[name] is None else actors[name]))
            crimes[name] = [t+1 for t in range(len(actions)) if actions[t]['verb'] == 'takeResources']
            # Aggregate crime by pre, in, post hurricane periods
            hurricane = 0
            index = 0
            while index < len(crimes[name]):
                if crimes[name][index] < hurricanes[hurricane]['Start']:
                    epochs[name].add('Pre %d' % (hurricanes[hurricane]['Hurricane']))
                    index += 1
                elif crimes[name][index] < hurricanes[hurricane]['End']:
                    epochs[name].add('In %d' % (hurricanes[hurricane]['Hurricane']))
                    index += 1
                else:
                    hurricane += 1
                    if hurricane == len(hurricanes):
                        # After the last hurricane
                        epochs[name].add('Post %d' % (hurricane))
                        break
        output = []
        for region in sorted(regions):
            criminals = {name for name in regions[region] if epochs[name]}
            for name in criminals:
                if accessibility.instancePhase(instance) == 1:
                    record = accessibility.readDemographics(data,instance == 1,crimes[name][-1],name)[name]
                else:
                    record = accessibility.getCurrentDemographics(args,name,world,states,config,crimes[name][-1])
                record['Timestep'] = crimes[name][-1]
                record['# Crimes'] = len(epochs[name])
                record['Severity of Crimes'] = accessibility.toLikert(severity*len(crimes[name])/len(epochs[name]),7)
                output.append(record)
        accessibility.writeOutput(args,output,fields,'TA2A-TA1C-0272.tsv',os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
