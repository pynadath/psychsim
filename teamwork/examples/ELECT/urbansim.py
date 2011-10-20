import cStringIO
import datetime
import fileinput
import os.path
import sys
import time
#from psychsim_interface import USim_Proxy
from teamwork.math.KeyedVector import KeyedVector
from teamwork.math.Keys import StateKey,LinkKey
from teamwork.action.PsychActions import Action
from teamwork.multiagent.pwlSimulation import loadScenario

floors = {'Economics': -1.,
          'Governance': -1.,
          'HN Security Forces': 0.,
          'Essential Services': 0.,
          'Civil Security': -1.,
          'Information Operations': -1.,
          'Population Support': -1.,
          }

class Strategy:
    """Base class for representing a player strategy.  Executes random actions
    """
    def __init__(self,scenario,horizon=1):
        self.scenario = scenario
        self.horizon = horizon

    def execute(self,t,state):
        return {None:None}

class Replay(Strategy):
    """A strategy that replays a given sequence of actions as stored in a game log
    @ivar turns: the sequence of player moves stored in the log file
    @ivar startTime: the starting time of the game
    @type startTime: C{datetime.datetime}
    @ivar subject: the user name of the subject in this log
    @ivar initialLOE: the LOE the subject chose as the initial priority
    @ivar aggressive: the aggressiveness chosen by the subject
    @cvar ignore: list of message type labels that are ignored when processing game logs
    """

    ignore = ['msg_sys_ready','msg_ui_ready','msg_ready_acknowledged','msg_autosave_game',
              'msg_progress','msg_login','msg_new_turn','msg_hypothetical_turn','msg_tutor_anticipation']
    
    def __init__(self,scenario,filename=None,horizon=1,root='.',output=None,
                 turns=False):
        Strategy.__init__(self,scenario,horizon)
        self.log = []
        self.subject = None
        self.initialLOE = None
        self.aggressive = None
        self.times = []
        self.reset()
        self.filename = filename
        if filename:
            self.extractTurns(filename,root,output,turns)
#             state = scenario.state.expectation()
#             assert len(state) == len(self.history[0]) + 1
#             for key in self.history[0].keys():
#                 assert abs(state[key]-self.history[0][key]) < 1e-8

    def execute(self,t,state):
        return self.turns[t]

    def reset(self):
        self.scenarioName = None
        self.initialMatrix = []
        self.LOEs = []
        self.support = []
        self.startTime = None
        self.startDate = 0
        self.turns = []
        self.history = []
        
    def extractTurns(self,filename,root='.',output=None,turnsOnly=False):
        f = open(os.path.join(root,filename),'r')
        data = unicode(f.read(),errors='ignore')
        f.close()
        messages = data.split('\n========= Msg ')
        for index in range(1,len(messages)): # Skip log header
            # Look at separator for timestamp
            printMe = not turnsOnly
            elements = messages[index].split('\n')
            header = elements[0]
            headerParts = header.split()
            separator = headerParts[0]
            timestamp = headerParts[1]
            content = {'time': datetime.datetime.strptime(timestamp,'%H:%M:%S'),
                       'index': int(separator[1:])}
            if self.startTime is None:
                self.startTime = content['time']
            content['delta'] = content['time']-self.startTime
            assert elements[-1] == ''
            assert elements[-2] == ''
            # Extract XML message
            message = '\n'.join(elements[1:-2])
            doc = minidom.parseString(message.encode('utf-8'))
            assert doc.documentElement.tagName == 'MESSAGE'
            node = doc.documentElement.firstChild
            while node:
                if node.nodeType == node.ELEMENT_NODE:
                    if node.tagName == 'HEADER':
                        # XML message header
                        content['type'] = str(node.getAttribute('msg_type'))
                        assert content['type']
                        content['sender'] = str(node.getAttribute('sender'))
                        assert content['sender']
                        content['receiver'] = str(node.getAttribute('receiver'))
                        assert content['receiver']
                        misc = str(node.getAttribute('misc'))
                        if content['type'] == 'msg_exit_instanced_game':
                            # Quit so reset everything
                            self.reset()
                    elif node.tagName == 'PLAYER':
                        # Extract subject name
                        name = str(node.getAttribute('NAME'))
                        if name:
                            if self.subject is None:
                                self.subject = name
                            else:
                                assert name == self.subject
                    elif node.tagName == 'SCENARIO':
                        # Extract scenario name
                        if content['type'] == 'msg_load_scenario':
                            if self.scenarioName is None:
                                if misc:
                                    self.scenarioName = misc
                            elif misc:
                                assert misc == self.scenarioName,'%s != %s' % (misc,self.scenarioName)
                    elif node.tagName == 'LOE_EFFECT':
                        if content['type'] != 'msg_load_game':
                            # Extract initial LOEs
                            if len(self.LOEs) == 0 or content['index'] != self.LOEs[-1]['index']:
                                self.LOEs.append({'index': content['index']})
                            name = str(node.getAttribute('LOE_ID'))
                            self.LOEs[-1][name] = float(node.getAttribute('ACTUAL'))
                    elif node.tagName == 'WORLD_STATE':
                        if content['type'] in ['msg_sync_matrix_edit',
                                               'msg_sync_matrix_move',
                                               'msg_assess_performance',
                                               'msg_load_game']:
                            # Extract SYNCMATRIX element
                            child = node.firstChild
                            while child:
                                if child.nodeType == child.ELEMENT_NODE \
                                   and child.tagName == 'SYNCMATRIX':
                                    if len(self.initialMatrix) == 0:
                                        # Extract initial sync matrix
                                        self.parseMatrix(child)
                                        if len(self.initialMatrix) > 0:
                                            self.times.append(content['time'])
                                        for t in range(self.startDate):
                                            self.initialMatrix.insert(0,{})
                                        content['move'] = None
                                    else:
                                        # Extract move
                                        content['move'] = []
                                        content['dayAdd'],content['dayDel'] = self.parseMatrix(child,False,content['move'])
                                        if content['move'] and len(content['move'][0]) == 8:
                                            if content['sender'] == 'ui':
                                                # New sync matrix
                                                result = self.classifyMatrix(content['move'])
                                                if result != [self.initialLOE,self.aggressive]:
                                                    content['move'] = None
                                                    self.initialLOE = result[0]
                                                    self.aggressive = result[1]
                                        else:
                                            # Editing of matrix
                                            for t in range(len(content['move'])):
                                                content['move'][t] = ','.join(map(lambda tup: self.scenario[tup[0]].makeActionKey(tup[1]),
                                                                                  content['move'][t].items()))
                                elif child.nodeType == child.ELEMENT_NODE \
                                     and child.tagName == 'SCENARIO':
                                    grandchild = child.firstChild
                                    while grandchild:
                                        if grandchild.nodeType == child.ELEMENT_NODE \
                                           and grandchild.tagName == 'MISSION':
                                            break
                                        grandchild = grandchild.nextSibling
                                    grandchild = grandchild.firstChild
                                    LOEs = {'index': content['index']}
                                    while grandchild:
                                        if grandchild.nodeType == child.ELEMENT_NODE \
                                           and grandchild.tagName == 'POP_SUPPORT':
                                            # Popular support
                                            support = {}
                                            support['against'] = float(grandchild.getAttribute('AGAINST'))
                                            support['for'] = float(grandchild.getAttribute('FOR'))
                                            support['neutral'] = float(grandchild.getAttribute('NEUTRAL'))
                                            if len(self.support) == len(self.turns):
                                                self.support.append(support)
##                                            else:
##                                                assert support == self.support[-1]
                                        elif grandchild.nodeType == child.ELEMENT_NODE \
                                             and grandchild.tagName == 'LOE':
                                            # Find LOE values
                                            name = str(grandchild.getAttribute('LOE_ID'))
                                            LOEs[name] = float(grandchild.getAttribute('PROGRESS'))
                                        grandchild = grandchild.nextSibling
                                    if len(self.LOEs) == len(self.turns):
                                        self.LOEs.append(LOEs)
                                child = child.nextSibling
                        elif content['type'] == 'msg_sync_matrix_clear':
                            if len(self.initialMatrix) > 0:
                                self.initialMatrix = map(lambda t: {},range(15))
                    elif node.tagName == 'PROGRESS':
                        content['percent'] = int(node.getAttribute('PERCENTCOMPLETE'))
                    elif node.tagName == 'GAME_OBJECT':
                        if content['type'] == 'msg_allowable_actions' or \
                               content['type'] == 'msg_select_subject':
                            content['entity'] = str(node.getAttribute('NAME'))
                    elif node.tagName == 'TUTOR_REVIEW':
                        content['review'] = str(node.getAttribute('TYPE'))
                    elif node.tagName == 'GAME_STATE':
                        if content['type'] == 'msg_load_game':
                            child = node.firstChild
                            while child:
                                if child.nodeType == child.ELEMENT_NODE and \
                                       child.tagName == 'WORLD_STATE':
                                    break
                                child = child.nextSibling
                            child = child.firstChild
                            while child:
                                if child.nodeType == child.ELEMENT_NODE and \
                                       child.tagName == 'SCENARIO':
                                    start = int(str(child.getAttribute('START_DATE'))[-2:])
                                    now = int(str(child.getAttribute('GAME_DATE'))[-2:])
                                    if now > start:
                                        # Loaded mid-game
                                        self.startDate = now-start
                                child = child.nextSibling
                    elif node.tagName == 'ASSESSMENT':
                        LOE = {'index': content['index']}
                        for child in node.getElementsByTagName('LOE'):
                            name = str(child.getAttribute('LOE_ID'))
                            value = float(child.getAttribute('PROGRESS'))
                            LOE[name] = int(100.*(value-floors[name])/(1.-floors[name]))
                        self.LOEs.append(LOE)
                    elif node.tagName == 'GAMETURN':
                        content['day'] = int(node.getAttribute('GAMETURN_ID'))
                        if content['receiver'] == 'behaviorengine':
                            # Ignore a second game in the same log
                            self.turns.append({})
                            frago,delete = self.parseMove(node)
                            if self.startDate == 0:
                                original = self.initialMatrix[content['day']-1]
                            else:
                                original = {}
                            for name,option in frago.items():
                                assert len(option) == 1
                                if option[0]['object']:
                                    key = '%s:%s:%s' % (option[0]['actor'],option[0]['type'],option[0]['object'])
                                else:
                                    key = '%s:%s' % (option[0]['actor'],option[0]['type'])
                                if not original.has_key(name):
                                    # Assigned previously unassigned agent
                                    self.turns[-1][name] = (None,key)
                                elif key != original[name]:
                                    self.turns[-1][name] = (original[name],key)
                                self.times.append(content['time'])
                        elif content['type'] == 'msg_new_turn':
                            # Updated game state
                            child = node.firstChild
                            while child:
                                if child.nodeType == child.ELEMENT_NODE and \
                                   child.tagName == 'CYCLE':
                                    # Find LOE values
                                    LOEs = {'index': content['index']}
                                    for grandchild in child.getElementsByTagName('LOE'):
                                        name = str(grandchild.getAttribute('LOE_ID'))
                                        LOEs[name] = float(grandchild.getAttribute('PROGRESS'))
                                    self.LOEs.append(LOEs)
                                    # Popular support
                                    for grandchild in child.getElementsByTagName('POP_SUPPORT'):
                                        support = {}
                                        support['against'] = float(grandchild.getAttribute('AGAINST'))
                                        support['for'] = float(grandchild.getAttribute('FOR'))
                                        support['neutral'] = float(grandchild.getAttribute('NEUTRAL'))
                                        if len(self.support) == len(self.turns):
                                            self.support.append(support)
                                        break
                                child = child.nextSibling
                node = node.nextSibling
            self.log.append(content)
            if output and not content['type'] in self.ignore:
                # Print out readable version of this message
                rest = None
                if content['type'] == 'msg_load_scenario':
                    if content['sender'] == 'ui':
                        rest = 'load_scenario, %s' % (self.scenarioName)
                elif content['type'] == 'msg_allowable_actions':
                    if content['sender'] == 'ui':
                        rest = 'select_entity, %s' % (content['entity'])
                elif content['type'] == 'msg_sync_matrix_clear':
                    if content['sender'] == 'ui':
                        rest = 'clear_sync_matrix'
                elif content['type'] == 'msg_select_subject':
                    if content.has_key('entity'):
                        rest = 'select_unit, %s' % (content['entity'])
                elif content['type'] == 'msg_sync_matrix_edit':
                    if content['move'] is None:
                        rest = 'initial_sync_matrix, %s, %s' % (self.initialLOE,self.aggressive)
#                        printMe = True
                    elif content['move'] and content['sender'] == 'gamecontroller':
                        while len(content['move']) > 1:
                            if content['move'][-1] != content['move'][0]:
                                rest = 'load_sync_matrix?'
                                break
                            content['move'].pop()
                        if rest is None:
                            # Single edit of sync matrix
                            if content['dayDel']:
                                if content['dayAdd']:
                                    rest = 'move_sync_matrix, %d, %d, %s' % (content['dayDel'],content['dayAdd'],content['move'][0])
                                else:
                                    rest = 'remove_sync_matrix, %d, %s' % (content['dayDel'],content['move'][0])
                            else:
                                rest = 'add_sync_matrix, %d, %s' % (content['dayAdd'],content['move'][0])
#                    else:
#                         rest ='edit_sync_matrix'
                elif content['type'] == 'msg_sync_matrix_move':
                    pass
##                    while len(content['move']) > 1:
##                        assert content['move'][-1][0] == content['move'][0][0]
##                        content['move'].pop()
##                    rest = 'move_sync_matrix, %d, %d, %s' % \
##                           (content['dayDel'],content['dayAdd'],content['move'][0])
                elif content['type'] == 'msg_commit_turn':
                    if content['sender'] == 'gamecontroller':
                        rest = 'commit_turn, %d' % (content['day'])
#                        assert len(self.LOEs) == len(self.support) == len(self.turns),'%s:%d' % (self.filename,content['index'])
                        # Add popular support
                        support = self.support[-1]
                        rest = '%s,%s:%s' % (rest,''.join(map(lambda k: k.capitalize(),support.keys())),
                                             ':'.join(map(lambda k: '%d' % (int(support[k]*100.)),support.keys())))
                        # Add LOEs
                        score = filter(lambda t: t[0] !='index',self.LOEs[-1].items())
                        score.sort()
                        score = map(lambda s: '%s:%d' % (s[0],int(100.*(s[1]-floors[s[0]])/(1.-floors[s[0]]))),score)
                        rest = '%s,%s' % (rest,';'.join(score))
                        # Add moves
                        moves = map(lambda t: t[1],self.turns[-1].values())
                        moves.sort()
                        rest = '%s,%s' % (rest,';'.join(moves))
#                        printMe = True
                elif content['type'] == 'msg_assess_performance':
                    printMe = True
                    rest = 'assess_performance,'
                    # Add popular support
                    support = self.support[-1]
                    rest = '%s,%s:%s' % (rest,''.join(map(lambda k: k.capitalize(),support.keys())),
                                         ':'.join(map(lambda k: '%d' % (int(support[k]*100.)),support.keys())))
                    # Add LOEs
                    score = filter(lambda t: t[0] !='index',self.LOEs[-1].items())
                    score.sort()
                    score = map(lambda s: '%s:%d' % (s[0],s[1]),score)
                    rest = '%s,%s' % (rest,';'.join(score))
                elif 'missionplan' in content['type']:
                    if content['sender'] == 'ui':
                        rest = content['type'][4:]
                elif content['type'] in ['msg_track_moe','msg_request_humint',
                                         'msg_exit_instanced_game','msg_quit']:
                    if content['sender'] == 'ui':
                        rest = content['type'][4:]
                elif content['type'] == 'msg_request_review':
                    if content['sender'] == 'ui' and content['review']:
                        rest = 'request_tutor, %s' % (content['review'])
                else:
                    if content['sender'] == 'ui':
                        rest = content['type']
                if rest and printMe:
                    print self.filename,
                    output = None
                    print >> output,'%4d,' % (content['index']),
                    print >> output,'%3d:%02d,' % (content['delta'].seconds/60,content['delta'].seconds%60),
                    print >> output,rest
#        assert self.subject
#        assert len(self.turns) == 15,"%d turns in %s" % (len(self.turns),filename)
#        assert self.initialLOE
#        assert self.aggressive
#        assert len(self.initialMatrix) == 15
        return

    def parseMatrix(self,root,output=False,matrix=None):
        """
        @param output: if C{True}, then print matrix to standard output and exit
        """
        if matrix is None:
            matrix = self.initialMatrix
        day = root.firstChild
        firstAdd = None
        firstDel = None
        while day:
            if day.nodeType == day.ELEMENT_NODE and \
               day.tagName == 'DATES':
                t = int(day.getAttribute('DAY'))
                frago,delete = self.parseMove(day)
                if frago:
                    if delete:
                        if firstDel is None:
                            firstDel = t
                    elif firstAdd is None:
                        firstAdd = t
                    matrix.append(frago)
            day = day.nextSibling
        # Optional matrix dump to standard output
        if output and self.initialMatrix:
            print self.matrix2str()
            sys.exit(0)
        if matrix is self.initialMatrix:
            # Classify starting objective
            self.initialLOE,self.aggressive = self.classifyMatrix(matrix)
        return firstAdd,firstDel

    def classifyMatrix(self,sync):
        matrix = self.matrix2str(sync)
        for name in os.listdir('Syncs'):
            f = open(os.path.join('Syncs',name),'r')
            data = f.read()
            f.close()
            if data == matrix:
                assert name[-4:] == '.txt'
                return name[:-4].split('-')
        else:
            return None,None
        
    def matrix2str(self,matrix=None):
        """Generates a canonical string representation of the initial sync matrix
        """
        if matrix is None:
            matrix = self.initialMatrix
        buf = cStringIO.StringIO()
        for frago in matrix:
            names = frago.keys()
            names.sort()
            for name in names:
                option = frago[name]
                print >> buf,name,self.scenario[name].makeActionKey(option)
            print >> buf
        content = buf.getvalue()
        buf.close()
        return content

    def parseMove(self,node):
        """Get a set of playermoves from a turn or matrix day node
        """
        frago = {}
        move = node.firstChild
        delete = None
        while move:
            if move.nodeType == move.ELEMENT_NODE and \
               move.tagName == 'PLAYERMOVE':
                verb = str(move.getAttribute('VERB1'))
                if verb:
                    # Action assigned to this agent
                    agent = self.scenario[str(move.getAttribute('SUBJECT'))]
                    obj = str(move.getAttribute('OBJECT'))
                    if len(obj) == 0:
                        obj = None
                    if delete is None:
                        delete = str(move.getAttribute('DELETE')).lower() == 'true'
                    for option in agent.actions.getOptions():
                        assert len(option) == 1
                        if option[0]['type'] == verb and \
                           option[0]['object'] == obj:
                            frago[agent.name] = option
                            break
                    else:
                        sys.stderr.write('Unable to find action %s %s for %s\n' % (verb,obj,agent.name))
            move = move.nextSibling
        return frago,delete
        
    def oldextraction(self,filename):
        data = None
        vector = KeyedVector()
        for line in fileinput.input(filename):
            if line[:8] == '========':
                # New message
                if not data is None:
                    print data
                    doc = minidom.parseString(data)
                    child = doc.documentElement.firstChild
                    while child:
                        if child.nodeType == child.ELEMENT_NODE:
                            if child.tagName == 'HEADER':
                                sender = child.getAttribute('sender')
                                receiver = child.getAttribute('receiver')
                                msgType = child.getAttribute('msg_type')
                            elif sender == 'behaviorengine':
                                if child.tagName == 'GAME_OBJECT':
                                    name = str(child.getAttribute('NAME'))
                                    assert self.scenario.has_key(name),'Scenario missing: %s' % (name)
                                    for element in child.getElementsByTagName('STATE_FEATURE'):
                                        feature = element.getAttribute('NAME')
                                        value = float(element.getAttribute('VALUE'))
                                        object = str(element.getAttribute('OBJECT'))
                                        if object:
                                            key = LinkKey({'subject': name,
                                                           'verb': feature,
                                                           'object': object})
                                        else:
                                            key = StateKey({'entity': name,
                                                            'feature':feature})
                                            vector[key] = value
                            elif sender == 'gamecontroller' and \
                                    receiver == 'behaviorengine':
                                if msgType == 'msg_commit_turn' and \
                                        child.tagName == 'GAMETURN':
                                    # Reset current state
                                    self.history.append(vector)
                                    vector = KeyedVector()
                                    sys.stderr.write('%d\n' % (len(self.turns)))
                                    step = {}
                                    for move in child.getElementsByTagName('PLAYERMOVE'):
                                        actor = str(move.getAttribute('SUBJECT'))
                                        verb = str(move.getAttribute('VERB1'))
                                        obj = str(move.getAttribute('OBJECT'))
                                        if obj:
                                            action = Action({'actor':actor,
                                                             'type':verb,
                                                             'object':obj})
                                        else:
                                            action = Action({'actor':actor,
                                                             'type':verb})
                                        step[actor] = action
                                    for cycle in child.getElementsByTagName('CYCLE'):
                                        for event in cycle.getElementsByTagName('STORY_EFFECT'):
                                            sys.stderr.write('%s\n' % event.getAttribute('EVENT_TITLE'))
                                    self.turns.append(step)
                        child = child.nextSibling
                data = ''
            elif not data is None and line[:5] != '<?xml': # Hack!
                data += line.strip()
        fileinput.close()

class ClearHoldBuild(Strategy):
    """A strategy consisting of a sequence of Clear-Hold-Build phases in some order
    @cvar categories: mapping from verbs to a list of Clear-Hold-Build categories which the verb fits under (C{None} means that the verb fits under all three)
    @type categories: strS{->}str[]
    @ivar actionClasses
    """
    categories = {
        'do nothing': [],
        'Advise': ['Hold', 'Build'],
        'Arrest Person':  None,
        'Attack Group': ['Clear'],
        'Attack Structure': ['Clear'],
        'Construct': ['Build'],
        'Cordon and Search': ['Clear'],
        'Cordon and Knock': ['Clear'],
        'Dispatch Individual': ['Clear'],
        'Give Gift': None,
        'Give Propaganda': None,
        'Host Meeting': None,
        'Information Engagement': None,
        'Joint Investigate':  ['Hold'],
        'Patrol Neighborhood': None,
        'Pay': None,
        'Recruit Soldiers': ['Hold', 'Build'],
        'Recruit Police': ['Hold', 'Build'],
        'Release Person': None,
        'Remove': ['Clear', 'Hold'],
        'Repair': ['Build'],
        'Seize Structure': ['Clear'],
        'Set up Checkpoint': ['Clear', 'Hold'],
        'Support Politically': None,
        'Treat Wounds/Illnesses': None,
    }

    def __init__(self,scenario,specString='chb',horizon=1):
        """
        @param specString: a specification of the strategy as a sequence of Clear-Hold-Build phases, each indicated by the first letter of the phase name (e.g., "chb" indicates a Clear-Hold-Build strategy
        @type specString: str
        """
        Strategy.__init__(self,scenario,horizon)
        self.specString = specString
        self.actionClasses = self.categorize()

    def categorize(self):
        """Sort actions into clear-hold-build
        """
        actionClasses = {}
        actionClasses['c'] = {}
        actionClasses['h'] = {}
        actionClasses['b'] = {}
        actionClasses['*'] = {}
        missing = {}
        for agent in filter(lambda a: a.instanceof('Player'),self.scenario.members()):
            for table in actionClasses.values():
                table[agent.name] = []
            actionClasses['*'][agent.name] = agent.actions.getOptions()[:]
            for option in agent.actions.getOptions():
                assert len(option) == 1,'Unable to handle joint actions'
                try:
                    classification = self.categories[option[0]['type']]
                except KeyError:
                    missing[option[0]['type']] = True
                    continue
                if classification is None:
                    classification = ['c','h','b']
                for key in classification:
                    category = key[0].lower()
                    actionClasses[category][agent.name].append(option)
        if len(missing) > 0:
            sys.stderr.write('Unclassified verbs: %s\n' % (missing.keys()))
        return actionClasses

    def execute(self,t,state):
        category = self.specString[t*len(self.specString)/self.horizon].lower()
        return self.actionClasses[category]

def parsePrecondition(root):
    conditions = []
    node = root.firstChild
    while node:
        if node.nodeType == node.ELEMENT_NODE:
            if node.tagName == 'USER_ACTION_PRECONDITION':
                conditions.append({'type': 'action',
                                   'subject': str(node.getAttribute('SUBJECT')),
                                   'verb': str(node.getAttribute('VERB1')),
                                   'object': str(node.getAttribute('OBJECT'))})
            elif node.tagName == 'WORLD_STATE_PRECONDITION':
                if str(node.getAttribute('OPERATOR')) == 'LESSTHAN':
                    test = lambda value,threshold=float(node.getAttribute('VALUE')):\
                           value < threshold
                elif str(node.getAttribute('OPERATOR')) == 'GREATERTHAN':
                    test = lambda value,threshold=float(node.getAttribute('VALUE')):\
                           value > threshold
                elif str(node.getAttribute('OPERATOR')) == 'EQUAL':
                    test = lambda value,threshold=float(node.getAttribute('VALUE')):\
                           value == threshold
                else:
                    raise ValueError,'Unknown operator: %s' % (str(node.getAttribute('OPERATOR')))
                condition = {'type': 'state',
                             'key': StateKey({'entity': str(node.getAttribute('SUBJECT')),
                                              'feature': str(node.getAttribute('ATTRIBUTE'))}),
                             'test': test}
                if len(condition['key']['entity']) == 0:
                    # Tied to class, not specific entity
                    nodeList = node.getElementsByTagName('CLASS')
                    assert len(nodeList) == 1,'Multiple CLASS elements in WORLD_STATE_PRECONDITION'
                    condition['key']['entity'] = str(nodeList[0].firstChild.data).strip()
                conditions.append(condition)
            elif node.tagName == 'TIME_PRECONDITION':
                condition = {'type': 'time'}
                child = node.firstChild
                while child:
                    if child.nodeType == child.ELEMENT_NODE:
                        if child.tagName == 'EXACT_DATE':
                            start = datetime.date(2008,10,10)
                            year,month,day = map(int,str(child.firstChild.data).split('-'))
                            condition['day'] = (datetime.date(year,month,day)-start).days
                        elif child.tagName == 'RELATIVE_EVENT':
                            condition['day'] = int(child.getAttribute('DAYS'))
                            condition['event'] = str(child.firstChild.data)
                        else:
                            raise NameError,'Unknown time precondition: %s' % (child.tagName)
                    child = child.nextSibling
                conditions.append(condition)
            else:
                raise NameError,'Unknown precondition: %s' % (node.tagName)
        node = node.nextSibling
    return conditions

def parseEffect(root):
    effects = []
    node = root.firstChild
    while node:
        if node.nodeType == node.ELEMENT_NODE:
            effect = {'feature': str(node.getAttribute('FEATURE'))}
            if node.tagName == 'ABSOLUTE_EFFECT':
                effect['value'] = float(node.getAttribute('VALUE'))
            elif node.tagName == 'RELATIVE_EFFECT':
                effect['delta'] = float(node.getAttribute('DELTA'))
            else:
                raise NameError,'Unknown effect type: %s' % (node.tagName)
            child = node.firstChild
            while child:
                if child.nodeType == child.ELEMENT_NODE:
                    if child.tagName == 'EFFECT_SUBJECT':
                        effect['subject'] = str(child.getAttribute('SUBJECT'))
                    elif child.tagName == 'EFFECT_COLOCATION':
                        location = str(child.getAttribute('EXACT_LOCATION')).strip().upper()
                        if location:
                            assert location == 'ANYWHERE','Unknown location: %s' % (location)
                    else:
                        raise NameError,'Unknown effect field: %s' % (child.tagName)
                child = child.nextSibling
            effects.append(effect)
        node = node.nextSibling
    return effects

def parseEvent(root):
    event = {'fired': -1}
    node = root.firstChild
    while node:
        if node.nodeType == node.ELEMENT_NODE:
            if node.tagName == 'PRECONDITIONS':
                event['preconditions'] = parsePrecondition(node)
            elif node.tagName == 'EFFECTS':
                event['effects'] = parseEffect(node)
        node = node.nextSibling
    return event
        
def parseStories(filename,scenario):
    try:
        doc = minidom.parse(filename)
    except IOError:
        sys.stderr.write('Unable to parse story file: %s\n' % (filename))
        return {}
    stories = {}
    node = doc.documentElement.firstChild
    while node.nodeType != node.ELEMENT_NODE or \
            node.tagName.lower() != 'arrayofstory':
        node = node.nextSibling
    node = node.firstChild
    while node:
        if node.nodeType == node.ELEMENT_NODE:
            assert node.tagName == 'STORY'
            if str(node.getAttribute('SCENARIO_ID')) == scenario:
                story = str(node.getAttribute('STORY_TITLE'))
                assert not stories.has_key(story)
                stories[story] = {}
                child = node.firstChild
                while child:
                    if child.nodeType == node.ELEMENT_NODE:
                        assert child.tagName == 'EVENT'
                        event = str(child.getAttribute('EVENT_TITLE'))
                        assert not stories[story].has_key(event)
                        stories[story][event] = parseEvent(child)
                    child = child.nextSibling
        node = node.nextSibling
    return stories

def applyStories(stories,scenario,day,player,doc):
    root = doc.documentElement.firstChild
    while root:
        if root.nodeType == root.ELEMENT_NODE:
            if root.tagName == 'GAMETURN':
                break
        root = root.nextSibling
    # Potential story effects go here
    cycle = doc.createElement('CYCLE')
    cycle.setAttribute('CYCLE_ID','0')
    cycle.setAttribute('LETHAL','0')
    cycle.setAttribute('NONLETHAL','0')
    root.appendChild(cycle)
    # Find out which stories fire
    state = scenario.state.expectation()
    for storyTitle,story in stories.items():
        for eventTitle,event in story.items():
            if event['fired'] < 0:
                substitution = {}
                # Story events cannot fire twice
                for condition in event['preconditions']:
                    if condition['type'] == 'state':
                        # Does any entity of this class meet the condition?
                        for entity in filter(lambda e: e.instanceof(condition['key']['entity']),
                                             scenario.members()):
                            key = StateKey(condition['key'])
                            key['entity'] = entity.name
                            try:
                                match = condition['test'](state[key])
                            except KeyError:
                                sys.stderr.write('Unknown state feature: %s\n' % (key))
                                continue
                            if match:
                                if entity.name != condition['key']['entity']:
                                    # Record which instance generated the match
                                    if substitution.has_key(condition['key']['entity']):
                                        assert substitution[condition['key']['entity']] == entity.name,\
                                               'Ambiguous match of event preconditions'
                                    substitution[condition['key']['entity']] = entity.name
                                break
                        else:
                            # Nope
                            break
                    elif condition['type'] == 'action':
                        # Does any player move match the desired condition?
                        for subject,action in player.items():
                            if subject and scenario[subject].instanceof(condition['subject']):
                                if action['type'] == condition['verb'] and \
                                   action['object'] == condition['object']:
                                    # Match
                                    if subject != condition['subject']:
                                        # Record which instance generated the match
                                        if substitution.has_key(condition['subject']):
                                            assert substitution[condition['subject']] == subject,\
                                                   'Ambiguous match of event preconditions'
                                        substitution[condition['subject']] = subject
                                    break
                        else:
                            # Nope
                            break
                    elif condition['type'] == 'time':
                        # Are we on the right day?
                        target = condition['day']
                        if condition.has_key('event'):
                            if story[condition['event']]['fired'] < 0:
                                # Prerequisite event has not occurred
                                break
                            # Add delta to when prerequisite event occurred
                            target += story[condition['event']]['fired']
                        if day != target:
                            # Nope
                            break
                    else:
                        sys.stderr.write('Unhandled condition: %s\n' % (str(condition)))
                else:
                    event['fired'] = day
                    sys.stderr.write('Story firing: %s\nEvent: %s\n' % (storyTitle,eventTitle))
                    for effect in event['effects']:
                        node = doc.createElement('STORY_EFFECT')
                        cycle.appendChild(node)
                        key = StateKey({'entity': effect['subject'],
                                        'feature': effect['feature']})
                        if not state.has_key(key):
                            if substitution.has_key(effect['subject']):
                                key = StateKey({'entity': substitution[effect['subject']],
                                                'feature': effect['feature']})
                                if not state.has_key(key):
                                    key = None
                            else:
                                key = None
                        keys = []
                        if key is None:
                            keys = filter(lambda k: isinstance(k,StateKey),state.keys())
                            keys = filter(lambda k: k['feature'] == effect['feature'],keys)
                            keys = filter(lambda k: scenario[k['entity']].instanceof(effect['subject']),keys)
                        else:
                            keys.append(key)
                        assert len(keys) > 0
                        for key in keys:
                            assert state.has_key(key),'Unknown feature: %s' % (key)
                            child = doc.createElement('EFFECT')
                            node.appendChild(child)
                            child.setAttribute('SUBJECT',str(key['entity']))
                            child.setAttribute('FEATURE',str(key['feature']))
                            try:
                                child.setAttribute('DELTA',str(effect['delta']))
                            except KeyError:
                                try:
                                    child.setAttribute('DELTA',str(effect['value']-state[key]))
                                except KeyError:
                                    raise NotImplementedError,'Unable to determine story effect: %s' % (str(effect))
    
if __name__ == '__main__':
    try:
        from numpy.core.numeric import array
        from numpy.matlib import std
    except ImportError:
        from Numeric import array
        std = None
    from optparse import OptionParser
    from xml.dom import minidom

    parser = OptionParser()
    # Optional argument that sets the location of the scenario
    parser.add_option('--scenario',action='store',type='string',
                      dest='scenario',default='AlHamra3.xml.bz2',
                      help='scenario file [default: %default]')
    # Optional argument that sets the location of the society
    parser.add_option('--society',action='store',type='string',
                      dest='society',default='alhamra_1-303CAV/alhamra_1-303CAV.soc',
                      help='society file [default: %default]')
    # Optional argument that sets the number of iterations
    parser.add_option('-i','--iterations',action='store',
                      dest='iterations',type='int',default=1,
                      help='number of iterations to run [default: %default]')
    # Optional argument that sets the number of days per iteration
    parser.add_option('--horizon',action='store',
                      dest='horizon',type='int',default=15,
                      help='number of days to simulate per iteration [default: %default]')
    # Optional argument that sets the player strategy to simulate
    parser.add_option('--strategy',action='store',type='string',
                      dest='strategy',default=None,
                      help='Player strategy to test (e.g., "chb")')
    # Optional argument that specifies a game log to replay
    parser.add_option('--replay',action='store',type='string',
                      dest='replay',default=None,
                      help='Game log to replay')
    # Optional argument for extracting turns
    parser.add_option('--turns',action='store_true',
                      dest='turns',default=False,
                      help='Extract only committed turns from log [default: %default]')
    (options, args) = parser.parse_args()
    scenario = loadScenario(options.scenario)
#     table = {}
#     for agent in filter(lambda e: e.instanceof('Player'),scenario.members()):
#         for option in agent.actions.getOptions():
#             assert len(option) == 1
#             if scenario[option[0]['object']].getState('Legal Object').expectation() < 0.5:
#                 sys.stderr.write('%s\n' % (agent.makeActionKey(option)))
#                 continue
#             try:
#                 entry = table[option[0]['type']]
#             except KeyError:
#                 entry = {}
#                 table[option[0]['type']] = entry
#             try:
#                 subentry = entry[agent.classes[0]]
#             except KeyError:
#                 subentry = {}
#                 entry[agent.classes[0]] = subentry
#             subentry[scenario[option[0]['object']].classes[0]] = True
#     for verb in table.keys():
#         for actor,objects in table[verb].items():
#             for obj in objects.keys():
#                 print '%s,%s,%s' % (actor,verb,obj)
#     sys.stderr.write('Load %s\n' % (options.scenario))
#     sys.exit(0)
    names = {'first': 1, 'second': 2, 'third': 3,
             'fourth': 4, 'fifth': 5}
    first = True
    files = os.listdir('logs')
    for name in files:
        if name[-4:] == '.log':
            output = open('processed/%s.csv' % (name[:-4]),'w')
            print >> output,'  # ,   Time, Type, Content'
            strategy = Replay(scenario,name,options.horizon,'logs',output,
                              options.turns)
            output.close()
            assert name[:len(strategy.subject)] == strategy.subject,'%s filename does not match subject name %s' % (name,strategy.subject)
            elements = name[len(strategy.subject):-4].split('.')
            assert len(elements[0]) == 0
            assert elements[1][-3:] == 'run',name
            number = names[elements[1][:-3]]
            empty = len(elements) == 3
            changes = sum(map(len,strategy.turns))
            try:
                duration = strategy.times[-1] - strategy.times[0]
                finalScore = strategy.LOEs[-1]
                LOEs = finalScore.keys()
                LOEs.sort()
                scores = ','.join(map(lambda loe: '%d' % (100.*finalScore[loe]),LOEs))
            except IndexError:
                duration = 'crash'
                LOEs = ['LOEs']
                scores = 'crash'
            if first:
#                print 'Subject,Run,Empty,LOE,Aggressive,Changes,Time,%s' % (','.join(LOEs))
                first = False
#            print '%s,%s,%s,%s,%s,%d,%s,%s' % (strategy.subject,number,empty,strategy.initialLOE,strategy.aggressive,changes,duration,scores)
            sys.stdout.flush()
#            sys.exit(-1)
    sys.exit(0)
#    # Create UrbanSim proxy
#    proxy = USim_Proxy()
#    proxy.root = os.environ['HOME']
#    try:
#        os.stat(os.path.join(proxy.root,'UrbanSim'))
#        proxy.root = os.path.join(proxy.root,'UrbanSim','Builds','working','urbansim','data')
#    except OSError:
#        os.stat(os.path.join(proxy.root,'workspace','UrbanSim'))    
#        proxy.root = os.path.join(proxy.root,'workspace','UrbanSim','data')
#    proxy.loadScenario(options.scenario)
#    if proxy.society is None:
#        proxy.loadSociety(options.society)
    stories = parseStories(os.path.join(proxy.root,'scenarios',options.scenario,
                                        'Stories.xml'),options.scenario)
    history = {}
    player = {}
    strategy = None
    # Print out headings
    line = ['Iteration','Feature']
    line += sum(map(lambda x: ['mean(%d)' % (x),'std(%d)' % (x)],
                    range(options.horizon+1)),[])
    line.append('mean(delta)')
    line.append('std(delta)')
#    print ','.join(line)
    for iteration in range(options.iterations):
        start = time.time()
        proxy.loadScenario(options.scenario)
        if proxy.society is None:
            proxy.loadSociety(options.society)
        sys.stderr.write('Load %s: %d s\n' % (options.scenario,int(time.time()-start)))
        assert len(proxy.scenario) > 0,'Unable to load %s scenario' % (options.scenario)
        if strategy is None:
            if options.replay:
                strategy = Replay(proxy.scenario,options.replay,options.horizon)
            elif options.strategy:
                strategy = ClearHoldBuild(proxy.scenario,options.strategy,options.horizon)
            else:
                strategy = Strategy(proxy.scenario,options.horizon)
        # Set up record of simulation history
        state = proxy.scenario.state.expectation()
        loes = {}
        proxy.evaluateLOEs(state,loes)
        for key,value in loes.items():
            try:
                history[proxy.LOEs[key]['name']][0].append(value)
            except KeyError:
                history[proxy.LOEs[key]['name']] = [[value]]
        for t in range(options.horizon):
            sys.stderr.write('%d\n' % (t))
            state = proxy.scenario.state.expectation()
            # Generate player actions
            player.clear()
            player.update(strategy.execute(t,state))
            print player
            # Process day
            start = time.time()
            doc = proxy.generateTurn('commit',1,player=player)
            start = time.time()
            applyStories(stories,proxy.scenario,t,player,doc)
            for actor,option in player.items():
                if actor:
                    try:
                        history[actor][t].append(option)
                    except IndexError:
                        history[actor].append([option])
                    except KeyError:
                        history[actor] = [[option]]
            start = time.time()
            proxy.onMessage(doc.toxml())
            state = proxy.scenario.state.expectation()
            # Calculate scores
            proxy.evaluateLOEs(state,loes)
            for key,value in loes.items():
                try:
                    history[proxy.LOEs[key]['name']][t+1].append(value)
                except IndexError:
                    history[proxy.LOEs[key]['name']].append([value])
        # Calculate LOE deltas
        for loe in proxy.LOEs:
            delta = history[loe['name']][options.horizon][-1] - history[loe['name']][0][-1]
            try:
                history[loe['name']][options.horizon+1].append(delta)
            except IndexError:
                history[loe['name']].append([delta])
    # Print out LOE history
    for loe in proxy.LOEs:
        line = ['n/a',loe['name']]
        for t in range(options.horizon+2):
            values = history[loe['name']][t]
            line += ['%8.3f' % (sum(values)/float(options.iterations)),
                     '%8.3f' % (std(array(values)))]
        print ','.join(line)
    # Print player moves
    players = map(lambda a: a.name,filter(lambda a: a.instanceof('Player'),
                                          proxy.scenario.members()))
    players.sort()
    for iteration in range(options.iterations):
        for actor in players:
            line = [str(iteration),actor]
            for t in range(options.horizon):
                option = history[actor][t][iteration]
                line.append('%s,%s' % (option['type'],option['object']))
            print ','.join(line)
