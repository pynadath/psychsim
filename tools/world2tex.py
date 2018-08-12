import os
import sys

from pylatex import *
from pylatex.utils import *

from psychsim.pwl.keys import *
from psychsim.action import ActionSet
from psychsim.world import World
from psychsim.graph import DependencyGraph

def addGraph(doc,key,fname):
    with doc.create(Figure(position='ht')) as gtGraph:
        gtGraph.add_image('%s' % (os.path.join('images','%s.png' % (fname))))
        gtGraph.add_caption('Ground Truth subgraph for %s' % (key))
    
def addTree(doc,tree,indent=0,prefix=None):
    if indent:
        doc.append(HorizontalSpace('%dem' % (indent)))
    if prefix:
        doc.append('%s: ' % (prefix))
    if tree.isLeaf():
        matrix = tree.children[None]
        assert len(matrix) == 1
        key,row = matrix.items()[0]
        doc.append(makePresent(key))
    elif tree.isProbabilistic():
        for value in tree.children.domain():
            doc.append(LineBreak())
            addTree(doc,value,indent+2,'%d' % (tree.children[value]*100))
    else:
        doc.append('IF %s' % (str(tree.branch)))
        for value,child in tree.children.items():
            doc.append(LineBreak())
            addTree(doc,child,indent+2,value)
#        doc.append(escape_latex(line.strip()))
    doc.append(LineBreak())
    
if __name__ == '__main__':
    world = World(sys.argv[1])

    graph = DependencyGraph(world)
    graph.computeGraph()

    doc = Document(geometry_options={'tmargin': '1in', 
                                     'lmargin': '1in',
                                     'textwidth': '6.5in',
                                     'textheight': '9in'})

    doc.preamble.append(Command('usepackage','hyperref'))
    doc.preamble.append(Command('hypersetup','colorlinks'))
    doc.append(NoEscape(r'\tableofcontents'))
    doc.append(NoEscape(r'\clearpage'))    
    with doc.create(Section('State')):
        for name,variable in sorted(world.variables.items()):
            if isStateKey(name):
                if name in world.dynamics:
                    with doc.create(Subsection(name)):
                        addGraph(doc,name,escapeKey(name))
                        for action,tree in sorted(world.dynamics[name].items()):
                            if state2agent(name) == WORLD:
                                name = state2feature(name)
                            if action is True:
                                heading = 'Default Change in %s' % (name)
                            else:
                                heading = 'Effect of %s on %s' % (str(action),name)
                            with doc.create(Subsubsection(heading)):
                                with doc.create(FlushLeft()):
                                    addTree(doc,tree)
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
                        for other,tree in table.items():
                            if other == action:
                                with doc.create(Subsubsection('Effect on %s of %s' % (key,label))):
                                    with doc.create(FlushLeft()):
                                        addTree(doc,tree)
                                break
                            

    doc.generate_pdf(sys.argv[2],clean_tex=False)
