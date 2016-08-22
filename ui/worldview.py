import math
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import graph
import diagram
from world import *

def getLayout(graph):
    layout = {'state pre': [set()],
              'state post': [set()],
              'action': set(),
              'utility': set(),
              }
    for target in ['state pre','state post']:
        remaining = []
        for key,table in graph.items():
            if table['type'] == target:
                parents = set([parent for parent in table['parents'] \
                                   if graph[parent]['type'] == target])
                if len(parents) == 0:
                    table['index'] = 0
                    layout[target][0].add(key)
                else:
                    remaining.append((key,parents))
        while len(remaining) > 0:
            layout[target].append(set())
            temp = []
            for key,parents in remaining:
                parents -= layout[target][-2]
                if parents:
                    temp.append((key,parents))
                else:
                    layout[target][-1].add(key)
            remaining = temp
    for target in ['action','utility']:
        for key,table in graph.items():
            if table['type'] == target:
                layout[target].add(key)

    return layout
    
class WorldView(QGraphicsScene):
    rowHeight = 100
    colWidth = 150
    arrowAngle = math.radians(15.)
    arrowLength = 15.

    def __init__(self,parent = None):
        super(WorldView,self).__init__(parent)
        self.nodes = {'state pre': {},
                      'state post': {},
                      'action': {},
                      'utility': {}}
        self.edgesOut = {}
        self.edgesIn = {}
        self.agentColors = {}
        self.world = None
        self.graph = None
        self.dirty = False

    def displayWorld(self,world):
        for table in self.nodes.values():
            table.clear()
        self.edgesOut.clear()
        self.edgesIn.clear()
        if not isinstance(world.diagram,diagram.Diagram):
            if world.diagram is None:
                # Creating a diagram for the first time
                self.setDirty()
            world.diagram = diagram.Diagram(world.diagram)
        self.world = world

        self.graph = graph.DependencyGraph(self.world)
        self.graph.computeGraph()
        layout = getLayout(self.graph)

        # Lay out the pre variable nodes
        x = 0
        even = True
        for layer in layout['state pre']:
            y = 0
            for key in sorted(layer,lambda k0,k1: cmp((self.graph[k0]['agent'],k0),
                                                      (self.graph[k1]['agent'],k1))):
                if not self.world.variables[key].has_key('xpre'):
                    if y >= 10*self.rowHeight:
                        even = not even
                        if even:
                            y = 0
                        else:
                            y = 50
                        x += int(0.75*self.colWidth)
                    self.world.variables[key]['xpre'] = x
                    self.world.variables[key]['ypre'] = y
                    # Move on to next Y
                    y += self.rowHeight
                if self.graph[key]['agent']:
                    agent = self.world.agents[self.graph[key]['agent']]
                    if isBinaryKey(key):
                        node = VariableNode(agent,key[len(agent.name)+1:],key,
                                            self.world.variables[key]['xpre'],self.world.variables[key]['ypre'],
                                            100,50,scene=self)
                    else:
                        node = VariableNode(agent,key[len(agent.name)+3:],key,
                                            self.world.variables[key]['xpre'],self.world.variables[key]['ypre'],
                                            100,50,scene=self)
                else:
                    node = VariableNode(None,key,key,
                                        self.world.variables[key]['xpre'],self.world.variables[key]['ypre'],
                                        100,50,scene=self)
                self.nodes[self.graph[key]['type']][key] = node
            x += self.colWidth
        assert len(self.nodes['state pre']) == sum(map(len,self.world.locals.values()))+\
            sum(map(len,self.world.relations.values()))
        # Lay out the action nodes
        y = 0
        for action in sorted(layout['action']):
            if self.world.diagram.getX(action) is None:
                self.setDirty()
                self.world.diagram.x[action] = x
                self.world.diagram.y[action] = y
                # Move on to next Y
                y += self.rowHeight
                if y >= 10*self.rowHeight:
                    y = 0
                    x += self.colWidth
            node = ActionNode(self.world.agents[self.graph[action]['agent']],action,scene=self)
            self.nodes[self.graph[action]['type']][action] = node
        x += self.colWidth
        # Lay out the post variable nodes
        even = True
        for layer in layout['state post']:
            y = 0
            for key in sorted(layer,lambda k0,k1: cmp((self.graph[k0]['agent'],k0),
                                                      (self.graph[k1]['agent'],k1))):
                if not self.world.variables[makePresent(key)].has_key('xpost'):
                    if y >= 10*self.rowHeight:
                        even = not even
                        if even:
                            y = 0
                        else:
                            y = 50
                        x += int(0.75*self.colWidth)
                    self.world.variables[makePresent(key)]['xpost'] = x
                    self.world.variables[makePresent(key)]['ypost'] = y
                    # Move on to next Y
                    y += self.rowHeight
                if self.graph[key]['agent']:
                    agent = self.world.agents[self.graph[key]['agent']]
                    if isBinaryKey(key):
                        node = VariableNode(agent,key[len(agent.name)+1:],key,
                                            self.world.variables[makePresent(key)]['xpost'],
                                            self.world.variables[makePresent(key)]['ypost'],
                                            100,50,scene=self)
                    else:
                        node = VariableNode(agent,key[len(agent.name)+3:],key,
                                            self.world.variables[makePresent(key)]['xpost'],
                                            self.world.variables[makePresent(key)]['ypost'],
                                            100,50,scene=self)
                else:
                    node = VariableNode(None,key,key,
                                        self.world.variables[makePresent(key)]['xpost'],
                                        self.world.variables[makePresent(key)]['ypost'],
                                        100,50,scene=self)
                self.nodes[self.graph[key]['type']][key] = node
            x += self.colWidth
        # Lay out the utility nodes
        y = -self.rowHeight
        for name in sorted(self.world.agents.keys()):
            if self.graph.has_key(name):
                agent = self.world.agents[name]
                if self.world.diagram.getX(agent.name) is None:
                    self.setDirty()
                    y += self.rowHeight
                    self.world.diagram.x[agent.name] = x
                    self.world.diagram.y[agent.name] = y
                node = UtilityNode(agent,x,y,scene=self)
                self.nodes[self.graph[name]['type']][name] = node
        x += self.colWidth
        self.colorNodes()
        # Lay out edges
        for key,entry in self.graph.items():
            node = self.nodes[entry['type']][key]
            for child in entry['children']:
                self.drawEdge(key,child)

    def drawEdge(self,parent,child):
        node0 = self.nodes[self.graph[parent]['type']][parent]
        node1 = self.nodes[self.graph[child]['type']][child]
        rect0 = node0.boundingRect()
        rect1 = node1.boundingRect()
        x0 = rect0.x()+rect0.width()
        y0 = rect0.y()+rect0.height()/2
        x1 = rect1.x()
        y1 = rect1.y()+rect1.height()/2
        edge = QGraphicsLineItem(x0,y0,x1,y1,scene=node0.scene())
        edge.setZValue(0.)
        # # Draw arrow
        # line = edge.line()
        # point0 = QPointF(x1,y1)
        # sideLength = self.arrowLength/math.cos(math.radians(self.arrowAngle))
        # point1 = QPointF(x1 - math.sin(math.atan(x1/y1)-self.arrowAngle)*sideLength,
        #                  y1 - math.cos(math.atan(x1/y1)-self.arrowAngle)*sideLength)
        # point2 = QPointF(x1 - math.cos(math.atan(y1/x1)-self.arrowAngle)*sideLength,
        #                  y1 - math.sin(math.atan(y1/x1)-self.arrowAngle)*sideLength)
        # arrow = QGraphicsPolygonItem(QPolygonF([point0,point1,point2]),edge,edge.scene())
        # arrow.setBrush(QBrush(QColor('black')))
        # arrow.setPen(QPen(QColor('black')))

        try:
            self.edgesOut[parent][child] = edge
        except KeyError:
            self.edgesOut[parent] = {child: edge}
        try:
            self.edgesIn[child][parent] = edge
        except KeyError:
            self.edgesIn[child] = {parent: edge}
        return edge

    def highlightEdges(self,center):
        """
        Highlight any edges originating or ending at the named node
        @type center: str
        """
        for key,table in self.edgesOut.items()+self.edgesIn.items():
            if key == center:
                # All edges are important!
                for edge in table.values():
                    edge.setPen(QPen(QBrush(QColor('black')),5))
                    edge.setZValue(2.0)
            else:
                for subkey,edge in table.items():
                    if subkey == center:
                        # This edge is important
                        edge.setPen(QPen(QBrush(QColor('black')),5))
                        edge.setZValue(2.0)
                    else:
                        # This edge is unimportant
                        edge.setPen(QPen(QColor('black')))
                        edge.setZValue(0.0)

    def updateEdges(self,key,rect):
        self.setDirty()
        if self.edgesOut.has_key(key):
            for edge in self.edgesOut[key].values():
                line = edge.line()
                line.setP1(QPointF(rect.x()+rect.width(),rect.y()+rect.height()/2))
                edge.setLine(line)
        if self.edgesIn.has_key(key):
            for edge in self.edgesIn[key].values():
                line = edge.line()
                line.setP2(QPointF(rect.x(),rect.y()+rect.height()/2))
                edge.setLine(line)

    def step(self):
        self.world.step()
        self.world.printState()
        self.colorNodes('likelihood')
        
    def colorNodes(self,mode='agent'):
        cache = None
        for category,nodes in self.nodes.items():
            for node in nodes.values():
                color = node.defaultColor
                if mode == 'agent':
                    if node.agent:
                        color = self.world.diagram.getColor(node.agent.name)
                    elif node.agent is None:
                        color = self.world.diagram.getColor(None)
                elif mode == 'likelihood':
                    if cache is None:
                        # Pre-compute some outcomes
                        cache = {}
                        outcomes = self.world.step(real=False)
                        for outcome in outcomes:
                            # Update action probabilities
                            for name,distribution in outcome['actions'].items():
                                if not cache.has_key(name):
                                    cache[name] = Distribution()
                                for action in distribution.domain():
                                    cache[name].addProb(action,outcome['probability']*distribution[action])
                            # Update state probabilities
                            for vector in outcome['new'].domain():
                                for key,value in vector.items():
                                    if not cache.has_key(key):
                                        cache[key] = Distribution()
                                    cache[key].addProb(value,outcome['probability']*outcome['new'][vector])
                    if category == 'state pre':
                        if node.agent:
                            key = stateKey(node.agent.name,node.feature)
                        else:
                            key = stateKey(None,node.feature)
                        variable = self.world.variables[key]
                        marginal = self.world.getFeature(key)
                        if variable['domain'] is bool:
                            color = dist2color(marginal)
                        else:
                            print key,variable['domain']
                    elif category == 'action':
                        uniform = 1./float(len(cache[node.agent.name]))
                        prob = cache[node.agent.name].getProb(node.action)
                        if prob < uniform:
                            prob = 0.5*prob/uniform
                        else:
                            prob = 0.5*(prob-uniform)/(1.-uniform) + 0.5
                        distribution = Distribution({True: prob})
                        distribution[False] = 1.-distribution[True]
                        color = dist2color(distribution)
                    elif category == 'state post':
                        if node.agent:
                            key = stateKey(node.agent.name,node.feature)
                        else:
                            key = stateKey(None,node.feature)
                        key = makePresent(key)
                        if self.world.variables[key]['domain'] is bool:
                            dist = self.world.float2value(key,cache[key])
                            color = dist2color(dist)
                node.setBrush(QBrush(color))

    def setDirty(self):
        self.parent().parent().parent().actionSave.setEnabled(True)
        self.dirty = True

    def unsetDirty(self):
        self.parent().parent().parent().actionSave.setEnabled(False)
        self.dirty = False

def initializeNode(node,label):
    """
    Sets some standard parameters across node types
    """
    node.setFlags(QGraphicsItem.ItemIsSelectable|
                  QGraphicsItem.ItemIsMovable|
                  QGraphicsItem.ItemSendsGeometryChanges)
    # Draw black outline
    node.setPen(QPen(QBrush(QColor('black')),3))
    # Draw label
    rect = node.boundingRect()
    node.text = QGraphicsTextItem(node,node.scene())
    doc = QTextDocument(label,node.text)
    doc.setDefaultTextOption(QTextOption(Qt.AlignCenter))
    node.text.setDocument(doc)
    node.text.setPos(rect.x(),rect.y())
    node.text.setTextWidth(rect.width())
    node.setZValue(1.0)
    myRect = node.text.boundingRect()
    if myRect.height() > rect.height():
        rect.setHeight(myRect.height())
    # Vertical centering of label
    node.text.setPos(rect.x(),rect.y()+(rect.height()-myRect.height())/2.)
    
class VariableNode(QGraphicsEllipseItem):
    defaultWidth = 100
    defaultHeight = 50
    defaultColor = 'wheat'

    def __init__(self,agent,feature,key,x,y,w=None,h=None,scene=None):
        if w is None:
            w = self.defaultWidth
        if h is None:
            h = self.defaultHeight
        super(VariableNode,self).__init__(x,y,w,h,scene=scene)
        self.agent = agent
        self.feature = feature
        if isFuture(key):
            initializeNode(self,makePresent(feature))
        else:
            initializeNode(self,feature)
        self.setToolTip(str(key))

    def mouseDoubleClickEvent(self,event):
        self.scene().highlightEdges(stateKey(self.agent,self.feature))

    def itemChange(self,change,value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            rect = self.sceneBoundingRect()
            key = stateKey(self.agent,self.feature)
            self.scene().updateEdges(key,rect)
            if isFuture(key):
                self.scene().world.variables[makePresent(key)]['xpost'] = int(rect.x())
                self.scene().world.variables[makePresent(key)]['ypost'] = int(rect.y())
            else:
                self.scene().world.variables[key]['xpre'] = int(rect.x())
                self.scene().world.variables[key]['ypre'] = int(rect.y())
        return QGraphicsEllipseItem.itemChange(self,change,value)

class ActionNode(QGraphicsRectItem):
    defaultWidth = 100
    defaultHeight = 50
    defaultColor = 'wheat'

    def __init__(self,agent,action,x=None,y=None,w=None,h=None,scene=None):
        if x is None:
            x = agent.world.diagram.getX(action)
        if y is None:
            y = agent.world.diagram.getY(action)
        if w is None:
            w = self.defaultWidth
        if h is None:
            h = max(self.defaultHeight,len(action)*25)
        super(ActionNode,self).__init__(x,y,w,h,scene=scene)
        self.agent = agent
        self.action = action
        initializeNode(self,'\n'.join(map(str,self.action.agentLess())))
        self.setToolTip(str(action))

    def mouseDoubleClickEvent(self,event):
        self.scene().highlightEdges(self.action)

    def itemChange(self,change,value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            rect = self.sceneBoundingRect()
            self.scene().updateEdges(self.action,rect)
            self.action.x = int(rect.x())
            self.action.y = int(rect.y())
        return QGraphicsEllipseItem.itemChange(self,change,value)

class UtilityNode(QGraphicsPolygonItem):
    defaultColor = 'wheat'
    points = [(10,0),(90,0),(100,25),(90,50),(10,50),(0,25)]

    def __init__(self,agent,x=None,y=None,scene=None):
        poly = QPolygonF([QPointF(x+pt[0],y+pt[1]) for pt in self.points])
        super(UtilityNode,self).__init__(poly,scene=scene)
        self.agent = agent
        initializeNode(self,self.agent.name)
        self.setToolTip('%s\'s utility' % (self.agent.name))

    def mouseDoubleClickEvent(self,event):
        self.scene().highlightEdges(self.agent.name)

    def itemChange(self,change,value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.scene().updateEdges(self.agent.name,self.sceneBoundingRect())
        return QGraphicsEllipseItem.itemChange(self,change,value)

def dist2color(distribution):
    """
    @type distribution: L{Distribution}
    @rtype: QColor
    """
    r = round(distribution.getProb(False)*255.)
    g = round(distribution.getProb(True)*255.)
    b = 127
    return QColor(r,g,b)
