from argparse import ArgumentParser
import sys

from psychsim.world import World

def printHelp():
    keys = commands.keys()
    keys.sort()
    for cmd in keys:
        print '%s\t%s' % (cmd,commands[cmd]['help'])

def loadScenario(filename):
    global world
    world = World(filename)

def step(actions=None):
    outcome = world.step(actions)
    world.explain(outcome,args['debug'])
    world.state.select()

def act(label):
    assert len(world.state) == 1,'Unable to work with uncertain state'
    vector = world.state.domain()[0]
    assert len(world.next(vector)) == 1,'Forcing actions allowed only in serial execution'
    agent = world.agents[world.next(vector)[0]]
    for action in agent.getActions(vector):
        if str(action) == label:
            step({agent.name: action})
            break
    else:
        raise AssertionError,'%s has no legal action: %s' % (agent.name,label)

def choose():
    assert len(world.state) == 1,'Unable to work with uncertain state'
    vector = world.state.domain()[0]
    assert len(world.next(vector)) == 1,'Choosing actions allowed only in serial execution'
    choice = {}
    for name in world.next(vector):
        agent = world.agents[name]
        actions = list(agent.getActions(vector))
        actions.sort()
        for index in range(len(actions)):
            print '%d) %s' % (index,actions[index])
        print 'Choose action: ',
        choice[name] = actions[int(stream.readline())]
        print
    step(choice)

if __name__ == '__main__':
    parser = ArgumentParser()
    # Optional argument that sets the filename for a command script
    parser.add_argument('-i','--input',action='store',
                      dest='input',default=None,
                      help='input file [default: %(default)s]')
    # Optional argument that sets the filename for the scenario
    parser.add_argument('-s','--scenario',action='store',
                      dest='scenario',default=None,
                      help='scenario file [default: %(default)s]')
    # Optional argument that sets the level of explanations when running the simulation
    parser.add_argument('-d',action='store',
                        dest='debug',type=int,default=1,
                        help='level of explanation detail [default: %(default)s]')
    args = vars(parser.parse_args())
    if args['input'] is None:
        stream = sys.stdin
    else:
        stream = open(args['input'],'r')
    if args['scenario'] is None:
        world = None
    else:
        loadScenario(args['scenario'])

    commands = {'quit': {'function': sys.exit,
                         'args': [],'state': False,'world': False,
                         'help': 'Exit the shell'},
                'help': {'function': printHelp,
                         'args': [],'state': False,'world': False,
                         'help': 'Print this message'},
                'load': {'function': loadScenario,
                         'args': ['filename'],'state': True,'world': False,
                         'help': 'Load a PsychSim Scenario'},
                'step': {'function': step,
                         'args': [],'state': True,'world': True,
                         'help': 'Perform a simulation step'},
                'choose': {'function': choose,
                         'args': [],'state': True,'world': True,
                         'help': 'Make an interactive choice for the agent'},
                'act': {'function': act,
                         'args': ['action'],'state': True,'world': True,
                         'help': 'Force agent to take specified action'},
                }
    while True:
        prompt = '> '
        if world:
            prompt = '%s%s' % (','.join(world.next()),prompt)
        print prompt,
        line = stream.readline().strip()
        print
        elements = line.split()
        if elements:
            cmd = elements[0]
            if commands.has_key(cmd):
                if len(commands[cmd]['args']) == 1:
                    params = (' '.join(elements[1:]),)
                else:
                    params = elements[1:]
                if len(params) != len(commands[cmd]['args']):
                    print 'Usage: %s %s' % (cmd,' '.join(commands[cmd]['args']))
                elif commands[cmd]['world'] and world is None:
                    print 'Must load scenario before performing command "%s"' % (cmd)
                else:
                    try:
                        apply(commands[cmd]['function'],params)
                        if commands[cmd]['state']:
                            world.printState()
                    except AssertionError,msg:
                        print 'Error: %s' % (msg)
            else:
                print 'Unknown command: "%s"' % (cmd)
                print elements
        print
