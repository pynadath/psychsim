from argparse import ArgumentParser
import logging
import os.path
import random

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility

def aidWillingnessEtc(args,agent,record,world,states,demos,hurricanes,alive,variables=None):
    """
    :param args: The usual instance/run/span/etc. dictionary
    :type args: dict
    :param agent: The agent object that is being surveyed
    :type agent: Agent
    :param record: The response record being filled out (modified in place)
    :type record: dict
    :param world: The PsychSim object
    :type world: World
    :param states: the dictionary of pickled states (or run data if Phase 1)
    :type states: dict
    :param demos: Table of demographic data
    :type demos: dict
    :param hurricanes: List of hurricanes
    :type hurricanes: list
    :param alive: set of names of actors who are still alive
    :type alive: set
    :param variables: if provided, any new variables defined are appended (default is None)
    :type variables: list
    """
    if variables:
        variables.append({'Name': 'Out Friends','Values': '[0+]','VarType': 'dynamic','DataType': 'Integer','Notes': '0.i.k'})
    friends = agent.getFriends() & alive # Dead friends don't count
    neighbors = agent.getNeighbors() & alive # Dead neighbors don't count
    record['Out Friends'] = len(friends - neighbors)
    # 0.i.l
    if variables:
        variables.append({'Name': 'In Friends','Values': '[0+]','VarType': 'dynamic','DataType': 'Integer','Notes': '0.i.l'})
    record['In Friends'] = len(friends & neighbors)
    # 0.i.m
    if variables:
        variables.append({'Name': 'Acquaintances','Values': '[0+]','VarType': 'dynamic','DataType': 'Integer', 'Notes': '0.i.m: Friends not included'})
    record['Acquaintances'] = len(neighbors - friends)
    # 0.ii.a
    if variables:
        variables.append({'Name': 'Aid if Wealth Loss','Values':'[0-6]','DataType': 'Integer','Notes': '0.ii.a'})
    record['Aid if Wealth Loss'] = accessibility.toLikert(accessibility.aidIfWealthLoss(agent),7) - 1
    # 0.ii.b
    if variables:
        variables.append({'Name': 'Hurricane Vulnerability','Values':'[0-6]','DataType': 'Integer','Notes': '0.ii.b'})
    beliefs = map(float,accessibility.getInitialState(args,agent.name,'risk',world,states,(1,args['span']),agent.name))
    record['Hurricane Vulnerability'] = accessibility.toLikert(max(beliefs),7) - 1
    # 0.ii.c
    if variables:
        variables.append({'Name': 'Stay Home Willingness','Values':'[0-6]','DataType': 'Integer','Notes': '0.ii.c'})
    count = 0
    for hurricane in hurricanes:
        locations = set(accessibility.getInitialState(args,agent.name,'location',world,states,(hurricane['Start'],hurricane['End']+1)))
        if len(locations) == 1 and record['Residence'] in locations:
            # Person stayed home the whole time
            count += 1
    record['Stay Home Willingness'] = accessibility.toLikert(count/len(hurricanes),7)-1
    # 0.ii.d-k
    altruism = agent.Rweights['neighbors']/sum(agent.Rweights.values())
    for hi in range(20,100,10):
        value = altruism*len([other for other in neighbors if hi-10 <= demos[other]['Age'] < hi])
        if hi == 20:
            value += altruism*sum([demos[other]['Children'] for other in neighbors])
            # This includes my children!
            value += demos[agent.name]['Children']*agent.Rweights['childrenHealth']/sum(agent.Rweights.values())
        if hi-10 <= demos[agent.name]['Age'] < hi:
            # This includes me!
            value += agent.Rweights['health']/sum(agent.Rweights.values())
        condition = 'Age'
        if hi != 20:
            condition = '%d<=%s' % (hi-10,condition)
        if hi < 90:
            condition = '%s<%d' % (condition,hi)
        var = 'Aid %s' % (condition)
        if variables:
            variables.append({'Name': var,'Values':'[0-6]','DataType': 'Integer',
                'Notes': '0.ii.%s' % (chr(ord('d')+(hi-20)//10))})
        record[var] = accessibility.toLikert(value,7)-1
    # 0.ii.l-m
    for letter,target in {'l': 'female','m': 'male'}.items():
        value = altruism*len([other for other in neighbors if demos[other]['Gender'] == target])
        if demos[agent.name]['Gender'] == target:
            # This includes me!
            value += agent.Rweights['health']/sum(agent.Rweights.values())
        var = 'Aid %s' % (target.capitalize())
        if variables:
            variables.append({'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': '0.ii.%s' % (letter)})
        record[var] = accessibility.toLikert(value,7)-1
    # 0.ii.n-o
    for letter,target in {'n': 'minority','o': 'majority'}.items():
        value = altruism*len([other for other in neighbors if demos[other]['Ethnicity'] == target])
        if demos[agent.name]['Ethnicity'] == target:
            # This includes me!
            value += agent.Rweights['health']/sum(agent.Rweights.values())
        var = 'Aid %s Ethnicity' % (target.capitalize())
        if variables:
            variables.append({'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': '0.ii.%s' % (letter)})
        record[var] = accessibility.toLikert(value,7)-1
    # 0.ii.p-r
    for letter,target in {'p': 'minority','q': 'majority', 'r': 'none'}.items():
        value = altruism*len([other for other in neighbors if demos[other]['Religion'] == target])
        if demos[agent.name]['Religion'] == target:
            # This includes me!
            value += agent.Rweights['health']/sum(agent.Rweights.values())
        var = 'Aid %s Religion' % (target.capitalize())
        if variables:
            variables.append({'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': '0.ii.%s' % (letter)})
        record[var] = accessibility.toLikert(value,7)-1
    # 0.ii.s-u
    for letter,target in {'s': 0,'t': 1, 'u': 2}.items():
        value = altruism*len([other for other in neighbors if demos[other]['Children'] == target])
        if demos[agent.name]['Children'] == target:
            # This includes me!
            value += agent.Rweights['health']/sum(agent.Rweights.values())
        var = 'Aid %d Children' % (target)
        if variables:
            variables.append({'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': '0.ii.%s' % (letter)})
        record[var] = accessibility.toLikert(value,7)-1
    # 0.ii.v-w
    for letter,target in {'v': 'yes','w': 'no'}.items():
        value = altruism*len([other for other in neighbors if demos[other]['Fulltime Job'] == target])
        if demos[agent.name]['Fulltime Job'] == target:
            # This includes me!
            value += agent.Rweights['health']/sum(agent.Rweights.values())
        var = 'Aid %s Job' % ('with' if target == 'yes' else 'without')
        if variables:
            variables.append({'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': '0.ii.%s' % (letter)})
        record[var] = accessibility.toLikert(value,7)-1
    # 0.ii.x-y
    for letter,target in {'x': 'yes','y': 'no'}.items():
        value = altruism*len([other for other in neighbors if demos[other]['Pets'] == target])
        if demos[agent.name]['Pets'] == target:
            # This includes me!
            value += agent.Rweights['health']/sum(agent.Rweights.values())
        var = 'Aid %s Pets' % ('with' if target == 'yes' else 'without')
        if variables:
            variables.append({'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': '0.ii.%s' % (letter)})
        record[var] = accessibility.toLikert(value,7)-1
    # 0.ii.z-ee
    for letter,target in {'z': 5,'aa': 4,'bb': 3,'cc': 2,'dd': 1,'ee': 0}.items():
        value = altruism*len([other for other in neighbors if demos[other]['Wealth'] == target])
        if demos[agent.name]['Wealth'] == target:
            # This includes me!
            value += agent.Rweights['health']/sum(agent.Rweights.values())
        var = 'Aid Wealth %d' % (target)
        if variables:
            variables.append({'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': '0.ii.%s' % (letter)})
        record[var] = accessibility.toLikert(value,7)-1
    # 0.ii.ff
    net = 0
    for other in neighbors:
        for hurricane in hurricanes:
            actions = set([act['verb'] for act in accessibility.getAction(args,other,world,states,(hurricane['Start'],hurricane['End']+1))])
            if 'decreaseRisk' in actions:
                net -= 1
            if 'takeResources' in actions:
                net += 1
    value = net/(len(neighbors)*len(hurricanes)) + 0.5
    var = 'Most Take Advantage'
    if variables:
        variables.append({'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': '0.ii.ff'})
    record[var] = accessibility.toLikert(value,7)-1
    # 0.ii.gg
    config = accessibility.getConfig(args['instance'])
    trust = {'over': config.getint('Actors','friend_opt_trust'),
        'under': config.getint('Actors','friend_pess_trust')}
    trust['none'] = (trust['over']+trust['under'])/2
    if friends:
        level = sum([trust[world.agents[friend].distortion] for friend in friends])/len(friends)/5
    else:
        level = 0.5
    var = 'People Can Be Trusted'
    if variables:
        variables.append({'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': '0.ii.gg'})
    record[var] = accessibility.toLikert(level,7)-1

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    cmd = vars(parser.parse_args())
    random.seed(252)
    defined = False
    variables = accessibility.boilerPlate[:]
    for instance,args in accessibility.allArgs():
        if cmd['debug']:
            print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        world = accessibility.unpickle(instance)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run'],'Input' if 3 <= instance <= 14 else None)
            if h['End'] <= args['span']]
        if accessibility.instancePhase(instance) == 1:
            states = accessibility.loadRunData(args['instance'],args['run'],args['span'],subs=['Input'] if 3 <= instance <= 14 else [None])
            population = accessibility.getPopulation(states)
            actors = {}
            # Find day of death
            for name in population:
                if states[name][stateKey(name,'alive')][len(states[name][stateKey(name,'alive')])-1]:
                    actors[name] = None
                else:
                    # Person died some time
                    for t,value in states[name][stateKey(name,'alive')].items():
                        if not value:
                            actors[name] = t
                            break        
        else:
            states = {}
            actors = accessibility.getLivePopulation(args,world,states,args['span'])
        pool = {name for name,death in actors.items() if death is None}
        demos = {name: accessibility.getCurrentDemographics(args,name,world,states,config,args['span']) for name in pool}
        participants = random.sample(pool,len(pool)//10)
        try:
            regions = {region: {name for name in actors if world.agents[name].demographics['home'] == region} 
                for region in world.agents if region[:6] == 'Region'}
        except AttributeError:
            regions = {region: {name for name in actors if world.agents[name].home == region} 
                for region in world.agents if region[:6] == 'Region'}
        output = []
        for partID in range(len(participants)):
            if not defined:
                variables.insert(0,{'Name': 'Participant','Values': '[1+]','VarType': 'fixed','DataType': 'Integer'})
            record = {'Participant': partID+1}
            output.append(record)
            name = participants[partID]
            logging.info('Participant %d: %s' % (record['Participant'],name))
            agent = world.agents[name]
            # 0.i.a-i
            record.update(demos[name])
            # 0.i.j
            record['Timestep'] = args['span']
            # 0.i.k
            aidWillingnessEtc(args,agent,record,world,states,demos,hurricanes,pool,None if defined else variables)
            # 1.one
            sources = [('i','Social Media'),('ii','Government Broadcast'),('iii','Government Officials'),('iv','Friends'),('v','Acquaintances'),
                ('vi','Strangers'),('vii','Observation')]
            # 1.one.a
            var = 'Know Injured Friends'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.a'})
            record[var] = 'yes'
            for letter,source in sources:
                subvar = '%s from %s' % (var,source)
                if not defined:
                    variables.append({'Name': subvar,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.a.%s' % (letter)})
                if record[var] == 'yes' and source in {'Social Media','Friends'}:
                    record[subvar] = 'yes'
                else:
                    record[subvar] = 'no'
            # 1.one.b
            var = 'Know Evacuated Friends'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b'})
            record[var] = 'yes'
            for letter,source in sources:
                subvar = '%s from %s' % (var,source)
                if not defined:
                    variables.append({'Name': subvar,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b.%s' % (letter)})
                if record[var] == 'yes' and source in {'Social Media','Friends'}:
                    record[subvar] = 'yes'
                else:
                    record[subvar] = 'no'
            # 1.one.b
            var = 'Know Sheltered Friends'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b'})
            record[var] = 'yes'
            for letter,source in sources:
                subvar = '%s from %s' % (var,source)
                if not defined:
                    variables.append({'Name': subvar,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b.%s' % (letter)})
                if record[var] == 'yes' and source in {'Social Media','Friends','Observation'}:
                    record[subvar] = 'yes'
                else:
                    record[subvar] = 'no'
            # 1.one.b
            var = 'Know Injured Acquaintances'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b'})
            record[var] = 'yes'
            for letter,source in sources:
                subvar = '%s from %s' % (var,source)
                if not defined:
                    variables.append({'Name': subvar,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b.%s' % (letter)})
                if record[var] == 'yes' and source in {'Social Media','Acquaintances','Government Broadcast','Observation'}:
                    record[subvar] = 'yes'
                else:
                    record[subvar] = 'no'
            # 1.one.b
            var = 'Know Evacuated Acquaintances'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b'})
            record[var] = 'yes'
            for letter,source in sources:
                subvar = '%s from %s' % (var,source)
                if not defined:
                    variables.append({'Name': subvar,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b.%s' % (letter)})
                if record[var] == 'yes' and source in {'Social Media','Acquaintances','Government Broadcast','Observation'}:
                    record[subvar] = 'yes'
                else:
                    record[subvar] = 'no'
            # 1.one.b
            var = 'Know Sheltered Acquaintances'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b'})
            record[var] = 'yes'
            for letter,source in sources:
                subvar = '%s from %s' % (var,source)
                if not defined:
                    variables.append({'Name': subvar,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b.%s' % (letter)})
                if record[var] == 'yes' and source in {'Social Media','Acquaintances','Government Broadcast','Observation'}:
                    record[subvar] = 'yes'
                else:
                    record[subvar] = 'no'
            # 1.one.g
            var = 'Know Injured Strangers'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.g'})
            record[var] = 'yes'
            for letter,source in sources:
                subvar = '%s from %s' % (var,source)
                if not defined:
                    variables.append({'Name': subvar,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.g.%s' % (letter)})
                if record[var] == 'yes' and source in {'Social Media','Strangers','Government Broadcast','Observation'}:
                    record[subvar] = 'yes'
                else:
                    record[subvar] = 'no'
            # 1.one.b
            var = 'Know Evacuated Strangers'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b'})
            record[var] = 'yes'
            for letter,source in sources:
                subvar = '%s from %s' % (var,source)
                if not defined:
                    variables.append({'Name': subvar,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b.%s' % (letter)})
                if record[var] == 'yes' and source in {'Social Media','Strangers','Government Broadcast','Observation'}:
                    record[subvar] = 'yes'
                else:
                    record[subvar] = 'no'
            # 1.one.b
            var = 'Know Sheltered Strangers'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b'})
            record[var] = 'yes'
            for letter,source in sources:
                subvar = '%s from %s' % (var,source)
                if not defined:
                    variables.append({'Name': subvar,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b.%s' % (letter)})
                if record[var] == 'yes' and source in {'Social Media','Strangers','Government Broadcast','Observation'}:
                    record[subvar] = 'yes'
                else:
                    record[subvar] = 'no'
            # 1.one.j
            var = 'Know Total Dead'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.j'})
            record[var] = 'yes'
            for letter,source in sources:
                subvar = '%s from %s' % (var,source)
                if not defined:
                    variables.append({'Name': subvar,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.j.%s' % (letter)})
                if record[var] == 'yes' and source in {'Social Media','Government Broadcast'}:
                    record[subvar] = 'yes'
                else:
                    record[subvar] = 'no'
            # 1.one.b
            var = 'Know Total Injured'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b'})
            record[var] = 'yes'
            for letter,source in sources:
                subvar = '%s from %s' % (var,source)
                if not defined:
                    variables.append({'Name': subvar,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b.%s' % (letter)})
                if record[var] == 'yes' and source in {'Social Media','Government Broadcast'}:
                    record[subvar] = 'yes'
                else:
                    record[subvar] = 'no'
            # 1.one.b
            var = 'Know Total Evacuated'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b'})
            record[var] = 'yes'
            for letter,source in sources:
                subvar = '%s from %s' % (var,source)
                if not defined:
                    variables.append({'Name': subvar,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b.%s' % (letter)})
                if record[var] == 'yes' and source in {'Social Media','Government Broadcast'}:
                    record[subvar] = 'yes'
                else:
                    record[subvar] = 'no'
            # 1.one.b
            var = 'Know Total Sheltered'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b'})
            record[var] = 'yes'
            for letter,source in sources:
                subvar = '%s from %s' % (var,source)
                if not defined:
                    variables.append({'Name': subvar,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b.%s' % (letter)})
                if record[var] == 'yes' and source in {'Social Media','Government Broadcast'}:
                    record[subvar] = 'yes'
                else:
                    record[subvar] = 'no'
            # 1.one.n
            var = 'Know Regional Dead'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.j'})
            record[var] = 'yes'
            for letter,source in sources:
                subvar = '%s from %s' % (var,source)
                if not defined:
                    variables.append({'Name': subvar,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.j.%s' % (letter)})
                if record[var] == 'yes' and source in {'Social Media','Government Broadcast'}:
                    record[subvar] = 'yes'
                else:
                    record[subvar] = 'no'
            # 1.one.b
            var = 'Know Regional Injured'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b'})
            record[var] = 'yes'
            for letter,source in sources:
                subvar = '%s from %s' % (var,source)
                if not defined:
                    variables.append({'Name': subvar,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b.%s' % (letter)})
                if record[var] == 'yes' and source in {'Social Media','Government Broadcast'}:
                    record[subvar] = 'yes'
                else:
                    record[subvar] = 'no'
            # 1.one.b
            var = 'Know Regional Evacuated'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b'})
            record[var] = 'yes'
            for letter,source in sources:
                subvar = '%s from %s' % (var,source)
                if not defined:
                    variables.append({'Name': subvar,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b.%s' % (letter)})
                if record[var] == 'yes' and source in {'Social Media','Government Broadcast'}:
                    record[subvar] = 'yes'
                else:
                    record[subvar] = 'no'
            # 1.one.b
            var = 'Know Regional Sheltered'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b'})
            record[var] = 'yes'
            for letter,source in sources:
                subvar = '%s from %s' % (var,source)
                if not defined:
                    variables.append({'Name': subvar,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.b.%s' % (letter)})
                if record[var] == 'yes' and source in {'Social Media','Government Broadcast'}:
                    record[subvar] = 'yes'
                else:
                    record[subvar] = 'no'
            # 1.one.r
            var = 'Know Hurricane Prediction'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.r'})
            record[var] = 'yes'
            for letter,source in sources:
                subvar = '%s from %s' % (var,source)
                if not defined:
                    variables.append({'Name': subvar,'Values':'yes,no','DataType': 'Boolean','Notes': '1.one.r.%s' % (letter)})
                if record[var] == 'yes' and source in {'Social Media','Government Broadcast','Friends','Observation'}:
                    record[subvar] = 'yes'
                else:
                    record[subvar] = 'no'
            # 1.two.i
            var = 'Wealth Decrease Hurricane'
            wealth = accessibility.getInitialState(args,name,'resources',world,states,(1,args['span']))
            delta = [float(wealth[t])-float(wealth[t-1]) for t in range(1,len(wealth))]
            if not defined:
                variables.append({'Name': var,'Values':'yes,no,NA','DataType': 'Boolean','Notes': '1.two.i'})
            if min(delta) < 0.:
                record[var] = 'no'
            else:
                record[var] = 'NA'
            # 1.two.ii
            var = 'Wealth Decrease Serious Injury'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no,NA','DataType': 'Boolean','Notes': '1.two.ii'})
            if min(delta) < 0.:
                record[var] = 'no'
            else:
                record[var] = 'NA'
            # 1.two.iii
            var = 'Wealth Decrease Minor Injury'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no,NA','DataType': 'Boolean','Notes': '1.two.iii'})
            if min(delta) < 0.:
                record[var] = 'no'
            else:
                record[var] = 'NA'
            # 1.two.iv
            var = 'Wealth Increase Profiteering'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no,NA','DataType': 'Boolean','Notes': '1.two.ii'})
            if max(delta) > 0.:
                record[var] = 'no'
            else:
                record[var] = 'NA'
            # 1.three.i
            var = 'Alcoholic'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.three.i'})
            record[var] = 'no'
            # 1.three.ii
            var = 'Training'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.three.ii'})
            record[var] = 'no'
            # 1.three.iii
            var = 'Risky Hobbies'
            if not defined:
                variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.three.iii'})
            record[var] = 'no'
            # 2.i
            var = 'Comfort Home'
            if not defined:
                variables.append({'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': '2.i'})
            locations = [loc if isinstance(loc,str) else loc.first() 
                for loc in accessibility.getInitialState(args,name,'location',world,states,(1,args['span']))]
            risk = accessibility.getInitialState(args,name,'risk',world,states,(1,args['span'],name))
            values = [1.-float(risk[t]) for t in range(len(locations)) if locations[t] == record['Residence']]
            record[var] = accessibility.toLikert(sum(values)/len(values),7)-1
            # 2.ii
            var = 'Comfort Evacuated'
            if not defined:
                variables.append({'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': '2.ii'})
            values = [1.-float(risk[t]) for t in range(len(locations)) if locations[t] == 'evacuated']
            if values:
                record[var] = accessibility.toLikert(sum(values)/len(values),7)-1
            else:
                record[var] = 'NA'
            # 2.iii
            var = 'Comfort Sheltered'
            if not defined:
                variables.append({'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': '2.iii'})
            values = [1.-float(risk[t]) for t in range(len(locations)) if locations[t][:7] == 'shelter']
            if values:
                record[var] = accessibility.toLikert(sum(values)/len(values),7)-1
            else:
                record[var] = 'NA'
            if cmd['debug']:
                print(record)
            if not defined:
                if not cmd['debug']:
                    accessibility.writeVarDef(os.path.dirname(__file__),variables)
                defined = True
        if not cmd['debug']:
            accessibility.writeOutput(args,output,[var['Name'] for var in variables],'TA2A-TA1C-0252.tsv',os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
