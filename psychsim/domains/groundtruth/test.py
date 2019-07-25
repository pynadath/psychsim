from argparse import ArgumentParser
import csv
import logging
import os.path
import pickle
import random
import unittest

from psychsim.pwl.keys import *

from psychsim.domains.groundtruth import accessibility


class TestRunData(unittest.TestCase):
    instances = {90: [0]}
    turn = ['Actor','System','Nature']

    def testDynamics(self):
        args = {}
        for args['instance'],runs in self.instances.items():
            # Grab some parameters for this instance
            config = accessibility.getConfig(args['instance'])
            simPhase = config.getint('Simulation','phase',fallback=1)
            self.assertGreater(simPhase,1,'Not equipped to test Phase %d simulations' % (simPhase))
            base_increase = accessibility.likert[5][config.getint('Disaster','risk_impact')-1]
            base_decrease = accessibility.likert[5][config.getint('Disaster','risk_decay')-1]
            allocation = config.getint('System','system_allocation')
            scale = allocation/accessibility.likert[5][max(allocation,1)]
            aidImpact = 1-pow(1-accessibility.likert[5][config.getint('System','system_impact')-1],scale)
            # Test all runs of this instance
            for args['run'] in runs:
                dirName = accessibility.getDirectory(args)
                # Load in initial simulation
                with open(os.path.join(dirName,'scenario0.pkl'),'rb') as f:
                    world = pickle.load(f)
                actors = {name for name in world.agents if name[:5] == 'Actor'}
                regions = {name for name in world.agents if name[:6] == 'Region'}
                t = 1
                turn = 0
                s0 = None
                # Replay logged states and belief states
                while True:
                    fname = os.path.join(dirName,'state%d%s.pkl' % (t,self.turn[turn]))
                    if not os.path.exists(fname):
                        # Presumably we have gone past the end of the simulation
                        break
                    with open(fname,'rb') as f:
                        s1 = pickle.load(f)
                    print(t,self.turn[turn])
                    # Verify state of turn order
                    for name,state in s1.items():
                        for key in state.keys():
                            if isTurnKey(key):
                                self.assertEqual(len(state[key]),1)
                                other = state2agent(key)
                                if other[:5] == 'Actor':
                                    value = self.turn.index('Actor') - turn - 1
                                else:
                                    value = self.turn.index(other) - turn - 1
                                self.assertAlmostEqual(state[key].first(),value % len(self.turn),8)
                    # Verify true state has no uncertainty
                    self.assertEqual(len(s1['__state__']),1)
                    newValues = {key: world.getFeature(key,s1['__state__']).first() for key in s1['__state__'].keys()}
                    # Hurricane's true state
                    phase = newValues[stateKey('Nature','phase')]
                    for name,state in s1.items():
                        if name != '__state__':
                            # Belief state of an individual actor
                            self.assertEqual(len(state),1)
                            model,belief = next(iter(state.items()))
                            for key in belief.keys():
                                dist = belief[key]
                                if key in {stateKey('Nature','category'),stateKey(world.agents[name].demographics['home'],'risk'),
                                    stateKey(name,'risk')} or key[-11:] == 'shelterRisk':
                                    if phase == 'none' or world.agents[name].distortion == 'none':
                                        self.assertEqual(len(dist),1)
                                    else:
                                        self.assertLess(len(dist),3)
                                else:
                                    self.assertEqual(len(belief[key]),1,'%s has unexpectedly uncertain belief about %s' % (name,key))
                                    self.assertAlmostEqual(belief[key].first(),s1['__state__'][key].first(),
                                        msg='%s has incorrect belief about %s' % (name,key))
                                if key == stateKey('Nature','category'):
                                    if len(dist) > 1:
                                        for value in dist.domain():
                                            if value != newValues[key]:
                                                self.assertEqual(abs(value-newValues[key]),1)
                                    self.assertIn(newValues[key],dist.domain(),'%s has impossible belief for %s' % (name,key))
                    if s0 is None:
                        s0 = s1
                    else:
                        # Verify transition
                        for name,state in s1.items():
                            self.assertEqual(state.keys(),s0[name].keys(),'Set of variables has changed for %s' % (name))
                            if name == '__state__':
                                actions = {state2agent(key): world.getFeature(key,state).first() for key in state.keys() if isActionKey(key)}
                                for key in state.keys():
                                    agent,feature = state2tuple(key)
                                    if feature == 'risk':
                                        if agent[:5] == 'Actor':
                                            # Personal risk
                                            if self.turn[turn] == 'Actor':
                                                if newValues[stateKey(agent,'alive')]:
                                                    if actions[agent]['verb'] == 'takeResources' and config.getint('Actors','antiresources_cost_risk') > 0:
                                                        # //GT: edge 14
                                                        cost = config.getint('Actors','antiresources_cost_risk')
                                                        if phase == 'none':
                                                            self.assertAlmostEqual(oldValues[key]+(1.-oldValues[key])*accessibility.likert[5][3],newValues[key])
                                                        else:
                                                            self.assertAlmostEqual(oldValues[key]+(1.-oldValues[key])*accessibility.likert[5][cost-1],newValues[key])
                                                    elif actions[agent]['verb'] == 'decreaseRisk' and config.getint('Actors','prorisk_cost_risk') > 0:
                                                        # //GT: edge 2
                                                        cost = config.getint('Actors','prorisk_cost_risk')
                                                        if phase == 'none':
                                                            self.assertAlmostEqual(oldValues[key]+(1.-oldValues[key])*accessibility.likert[5][3],newValues[key])
                                                        else:
                                                            self.assertAlmostEqual(oldValues[key]+(1.-oldValues[key])*accessibility.likert[5][cost-1],newValues[key])
                                                    else:
                                                        # Default risk dynamics
                                                        # //GT: edge 27
                                                        if newValues[stateKey(agent,'location')] == 'evacuated':
                                                            # If evacuated, risk drops 90%
                                                            self.assertAlmostEqual(oldValues[key]*0.1,newValues[key])
                                                        elif newValues[stateKey(agent,'location')] == world.agents[agent].demographics['home']:
                                                            # If sheltering at home, risk equals regional risk
                                                            # //GT: edge 55
                                                            self.assertAlmostEqual(newValues[stateKey(world.agents[agent].demographics['home'],'risk')],
                                                                newValues[key],msg='Personal risk (%s) != Regional risk (%s) for %s' % \
                                                                    (state[key],state[stateKey(world.agents[agent].demographics['home'],'risk')],agent))
                                                        elif newValues[stateKey(agent,'location')][:7] == 'shelter':
                                                            # If sheltering at shelter, risk equals shelter risk
                                                            # //GT: edge 58
                                                            self.assertAlmostEqual(newValues[stateKey('Region%s' % (newValues[stateKey(agent,'location')][7:]),
                                                                'shelterRisk')],newValues[key])
                                                        else:
                                                            self.fail('Unknown location of %s: %s' % (agent,newValues[stateKey(agent,'location')]))
                                                else:
                                                    self.assertAlmostEqual(newValues[key],0.)
                                            else:
                                                self.assertAlmostEqual(oldValues[key],newValues[key],
                                                    msg='%s changed on %s turn' % (key,self.turn[turn]))
                                        else:
                                            # Regional risk
                                            if self.turn[turn] == 'Nature':
                                                # //GT: edge 48
                                                # //GT: edge 53
                                                if phase == 'active' and newValues[stateKey('Nature','location')] != 'none':
                                                    distance = world.agents[agent].distance(world.agents[newValues[stateKey('Nature','location')]])
                                                    self.assertAlmostEqual(oldValues[key]+(1.-oldValues[key])*base_increase*\
                                                        float(newValues[stateKey('Nature','category')])/max(distance,1),newValues[key])
                                                else:
                                                    self.assertAlmostEqual(oldValues[key]+base_decrease*(world.agents[agent].risk-oldValues[key]),
                                                        newValues[key])
                                            elif self.turn[turn] == 'Actor':
                                                # //GT: edge 3
                                                count = len([action for action in actions.values() if action['verb'] == 'decreaseRisk' and action['object'] == agent])
                                                if count > 0:
                                                    self.assertGreater(oldValues[key],newValues[key])
                                                else:
                                                    self.assertAlmostEqual(oldValues[key],newValues[key])
                                            else:
                                                # System allocation
                                                # //GT: edge 60
                                                if actions['System']['object'] == agent:
                                                    self.assertAlmostEqual(oldValues[key]+(world.agents[agent].risk-oldValues[key])*aidImpact,newValues[key])
                                                else:
                                                    self.assertAlmostEqual(oldValues[key],newValues[key])
                            else:
                                pass
                    turn += 1
                    if turn == len(self.turn):
                        turn = 0
                        t += 1
                    oldValues = newValues
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
    
