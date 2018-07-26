import math
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import graph
import diagram
from world import *
from pwl.keys import WORLD

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

    def __init__(self,parent = None):
        super(WorldView,self).__init__(parent)
        self.setBackgroundBrush(QColor('white'))
        self.nodes = {'state pre': {},
                      'state post': {},
                      'action': {},
                      'utility': {}}
        self.edgesOut = {}
        self.edgesIn = {}
        self.agents = {}
        self.world = None
        self.graph = {}
        self.dirty = False
        self.center = None

    def clear(self):
        super(WorldView,self).clear()
        for table in self.nodes.values():
            table.clear()
        self.edgesOut.clear()
        self.edgesIn.clear()
        self.center = None
        
    def displayWorld(self,world,agents=None):
        self.clear()
        if not isinstance(world.diagram,diagram.Diagram):
            if world.diagram is None:
                # Creating a diagram for the first time
                self.setDirty()
            world.diagram = diagram.Diagram(world.diagram)
        self.world = world

        self.graph = graph.DependencyGraph(self.world)
        self.graph.computeGraph(agents)
        layout = getLayout(self.graph)

        # Lay out the pre variable nodes
        x = self.drawStateNodes(layout['state pre'],self.graph,0,0,'xpre','ypre')
        # Lay out the action nodes
        x = self.drawActionNodes(layout['action'],x,0)
        # Lay out the post variable nodes
        x = self.drawStateNodes(layout['state post'],self.graph,x,0,'xpost','ypost')
        # Lay out the utility nodes
        x = self.drawUtilityNodes(x,0,self.graph,sorted(world.agents.keys()))
        self.colorNodes()
        # Lay out edges
        for key,entry in self.graph.items():
            node = self.nodes[entry['type']][key]
            for child in entry['children']:
                self.drawEdge(key,child)

    def displayGroundTruth(self,agent=WORLD,x0=0,y0=0):
        """
        @warning: Assumes that L{displayWorld} has already been called
        """
        x = x0
        y = y0
        if agent == WORLD:
            self.clear()
            g = self.graph
            state = self.world.state
        else:
            g = graph.DependencyGraph(self.world)
            state = self.world.agents[agent].getBelief()
            assert len(state) == 1
            g.computeGraph(state=state['%s0' % (agent)])
        layout = getLayout(g)
        if agent == WORLD:
            # Lay out the action nodes
            x = self.drawActionNodes(layout['action'],x,y)
            xPostAction = x
            believer = None
            xkey = 'xpost'
            ykey = 'ypost'
        else:
            believer = agent
            xkey = beliefKey(believer,'xpost')
            ykey = beliefKey(believer,'ypost')
        # Lay out the post variable nodes
        x = self.drawStateNodes(layout['state post'],g,x,y,xkey,ykey,believer)
        # Lay out the utility nodes
        if agent == WORLD:
            uNodes = [a.name for a in self.world.agents.values() \
            if a.getAttribute('beliefs','%s0' % (a.name)) is True]
        else:
            uNodes = [agent]
        x = self.drawUtilityNodes(x,y,g,uNodes)
        if agent == WORLD:
            # Draw links from utility back to actions
            for name in self.world.agents:
                if self.world.agents[name].getAttribute('beliefs','%s0' % (name)) is True:
                    if name in g:
                        actions = self.world.agents[name].actions
                        if len(actions) > 1:
                            for action in actions:
                                if action in g:
                                    self.drawEdge(name,action,g)
                else:
                    y += 11 * self.rowHeight
                    self.displayGroundTruth(name,xPostAction,y)
            self.colorNodes()
        # Draw links, reusing post nodes as pre nodes
        for key,entry in g.items():
            if isStateKey(key) or isBinaryKey(key):
                if not isFuture(key):
                    key = makeFuture(key)
                if agent != WORLD:
                    key = beliefKey(agent,key)
            elif agent != WORLD:
                continue
            for child in entry['children']:
                if agent != WORLD and child in self.world.agents and not child in uNodes:
                    continue
                if isStateKey(child) or isBinaryKey(child):
                    if agent != WORLD:
                        child = beliefKey(agent,child)
                elif agent != WORLD and not child in uNodes:
                    continue
                if child in self.world.agents and not child in uNodes:
                    continue
                self.drawEdge(key,child,g)
        if agent == WORLD:
            x += self.colWidth
        self.agents[agent] = {'box': QGraphicsRectItem(QRectF(-self.colWidth/2,y0-self.rowHeight/2,
                                                              x0+x,10.5*self.rowHeight))}
        self.agents[agent]['box'].setPen(QPen(QBrush(QColor('black')),3))
        self.agents[agent]['box'].setZValue(0.)
        if agent != WORLD:
            rect = self.agents[agent]['box'].rect()
            self.agents[agent]['text'] = QGraphicsTextItem(self.agents[agent]['box'])
            doc = QTextDocument(agent,self.agents[agent]['text'])
            self.agents[agent]['text'].setPos(rect.x(),rect.y())
            self.agents[agent]['text'].setTextWidth(rect.width())
            self.agents[agent]['text'].setDocument(doc)
        if agent != WORLD:
            color = self.world.diagram.getColor(agent)
            color.setAlpha(128)
            self.agents[agent]['box'].setBrush(QBrush(QColor(color)))
        self.addItem(self.agents[agent]['box'])
                

    def drawStateNodes(self,nodes,graph,x0,y0,xkey,ykey,believer=None):
        x = x0
        even = True
        for layer in nodes:
            y = y0
            for key in sorted(layer,lambda k0,k1: cmp((graph[k0]['agent'],k0),
                                                      (graph[k1]['agent'],k1))):
                if believer:
                    label = beliefKey(believer,key)
                else:
                    label = key
                variable = self.world.variables[makePresent(key)]
                if y >= y0+10*self.rowHeight:
                    even = not even
                    if even:
                        y = y0
                    else:
                        y = y0+50
                    x += int(0.75*self.colWidth)
                if not xkey in variable:
                    variable[xkey] = x
                    variable[ykey] = y
                # Move on to next Y
                y += self.rowHeight
                if graph[key]['agent'] != WORLD and graph[key]['agent']:
                    agent = self.world.agents[graph[key]['agent']]
                    if isBinaryKey(key):
                        node = VariableNode(agent,key[len(agent.name)+1:],key,
                                            variable[xkey],variable[ykey],
                                            100,50,scene=self)
                    else:
                        node = VariableNode(agent,key[len(agent.name)+3:],key,
                                            variable[xkey],variable[ykey],
                                            100,50,scene=self)
                else:
                    node = VariableNode(None,state2feature(key),key,
                                        variable[xkey],variable[ykey],
                                        100,50,scene=self)
                self.nodes[graph[key]['type']][label] = node
            x += self.colWidth
        return x

    def drawActionNodes(self,nodes,x0,y0):
        x = x0
        y = y0
        for action in sorted(nodes):
            if self.world.diagram.getX(action) is None:
                self.setDirty()
                self.world.diagram.x[action] = x
                self.world.diagram.y[action] = y
                # Move on to next Y
                y += self.rowHeight
                if y >= 10*self.rowHeight:
                    y = y0
                    x += self.colWidth
            node = ActionNode(self.world.agents[self.graph[action]['agent']],action,scene=self)
            self.nodes[self.graph[action]['type']][action] = node
        x += self.colWidth
        return x

    def drawUtilityNodes(self,x0,y0,graph,agents):
        x = x0
        y = y0 - self.rowHeight
        for name in agents:
            if graph.has_key(name):
                agent = self.world.agents[name]
                if self.world.diagram.getX(agent.name) is None:
                    self.setDirty()
                    y += self.rowHeight
                    self.world.diagram.x[agent.name] = x
                    self.world.diagram.y[agent.name] = y
                node = UtilityNode(agent,x,y,scene=self)
                self.nodes[graph[name]['type']][name] = node
        x += self.colWidth
        return x
        
    def drawEdge(self,parent,child,graph=None,rect0=None,rect1=None):
        if graph is None:
            graph = self.graph
        if isBeliefKey(parent):
            node0 = self.nodes[graph[belief2key(parent)]['type']][parent]
        else:
            node0 = self.nodes[graph[parent]['type']][parent]
        if isBeliefKey(child):
            node1 = self.nodes[graph[belief2key(child)]['type']][child]
        else:
            node1 = self.nodes[graph[child]['type']][child]
        if rect0 is None:
            rect0 = node0.boundingRect()
        if rect1 is None:
            rect1 = node1.boundingRect()
        if parent == child:
            # Loop back to self
            x0 = rect0.x()+rect0.width()/15
            y0 = rect0.y()+2*rect0.height()/3
            path = QPainterPath(QPointF(x0,y0))
            path.arcTo(rect0.x(),rect0.y()+rect0.height()/2,rect0.width(),rect0.height(),145,250)
            edge = QGraphicsPathItem(path,node0)
            arrow = drawArrow(QLineF(x0-5,y0+25,x0,y0),edge)
        elif rect0.y() == rect1.y():
            # Same row, so arc
            x0 = rect0.x()+rect0.width()/2
            x1 = rect1.x()+rect1.width()/2
            path = QPainterPath(QPointF(x1,rect1.y()+rect1.height()/2))
            path.arcTo(x1,rect1.y()+rect1.height()/2,x0-x1,rect1.height(),180,180)
            edge = QGraphicsPathItem(path)
            node0.scene().addItem(edge)
            if x1 < x0:
                arrow = drawArrow(QLineF(x1+25,rect1.y()+rect1.height()+15,
                                         x1-5,rect1.y()+rect1.height()),edge)
            else:
                arrow = drawArrow(QLineF(x1-25,rect1.y()+rect1.height()+15,
                                         x1+5,rect1.y()+rect1.height()),edge)
        else:
            # straight-line link
            if rect0.x() < rect1.x():
                x0 = rect0.right()
                x1 = rect1.left()
            else:
                x0 = rect0.left()
                x1 = rect1.right()
            y0 = rect0.y()+rect0.height()/2
            y1 = rect1.y()+rect1.height()/2
            edge = QGraphicsLineItem(x0,y0,x1,y1)
            node0.scene().addItem(edge)
            arrow = drawArrow(edge.line(),edge)

        edge.setZValue(1.)
        if not parent in self.edgesOut:
            self.edgesOut[parent] = {}
        if child in self.edgesOut[parent]:
            node0.scene().removeItem(self.edgesOut[parent][child][0])
        self.edgesOut[parent][child] = (edge,arrow)
        if not child in self.edgesIn:
            self.edgesIn[child] = {}
        if parent != child:
            self.edgesIn[child][parent] = (edge,arrow)
        return edge

    def highlightEdges(self,center):
        """
        Hide any edges *not* originating or ending at the named node
        @type center: str
        """
        self.center = center
        for key,table in self.edgesOut.items()+self.edgesIn.items():
            if key == center:
                # All edges are important!
                for edge,arrow in table.values():
                    edge.show()
            else:
                for subkey,(edge,arrow) in table.items():
                    if subkey == center:
                        # This edge is important
                        edge.show()
                    else:
                        # This edge is unimportant
                        edge.hide()
                        
    def boldEdges(self,center):
        """
        Highlight any edges originating or ending at the named node
        @type center: str
        """
        for key,table in self.edgesOut.items()+self.edgesIn.items():
            if key == center:
                # All edges are important!
                for edge,arrow in table.values():
                    edge.setPen(QPen(QBrush(QColor('black')),5))
                    edge.setZValue(2.0)
            else:
                for subkey,(edge,arrow) in table.items():
                    if subkey == center:
                        # This edge is important
                        edge.setPen(QPen(QBrush(QColor('black')),5))
                        edge.setZValue(2.0)
                    else:
                        # This edge is unimportant
                        edge.setPen(QPen(QColor('black')))
                        edge.setZValue(1.0)

    def updateEdges(self,key,rect):
        self.setDirty()
        if self.edgesOut.has_key(key):
            for subkey,(edge,arrow) in self.edgesOut[key].items():
                if self.center is None or self.center == key or self.center == subkey:
                    if isinstance(edge,QGraphicsLineItem):
                        line = edge.line()
                        line.setP1(QPointF(rect.x()+rect.width(),rect.y()+rect.height()/2))
                        edge.setLine(line)
                        drawArrow(line,arrow=arrow)
                    elif key != subkey:
                        edge.scene().removeItem(edge)
                        del self.edgesOut[key][subkey]
                        del self.edgesIn[subkey][key]
                        self.drawEdge(key,subkey,rect0=rect)
        if self.edgesIn.has_key(key):
            for subkey,(edge,arrow) in self.edgesIn[key].items():
                if self.center is None or self.center == key or self.center == subkey:
                    if isinstance(edge,QGraphicsLineItem):
                        line = edge.line()
                        line.setP2(QPointF(rect.x(),rect.y()+rect.height()/2))
                        edge.setLine(line)
                        drawArrow(line,arrow=arrow)
                    elif key != subkey:
                        edge.scene().removeItem(edge)
                        del self.edgesIn[key][subkey]
                        del self.edgesOut[subkey][key]
                        self.drawEdge(subkey,key,rect1=rect)

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
    node.text = QGraphicsTextItem(node)
    doc = QTextDocument(label,node.text)
    doc.setDefaultTextOption(QTextOption(Qt.AlignCenter))
    node.text.setDocument(doc)
    node.text.setPos(rect.x(),rect.y())
    node.text.setTextWidth(rect.width())
    node.setZValue(3.0)
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
        super(VariableNode,self).__init__(x,y,w,h)
        scene.addItem(self)
        self.agent = agent
        self.feature = feature
        if isFuture(key):
            initializeNode(self,makePresent(feature))
        else:
            initializeNode(self,feature)
        self.setToolTip(str(key))

    def mouseDoubleClickEvent(self,event):
        if self.agent:
            key = stateKey(self.agent.name,self.feature)
        else:
            key = stateKey(WORLD,self.feature)
        self.scene().highlightEdges(key)

    def itemChange(self,change,value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            rect = self.sceneBoundingRect()
            if self.agent:
                key = stateKey(self.agent.name,self.feature)
            else:
                key = stateKey(WORLD,self.feature)
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
        super(ActionNode,self).__init__(x,y,w,h)
        scene.addItem(self)
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
        super(UtilityNode,self).__init__(poly)
        scene.addItem(self)
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

def computeArrow(line):
    point0 = line.p2()
    arrowSize = 25.
    angle = math.atan2(-line.dy(), line.dx())
    point1 = line.p2() - QPointF(math.sin(angle + math.radians(75.)) * arrowSize,
                                          math.cos(angle + math.radians(75.)) * arrowSize)
    point2 = line.p2() - QPointF(math.sin(angle + math.pi - math.radians(75.)) * arrowSize,
                                          math.cos(angle + math.pi - math.radians(75.)) * arrowSize)

    return QPolygonF([point0,point1,point2])
    
def drawArrow(line,parent=None,arrow=None):
    if arrow:
        arrow.setPolygon(computeArrow(line))
    else:
        arrow = QGraphicsPolygonItem(computeArrow(line),parent)
        arrow.setBrush(QBrush(QColor('black')))
        arrow.setPen(QPen(QColor('black')))
    return arrow
