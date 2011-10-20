if __name__ == '__main__':
    from optparse import OptionParser
    from teamwork.policy.pwlTable import PWLTable
    from teamwork.multiagent.PsychAgents import loadScenario
    import os
    import time

    parser = OptionParser()
    parser.add_option('--solver',action='store',type='string',
                      dest='solver',default='~/pomdp-solve-5.3',
                      help='POMDP solver directory [default: %default]')
    parser.add_option('--scenario',action='store',type='string',
                      dest='scenario',default='tiger.scn',
                      help='PsychSim scenario filename [default: %default]')
    parser.add_option('-t','--max',action='store',
                      dest='max',type='int',default=1,
                      help='maximum horizon for POMDP solution [default: %default]')
    parser.add_option('-d','--debug',action='store_true',
                      dest='debug',default=False,
                      help='flag for debug mode of simulation [default: %default]')
    (options, args) = parser.parse_args()

    scenario = loadScenario(options.scenario)
    scenario.nullPolicy()
    for agent in scenario.activeMembers():
        agent.entities.nullPolicy()
        del agent.policy.tables[0][0]
    # Generate value functions for each agent over different horizons
    print 'Horizon,Time,ER'
    for horizon in range(options.max+1):
        delta = 0.
        for agent in scenario.activeMembers():
            file = agent.name.replace(' ','').lower()
            # Solve POMDP
            cmd = '%s/src/pomdp-solve -stdout /tmp/pomdp.log' % \
                (options.solver)
            args = '-pomdp %s.pomdp -horizon %d -o %s-%02d' % \
                (file,horizon+1,file,horizon+1)
            start = time.time()
            os.system('%s %s' % (cmd,args))
            delta += time.time()-start
            # Load value function
            table = PWLTable()
            table.load(agent,'%s-%02d.alpha' % (file,horizon+1))
            agent.policy.tables[0].append(table)
        # Run simulations to find expected reward
        reward = scenario.simulate(options.max,options.debug)
        print '%d,%f,%f' % (horizon,delta,reward)
    scenario.save(options.scenario)

