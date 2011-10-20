import tkMessageBox
from Tkinter import *
import Pmw
from teamwork.widgets.bigwidgets import *
from teamwork.widgets.fsa import *
from teamwork.math.matrices import epsilon

class MAIDFrame(Pmw.MegaWidget):
    """Window that displays a MultiAgent Influence Diagram view of a L{scenario<teamwork.multiagent.PsychAgents.PsychAgents>}
    """
    colors = ['#ffff00','#ff00ff','#00ffff','#ffffff']
    def __init__(self,frame,**kw):
        optiondefs = (
            ('entities',   {}, self.drawMAID),
            )
	self.defineoptions(kw, optiondefs)
        Pmw.MegaWidget.__init__(self,frame)
        self.frame = CanvasFrame(self.component('hull'),
                                 width=self.winfo_screenwidth(),
                                 height=self.winfo_screenheight())
        self.frame.pack(expand = 'yes', fill = 'both', side='top')
        self.dynamics = {}
	self.initialiseoptions()

    def drawMAID(self):
        self.dynamics.clear()
        canvas = self.frame.canvas()
        states = {}
        actions = {}
        actionTypes = {}
        utilities = {}
        nodes = []
        color = 0
        for name,agent in self['entities'].items():
            # Draw state nodes
            for key in agent.state.domainKeys():
                if isinstance(key,StateKey) and key['entity'] == name:
                    label = TextWidget(canvas,str(key))
                    states[key] = OvalWidget(canvas,label,draggable=True,
                                             fill=self.colors[color])
                    nodes.append(states[key])
            # Draw action nodes
            for option in agent.actions.getOptions():
                label = str(option)
                actions[label] = BoxWidget(canvas,TextWidget(canvas,label),
                                           draggable=True,
                                           fill=self.colors[color])
                nodes.append(actions[label])
                # Store action nodes also indexed by type
                for action in option:
                    if actionTypes.has_key(action['type']):
                        if not option in actionTypes[action['type']]:
                            actionTypes[action['type']].append(actions[label])
                    else:
                        actionTypes[action['type']] = [actions[label]]
            # Draw utility nodes
            utilities[name] = PolygonWidget(canvas,TextWidget(canvas,name),
                                            draggable=True,
                                            fill=self.colors[color])
            nodes.append(utilities[name])
            color = (color+1)%(len(self.colors))
        edges = {}
        for name,agent in self['entities'].items():
            # Draw dynamics links among state and action nodes
            for feature,table in agent.dynamics.items():
                key = StateKey({'entity':agent.name,'feature':feature})
                for action,dynFun in table.items():
                    if isinstance(action,str):
                        continue
                    # The following assumes serial actions!
                    label = str([action])
                    origins = []
                    tree = dynFun.getTree()
                    # Find all the keys that the tree branches on
                    for plane in tree.branches().values():
                        for other in plane.weights.keys():
                            if isinstance(other,StateKey) and \
                                   abs(plane.weights[other]) > epsilon and \
                                   not states[other] in origins:
                                origins.append(states[other])
                    # Find all the keys in the leaf matrices
                    for leaf in tree.leaves():
                        vector = leaf[key]
                        for other in vector.keys():
                            if other == key:
                                nochange = 1.
                            else:
                                nochange = 0.
                            if isinstance(other,StateKey) and \
                                   abs(vector[other]-nochange) > epsilon and \
                                   not states[other] in origins:
                                origins.append(states[other])
                    if len(origins) > 0:
                        origins.append(actions[label])
                    # Draw the relevant links that we have found
                    for node in origins:
                        edge = GraphEdgeWidget(canvas,0,0,0,0,
                                               TextWidget(canvas,' '))
                        index = str(node)+str(key)
                        if not edges.has_key(index):
                            edges[index] = ((node,states[key],edge))
                            try:
                                self.dynamics[label].append(edge)
                            except KeyError:
                                self.dynamics[label] = [edge]
            # Draw goal links to utility nodes
            for goal in agent.getGoals():
                if goal.type == 'state':
                    # Link from state node to utility node
                    if len(goal.entity) == 1:
                        key = StateKey({'entity':goal.entity[0],
                                        'feature':goal.key})
                        origins = [states[key]]
                    else:
                        raise NotImplementedError,'Unable to plot belief goals'
                elif goal.type == 'action':
                    # Link from action node to utility node
                    try:
                        origins = actionTypes[goal.key]
                    except KeyError:
                        origins = []
                else:
                    raise NotImplementedError,'Unable to graph goals of type %s' % (goal.type)
                # Draw the relevant links that we have found
                for node in origins:
                    weight = agent.getGoalWeight(goal)
                    label = TextWidget(canvas,' ')
                    edge = GraphEdgeWidget(canvas,0,0,0,0,label)
                    if goal.direction == 'max':
                        color = '#00ff00'
                    else:
                        color = '#ff0000'
                    edge['color'] = color
                    edge['width'] = weight*10.
                    index = str(node)+str(name)
                    if not edges.has_key(index):
                        edges[index] = ((node,utilities[name],edge))
        graph = GraphWidget(canvas,nodes,edges.values(),draggable=True)
        for option,node in actions.items():
            node.bind_click(self.viewDynamics)
        self.frame.add_widget(graph)

    def viewDynamics(self,event,widget):
        label = widget.child().text()
        for option,edges in self.dynamics.items():
            if option == label:
                for edge in edges:
                    edge.show()
            else:
                for edge in edges:
                    edge.hide()
        
