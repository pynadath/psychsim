import csv
import logging
import os.path
import random

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.action import *

nodes = [stateKey('Actor','Expected Reward'),binaryKey('Actor','Actor','friendOf'),binaryKey('Actor','Actor','neighbor'),
    Action({'subject': 'Actor','verb': 'decreaseRisk','object': 'Region'}),Action({'subject': 'Actor','verb': 'evacuate'}),
    Action({'subject': 'Actor','verb': 'moveTo','object': 'Region'}),Action({'subject': 'Actor','verb': 'moveTo','object': 'shelter'}),
    Action({'subject': 'Actor','verb': 'stayInLocation'}),Action({'subject': 'Actor','verb': 'takeResources','object': 'Region'}),
    beliefKey('Actor',stateKey('Nature','category')),#beliefKey('Actor',stateKey('Nature','days')),
    beliefKey('Actor',stateKey('Region','risk')),
    stateKey('Actor','childrenHealth'),stateKey('Actor','employed'),stateKey('Actor','grievance'),stateKey('Actor','health'),
    stateKey('Actor','horizon'),stateKey('Actor','location'),stateKey('Actor','perceivedCategory'),#stateKey('Actor','perceivedDays'),
    stateKey('Actor','pet'),stateKey('Actor','region'),stateKey('Actor','resources'),stateKey('Actor','risk'),
    stateKey('Nature','category'),stateKey('Nature','days'),stateKey('Nature','location'),stateKey('Nature','phase'),stateKey('Region','risk'),
    stateKey('Region','shelterPets'),stateKey('Region','shelterRisk'),Action({'actor': 'System','verb': 'allocate','object': 'Region'}),
    ]

fields = ['Timestep','VariableName','EntityIdx','Value','Notes']

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename=os.path.join(os.path.dirname(__file__),'total.log'))
    for instance in range(1,15):
        logging.info('Instance %d' % (instance))
        mismatch = 0
        args = accessibility.instances[instance-1]
        config = accessibility.getConfig(args['instance'])
        data = accessibility.loadRunData(args['instance'],args['run'],args['span'],subs=['Input'] if instance > 2 else [None])
        print('Unpickling',instance)
        world = accessibility.loadPickle(args['instance'],args['run'],args['span']+(1 if instance == 2 or instance > 8 else 0),
            sub='Input' if instance > 2 else None)
        print('done')
        demos = accessibility.readDemographics(data,last=args['span'])
        network = accessibility.readNetwork(args['instance'],args['run'],'Input' if instance > 2 else None)
        for name in world.agents:
            if name[:5] == 'Actor':
                accessibility.backwardDemographics(world.agents[name],demos)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run'],'Input' if instance > 2 else None) 
            if h['End'] < args['span']]
        output = []
        actors = {name for name in demos if name[:5] == 'Actor'}
#        for name in actors:
#            print('Compiling %s value function' % (name))
#            world.agents[name].compileV()
        regions = [name for name in data if name[:6] == 'Region']
        hurricane = None
        for t in range(1,args['span']+1):
            if hurricane is None:
                hurricane = accessibility.findHurricane(t,hurricanes)
                if hurricane is None:
                    hurricane = 0
                else:
                    hurricane = hurricane[['Hurricane']] - 1
            if t not in data['Actor0001'][stateKey('Actor0001','alive')]:
                # Offseason
                continue
            try:
                print(t,hurricanes[hurricane])
            except IndexError:
                print(t)
            # Process hurricane state
            if hurricane == len(hurricanes):
                world.setState('Nature','days',t-hurricanes[hurricane-1]['End'])
            elif t < hurricanes[hurricane]['Start']:
                world.setState('Nature','phase','none')
                world.setState('Nature','category',0)
                world.setState('Nature','location','none')
                if hurricane == 0:
                    world.setState('Nature','days',t-1)
                else:
                    world.setState('Nature','days',t-hurricanes[hurricane-1]['End'])
            elif t < hurricanes[hurricane]['Landfall']:
                world.setState('Nature','phase','approaching')
                world.setState('Nature','category',hurricanes[hurricane]['Actual Category'][t-hurricanes[hurricane]['Start']])
                world.setState('Nature','location',hurricanes[hurricane]['Actual Location'][t-hurricanes[hurricane]['Start']])
                world.setState('Nature','days',t-hurricanes[hurricane]['Start'])
            elif t < hurricanes[hurricane]['End']:
                world.setState('Nature','phase','active')
                world.setState('Nature','category',hurricanes[hurricane]['Actual Category'][t-hurricanes[hurricane]['Start']])
                world.setState('Nature','location',hurricanes[hurricane]['Actual Location'][t-hurricanes[hurricane]['Start']])
                world.setState('Nature','days',t-hurricanes[hurricane]['Landfall'])
            else:
                world.setState('Nature','phase','active')
                world.setState('Nature','category',hurricanes[hurricane]['Actual Category'][t-hurricanes[hurricane]['Start']])
                world.setState('Nature','location','none')
                world.setState('Nature','days',t-hurricanes[hurricane]['Landfall'])
                hurricane += 1
            for name in actors:
                world.setState(name,'location',data[name][stateKey(name,'location')][t])
                world.setState(name,'alive',data[name][stateKey(name,'alive')][t])
            for node in nodes:
                if isinstance(node,Action):
                    if 'subject' in node and node['subject'] == 'Actor':
                        for name in actors:
                            if t in data[name][actionKey(name)] and data[name][stateKey(name,'alive')][t]:
                                actual = data[name][actionKey(name)][t]
                                if node['verb'] == actual['verb'] and ('object' not in actual or actual['object'] == node['object']):
                                    output.append({'Timestep': t,'VariableName': str(node),'EntityIdx': name,'Value': 'yes' })
                                else:
                                    output.append({'Timestep': t,'VariableName': str(node),'EntityIdx': name,'Value': 'no' })
                    else:
                        assert node['actor'] == 'System'
                        if t in data['System'][actionKey('System')]:
                            output.append({'Timestep': t,'VariableName': str(node),'EntityIdx': 'System',
                                'Value': data['System'][actionKey('System')][t]['object']})
                elif isBeliefKey(node):
                    key = belief2key(node)
                    for name in actors:
                        value = data[name]['__beliefs__'][key][t]
                        if isinstance(value,Distribution):
                            output.append({'Timestep': t,'VariableName': 'ActorBeliefOf%s' % (accessibility.shorten(key)),'EntityIdx': name,
                                'Value': ','.join(['%d%%: %s' % (int(round(100*value[el])),el) for el in value.domain()])})
                        else:
                            output.append({'Timestep': t,'VariableName': 'ActorBeliefOf%s' % (accessibility.shorten(key)),'EntityIdx': name,'Value': value})
                elif isBinaryKey(node):
                    if t == 1:
                        relation = key2relation(node)['relation']
                        for name1 in network[relation]:
                            for name2 in network[relation][name1]:
                                output.append({'Timestep': t,'VariableName': binaryKey(name1,name2,relation),'Value': 'yes'})
                else:
                    assert isStateKey(node),'Non-state key: %s' % (node)
                    agent,feature = state2tuple(node)
                    if feature == 'Expected Reward':
                        for name in sorted(actors):
                            if t in data[name][actionKey(name)]:
                                belief = accessibility.setBelief(name,world,data,t)
                                model = world.getModel(name)
                                assert len(model) == 1,'Ambiguous model: %s' % (model)
                                model = next(iter(model.domain()))
                                actual = str(data[name][actionKey(name)][t])
                                actions = world.agents[name].getActions(world.state)
                                V = {str(action): world.agents[name].value(belief,action,model,keySet=belief.keys(),updateBeliefs=False) \
                                    for action in actions}
                                values = sorted([(entry['__ER__'][0],act) for act,entry in V.items()],reverse=True)
                                order = [entry[1] for entry in values]
                                if actual not in V:
                                    print(t,name)
                                    for key,tree in world.agents[name].legal.items():
                                        if str(key) == actual:
                                            print(tree)
                                            print(tree[world.state])
                                            print(world.state[stateKey('Nature','phase')])
                                            print(world.state[stateKey(name,'location')])
                                            print(world.state[stateKey(name,'alive')])
                                            print(world.getState('Nature','phase'))
                                if V[actual]['__ER__'][0] != max(values)[0]:
                                    logging.warning('%d %s Performed: %s' % (t,name,data[name][actionKey(name)][t]))
                                    logging.warning(str(V))
                                    mismatch += 1
                                    order.remove(actual)
                                    order.insert(0,actual)
                                output.append({'Timestep': t,'VariableName': node,'EntityIdx': name,
                                    'Value': ','.join(order),'Notes': 'Descending order'})
                    elif feature == 'perceivedDays':
                        # This should really be the same as the true days
                        pass
                    elif agent == 'Actor':
                        for name in actors:
                            if feature == 'childrenHealth' and demos[name]['Children'] == 0:
                                continue
                            elif feature == 'horizon':
                                if t > 1:
                                    continue
                                value = data[WORLD][stateKey(WORLD,'%sHorizon' % (name))][t]
                            elif feature == 'perceivedCategory':
                                if t == 1:
                                    value = 0
                                else:
                                    newBelief = data[name]['__beliefs__'][stateKey('Nature','category')][t]
                                    if isinstance(newBelief,int):
                                        value = newBelief
                                    else:
                                        oldBelief = data[name]['__beliefs__'][stateKey('Nature','category')][t-1]
                                        if isinstance(oldBelief,int):
                                            value = newBelief.max()
                                        else:
                                            value = oldBelief.max()+(newBelief-oldBelief).max()
                            elif stateKey(name,feature) not in data[name]:
                                raise NameError('Missing key: %s' % (stateKey(name,feature)))
                            else:
                                try:
                                    value = data[name][stateKey(name,feature)][t]
                                except KeyError:
                                    if feature in {'employed','pet','region'}:
                                        value = data[name][stateKey(name,feature)][1]
                                    else:
                                        raise ValueError('Time %d missing from %s' % (t,stateKey(name,feature)))
                            assert isinstance(value,float) or isinstance(value,int) or isinstance(value,str),'Illegal value type of: %s' % (value)
                            output.append({'Timestep': t,'VariableName': accessibility.shorten(node),'EntityIdx': name,'Value': value})
                    elif agent == 'Region':
                        for name in regions:
                            key = stateKey(name,feature)
                            if key in data[name] and t in data[name][key]:
                                output.append({'Timestep': t,'VariableName': node,'EntityIdx': name,'Value': data[name][key][t]})
                    elif agent == 'Nature':
                        output.append({'Timestep': t,'VariableName': node,'EntityIdx': agent,'Value': world.getFeature(node).first()})
                    else:
                        raise ValueError('Unable to process node %s' % (node))
            actors -= {name for name in actors if not data[name][stateKey(name,'alive')][t]}
        accessibility.writeOutput(args,output,fields,'CompleteData.tsv')
        logging.warning('%d/%d mismatches' % (mismatch,args['span']*160))
