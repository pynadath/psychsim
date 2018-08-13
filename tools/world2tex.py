import inspect
import os
import sys

from pylatex import *
from pylatex.utils import *

from psychsim.pwl.keys import *
from psychsim.action import ActionSet
from psychsim.world import World
from psychsim.graph import DependencyGraph

def key2tex(key):
    if isStateKey(key) and state2agent(key) == WORLD:
        key = state2feature(key)
    elif isBinaryKey(key):
        relation = key2relation(key)
        key = '%s %s %s' % (relation['subject'],relation['relation'],relation['object'])
    elif isRewardKey(key):
        key = '%s\'s Reward' % (state2agent(key))
    elif isRewardKey(makePresent(key)):
        key = makeFuture('%s\'s Reward') % (state2agent(key))
    if isFuture(key):
        return Math(data=[Command('mbox',bold(makePresent(key))),"'"],inline=True)
    else:
        return bold(key)
    
def addGraph(doc,key,fname):
    with doc.create(Figure(position='ht')) as gtGraph:
        gtGraph.add_image('%s' % (os.path.join('images','%s.png' % (fname))))
        gtGraph.add_caption('Ground Truth subgraph for %s' % (key))
    
def addTree(doc,tree,world,indent=0,prefix=None):
    if indent:
        doc.append(HorizontalSpace('%dem' % (indent)))
    if prefix:
        doc.append('%s ' % (prefix))
    if tree.isLeaf():
        matrix = tree.children[None]
        if isinstance(matrix,bool):
            if matrix:
                doc.append(bold('true'))
            else:
                doc.append(bold('false'))
        else:
            assert len(matrix) == 1
            key,row = matrix.items()[0]
            if isRewardKey(makePresent(key)):
                variable = {'domain': float}
            else:
                variable = world.variables[makePresent(key)]
            doc.append(key2tex(key))
            doc.append(Math(data=Command('leftarrow'),inline=True))
            if variable['domain'] is bool:
                assert len(row) == 1
                if CONSTANT in row:
                    if row[CONSTANT] > 0.5:
                        doc.append(bold('true'))
                    else:
                        doc.append(bold('false'))
                else:
                    subkey = row.keys()[0]
                    assert subkey == makePresent(key) in row
                    if row[subkey] < 0.:
                        doc.append(Math(data=Command('lnot'),inline=True))
                    doc.append(key2tex(subkey))
            elif variable['domain'] is set or variable['domain'] is list:
                assert len(row) == 1
                subkey = row.keys()[0]
                if subkey == CONSTANT:
                    doc.append(bold(world.float2value(makePresent(key),row[CONSTANT])))
                else:
                    assert row[subkey] == 1.
                    doc.append(key2tex(subkey))
            else:
                elements = {key: value for key,value in row.items()}
                first = True
                for key in sorted(elements.keys()):
                    value = elements[key]
                    if key != CONSTANT:
                        if first:
                            first = False
                        else:
                            doc.append('+')
                        if value != 1.:
                            doc.append('%d%%' % (100.*value))
                            doc.append(Math(data=Command('cdot'),inline=True))
                        doc.append(key2tex(key))
                if CONSTANT in elements:
                    if elements[CONSTANT] < 0.:
                        if variable['domain'] is int:
                            doc.append(Math(data='-%d' % (abs(elements[CONSTANT])),inline=True))
                        else:
                            doc.append(Math(data='-%4.2f' % (abs(elements[CONSTANT])),inline=True))
                    elif len(elements) == 1:
                        if variable['domain'] is int:
                            doc.append('%d' % (elements[CONSTANT]))
                        else:
                            doc.append('%4.2f' % (elements[CONSTANT]))
                    elif elements[CONSTANT] > 0.:
                        if variable['domain'] is int:
                            doc.append('+%d' % (elements[CONSTANT]))
                        else:
                            doc.append('+%4.2f' % (elements[CONSTANT]))
    elif tree.isProbabilistic():
        if len(tree.children) == 1:
            addTree(doc,tree.children.domain()[0],world,0)
        else:
            for value in tree.children.domain():
                doc.append(LineBreak())
                addTree(doc,value,world,indent+2,'%d%%:' % (tree.children[value]*100))
    else:
        doc.append('IF ')
        assert len(tree.branch.planes) == 1
        done = False
        allInt = True
        for vector,threshold,comparison in tree.branch.planes:
            for key in sorted(vector.keys()):
                variable = world.variables[makePresent(key)]
                if variable['domain'] is bool:
                    assert len(vector) == 1
                    assert abs(vector[key]-1.) < 1e-6,tree.branch
                    assert abs(threshold-.5) < 1e-6,tree.branch
                    if comparison < 0:
                        doc.append(Math(data=Command('lnot'),inline=True))
                    doc.append(key2tex(key))
                    done = True
                elif variable['domain'] is set or variable['domain'] is list:
                    assert comparison == 0
                    doc.append(key2tex(key))
                    if len(vector) == 1:
                        assert abs(vector[key]-1.) < 1e-6,tree.branch
                        doc.append(Math(data='=',inline=True))
                        if isinstance(threshold,list):
                            for value in sorted(threshold):
                                if value != sorted(threshold)[0]:
                                    doc.append(' or ')
                                doc.append(bold(world.float2value(makePresent(key),value)))
                        else:
                            doc.append(bold(world.float2value(makePresent(key),threshold)))
                        done = True
                    else:
                        assert len(vector) == 2
                        if key == sorted(vector.keys())[0]:
                            doc.append(Math(data='=',inline=True))
                        else:
                            done = True
                elif variable['domain'] is float or variable['domain'] is int:
                    allInt &= variable['domain'] is int
                    if key != sorted(vector.keys())[0]:
                        if vector[key] < 0.:
                            doc.append('-')
                        else:
                            doc.append('+')
                    if abs(vector[key]) != 1.:
                        doc.append('%d%%' % (100.*abs(value)))
                        doc.append(Math(data=Command('cdot'),inline=True))
                    doc.append(key2tex(key))
                else:
                    print tree.branch
                    raise RuntimeError,variable['domain']
            if not done:
                if comparison == 0:
                    doc.append(Math(data='=',inline=True))
                elif comparison < 0:
                    doc.append(Math(data='<',inline=True))
                else:
                    doc.append(Math(data='>',inline=True))
                if allInt:
                    doc.append('%d' % (threshold))
                else:
                    doc.append('%4.2f' % (threshold))
        if len(tree.children) == 2 and True in tree.children and False in tree.children:
            values = [True,False]
        else:
            values = sorted(tree.children.keys())
        for value in values:
            child = tree.children[value]
            doc.append(LineBreak())
            if value is True:
                addTree(doc,child,world,indent+2,'THEN')
            elif value is False:
                addTree(doc,child,world,indent+2,'ELSE')
            else:
                addTree(doc,child,world,indent+2,value)
#        doc.append(escape_latex(line.strip()))
#    doc.append(LineBreak())

def addState(doc,world):
    with doc.create(Section('State')):
        for name,variable in sorted(world.variables.items()):
            if isStateKey(name):
                if name in world.dynamics:
                    if state2agent(name) == WORLD:
                        label = state2feature(name)
                    else:
                        label = name
                    with doc.create(Subsection(label)):
                        if variable['domain'] is bool:
                            doc.append('Boolean')
                        elif variable['domain'] is int:
                            doc.append('Integer')
                        elif variable['domain'] is float:
                            doc.append('Real')
                        else:
                            doc.append('String: ')
                            for value in sorted(variable['elements']):
                                if value == sorted(variable['elements'])[0]:
                                    doc.append(bold(value))
                                else:
                                    doc.append(', ')
                                    doc.append(bold(value))
                        addGraph(doc,name,escapeKey(name))
                        for action,tree in sorted(world.dynamics[name].items()):
                            if action is True:
                                heading = 'Default Change in %s' % (label)
                            else:
                                heading = 'Effect of %s on %s' % (str(action),label)
                            with doc.create(Subsubsection(heading)):
                                with doc.create(FlushLeft()):
                                    addTree(doc,tree,world)

def addRelations(doc,world):
    with doc.create(Section('Relations')):
        for name,variable in sorted(world.variables.items()):
            if isBinaryKey(name):
                if name in world.dynamics:
                    relation = key2relation(name)
                    label = '%s %s %s' % (relation['subject'],relation['relation'],relation['object'])
                    with doc.create(Subsection(label)):
                        if variable['domain'] is bool:
                            doc.append('Boolean')
                        elif variable['domain'] is int:
                            doc.append('Integer')
                        elif variable['domain'] is float:
                            doc.append('Real')
                        else:
                            doc.append('String: ')
                            for value in sorted(variable['elements']):
                                if value == sorted(variable['elements'])[0]:
                                    doc.append(bold(value))
                                else:
                                    doc.append(', ')
                                    doc.append(bold(value))
                        addGraph(doc,name,escapeKey(name))
                        for action,tree in sorted(world.dynamics[name].items()):
                            if action is True:
                                heading = 'Default Change in %s' % (label)
                            else:
                                heading = 'Effect of %s on %s' % (str(action),label)
                            with doc.create(Subsubsection(heading)):
                                with doc.create(FlushLeft()):
                                    addTree(doc,tree,world)
    
def addActions(doc,world):
    with doc.create(Section('Actions')):
        for name,agent in world.agents.items():
            for action in sorted(agent.actions):
                try:
                    label = '%s %s %s' % (action['subject'],action['verb'],action['object'])
                except KeyError:
                    label = '%s %s' % (action['subject'],action['verb'])
                with doc.create(Subsection(label)):
                    addGraph(doc,action,str(action))
                    if action in agent.legal:
                        with doc.create(Subsubsection('Applicability Conditions')):
                            with doc.create(FlushLeft()):
                                addTree(doc,agent.legal[action],world)
                    for key,table in sorted(world.dynamics.items()):
                        if state2agent(key) == WORLD:
                            key = state2feature(key)
                        elif isBinaryKey(key):
                            relation = key2relation(key)
                            key = '%s %s %s' % (relation['subject'],relation['relation'],
                                                relation['object'])
                        for other,tree in table.items():
                            if other == action:
                                with doc.create(Subsubsection('Effect on %s of %s' % (key,label))):
                                    with doc.create(FlushLeft()):
                                        addTree(doc,tree,world)
                                break

def addReward(doc,world):
    with doc.create(Section('Expected Reward')):
        for name,agent in world.agents.items():
            if os.access(os.path.join('images','%s.png' % (name)),os.R_OK) and len(agent.actions) > 1:
                with doc.create(Subsection('%s\'s Reward' % (name))):
                    addGraph(doc,name,name)
                    with doc.create(FlushLeft()):
                        addTree(doc,agent.getReward('%s0' % (name)),world)
                        
def background(doc):
    filename = inspect.getframeinfo(inspect.currentframe()).filename
    path = os.path.dirname(os.path.abspath(filename))
    with doc.create(Section('Background')):
        doc.append('We use influence diagrams as the underlying graph structure for our ground truth. Here is a simple influence diagram for a simulation of two actors, showing the three types of nodes and some possible links (always directed) among them:')
        with doc.create(Figure(position='ht')) as gtGraph:
            gtGraph.add_image(os.path.join(path,'simple.png'))
            gtGraph.add_caption('Simple influence diagram')
        with doc.create(Itemize()) as itemize:
            itemize.add_item('Rectangular nodes are possible actions for a particular agent (``Actor 1\'\', indicated by color) representing a potential behavior. They are labeled with a verb (``action\'\') and an optional object of the verb (``Actor2\'\'). An action node has a binary value, indicating whether or not the action was chosen.')
            itemize.add_item('Oval nodes are state variables. Their value is potentially a probability distribution over a domain of possible values. All true state variables will be certain (i.e., 100\% probability for a single value), but agents\' perceptions of the true state will often be uncertain.')
            itemize.add_item('Hexagonal nodes are utility or reward nodes. They represent an expected value computation by the agent (``Actor1\'\'). The node\'s value is a table with each row corresponding to a possible action choice and its expected utility.')
            itemize.add_item('Links from action nodes to state nodes specify an effect that the action has on the value of the state.')
            itemize.add_item('Links from one state node to another specify an influence that the value of the first state node has on the effect of at least one action on the second state node.')
            itemize.add_item('Links from a state node to an agent\'s utility node specify that the state node is an input to the expected value calculation performed by that agent. There is a real-valued weight from $(0,1\]$ on each link specifying the priority of that variable\'s influence on that agent\'s reward calculation (higher values mean higher priority).')
            itemize.add_item('Links from utility nodes to action nodes indicate that the expected value calculation then determines whether or not that action is chosen. In the simulations described here, we use a strict maximization, so that the action choice is deterministic (i.e., the action with the highest expected value is performed, with ties broken by a pre-determined fixed order).')
            itemize.add_item('Therefore, in the above simple ground truth, whether or not ``Actor1\'\' chooses to do ``action\'\' to ``Actor2\'\' influences the subsequent value of the variable ``state\'\' (link from rectangle to oval). The subsequent value of ``state\'\' also depends on its prior value (link from oval to itself). ``Actor1\'\'\'s expected value of doing ``action\'\' to ``Actor2\'\' is a function of the value of ``state\'\' (link from oval to hexagon), and this expected value influences whether or not ``Actor1\'\' chooses to do so (link from hexagon to rectangle).')
        doc.append('Any real values (e.g., initial values of variables, conditional probability table values, reward weights) will be drawn from either a set {0, 0.5, 1} or {0, 0.2, 0.4, 0.6, 0.8, 1}, depending on the appropriate granularity needed.')
    
def createDoc():
    doc = Document(geometry_options={'tmargin': '1in', 
                                     'lmargin': '1in',
                                     'textwidth': '6.5in',
                                     'textheight': '9in'})

    doc.preamble.append(Command('usepackage','hyperref'))
    doc.preamble.append(Command('hypersetup','colorlinks'))
    doc.append(NoEscape(r'\tableofcontents'))
    doc.append(NoEscape(r'\clearpage'))
    background(doc)
    return doc
    
if __name__ == '__main__':
    world = World(sys.argv[1])

    doc = createDoc()
    addState(doc,world)
    addRelations(doc,world)
    addActions(doc,world)
    addReward(doc,world)

    doc.generate_pdf(sys.argv[2],clean_tex=False)
