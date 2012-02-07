import random

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

class SamplingStrategy(Strategy):
    LOEs = ['Civil Security','Economics','Essential Services','Governance','HN Security Forces','Information Operations']
    categories = {
        'clear': {'Seize Structure': 1.,'Cordon and Knock': 1.,
                  'Cordon and Search': 1.,
                  'Dispatch Individual':1.,'Attack Group': 1.,
                  'Set up Checkpoint':0.5,'Remove':0.5,
                  'Arrest Person':0.333333,'Give Gift':0.33333,
                  'Host Meeting':0.33333,'Support Politically':0.33333,
                  'Release Person':0.333333,'Pay':0.333333,
                  'Treat Wounds/Illnesses':0.333333,
                  'Patrol Neighborhood':0.333333,'Give Propaganda':0.333333},
        'hold': {'Joint Investigate':1.,'Recruit Soldiers':0.5,
                 'Recruit Police':0.5,'Advise':0.5,'Set up Checkpoint':0.5,
                 'Remove':0.5,'Arrest Person':0.333333,
                 'Give Gift':0.333333,'Host Meeting':0.333333,
                 'Support Politically':0.333333,'Release Person':0.333333,
                 'Pay':0.333333,'Treat Wounds/Illnesses':0.333333,
                 'Patrol Neighborhood':0.333333,'Give Propaganda':0.333333},
        'build': {'Repair':1.,'Recruit Soldiers':0.5,'Recruit Police':0.5,
                  'Advise':0.5,'Arrest Person':0.333333,'Give Gift':0.333333,
                  'Host Meeting':0.333333,'Support Politically':0.333333,
                  'Release Person':0.333333,'Pay':0.333333,
                  'Treat Wounds/Illnesses':0.333333,
                  'Patrol Neighborhood':0.333333,'Give Propaganda':0.333333}
        }

    def __init__(self,scenario,distribution=None):
        Strategy.__init__(self,scenario)
        self.reset()
        self.indices = {}
        for index in range(len(self.LOEs)):
            self.indices[self.LOEs[index]] = index
        if distribution is None:
            self.distribution = [
                {'decrease': [0.33,0.02,0.17,0.11,0.10,0.22],
                 'no change': [0.33,0.01,0.15,0.12,0.07,0.24],
                 'increase': [0.37,0.01,0.16,0.09,0.09,0.24]},
                {'decrease': [0.35,0.01,0.18,0.11,0.08,0.23],
                 'no change': [0.38,0.01,0.14,0.11,0.08,0.23],
                 'increase': [0.35,0.01,0.17,0.10,0.09,0.24]},
                {'decrease': [0.36,0.00,0.25,0.13,0.05,0.19],
                 'no change': [0.38,0.01,0.12,0.10,0.08,0.25],
                 'increase': [0.32,0.01,0.22,0.10,0.09,0.22]},
                {'decrease': [0.36,0.01,0.14,0.12,0.08,0.23],
                 'no change': [0.36,0.01,0.15,0.11,0.08,0.23],
                 'increase': [0.36,0.01,0.17,0.09,0.09,0.24]},
                {'decrease': [0.37,0.01,0.15,0.12,0.07,0.24],
                 'no change': [0.36,0.01,0.16,0.10,0.09,0.23],
                 'increase': [0.36,0.01,0.17,0.09,0.09,0.24]},
                {'decrease': [0.36,0.01,0.14,0.11,0.08,0.23],
                 'no change': [0.36,0.01,0.15,0.11,0.08,0.22],
                 'increase': [0.36,0.01,0.17,0.09,0.09,0.24]}]
        else:
            self.distribution = distribution
        # Classify actions
        self.moves = {}
        for entity in scenario.members():
            if entity.instanceof('Player'):
                self.moves[entity.name] = {}
                for loe in self.LOEs:
                    self.moves[entity.name][loe] = []
                for option in entity.actions.getOptions():
                    assert len(option) == 1
                    if option[0]['type'] in ['Seize Structure','Patrol Neighborhood','Cordon and Knock','Set up Checkpoint','Attack Group'] or \
                            (option[0]['type'] == 'Remove' and scenario[option[0]['object']].instanceof('Structures')):
                        self.moves[entity.name]['Civil Security'].append(option[0])
                    elif option[0]['type'] in ['Repair']:
                        self.moves[entity.name]['Essential Services'].append(option[0])
                    elif option[0]['type'] in ['Pay']:
                        self.moves[entity.name]['Economics'].append(option[0])
                    elif option[0]['type'] in ['Host Meeting','Joint Investigate','Advise','Support Politically']:
                        self.moves[entity.name]['Governance'].append(option[0])
                    elif option[0]['type'] in ['Recruit Police','Recruit Soldiers']:
                        self.moves[entity.name]['HN Security Forces'].append(option[0])
                    elif option[0]['type'] in ['Treat Wounds/Illnesses','Arrest Person','Release Person','Give Propaganda','Dispatch Individual','Give Gift','Cordon and Search']:
                        self.moves[entity.name]['Information Operations'].append(option[0])
                    else:
                        raise NameError,'Unclassified action: %s' % (entity.makeActionKey(option))

    def reset(self):
        self.count = {'clear': 0.,'hold': 0.,'build': 0.}
        self.good = True

    def execute(self,t,state):
        changes = []
        # Find increase/decrease rows
        for index in range(len(self.LOEs)):
            if state[self.LOEs[index]] != 'no change':
                changes.append(self.distribution[index][state[self.LOEs[index]]])
        if len(changes) == 0:
            # All no changes
            for index in range(len(self.LOEs)):
                changes.append(self.distribution[index]['no change'])
        distribution = []
        for index in range(len(self.LOEs)):
            total = sum(map(lambda entry: entry[index],changes))
            distribution.append(total/float(len(changes)))
        distribution = map(lambda element: element/sum(distribution),
                           distribution)
        # Generate moves
        player = {}
        for entity,table in self.moves.items():
            player[entity] = self.generateMove(entity,distribution,t)
            verb = player[entity]['type']
            for key,value in self.count.items():
                if self.categories[key].has_key(verb):
                    self.count[key] = value + self.categories[key][verb]
        if t == 6:
            # End of clear phase
            if self.count['clear']+1e-6 < max(self.count.values()):
                # Not enough clearing in first phase
                self.good = False
                self.count = {'clear': 0.,'hold': 0.,'build': 0.}
        elif t == 14:
            # End of build phase
            if self.count['build']+1e-6 < max(self.count.values()):
                # Not enough building
                self.good = False
        return player

    def generateMove(self,entity,distribution,t):
        """Generate a random LOE according to distribution
        """
        table = self.moves[entity]
        sample = random.random()
        index = 0
        done = False
        while not done:
            if len(table[self.LOEs[index]]) > 0:
                # Possible action category
                sample -= distribution[index]
            if sample < 0.:
                # Hit
                done = True
            else:
                # Go on to next LOE
                index = (index+1)%len(self.LOEs)
        return self.pickAction(table[self.LOEs[index]],t)

    def pickAction(self,options,t):
        """By default, use a uniform distribution to select a random action
        from the given list of options"""
        return random.choice(options)

class CorrectSamplingStrategy(SamplingStrategy):
    def pickAction(self,options,t):
        modified = options[:]
        count = {'clear': 0.,'hold': 0.,'build': 0.}
        for option in options:
            verb = option['type']
            for key in count.keys():
                if self.categories[key].has_key(verb):
                    count[key] += self.categories[key][verb]
            if t < 7:
                if self.categories['clear'].has_key(verb):
                    value = self.categories['clear'][verb]
                    if self.categories['hold'].has_key(verb):
                        if self.categories['hold'][verb] > self.categories['clear'][verb]:
                            value = -1.
                    if self.categories['build'].has_key(verb):
                        if self.categories['build'][verb] > self.categories['clear'][verb]:
                            value = -1.
                    if value > 0.4:
                        modified.append(option)
                    if value > 0.6:
                        modified.append(option)
                else:
                    value = -1.
                if value < 0. and random.random() < 0.5:
                    # Remove some of the unsatisfactory actions
                    modified.remove(option)
            elif t > 6:
                if self.categories['build'].has_key(verb):
                    value = self.categories['build'][verb]
                    if self.categories['hold'].has_key(verb):
                        if self.categories['hold'][verb] > self.categories['build'][verb]:
                            value = -1.
                    if self.categories['clear'].has_key(verb):
                        if self.categories['clear'][verb] > self.categories['build'][verb]:
                            value = -1.
                    if value > 0.4:
                        modified.append(option)
                    if value > 0.6:
                        modified.append(option)
                else:
                    value = -1.
                if value < 0. and random.random() < 0.9:
                    # Remove some of the unsatisfactory actions
                    modified.remove(option)
        # count = {'clear': 0.,'hold': 0.,'build': 0.}
        # for option in options:
        #     for key in count.keys():
        #         try:
        #             count[key] += self.categories[key][option['type']]
        #         except KeyError:
        #             pass
        # print t,count
        # count = {'clear': 0.,'hold': 0.,'build': 0.}
        # for option in modified:
        #     for key in count.keys():
        #         try:
        #             count[key] += self.categories[key][option['type']]
        #         except KeyError:
        #             pass
        # print 'new:',count
        return random.choice(modified)

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
