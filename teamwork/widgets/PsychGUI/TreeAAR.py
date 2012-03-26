import string
from Tkinter import *
import tkMessageBox
import Pmw
import tkFileDialog
from xml.dom.minidom import *

from teamwork.messages.PsychMessage import Message as PsychMessage
from teamwork.widgets.MultiWin import InnerWindow
from teamwork.widgets.TreeWidget import *
from teamwork.agent.Agent import Agent
from teamwork.action.PsychActions import Action
from teamwork.math.probability import Distribution
from teamwork.math.matrices import epsilon
from teamwork.math.Keys import Key,keyConstant
from teamwork.math.KeyedVector import KeyedVector,UnchangedRow
from teamwork.reward.goal import PWLGoal

try:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.rl_config import defaultPageSize
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    pdfCapability = True
except ImportError:
    pdfCapability = False


class JiveTalkingAAR(InnerWindow):
    """
    @ivar history: step history (allows collapsing of redundant nodes)
    @type history: dict
    @ivar doc: cumulative XML history (includes all steps, even those that are not displayed due to redundancy)
    @type doc: Element
    """

    def __init__(self,frame,**kw):
        optiondefs = (
            ('title',  'AAR', self.setTitle),
            ('font',   ("Helvetica", 10, "normal"), Pmw.INITOPT),
            ('fitCommand', None, Pmw.INITOPT),
            ('msgCommand', None, Pmw.INITOPT),
            ('reportTitle', "Scenario History Report", None),
            ('pageinfo', "history report", None),
            ('expert', False, None),
            ('entities',{},None),
            )
        self.defineoptions(kw,optiondefs)
        InnerWindow.__init__(self,frame)
        Button(self.component('frame'), text="Generate report",
                   command=self.generateReport).pack(side='top')
        widget = self.createcomponent('Tree',(),None,EasyTree,
                                      (self.component('frame'),),
                                      root_label="Simulation Trace",
                                      font=self['font'],
                                      )

        sb=Scrollbar(widget.master)
        sb.pack(side='right', fill='y')
        widget.configure(yscrollcommand=sb.set)
        sb.configure(command=widget.yview)

        widget.pack(side='top',fill='both',expand='yes')
        self.initialiseoptions()
        self.history = {}
        self.clear()

    def generateReport(self):
        if not self['entities']:
            tkMessageBox.showerror('Report Error','There are no agents on which to report.')
            return
        widget = self.component('Tree')
        paragraphs = []
        self.getNodeText(widget.easyRoot, 0, paragraphs)
        ftypes = [('XML file', '.xml')]
        if pdfCapability:
            ftypes.append(('PDF file', '.pdf'))
        filename = tkFileDialog.asksaveasfilename(filetypes=ftypes,
                                                  defaultextension='.xml')
        if filename:
            if filename[-4:] == '.pdf':
                # PDF format
                doc = SimpleDocTemplate(filename)
                Story = [Spacer(1, 2*inch)]
                style = getSampleStyleSheet()["Normal"]
                for (para,level) in paragraphs:
                    indent = level*8
                    para = "<para firstLineIndent=\"0\" leftIndent=\"" + str(indent) + "\">" + para + "</para>"
                    p = Paragraph(para, style)
                    Story.append(p)
                Story.append(Spacer(1, 0.2*inch))
                doc.build(Story, onFirstPage=self.myFirstPage, onLaterPages=self.myLaterPages)
            elif filename[-4:] == '.xml':
                # XML format
                f = open(filename,'w')
                f.write(self.doc.toxml())
                f.close()
            else: 
                raise NotImplementedError,'Unable to output history in %s format' % (filename[-3:].upper())

    def myFirstPage(self, canvas, doc):
        PAGE_WIDTH = defaultPageSize[0]
        PAGE_HEIGHT = defaultPageSize[1]
        canvas.saveState()
        canvas.setFont('Times-Bold', 16)
        canvas.drawCentredString(PAGE_WIDTH/2.0, PAGE_HEIGHT-108,
                                 self['reportTitle'])
        canvas.setFont('Times-Roman', 9)
        canvas.drawString(inch, 0.75 * inch,
                          "First Page / %s" % self['pageinfo'])
        canvas.restoreState()

    def myLaterPages(self,canvas, doc):
        canvas.saveState()
        canvas.setFont('Times-Roman', 9)
        canvas.drawString(inch, 0.75 * inch,
                          "Page %d %s" % (doc.page, self['pageinfo']))
        canvas.restoreState()

    def getNodeText(self, node, level, paragraphs):
        paragraphs.append((node['label'], level))
        for child in node['children']:
            self.getNodeText(child, level+1, paragraphs)
        
    def clear(self):
        """Removes any existing explanations from the display
        """
        widget = self.component('Tree')
        self.nodes = []
        rootNode = widget.easyRoot
        rootNode.deleteChildren()

        # Initialize XML content
        self.doc = Document()
        root = self.doc.createElement('history')
        self.doc.appendChild(root)
        # Initialize step history (allows collapsing of redundant nodes)
        self.history.clear()
        
    def displayAAR(self,elements,parent=None):
        widget = self.component('Tree')
        widget.inhibitDraw = True
        step = elements.firstChild
        while step:
            self.doc.documentElement.appendChild(step)
            if step.tagName == 'step':
                parent = self.addStep(step)
                #we might as well expand the root node
                widget.root.expand()
            else:
                raise UserWarning,step.tagName
            step = step.nextSibling
        widget.inhibitDraw = False

    def addStep(self,step):
        widget = self.component('Tree')
        index = int(step.getAttribute('time'))
        prefix = 'Step %d' % (index)
        #add the overarching step node to the root of the simulation history tree
        parentStepNode = self.findNode(prefix,widget.easyRoot)
        if str(step.getAttribute('hypothetical')) == str(True):
            prefix += ' (hypothetical)'
            parentStepNode['label'] = prefix
        # Generate a string for the overall decisions
        field = step.firstChild
        decisionStr = []
        actors = {}
        while field:
            if field.tagName == 'turn':
                # The decision of a single agent
                child = field.firstChild
                while child:
                    if child.tagName == 'decision':
                        # Set branch for this agent's turn
                        name = str(field.getAttribute('agent'))
                        actors[name] = True
                        turnStr = '%s ' % (name)
                        label = '%s\'s decision (ER=%s)' % (name,child.getAttribute('value'))
                        forced = str(field.getAttribute('forced')) == str(True)
                        node = self.findNode(label,parentStepNode)
                        option = extractAction(child)
                        actionStr = actionString(option)
                        decisionStr.append(turnStr+actionStr)
                        if forced:
                            node['label'] = label + ' (forced)'
                            node['isLeaf'] = True
                        else:
                            node['action'] = lambda n,e,s=self,a=name,o=option,\
                                          t=index:s.confirmAction(n,e,a,o,t)
                    elif child.tagName == 'explanation':
                        self.addExplanation(name,child,node,index)
                    elif child.tagName == 'suggestions':
                        self.addSuggestions(name,child,node)
                    child = child.nextSibling
            elif field.tagName == 'effect':
                self.addEffect(field,parentStepNode)
            else:
                print 'Unhandled:',field.tagName
            field = field.nextSibling
        # Check whether we want to collapse a previous node
        names = actors.keys()
        names.sort()
        key = '%d %s' % (index,' '.join(names))
        try:
            index = widget.easyRoot.childIndex(self.history[key])
        except KeyError:
            index = -1
        if index == -1:
            self.history[key] = parentStepNode
#        if index >= 0:
#            del widget.child[0].child[-1]
#            widget.child[0].child[index] = parent
        parentStepNode['label'] = '%s: %s' % (prefix,'; '.join(decisionStr))
        parentStepNode.refresh(widget)
        return parentStepNode

    def fitAction(self,agent,element,step):
        """
        Activates the fitting function for the given agent and alternative
        @param agent: the agent whose behavior is being fit
        @type agent: str
        @param element: the explanation structure for this alternative action
        @type element: Element
        @param step: the time that this action should occur
        @type step: int
        """
        option = []
        child = element.firstChild
        while child:
            if child.tagName == 'action':
                action = Action()
                action.parse(child)
                option.append(action)
            child = child.nextSibling
        self['fitCommand'](agent,option,step-1)
        
    def actionMenu(self,event,args):
        menu = Menu(self.component('frame'),tearoff=0)
        label = string.join(map(str,args['decision']),', ')
        menu.add_command(label='%s is correct' % (label),
                         command=lambda s=self,a=args['decision'],i=args:\
                         s['fitCommand'](a,i))
        if len(args['agent'].actions.getOptions()) > 1:
            menu.add_separator()
            for action in args['agent'].actions.getOptions():
                if action != args['decision']:
                    menu.add_command(label=string.join(map(str,action),', '),
                                     command=lambda s=self,a=action,i=args:\
                                     s['fitCommand'](a,i))
        menu.bind("<Leave>",self.unpost)
        menu.post(event.x_root, event.y_root)        

    def sendMenu(self,event,args):
        menu = Menu(self.component('frame'),tearoff=0)
        agent = self['entities'][args['violator']]
        entities = filter(lambda e: e.name != args['violator'] and \
                          len(e.entities) > 0,agent.getEntityBeliefs())
        for entity in entities:
            menu.add_command(label='Send from %s' % \
                             (entity.name),
                             command=lambda o=args,e=entity.name,s=self: \
                             s['msgCommand'](e,o))
        menu.bind("<Leave>",self.unpost)
        menu.post(event.x_root, event.y_root)
            
    def pop(self):
        """Removes the bottom-most bullet from the tree"""
        widget = self.component('Tree')
        del widget.child[0].child[-1]

    def unpost(self,event):
        event.widget.unpost()

    def findNode(self,label,parent):
        """
        @param label: the label prefix for the child node
        @type label: str
        @param parent: the parent node
        @return: the child node for the given parent with the given label.  If no such child already exists, then returns a newly created child node with the given label
        """
        widget = self.component('Tree')
        n = None
        for node in parent['children']:
            if node['label'][:len(label)] == label:
                n = node
                break

        if not n:
            n = parent.addChild(widget,label=label)
            n['label'] = label

        return n

    def addExplanation(self,agent,element,parent,step):
        """Extracts an agent's decision from an XML element and adds the corresponding subtree to the given parent tree
        @param agent: the agent whose decision is being explained
        @type agent: str
        @param element: the XML decision description
        @type element: Element
        @param parent: the node to add the decision explanation below
        @type parent: L{Node}
        @param step: the time that this decision occurred at
        @type step: int
        """
        widget = self.component('Tree')
        child = element.firstChild
        while child:
            if child.tagName == 'alternatives':
                subNode = self.findNode('Alternatives:',parent)
                subNode.deleteChildren()
                alternatives = []
                subChild = child.firstChild
                while subChild:
                    if subChild.tagName == 'goals':
                        goals = Distribution()
                        goals.parse(subChild.firstChild,PWLGoal)
                    else:
                        alternatives.append(subChild)
                    subChild = subChild.nextSibling
                for subChild in alternatives:
                    # Add the action
                    option = extractAction(subChild)
                    label = actionString(option)
                    label += ' (ER=%s)' % (str(subChild.getAttribute('value')))
                    try:
                        rank = int(subChild.getAttribute('rank'))
                        label += ' (rank #%d)' % (rank+1)
                    except ValueError:
                        pass
                    actNode = subNode.addChild(widget,label=label)
                    actNode['action'] = lambda l,e,s=self,a=agent,o=subChild,\
                                     t=step:s.fitAction(a,o,t)
                    field = subChild.firstChild
                    while field:
                        if field.tagName == 'vector':
                            # Find out which goals this action helps/hurts
                            good = []
                            bad = []
                            delta = KeyedVector()
                            delta.parse(field,True)
                            for goal in goals.domain():
                                value = goals[goal]*delta[goal.toKey()]
                                if value > epsilon:
                                    good.append(goal)
                                elif value < -epsilon:
                                    bad.append(goal)
                            if len(good) > 0:
                                self.addGoals('which would help:',actNode,
                                              good,goals)
                            if len(bad) > 0:
                                self.addGoals('but which would not:',
                                              actNode,bad,goals)
                            if len(good)+len(bad) == 0:
                                expNode = actNode.addChild(widget,label='which was just as good',isLeaf=True)
                                expNode['label']='which was just as good'
                        elif field.tagName == 'expectations':
                            self.addExpectations(agent,field,actNode,step)
                        field = field.nextSibling
            elif child.tagName == 'expectations':
                self.addExpectations(agent,child,parent,step)
            elif child.tagName == 'decision':
                pass
            else:
                print 'Unknown explanation field:',child.tagName
            child = child.nextSibling

    def addExpectations(self,agent,element,parent,step=1):
        # Display expected responses from other agents
        subNode = self.findNode('Expected countermoves:',parent)
        subNode.deleteChildren()
        subChild = element.firstChild
        while subChild:
            # Everything but the initial actor's first step is a response
            assert subChild.tagName == 'turn'
            name = str(subChild.getAttribute('agent'))
            t = int(subChild.getAttribute('time'))
            if t > 0 or name != agent:
                prob = float(subChild.getAttribute('probability'))
                model = str(subChild.getAttribute('model'))
                option = extractAction(subChild)
                label = 'Step %d) %s ' % (t+step,name)
                if model:
                    label += '[%s] ' % (model)
                label += '%s (prob=%d%%)' % (actionString(option),100*prob)
                actNode = subNode.addChild(self.component('Tree'),label=label,isLeaf=False)
                grandChild = subChild.firstChild
                while not grandChild is None:
                    if grandChild.nodeType == grandChild.ELEMENT_NODE:
                        if grandChild.tagName == 'explanation':
                            self.addExplanation(name,grandChild,actNode,t+step)
                        elif grandChild.tagName == 'state':
                            effect = self.findNode('Effect',actNode)
                            self.addStateEffect(grandChild,effect)
                    grandChild = grandChild.nextSibling
            subChild = subChild.nextSibling

    def addGoals(self,label,node,subset,goals):
        widget = self.component('Tree')
        expNode = node.addChild(widget,label=label)
        expNode['expanded'] = True
        for goal in subset:
##            if goals[goal] > epsilon:
##                goalStr = 'maximize '
##            else:
##                goalStr = 'minimize '
##            goalStr += str(goal.toKey())
            expNode.addChild(widget,label=str(goal),isLeaf=True)
        
    def addEffect(self,element,parent,delta=True):
        """Extracts an effect from an XML element and adds the corresponding subtree to the given parent tree
        @param element: the XML effect description
        @type element: Element
        @param parent: the node to add the effect below
        @type parent: L{Node}
        """
        widget = self.component('Tree')
        if delta:
            node = self.findNode('Effect',parent)
            node.deleteChildren()
        else:
            node = parent
        child = element.firstChild
        while child:
            if child.tagName == 'state':
                self.addStateEffect(child,node)
            elif child.tagName == 'hearer':
                name = str(child.getAttribute('agent'))
                isLeaf=False
                if str(child.getAttribute('decision')) == str(True):
                    label = '%s accept(s) message' % (name)
                else:
                    label = '%s reject(s) message' % (name)
                if str(child.getAttribute('forced')) == str(True):
                    isLeaf=True
                    label += ' (forced)'
                subNode = node.addChild(widget,label=label,isLeaf=isLeaf)
                subChild = child.firstChild
                while subChild:
                    assert subChild.tagName == 'factor'
                    if str(subChild.getAttribute('positive')) == str(True):
                        label = 'sufficient '
                    else:
                        label = 'insufficient '
                    label += str(subChild.getAttribute('type'))
                    subNode.addChild(widget,label=label,isLeaf=True)
                    subChild = subChild.nextSibling
            child = child.nextSibling

    def addStateEffect(self,effect,parent):
        """Describe the effect on the state
        """
        widget = self.component('Tree')
        elements = effect.getElementsByTagName('distribution')
        assert len(elements) == 1
        distribution = Distribution()
        distribution.parse(elements[0],KeyedVector)
        if len(distribution) > 1:
            for row,prob in distribution.items():
                subNode = parent.addChild(widget,label='with probability %5.3f' % (prob))
                for key,value in row.items():
                    if value > 0.0:
                        label = '%s increases by %5.3f' % (str(key),value)
                        subNode.addChild(widget,label=label,isLeaf=True)
                    elif value < 0.0:
                        subNode.addChild(widget,label='%s decreases by %5.3f' % (str(key),-value),isLeaf=True)
                if len(subNode['children']) == 0:
                    subNode.addChild(widget,label='no change',isLeaf=True)
        else:
            row = distribution.expectation()
            for key,value in row.items():
                if value > 0.0:
                    parent.addChild(widget,label='%s increases by %5.3f' % (str(key),value),isLeaf=True)
                elif value < 0.0:
                    parent.addChild(widget,label='%s decreases by %5.3f' % (str(key),-value),isLeaf=True)
            if len(parent['children']) == 0:
                parent.addChild(widget,label='no change',isLeaf=True)

    def confirmAction(self,name,event,agent,option,step):
        msg = 'Would you like to confirm this decision as the desired one?  '\
              'If you would like to specify another option as desired, '\
              'you can now do so by clicking on the alternative '\
              'action below.'
        if tkMessageBox.askyesno('Fitting',msg):
            self['fitCommand'](agent,option,step-1)

    def addSuggestions(self,agent,element,parent):
        widget = self.component('Tree')
        # Display the overall stats regarding objective satisfaction
        total = int(element.getAttribute('objectives'))
        if total == 0:
            # Don't write anything if no objectives
            return
        count = total - int(element.getAttribute('violations'))
        label = 'Satisfied %d / %d objectives' % (count,total)
        root = self.findNode('Satisfied',parent)
        root.deleteChildren()
        root['label'] = label
        child = element.firstChild
        # Extract violations, suggestions, and belief state
        violations = []
        while child:
            if child.tagName == 'objective':
                objective = {'who':str(child.getAttribute('who')),
                             'what':str(child.getAttribute('what')),
                             'how':str(child.getAttribute('how'))}
                suggestions = []
                suggestion = child.firstChild
                while suggestion:
                    assert suggestion.tagName == 'suggestion'
                    values = {}
                    belief = suggestion.firstChild
                    while belief:
                        key = Key()
                        key = key.parse(belief)
                        values[key] = {'min':float(belief.getAttribute('min')),
                                       'max':float(belief.getAttribute('max')),
                                       'key':key,
                                       'violator':agent}
                        belief = belief.nextSibling
                    suggestions.append(values)
                    suggestion = suggestion.nextSibling
                violations.append((objective,suggestions))
            elif child.tagName == 'distribution':
                state = Distribution()
                state.parse(child,KeyedVector)
                state = state.expectation()
            else:
                print 'Unknown tag in suggestions:',child.tagName
            child = child.nextSibling
        # Display the violated objectives
        for objective,suggestions in violations:
            node = root.addChild(widget,label='To satisfy %s %s:' % (objective['how'],objective['what']))
            first = True
            messages = {}
            for suggestion in suggestions:
                # Each suggestion is a conjunction of beliefs
                beliefs = []
                for key,threshold in suggestion.items():
                    if state[key] < threshold['min']:
                        # Generate a message about a belief that is too low
                        if self['expert']:
                            sugg = '%s is greater than %5.3f' % \
                                   (str(key),threshold['min'])
                        elif abs(threshold['min']) < epsilon:
                            sugg = '%s: positive %s' % \
                                   (key['entity'],key['feature'])
                        else:
                            sugg = '%s: increased %s' % \
                                   (key['entity'],key['feature'])
                        suggestion[key]['label'] = sugg
                        beliefs.append(sugg)
                    elif state[key] > threshold['max']:
                        # Generate a message about a belief that is too high
                        if self['expert']:
                            sugg = '%s is less than %5.3f' % \
                                   (str(key),threshold['max'])
                        elif abs(threshold['max']) < epsilon:
                            sugg = '%s: no %s' % \
                                   (key['entity'],key['feature'])
                        else:
                            sugg = '%s: decreased %s' % \
                                   (key['entity'],key['feature'])
                        suggestion[key]['label'] = sugg
                        beliefs.append(sugg)
                if len(beliefs) > 0:
                    if first:
                        first = False
                    else:
                        # Add a separator (not a very attractive one)
                        node.addChild(widget,label=' ',isLeaf=True)
                    for key,args in suggestion.items():
                        if args.has_key('label'):
                            messages[args['label']] = args
                            button = node.addChild(widget,label=args['label'],
                                                   isLeaf=True)
                            if self['msgCommand']:
                                button['action'] = lambda l,e,s=self,o=args:\
                                                s.sendMenu(e,o)
            # Add launcher for campaign analysis
            args = {'violator':agent,
                    'messages':messages.values()}
            node['action'] = lambda l,e,s=self,o=args:s.sendMenu(e,o)
                        
def extractAction(parent):
    """
    @type parent: Element
    @return: the actions in this XML Element
    @rtype: L{Action}[]
    """
    option = []
    element = parent.firstChild
    while element:
        if element.tagName.lower() == 'action':
            action = Action()
            action = action.parse(element)
            option.append(action)
        element = element.nextSibling
    return option

def actionString(option):
    """
    @type option: L{Action}[]
    @return: a string representation of these actions
    @rtype: str
    """
    actions = []
    for action in option:
        if isinstance(action,PsychMessage):
            content = []
            for factor in action['factors']:
                if factor.has_key('matrix'):
                    matrix = factor['matrix'].domain()[0]
                    for key,row in matrix.items():
                        if not isinstance(row,UnchangedRow):
                            content.append('%s: %s' % \
                                           (str(key),row.simpleText()))
            actions.append('sends "%s"' % (', '.join(content)))
        elif action['object']:
            actions.append('%s %s' % (action['type'],
                                      action['object']))
        else:
            actions.append('%s' % (action['type']))

    if len(actions) > 0:
        content = ', '.join(actions)
    else:
        content = 'do nothing'
    return content
