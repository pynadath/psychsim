import math
import tkMessageBox
from Tkinter import Frame,Button,SEL_FIRST,SEL_LAST,INSERT,Menu
import Pmw
from teamwork.widgets.MultiWin import InnerWindow
from teamwork.widgets.bigwidgets import CanvasFrame,TextWidget,BoxWidget,PolygonWidget,StackWidget,OvalWidget
from teamwork.widgets.fsa import GraphEdgeWidget,GraphWidget
from teamwork.agent.support import Supporter
from teamwork.agent.Generic import GenericModel
from teamwork.agent.DefaultBased import GenericEntity
from teamwork.widgets.images import loadImages
try:
    from pygraphviz import AGraph
    __GRAPHVIZ__ = True
except ImportError:
    __GRAPHVIZ__ = False
    
class PsymWindow(InnerWindow):
    """Dual-purpose widget that displays the entities graphically.

    Class Hierarchy View
    ====================
       - When viewing a L{generic society<teamwork.multiagent.GenericSociety>}, the window displays the entities as nodes in a hierarchy.  The links among nodes represent the sub/superclass relationships among them.
       - Left-clicking on a node will bring the corresponding agent's window
         to the top of the stack.
       - Right-clicking on a node will pop up a context menu with the
         following possible operations:
            - Rename the class
            - Add a new subclass
            - Delete this node (and all of its subclasses)
            - Raise the corresponding agent's window

    Social Network View
    ===================
       - When viewing a L{scenario<teamwork.multiagent.Simulation>}, the window displays the entities as nodes in a social network.  The links among nodes represent the current social relationships among them.
       - Left-clicking on a node will bring the corresponding agent's window
         to the top of the stack.
       - Right-clicking on a node will pop up a context menu with the
         following possible operations:
             - Center the network on this node, using a given relationship
             - Raise the corresponding agent's window

    @ivar selected: the node currently selected (C{None} if no node is selected)
    @type selected: L{CanvasWidget}
    """
    
    def __init__(self,frame,**kw):
        optiondefs = (
            ('entities',   None, self.setview),
            ('height',     600,  None),
            ('width',      600,  None),
            ('padx',       150,  None),
            ('pady',       180,  None),
            ('balloon',    None, None),
            # Dimensions of the rectangles for each node icon
            ('nodeWidth',  100,  None),
            ('nodeHeight', 50,   None),
            # Command invoked when deleting a node
            ('delete',     None, None),
            # Command invoked when adding a node
            ('add',        None, None),
            # Command invoked when renaming node
            ('rename', None, None),
            # Prefix string for the title of this window
            ('prefix',     "Network", self.setTitle),
            # Relationship label strings
            ('likingLabel','Liking',         None),
            ('trustLabel', 'Trust',          None),
            # Agent windows
            ('showWindow', None, Pmw.INITOPT),
            ('windows', {}, None),
            ('expert',     True, self.redrawSupport),
            ('options',    None, Pmw.INITOPT),
            ('layout',None,None),
            )
        self.defineoptions(kw, optiondefs)
        # Set up images if available
        self.images = loadImages({'del': 'icons/user--minus.gif',
                                  'add': 'icons/user--plus.gif',
                                  'edit': 'icons/user--pencil.gif'},
                                 self['options'].get('Appearance','PIL') == 'yes')
        self.edgedict = {}
        self.nodes = {}
        InnerWindow.__init__(self,frame)
        toolbar = Frame(self.component('frame'),bd=2,relief='raised')
        self.createcomponent('Selector',(),None,Pmw.OptionMenu,(toolbar,),
                             command=self.setview).pack(side='right')
        self.createcomponent('Add',(),None,Button,(toolbar,),
                             command=self.add)
        try:
            self.component('Add').configure(image=self.images['add'])
        except:
            self.component('Add').configure(text='Add')
        if self['balloon']:
            self['balloon'].bind(self.component('Add'),
                                 'Create new subclass of entity')
        self.createcomponent('Remove',(),None,Button,(toolbar,),
                             command=self.remove)
        try:
            self.component('Remove').configure(image=self.images['del'])
        except:
            self.component('Remove').configure(text='Delete')
        if self['balloon']:
            self['balloon'].bind(self.component('Remove'),
                                 'Delete selected entity and subclasses')
        self.createcomponent('Rename',(),None,Button,(toolbar,),
                             command=self.rename)
        try:
            self.component('Rename').configure(image=self.images['edit'])
        except:
            self.component('Rename').configure(text='Rename')
        if self['balloon']:
            self['balloon'].bind(self.component('Rename'),'Rename selected entity')
        self.createcomponent('Prev',(),None,Button,(toolbar,),
                             command=self.prev)
        self.component('Prev').configure(text='Prev')
        self.createcomponent('Next',(),None,Button,(toolbar,),
                             command=self.next)
        self.component('Next').configure(text='Next')
        if __GRAPHVIZ__:
            Button(toolbar,text='Layout',
                   command=self.layout).pack(side='right')
        toolbar.pack(fill='x',side='top')
        self.cf = CanvasFrame(parent = self.component('frame'))
        self.c = self.cf.canvas()
        self.c.configure(background='white')
        self.c.bind("<Key>", self.handle_key)
        self.cf.pack(expand = 'yes', fill = 'both', side='bottom')

        self.rel = None
        self.vname = None
        self.selected = None
        self.initialiseoptions()

    def clear(self):
        """Removes any existing network"""
        if self.selected:
            self.selectNode(None,self.selected)
        self.edgedict.clear()
        self.nodes.clear()
        self.edges = []
        self.c.delete('all')
       
    def setview(self,rel=None,name=None):
        """Redraws network to center on the named entity
        @param name: the entity to center on
        @type name: str
        @param rel: the relationship to use for link weights (if 'class', then draws the nodes in a hierarchy)
        @type rel: str
        """
        assert len(self['entities']) > 0
        self.clear()
#        if rel == 'class':
#            rel = '_parent'
        # Store view within entities for saving to file
        if rel is None and name is None:
            if self['entities'].extra.has_key('networkLink'):
                rel = self['entities'].extra['networkLink']
            if self['entities'].extra.has_key('networkEntity'):
                name = self['entities'].extra['networkEntity']
        else:
            if not rel is None:
                self['entities'].extra['networkLink'] = rel
            if not name is None:
                self['entities'].extra['networkEntity'] = name
        # Save new settings
        if rel is None:
            if self.rel in ['class',None] and \
               not isinstance(self['entities'].members()[0],GenericModel):
                self.rel = Supporter._supportFeature
            elif self.rel is None and \
               isinstance(self['entities'].members()[0],GenericModel):
                self.rel = 'class'
        else:
            self.rel = rel
        # Determine the options for network selector
        linkTypes = {}
        for entity in self['entities'].members():
            for relation in entity.getLinkTypes():
                linkTypes[relation] = True
        linkTypes = linkTypes.keys()
        if isinstance(self['entities'].members()[0],GenericModel):
            linkTypes.insert(0,'class')
        self.component('Selector_menu').delete(0,'end')
        self.component('Selector').setitems(linkTypes)
        if self.component('Selector').getvalue() != self.rel:
            self.component('Selector').setvalue(self.rel)
        if name is None:
            if self.vname is None or not self['entities'].has_key(self.vname):
                self.vname = self['entities'].keys()[0]
            else:
                name = self.vname
        else:
            self.vname = name
        coords = {}
        if self.rel == 'class':
            self.component('Add').pack(side='left')
            self.component('Remove').pack(side='left')
            self.component('Rename').pack(side='left')
            self.component('Next').pack_forget()
            self.component('Prev').pack_forget()
            self['title'] = 'Class %s' % (self['prefix'])
            self.setTitle()
            for entity in self['entities'].members():
                try:
                    coords[entity.name] = entity.attributes['coords']
                except KeyError:
                    coords[entity.name] = None
        else:
            self.component('Add').pack_forget()
            self.component('Remove').pack_forget()
            self.component('Rename').pack_forget()
            self.component('Prev').pack(side='left')
            self.component('Next').pack(side='left')
            self['title'] = '%s %s' % (self.rel.capitalize(),self['prefix'])
            # Set up entity at center
            entity = self['entities'][self.vname]
            x = float(self['width']-self['padx'])/2.
            y = float(self['height']-self['pady'])/2.
            coords[entity.name] = (x,y)
            # Set up others in a circle around
            index = 0
            offset = None
            linkees = entity.getLinkees(self.rel)
            for other in linkees:
                if entity.name != other:
                    if offset is None:
                        offset = 2.0*math.pi/float(len(linkees))
                    xloc, yloc = self.PickXY(other,float(index)*offset)
                    coords[other] = (xloc,yloc)
                    index += 1
        assert len(coords) > 0
        # Draw entity widgets
        for name in coords.keys():
            entity = self['entities'][name]
            self.nodes[name] = self.PickWidget(self.c, entity)
        # Event bindings for nodes
        if self.rel == 'class':
            # Draw lines as subclass relations
            links = []
            edges = {}
            for name in self['entities'].keys():
                edges[name] = {}
                for other in filter(lambda n:n!=name,self['entities'].keys()):
                    edges[name][other] = 1.
            for entity in self['entities'].members():
                for parent in entity.getParents():
                    assert self['entities'].has_key(parent)
                    label = TextWidget(self.c,'')
                    edge = GraphEdgeWidget(self.c,0,0,0,0,label)
                    self.edgedict['%s_%s' % (entity.name,parent)] = edge
                    links.append((self.nodes[entity.name],
                                  self.nodes[parent],edge))
                    edges[entity.name][parent] = 10.
        else:
            links = []
            entity = self['entities'][self.vname]
            for other in entity.getLinkees(self.rel):
                label = TextWidget(self.c,'')
                edge = GraphEdgeWidget(self.c,0,0,0,0,label)
                self.edgedict['%s_%s' % (self.vname,other)] = edge
                links.append((self.nodes[self.vname],
                              self.nodes[other],edge))
                # Update line thickness
                self.redrawSupport()
        assert len(self.nodes) > 0
        graph = GraphWidget(self.c,self.nodes.values(),links)
        self.cf.add_widget(graph)
##        from teamwork.math.forcebased import forcebased
##        coords = forcebased(coords,edges,maxIterations=100)
        for name,node in self.nodes.items():
            entity = self['entities'][name]
            node.bind_click(self.selectNode,1)
            node.bind_click(self.context,3)
            node.bind_click(self.raiseWindow,'double')
            try:
                point = coords[name]
            except KeyError:
                point = None
            if point:
                # Position node according to stored coordinates
                current = self.c.coords(node.tags()[0])
                deltaX = point[0]-current[0]
                deltaY = point[1]-current[1]
                node.move(deltaX,deltaY)
            else:
                # Move the node to the origin
                current = self.c.coords(node.tags()[0])
                node.move(-current[0],-current[1])
                entity.attributes['coords'] = self.c.coords(node.tags()[0])
            
    def PickXY(self,name,angle=0.):
        x = 0.5+math.cos(angle)/2.
        y = 0.5+math.sin(angle)/2.
        return float(self['width']-self['padx'])*x, \
               float(self['height']-self['pady'])*y
    

    def PickWidget(self,parent,entity):
        """Returns a shaped widget appropriate for the given entity"""
        palette = Pmw.Color.getdefaultpalette(self.parent.parent)
        # Find the appropriate shape for this node
        if isinstance(entity,GenericModel):
            widget = 'oval'
        elif isinstance(entity,GenericEntity):
            try:
                widget = entity.getDefault('widget')
            except KeyError:
                widget = 'oval'
            if widget is None:
                widget = 'oval'
        else:
            widget = 'oval'
        # Build the widget of the chosen shape
##        if entity.attributes.has_key('imageName'):
##            image = ImageWidget(parent,entity.attributes['image'])
##            widget = StackWidget(parent,image,
##                                 TextWidget(self.c,entity.name))
        if widget == 'oval':
            widget = OvalWidget(self.c,TextWidget(self.c,entity.name,),
                                fill=palette['background'],
                                outline=palette['foreground'])
        elif widget == 'polygon':
            widget = PolygonWidget(parent,TextWidget(parent,entity.name),
                                   fill=palette['background'],outline='red',width=2,
                                   margin=10)
        elif widget == 'box':
            widget = BoxWidget(parent,TextWidget(parent,entity.name),
                               fill=palette['background'],width=2,
                               outline=palette['foreground'],margin=10)
        else:
            raise NameError,'Unknown widget type %s' % widget
        if self.rel == 'class':
            widget['draggable'] = True
            widget.bind_drag(self.readCoords)
        return widget

    def layout(self):
        g = AGraph(strict=False,directed=True)
        for entity in self['entities'].members():
            g.add_node(entity.name)
        for entity in self['entities'].members():
            for child in self['entities'].network[entity.name]:
                g.add_edge(entity.name,child)
        if self['layout']:
            g.layout(self['layout'])
        else:
            g.layout()
        for entity in self['entities'].members():
            x,y = map(int,g.get_node(entity.name).attr['pos'].split(','))
            x *= 2
            y *= 2
            node = self.nodes[entity.name]
            current = self.c.coords(node.tags()[0])
            deltaX = x-current[0]
            deltaY = y-current[1]
            node.move(deltaX,deltaY)
        
    def prev(self):
        entities = map(lambda e: e.name,self['entities'].members())
        entities.sort(lambda x,y: cmp(x.lower(),y.lower()))
        index = entities.index(self.vname) - 1
        if index < 0:
            index += len(entities)
        self.setview(name=entities[index])

    def next(self):
        entities = map(lambda e: e.name,self['entities'].members())
        entities.sort(lambda x,y: cmp(x.lower(),y.lower()))
        index = entities.index(self.vname) + 1
        if index >= len(entities):
            index = 0
        self.setview(name=entities[index])

    def redrawSupport(self):
        """Updates thickness and color of any links in network"""
        for s1 in self['entities'].members():
            for s2 in self['entities'].members():
                key = s1.name + '_' + s2.name
                if self.edgedict.has_key(key):
                    edge = self.edgedict[key]
                    if self.rel == 'class':
                        # What should the lines look like in the hierarchy?
                        pass
                    else:
                        value = float(s1.getLink(self.rel,s2.name))
                        if self['expert']:
                            edge._label.set_text(str(value))
                        else:
                            edge._label.set_text('')
                        if value < 0.:
                            width = int(-10.*value)
                            color = 'red'
                        elif value > 0.:
                            width = int(10.*value)
                            color = 'green'
                        else:
                            width = value
                            color = 'black'
                        edge['color'] = color
                        edge['width'] = max(1,width)

    def selectNode(self,event,widget):
        """Callback when selecting a node (left-click)
        """
#        if isinstance(widget,StackWidget):
#            child = widget._children[1]
#        else:
#            child = widget.child()
#        entity = self['entities'][child.text()]
        palette = Pmw.Color.getdefaultpalette(self.parent.parent)
        if self.selected:
            self.selected.child()['color'] = palette['foreground']
            self.selected['fill'] = palette['background']
        if self.selected == widget:
            # Deselect node
            self.selected = None
        else:
            # Newly selected node
            widget.child()['color'] = palette['selectForeground']
            widget['fill'] = palette['selectBackground']
            self.selected = widget

    def copy(self,node):
        for name in self.nodes.keys():
            if self.nodes[name] is node:
                break
        else:
            raise UserWarning,'Unable to find node to copy'
        nodes = [self['entities'][name]]
        next = 0
        while next < len(nodes):
            for entity in self['entities'].network[nodes[next].name]:
                if not entity in nodes:
                    nodes.append(self['entities'][entity])
            next += 1
        return nodes

    def cut(self,node):
        result = self.copy(node)
        # Save parents for subtree, which will get clobbered upon deletion
        parents = {}
        for node in result[1:]:
            parents[node.name] = node.getParents()[:]
        # Delete copied nodes as well
        self.selectNode(None,self.selected)
        self.remove(result[0],True)
        # Cut agent no longer has parent links
        while len(result[0].getParents()):
            result[0].parentModels.pop()
        # Descendent agents maintain previous parent links
        for node in result[1:]:
            node.parentModels = parents[node.name]
        return result

    def paste(self,nodes):
        if self.selected is None:
            # Haven't selected anywhere to paste to
            return False
        for parent in self.nodes.keys():
            if self.nodes[parent] is self.selected:
                break
        else:
            raise UserWarning,'Unable to find node to paste to'
        self.add(self['entities'][parent],nodes[0])
        for node in nodes[1:]:
            self.add(self['entities'][node.getParents()[0]],node)
        return True

    def raiseWindow(self,event,widget):
        if isinstance(widget,StackWidget):
            child = widget._children[1]
        else:
            child = widget.child()
        entity = self['entities'][child.text()]
        self['showWindow'](entity.name)
        
    def context(self,event,widget):
        """Pops up a context-sensitive menu in the network"""
        if isinstance(widget,StackWidget):
            child = widget._children[1]
        else:
            child = widget.child()
        entity = self['entities'][child.text()]
        menu = Menu(self.component('frame'),tearoff=0)
        if isinstance(entity,GenericModel):
            # Menu allows modification of hierarchy
            if len(entity.getParents()) > 0:
                # Can't rename root node
                menu.add_command(label='Rename',
                                 command=lambda s=self,e=entity:s.rename(e))
            menu.add_command(label='Add subclass',
                             command=lambda s=self,e=entity:s.add(e))
            menu.add_command(label='Delete class',
                             command=lambda s=self,e=entity:s.remove(e))
            menu.add_separator()
            if self.rel != 'class':
                menu.add_command(label='Show class hierarchy',
                                 command=lambda s=self:
                                 s.setview(name=None,rel='class'))
        if isinstance(entity,Supporter):
            # Menu allows re-centering of support graph
            if entity.name != self.vname or \
                   self.rel != Supporter._supportFeature:
                menu.add_command(label='Center and show liking',
                                 command=lambda s=self,n=entity.name:
                                 s.setview(name=n,
                                           rel=Supporter._supportFeature))
            if entity.name != self.vname or \
                   self.rel != Supporter._trustFeature:
                menu.add_command(label='Center and show trust',
                                 command=lambda s=self,n=entity.name:
                                 s.setview(name=n,
                                           rel=Supporter._trustFeature))
            if entity.name != self.vname and self.rel != 'class' and \
                    isinstance(entity,GenericModel):
                menu.add_command(label='Delete link',
                                 command=lambda s=self,n=entity.name:
                                     s.delLink(n))
        menu.add_separator()
        menu.add_command(label='Show window',
                         command=lambda c=self['showWindow'],
                         n=entity.name:c(n))
        menu.bind("<Leave>",self.unpost)
        menu.post(event.x_root,event.y_root)

    def readCoords(self,widget):
        """Stores the coordinates of the nodes in their corresponding L{Agent<teamwork.agent.Agent.Agent>} objects
        """
        if self.rel == 'class':
            if isinstance(widget,StackWidget):
                name = widget._children[1].text()
            else:
                name = widget.child().text()
            entity = self['entities'][name]
            node = self.nodes[entity.name]
            entity.attributes['coords'] = self.c.coords(node.tags()[0])
            
    def unpost(self,event):
        event.widget.unpost()
            
    def add(self,entity=None,agent=None):
        """Adds a child to the selected entity"""
        if entity is None:
            if self.selected is None:
                tkMessageBox.showerror('No Entity Selected','You must select an entity class to add a subclass to.')
                return
            else:
                entity = self['entities'][self.selected.child().text()]
        if self['add']:
            self['add'](entity,agent)
        self.setview(name=self.vname)
        
    def remove(self,entity=None,confirm=None):
        """Removes the selected entity from the group"""
        if entity is None:
            if self.selected is None:
                tkMessageBox.showerror('No Entity Selected','You must select an entity class to delete.')
                return
            else:
                entity = self['entities'][self.selected.child().text()]
        if confirm is None:
            msg = 'Are you sure you want to permanently delete the entity %s and all of its descendent classes?' % \
                (entity.name)
            confirm = tkMessageBox.askyesno('Confirm Delete',msg)
        if confirm:
            if self['delete']:
                self['delete'](entity)
            if not self['entities'].has_key(entity.name):
                self.selected = None
                # We've actually deleted the class, so update view
                if self.vname == entity.name:
                    self.setview(name=self['entities'].members()[0].name)
                else:
                    self.setview(name=self.vname)
            
    def addLink(self,entity):
        """Adds the link from the center entity to the named one"""
        self['entities'][self.vname].setLink(self.rel,entity,0.)
        self.setview(name=self.vname)
        if self['windows'].has_key(self.vname):
            widget = self['windows'][self.vname].component('Relationships')
            widget.addDynamic(self.rel)

    def delLink(self,entity):
        """Removes the link from the center entity to the named one"""
        msg = 'Do you really want to delete the link, %s %s %s?' % \
              (self.vname,self.rel,entity)
        if tkMessageBox.askyesno('Confirm Delete',msg):
            self['entities'][self.vname].removeLink(self.rel,entity)
            self.setview(name=self.vname)
            if self['windows'].has_key(self.vname):
                widget = self['windows'][self.vname].component('Relationships')
                widget.addDynamic(self.rel)

    def rename(self,entity=None):
        if entity is None:
            if self.selected is None:
                tkMessageBox.showerror('No Entity Selected','You must select an entity class to rename.')
                return
            else:
                node = self.selected
        else:
            node = self.nodes[entity.name]
        tag = node.child().tags()[0]
        widget = self.c.find_withtag(tag)
        self.c.focus_set()
        self.c.focus(widget)
        self.c.select_from(widget, 0)
        self.c.select_to(widget,'end')
        
    def has_selection(self):
        # hack to work around bug in Tkinter 1.101 (Python 1.5.1)
        return self.c.tk.call(self.c._w, 'select', 'item')
   
    def highlight(self, item):
        # mark focused item.  note that this code recreates the
        # rectangle for each update, but that's fast enough for
        # this case.
        bbox = self.c.bbox(item)
        self.c.delete("highlight")
        if bbox:
            i = self.c.create_rectangle(bbox, fill="white",tag="highlight")
            self.c.lower(i, item)

    def handle_key(self, event):
        # widget-wide key dispatcher
        item = self.c.focus()
        if not item:
            return
        try:
            insert = self.c.index(item, INSERT)
        except:
            # Focus call doesn't work on Mac?
            return
        if event.char >= " ":
            # printable character
            if self.has_selection():
                self.c.dchars(item, SEL_FIRST, SEL_LAST)
                self.c.select_clear()
            self.c.insert(item, "insert", event.char)
            self.highlight(item)

        elif event.keysym == "BackSpace":
            if self.has_selection():
                self.c.dchars(item, SEL_FIRST, SEL_LAST)
                self.c.select_clear()
            else:
                if insert > 0:
                    self.c.dchars(item, insert-1, insert-1)
            self.highlight(item)

        # navigation
        elif event.keysym == "Home":
            self.c.icursor(item, 0)
            self.c.select_clear()
        elif event.keysym == "End":
            self.c.icursor(item, 'end')
            self.c.select_clear()
        elif event.keysym == "Right":
            self.c.icursor(item, insert+1)
            self.c.select_clear()
        elif event.keysym == "Left":
            self.c.icursor(item, insert-1)
            self.c.select_clear()
        elif event.keysym == 'Return':
            item = int(item)
            for node in self.nodes.values():
                if item == node.child()._tag:
                    break
            else:
                raise UserWarning,'Attempted to rename non-agent object!'
            # Grab and test new name
            new = node.child().text()
            old = node.child()._text
            if len(new) == 0:
                tkMessageBox.showerror('Illegal Agent Name','An agent cannot have an empty name.')
            elif new != old and self.nodes.has_key(new): 
                tkMessageBox.showerror('Illegal Agent Name','Agent names cannot be duplicated.')
            else:
                self.c.focus('')
                if old != new:
                    node.child()._text = new
                    del self.nodes[old]
                    self.nodes[new] = node
                    node.update(node.child())
                    if self['rename']:
                        # Update agent references
                        self['rename'](old,new)
                self.c.delete("highlight")
        else:
            pass

