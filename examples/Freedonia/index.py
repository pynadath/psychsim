#!/usr/bin/env python

import socket
__DEPLOYED__ = 'inmotionhosting.com' in socket.gethostname()

import cgi
import cgitb
if __DEPLOYED__:
    weblogdir = 'weblogs'
else:
    weblogdir = '/tmp'
cgitb.enable(display=0, logdir=weblogdir)
from ConfigParser import SafeConfigParser,NoOptionError,NoSectionError
import Cookie
import os
import re
import StringIO
import sys
import time

# Comment out the following if you want deterministic behavior
import random
random.seed()

import locale
if __DEPLOYED__:
    locale.setlocale(locale.LC_ALL,'en_US')

from psychsim.world import World,stateKey
from psychsim.action import Action

# Utility functions for extracting information from the current world

def getWorld(scenario,session):
    # Load scenario
    try:
        filename = getScenarioFile(scenario,session)
        os.stat(filename)
        first = False
    except OSError:
        filename = getScenarioFile(scenario)
        first = True
    # Get game configuration
    config = SafeConfigParser()
    if __DEPLOYED__:
        config.read('scenarios/%s.cfg' % (scenario))
    else:
        config.read('/home/david/PsychSim/psychsim/examples/%s.cfg' % (scenario))
    return World(filename),config,first

def getOutcomes(world):
    today = world.getState(None,'round').domain()[0]
    sequence = []
    for outcomes in world.history:
        # Extract this turn's event
        assert len(outcomes) == 1
        outcome = outcomes[0]
        day = int(outcome['old']['round']+0.5)
        if len(sequence) == day:
            sequence.append({'old': outcome['old']})
        # Extract actions
        actions = world.explainAction(outcome)
        assert len(actions) == 1 # Only one person acted
        action = iter(actions).next()
        assert len(action) == 1 # Only one action selected
        action = iter(action).next()
        try:
            sequence[day][action['subject']].append(action)
        except KeyError:
            sequence[day][action['subject']] = [action]
        # Extract result
        sequence[day]['delta'] = outcome['delta']
    return sequence

def getDelta(world,delta,config):
    """
    Translate a delta vector into a string representation
    """
    user = config.get('Game','user')
    phrases = []
    for name in world.agents.keys():
        for feature in world.features[name].keys():
            if config.has_option('Change',feature):
                key = stateKey(name,feature)
                value = delta[key]
                if feature == 'position':
                    if name == user:
                        if value < 0:
                            phrases.insert(0,'You lost the battle.')
                        elif value > 0:
                            phrases.insert(0,'You won the battle.')
                        else:
                            phrases.insert(0,'The battle was indecisive.')
                    continue
                elif value < 0:
                    phrase = '%s lost %s %s.' % (name,locale.format('%d',-delta[key],True),feature)
                elif value > 0:
                    phrase = '%s gained %s %s.' % (name,locale.format('%d',delta[key],True),feature)
                phrases.append(phrase.replace(user,'You'))
    return ' '.join(phrases)

def getAttacks(world,outcome,config):
    attackers = []
    for name in world.agents.keys():
        if outcome.has_key(name) and outcome[name][-1]['verb'] == 'attack':
            attackers.append(name)
    user = world.agents[config.get('Game','user')]
    if user.name in attackers:
        attackers.remove(user.name)
        attackers.insert(0,'You')
    return attackers

def getState(world,config):
    """
    Extract some useful properties of the current state of the world
    @return: the current state vector,the current phase of the game,whose turn it is,whether there is a choice to be made,the current round
    @rtype: KeyedVector,str,str,bool,int
    """
    assert len(world.state) == 1
    state = world.state.domain()[0]
    phase = world.getState(None,'phase').domain()[0]
    # Whose turn is it?
    turn = world.next(state)
    assert len(turn) == 1
    turn = turn[0]
    # Does s/he have a choice of actions?
    actions = world.agents[turn].getActions(state)
    if turn == config.get('Game','user'):
        choice = len(actions) > 1
    else:
        verbs = {}
        for action in actions:
            verbs[action['verb']] = True
        choice = len(verbs) > 1
    # What round is it?
    day = world.getState(None,'round').domain()[0]
    return state,phase,turn,choice,day

def getAction(world,form):
    """
    Extract an action from form submission
    """
    state = world.state.domain()[0]
    verb = form.getvalue('verb')
    action = None
    if verb:
        table = {'verb': str(verb), 'subject': str(form.getvalue('subject'))}
        for option in world.agents[table['subject']].getActions(state):
            atom = option.match(table)
            if atom:
                if atom.has_key('object'):
                    table['object'] = atom['object']
                for key in atom.getParameters():
                    # Make sure all parameters are specified
                    if form.getvalue(key):
                        try:
                            table[key] = int(form.getvalue(key))
                            continue
                        except TypeError:
                            # Invalid value
                            break
                        except ValueError:
                            # Maybe a float?
                            try:
                                table[key] = int(float(form.getvalue(key))+0.5)
                            except ValueError:
                                break
                    else:
                        # Empty value
                        break
                else:
                    # All parameters specified
                    action = Action(table)
                    break
    return action

# Functions for generating the content frames

def intro(config,session,scenario):
    if __DEPLOYED__:
        f = open('templates/Welcome.html','r')
    else:
        f = open('/home/david/Documents/Curious/Welcome.html','r')
    content = f.read()
    f.close()
    buf = StringIO.StringIO()
    print >> buf, '<form method="post">'
    print >> buf, '<input type="hidden" name="session" value="%ld"/>' % (session)
    print >> buf, '<input type="hidden" name="scenario" value="%s"/>' % (scenario)
    print >> buf, '<input type="submit" value="Next"/>'
    print >> buf, '</form>'
    content = content.replace('<a href="Bargain.html">[Next]</a>',buf.getvalue())
    buf.close()
    content = content.replace('Sylvania',config.get('Game','agent'))
    content = content.replace('Trentino',config.get('Game','region'))
    print content

def doSession(msg=''):
    f = open('templates/empty.html','r')
    template = f.read()
    f.close()
    content = '<p><form method="post">If you have already received your Participant ID, submit it here (you do not need to submit your worker ID below):'\
        '<input type="text" name="session"><input type="submit"/></form></p>'\
        '<p><form method="post">If you have not yet received (or have forgotten) your Participant ID, '\
        'enter your Amazon Mechanical Turk Worker ID: <input type="text" name="turk">'\
        '<input type="submit"/></form></p>'
    template = template.replace('<body/>','<body><div id="fullwidthbox">\n<h1>%s</h1>%s\n</div></body>' % (msg,content))
    print template
    sys.exit(0)

def doTurn(world,turn,config,logfile,session=1,scenario='default'):
    f = open('templates/Bargain.html','r')
    template = f.read()
    f.close()
    length = int(config.get('Game','rounds'))
    state = world.state.domain()[0]
    if world.terminated(state):
        # Game is over
        link = '<form method="post"><h4>Thank you for playing the game.</h4>\n'\
            '<input type="hidden" name="session" value="%ld"/>\n' % (session)+\
            '<input type="hidden" name="scenario" value="%s"/>\n' % (scenario)+\
            '<p>Click <input type="submit" value="here"/> for a postgame survey.</p>'
        template = template.replace('<h1>Day <1/h1>',
                                    '<h1>Negotiation Complete.</h1>\n%s' % (link))
        template = template.replace('Your Move','Game Over')
        template = template.replace('<actions/>',link)
        user = world.agents[config.get('Game','user')]
        territory = world.getState(user.name,'territory').expectation()
        template = template.replace('Day 1','Game Over: You own %d%% of disputed territory' % (territory))
        writeLog(logfile,'end','%d' % (territory))
    else:
        # Game is live
        template = template.replace('Day 1','Round %d of %d' % (turn+1,length))
        template = template.replace('<actions/>',
                                    doActions(world,turn,config,logfile,session,scenario))
    template = template.replace('<state/>',doState(world,turn,config,logfile,session))
    template = template.replace('<negotiation/>',doNegotiation(world,turn,config,logfile,session))
    template = template.replace('<battle/>',doBattle(world,turn,config,logfile,session))
    print template

def doState(world,turn,config,logfile,session=1):
    buf = StringIO.StringIO()
    print >> buf,'<h5>'
    print >> buf,'<table cellpadding="5" width="100%">'
    state = world.state.domain()[0]
    user = world.agents[config.get('Game','user')]
    features = world.features[user.name].keys()
    features.sort()
    for feature in filter(lambda f: config.has_option('Visible',f) and config.has_option('Visible',f),features):
        value = state[stateKey(user.name,feature)]
        desc = world.getDescription(user.name,feature)
        print >> buf,'<tr><td colspan="2">%s</td></tr>' % (desc)
        print >> buf,'<tr><td width="5%%" align="right">%s</td>' % \
            (locale.format('%d',value,True))
        span = world.features[user.name][feature]['hi'] - \
            world.features[user.name][feature]['lo'] 
        pct = 100*(value-world.features[user.name][feature]['lo'])/span
        print >> buf,'<td><table width="93%" border="1" frame="box" rules="none"><tr>'
        if pct > 0:
            print >> buf,'<td bgcolor="white" height="12" width="%d%%"/>' % (pct)
        else:
            print >> buf,'<td height="12"/>'
        print >> buf,'<td/></tr></table></td>'
        print >> buf,'</tr>'
    print >> buf,'</table>'
    print >> buf,'</h5>'
    contents = buf.getvalue()
    buf.close()
    return contents

def doActions(world,turn,config,logfile,session=1,scenario='default'):
    buf = StringIO.StringIO()
    user = world.agents[config.get('Game','user')]
    print >> buf, '<form method="post">'
    print >> buf,'<input type="hidden" name="subject" value="%s"/>' % (user.name)
    print >> buf,'<input type="hidden" name="scenario" value="%s"/>' % (scenario)
    print >> buf,'<input type="hidden" name="session" value="%ld"/>' % (session)
    actions = user.getActions(world.state.domain()[0])
    actionSelection(world,actions,buf,config,logfile)
    print >> buf,'<div align="right"><p><input type="submit"/></p></div>'
    print >> buf,'</form>'
    contents = buf.getvalue()
    buf.close()
    return contents

def actionSelection(world,actions,buf,config,logfile,var='verb'):
    processed = {}
    first = True
    actions = list(actions)
    actions.sort(lambda x,y: cmp(str(x),str(y)))
    for option in actions:
        if len(option) > 1:
            writeLog(logfile,'error','Option has %2 simultaneous actions' % (len(option)))
        action = iter(option).next()
        if not processed.has_key(action.root()):
            processed[action.root()] = True
            if first and var == 'verb':
                checked = ' checked'
                first = False
            else:
                checked = ''
            print >> buf,'<p><input type="radio" name="%s" value="%s"%s>%s</input></p>' %\
                (var,action['verb'],checked,action2label(action,world,True))

def action2label(action,world,form=False):
    pat = re.compile('<.*?>')
    if action['subject'] == config.get('Game','user'):
        lookup = action['verb']
    else:
        lookup = '%s %s' % (action['subject'],action['verb'])
    try:
        label = config.get('Actions',lookup)
    except NoOptionError:
        label = action['verb'].capitalize()
    for term in pat.findall(label):
        words = term[1:-1].split(':')
        if words[0] == 'action':
            if form:
                label = label.replace(term,'</input><input type="text" size="2" name="%s"/>' % (words[1]))
            else:
                label = label.replace(term,'%d' % (action[words[1]]))
        else:
            value = world.getState(words[0],words[1]).expectation()
            label = label.replace(term,'%d' % (value))
    return label

def doNegotiation(world,turn,config,logfile,session=1):
    buf = StringIO.StringIO()
    user = config.get('Game','user')
    other = config.get('Game','agent')
    if len(world.history) == 0:
        print >> buf,'<h2>No previous offers made.</h2>'
        previous = ''
        outcomes = []
    else:
        outcomes = getOutcomes(world)
        assert outcomes[-1].has_key(other)
        otherAction = outcomes[-1][other][0]
        print >> buf,'<h2>%s decided to %s</h2>' % (otherAction['subject'],action2label(otherAction,world))
    print >> buf,'<br/>'
    print >> buf,'<h3>Negotiation History</h3>'
    print >> buf,'<select size=8>'
    for day in range(len(outcomes)):
        print >> buf,'<option>%02d)' % (day+1)
        actions = {}
        for name in world.agents.keys():
            if outcomes[day].has_key(name):
                for action in outcomes[day][name]:
                    actions[action['verb']] = action
        if actions.has_key('offer'):
            subj = actions['offer']['subject'].replace(user,'you')
            obj = actions['offer']['object'].replace(user,'you')
            obj = obj.replace(other,'they')
            print >> buf,'%s offered %d%% to %s.' % \
                (subj.capitalize(),actions['offer']['amount'],actions['offer']['object'])
            if outcomes[day].has_key(actions['offer']['object']):
                print >> buf,'%s decided to %s.' % \
                    (obj.capitalize(),outcomes[day][actions['offer']['object']][0]['verb'])
        else:
            print >> buf,'No negotiation.'
        print >> buf,'</option>'
    print >> buf,'</select>'
    contents = buf.getvalue()
    buf.close()
    return contents

def doBattle(world,turn,config,logfile,session=1):
    buf = StringIO.StringIO()
    user = world.agents[config.get('Game','user')]
    if len(world.history) == 0:
        print >> buf,'<h2>No previous battle.</h2>'
        outcomes = []
    else:
        outcomes = getOutcomes(world)
        if not outcomes[-1].has_key(user.name):
            outcomes = outcomes[:-1]
        attackers = getAttacks(world,outcomes[-1],config)
        if attackers:
            if config.get('Game','battle') == 'mandatory':
                print >> buf,'<h2>Battle results</h2>'
            else:
                msg = ' and '.join(attackers)
                print >> buf,'<h2>%s attacked</h2>' % (msg)
            state = world.state.expectation()
            territory = stateKey(user.name,'territory')
            if state[territory] < 1:
                print >> buf,'<h5>You lost the war.</h5>'
            elif state[territory] > 99:
                print >> buf,'<h5>You won the war.</h5>'
            else:
                delta = state - outcomes[-1]['old']
                if delta[stateKey(user.name,'position')] > 0:
                    print >> buf,'<h5>You won the last battle.</h5>'
                elif delta[stateKey(user.name,'position')] < 0:
                    print >> buf,'<h5>You lost the last battle.</h5>'
                else:
                    print >> buf,'<h5>The last battle was indecisive.</h5>'
        elif config.get('Game','battle') == 'mandatory':
            print >> buf,'<h2>The results from the battle are not in yet.</h2>'
        else:
            print >> buf,'<h2>There was no battle.</h2>'
    print >> buf,'<br/>'
    print >> buf,'<h3>Battle History</h3>'
    print >> buf,'<select size=8>'
    for day in range(len(outcomes)):
        print >> buf,'<option>%02d)' % (day+1)
        attackers = getAttacks(world,outcomes[day],config)
        if attackers:
            print >> buf,'<h2>'
            if config.get('Game','battle') == 'optional':
                msg = ' and '.join(attackers)
                print >> buf,'%s attacked.' % (msg)
            try:
                delta = outcomes[day+1]['old'] - outcomes[day]['old']
            except IndexError:
                delta = state - outcomes[day]['old']
            print >> buf, '%s</h2>' % (getDelta(world,delta,config))
        elif config.get('Game','battle') == 'optional':
            print >> buf,'<h2>No battle.</h2>'
        else:
            print >> buf,'<h2>Results not in yet.</h2>'
        print >> buf,'</option>'
    print >> buf,'</select>'
    contents = buf.getvalue()
    buf.close()
    return contents

def doExpectation(world,turn,config,logfile,session=1,scenario='default'):
    f = open('templates/Poll.html','r')
    template = f.read()
    f.close()
    template = template.replace('Day 1','Round %d' % (turn+1))
    user = world.agents[config.get('Game','user')]
    other = world.agents[config.get('Game','agent')]
    action = iter(world.explainAction(world.history[-1][0])).next()
    atom = iter(action).next()
    template = template.replace('<action/>',action2label(atom,world))
    template = template.replace('<effect/>','<input type="radio" name="effect" value="opponent_collapse" /> %s collapses <br />' % (other.name)+\
                                    '<input type="radio" name="effect" value="Lose_battle" /> Lose battle <br />'\
                                    '<input type="radio" name="effect" value="Gain_territory" /> Gain territory <br />'\
                                    '<input type="radio" name="effect" value="Lose_territory" /> Lose territory')
    buf = StringIO.StringIO()
    for agent in world.agents.values():
        if agent.name != user.name:
            print >> buf,'<h2>How do you expect %s to respond?</h2>' % \
                (agent.name)
            print >> buf, '<h4>'
            actions = agent.getActions(world.state.expectation())
            actionSelection(world,actions,buf,config,logfile,agent.name)
            print >> buf,'</h4>'
    print >> buf,'<input type="hidden" name="action" value="%s"/>' % (action)
    print >> buf,'<input type="hidden" name="scenario" value="%s"/>' % (scenario)
    print >> buf,'<input type="hidden" name="phase" value="choose"/>'
    print >> buf,'<input type="hidden" name="session" value="%ld"/>' % (session)
    print >> buf,'<div align="right"><p><input type="submit"/></p></div>'
    template = template.replace('<response/>',buf.getvalue())
    buf.close()
    print template

def doFrame(url,logfile,session=None,scenario=None,header=None):
    if header is None:
        f = open('templates/Survey.html','r')
        template = f.read()
        f.close()
    else:
        f = open('templates/Header.html','r')
        template = f.read()
        f.close()
    if scenario:
        template = template.replace('<header/>','http://www.curiouslab.com/cgi-bin/COSMOS/?session=%ld&scenario=%s&header=yes' % (session,scenario))
    else:
        template = template.replace('<header/>','http://www.curiouslab.com/cgi-bin/COSMOS/?turk=%s&header=yes' % (session))
    if url:
        template = template.replace('<survey/>',url)
    if isinstance(session,long):
        template = template.replace('<session/>','%ld' % (session))
    if scenario:
        if header:
            template = template.replace('<scenario/>','%s %s' % (scenario,header))
        else:
            template = template.replace('<scenario/>','%s' % (scenario))
    else:
        template = template.replace('Game ID: <scenario/>','Write your ID down for future reference')
    print template

def doThanks(session=1,sequence=None):
    f = open('templates/empty.html','r')
    template = f.read()
    f.close()
    template = template.replace('<body/>','<body><div id="fullwidthbox">'\
                                    '<h1>You have finished all games. Thank you for participating!</h1>'\
                                    'Enter the following code in Mechanical Turk to complete the HIT.'\
                                    '<h2>%ld%s</h2>' % (session,sequence.replace(',',''))+\
                                    'You can use this code only once. If you have already used this code in our previous HITs, you <em>cannot</em> use it again in the current HIT. If you do, your HIT <em>will</em> be rejected.'\
                                    '</div></body>')
    print template

# Other utility functions

def performAction(world,action,logfile):
    """
    Perform the specified action, update the world, and write the result to the logfile
    """
    if action is None:
        # Free action by agent
        outcome = world.step()
    else:
        # User-specified action
        outcome = world.step({action['subject']: action})
    assert len(outcome) == 1,'Stochastic actions not allowed'
    for action in world.explainAction(outcome[0],level=0):
        writeLog(logfile,'turn',action)
    world.state.select()
    world.printVector(world.state.domain()[0],buf=logfile,csv=True,
                      prefix='%s,result' % (time.strftime('%c',time.localtime(time.time()))))
    return outcome

def getScenarioFile(scenario,session=None):
    if session is None:
        if __DEPLOYED__:
            filename = 'scenarios/%s.psy' % (scenario)
        else:
            filename = '/home/david/PsychSim/psychsim/examples/%s.psy' % (scenario)
    else:
        if __DEPLOYED__:
            filename = 'scenarios/%s%ld.psy' % (scenario,session)
        else:
            filename = '/home/david/PsychSim/psychsim/examples/%s%ld.psy' % (scenario,session)
    return filename

def writeLog(logfile,category,entry):
    print >> logfile,'%s,%s,%s' % (time.strftime('%c',time.localtime(time.time())),category,entry)
    
if __name__ == '__main__':
    print 'Content-Type: text/html'     # HTML is following
    form = cgi.FieldStorage()
    # Cookie handling
    cookie = Cookie.SimpleCookie()
    if os.environ.has_key('HTTP_COOKIE'):
        cookie.load(os.environ['HTTP_COOKIE'])
    # Get session ID
    turk = form.getvalue('turk')
    try:
        session = long(form.getvalue('session'))
    except TypeError:
        session = 0
        if cookie.has_key('session'):
            session = long(cookie['session'].value)
    except ValueError:
        session = -1
    # Get scenario name
    scenario = form.getvalue('scenario')
    if scenario is None:
        if cookie.has_key('scenario'):
            scenario = cookie['scenario'].value
    # Update cookie
#    cookie['session'] = session
#    cookie['scenario'] = scenario
    print cookie
    print                               # blank line, end of headers

    # Get session
    config = SafeConfigParser()
    config.read('sessions.cfg')
    if session <= 0:
        # Must first ask for session information
        if session < 0:
            doSession('Participant ID must be numeric')
        elif turk is None:
            doSession()
        else:
            result = re.search('\W*(\w{13,14})\W*',turk)
            if result is None:
                doSession('Worker ID should be 13-14 alphanumeric characters')
            else:
                try:
                    turk = result.group(1)
                except IndexError:
                    doSession('Worker ID should be 13-14 alphanumeric characters')
            try:
                value = config.get('Turk',turk.lower()).split('\n')[0] # Sometimes the config file returns multiple lines (not sure why)
                session = long(value)
            except NoOptionError:
                # Assign next player ID to this worker
                assigned = False
                rows = []
                import csv
                import fcntl
                lock = open('file.lock','w')
                fcntl.lockf(lock,fcntl.LOCK_EX)
                # Read mapping between Turk and participant IDs
                f = open('workers.csv','r')
                reader = csv.reader(f)
                for row in reader:
                    if len(row) == 1 and not assigned:
                        # Use this unassigned participant ID
                        session = long(row[0])
                        rows.append([row[0],turk])
                        assigned = True
                        config.set('Turk',turk,row[0])
                    else:
                        rows.append(row)
                f.close()
                if assigned:
                    # Write updated assignment
                    f = open('workers.csv','w')
                    writer = csv.writer(f)
                    writer.writerows(rows)
                    f.close()
                    # Write updated config
                    f = open('sessions.cfg','w')
                    config.write(f)
                    f.close()
                    fcntl.lockf(lock,fcntl.LOCK_UN)
                    lock.close()
                else:
                    # No unassigned IDs
                    fcntl.lockf(lock,fcntl.LOCK_UN)
                    doSession('No participant slots currently available.')
    # Get game sequence
    try:
        sequence = config.get('Sequences',str(session))
    except NoOptionError:
        doSession('Unknown participant ID')
    # Find next scenario for this participant
    scenarios = sequence.split(',')
    if scenario is None:
        for game in range(len(scenarios)):
            scenario = scenarios[game]
            # Remove stored scenario if requested
            if form.getvalue('reset'):
                os.remove(getScenarioFile(scenario,session))
            world,config,first = getWorld(scenario,session)
            if not world.terminated():
                # This scenario has not yet been played to completion
                break
        else:
            # All scenarios played
            doThanks(session,sequence)
            sys.exit(0)
    else:
        world,config,first = getWorld(scenario,session)
        game = scenarios.index(scenario)
    if turk and game == 0:
        # First time through, must generate pre-game pages
        if form.getvalue('header') == 'yes':
            doFrame(None,None,session,header='')
        elif first:
            doFrame('http://www.curiouslab.com/clsurvey/index.php?sid=94535&lang=en',None,turk)
        sys.exit(0)
    # We found next unplayed scenario
    try:
        user = config.get('Game','user')
    except NoSectionError:
        print 'Illegal game ID'
        sys.exit(-1)
    # Open logfile
    if __DEPLOYED__:
        logfile = open('logs/%ld.log' % (session),'a')
    else:
        logfile = open('/tmp/%ld.log' % (session),'a')
    # Determine game state
    state,phase,turn,choice,day = getState(world,config)
    if world.terminated():
        # If all done, do survey
        if form.getvalue('header'):
            header = '(Completed: %d/%d)' % (game+1,len(scenarios))
        else:
            header = None
        doFrame(config.get('Links','survey'),logfile,session,scenario,header)
    elif phase == 'paused':
        # Start of game, so print welcome screen and move to first offer stage
        intro(config,session,scenario)
        model = world.getState(None,'model').domain()[0]
        writeLog(logfile,'begin','%s,%d' % (model,world.getState(user,'territory').expectation()))
        # After intro, move to first game phase
        world.setState(None,'phase',world.features[None]['phase']['elements'][0])
        world.save(getScenarioFile(scenario,session))
    else:
        # Process any incoming actions
        action = getAction(world,form)
        if choice:
            if turn == user:
                # Wait for user to choose an action
                if action:
                    writeLog(logfile,'action',str(action))
                    outcome = performAction(world,action,logfile)
                    state,phase,turn,choice,day = getState(world,config)
            else:
                # Wait for user to specify expectations
                if not form.getvalue(turn) is None:
                    # User has specified expected response
                    writeLog(logfile,'expectation','%s,%s' % (turn,str(form.getvalue(turn))))
                    outcome = performAction(world,None,logfile)
                    state,phase,turn,choice,day = getState(world,config)
        # Step until we reach another choice point
        step = 0
        while not choice and not world.terminated(state):
            outcome = performAction(world,None,logfile)
            state,phase,turn,choice,day = getState(world,config)
            step += 1
            assert step < 5
        # Save current state
        world.save(getScenarioFile(scenario,session))
        if turn == user or world.terminated(state):
            # Display current state of the game
            doTurn(world,day,config,logfile,session,scenario)
        else:
            # Survey about agent response
            doExpectation(world,day,config,logfile,session,scenario)
    logfile.close()
