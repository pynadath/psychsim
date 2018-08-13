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
        assert len(matrix) == 1
        key,row = matrix.items()[0]
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
                        first = True
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

def createDoc():
    doc = Document(geometry_options={'tmargin': '1in', 
                                     'lmargin': '1in',
                                     'textwidth': '6.5in',
                                     'textheight': '9in'})

    doc.preamble.append(Command('usepackage','hyperref'))
    doc.preamble.append(Command('hypersetup','colorlinks'))
    doc.append(NoEscape(r'\tableofcontents'))
    doc.append(NoEscape(r'\clearpage'))
    return doc
    
if __name__ == '__main__':
    world = World(sys.argv[1])

    doc = createDoc()
    addState(doc,world)
    addRelations(doc,world)
    addActions(doc,world)
    

    doc.generate_pdf(sys.argv[2],clean_tex=False)
