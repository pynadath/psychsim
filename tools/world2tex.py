import os
import sys

from pylatex import *
from pylatex.utils import *

from psychsim.pwl.keys import *
from psychsim.action import ActionSet
from psychsim.world import World
from psychsim.graph import DependencyGraph

def addGraph(doc,key,fname):
    with doc.create(Figure()) as gtGraph:
        gtGraph.add_image('%s' % (os.path.join('images','%s.png' % (fname))))
        gtGraph.add_caption('Ground Truth subgraph for %s' % (key))
    
def addTree(doc,tree,indent=0):
    with doc.create(FlushLeft()):
        if indent:
            doc.append(HorizontalSpace('%dem' % (indent)))
        if tree.isLeaf():
            matrix = tree.children[None]
            assert len(matrix) == 1
            key,row = matrix.items()[0]
            doc.append(key)
            doc.appendMath('\leftarrow')#'%s $\leftarrow$ %s' % (key,row))
        elif tree.isProbabilistic():
            doc.append('DISTRIBUTION')
        else:
            doc.append('BRANCH')
#        doc.append(escape_latex(line.strip()))
        doc.append(LineBreak())
    
if __name__ == '__main__':
    world = World(sys.argv[1])

    doc = Document(geometry_options={'tmargin': '1in', 
                                     'lmargin': '1in',
                                     'textwidth': '6.5in',
                                     'textheight': '9in'})

    graph = DependencyGraph(world)
    graph.computeGraph()

    with doc.create(Section('State')):
        for name,variable in sorted(world.variables.items()):
            if isStateKey(name):
                if name in world.dynamics:
                    with doc.create(Subsection(name)):
                        addGraph(doc,name,escapeKey(name))
                        for action,tree in sorted(world.dynamics[name].items()):
                            if action is True:
                                action = 'Default'
                            assert action != None
                            with doc.create(Subsubsection(str(action))):
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
                        for other,tree in table.items():
                            if other == action:
                                with doc.create(Subsubsection(key)):
                                    addTree(doc,tree)
                                break
                            

    doc.generate_pdf('groundTruth')
