#!/usr/bin/env python
#
#   p r o l o g 3 . p y
#
import sys, copy, re, string

rules    = []
trace    = 0
indent   = ""

def fatal (mesg) :
    sys.stdout.write ("Fatal: %s\n" % mesg)
    sys.exit(1)

def split (l, sep, All=1) :
    "Split l by sep but honoring () and []"
    nest = 0
    lsep = len(sep)
    if l == "" : return []
    for i in range(len(l)) :
        c = l[i]
        if nest <= 0 and l[i:i+lsep] == sep :
            if All : return [l[:i]]+split(l[i+lsep:],sep)
            else   : return [l[:i],l[i+lsep:]]
        if c in ['[','('] : nest = nest+1
        if c in [']',')'] : nest = nest-1
    return [l]

def isVariable(term) : return term.args == [] and term.pred[0:1] in string.uppercase
def isConstant(term) : return term.args == [] and not term.pred[0:1] in string.uppercase

infixOps = ("*is*","==","<",">","+","--","*","/") # STacy
def splitInfix(s) :
    for op in infixOps:
        p = split(s,op,All=0)
        if len(p) > 1 : return (op,p)
    return None

def makeTerm (s) : return Term(s)

class Term :
    def __init__ (self, s, args=None) :
        if not args : parts = splitInfix(s)
        if args :            # Predicate and args seperately
            self.pred = s
            self.args = args
        elif parts :
            self.args = map(makeTerm,parts[1])
            self.pred = parts[0]
        elif s[-1] == ']' :  # Build list "term"
            flds = split(s[1:-1],",")
            fld2 = split(s[1:-1],"|")
            if len(fld2) > 1 :
                self.args = map(makeTerm,fld2)
                self.pred = '.'
            else :
                flds.reverse()
                l = Term('.',[])
                for fld in flds : l = Term('.',[Term(fld),l])
                self.pred = l.pred; self.args = l.args
        elif s[-1] == ')' :               # Compile from "pred(a,b,c)" string
            flds = split(s,'(',All=0)
            if len(flds) != 2 : fatal("Syntax error in term: %s" % [s])
            self.args = map(makeTerm,split(flds[1][:-1],','))
            self.pred = flds[0]
        else : 
            self.pred = s           # Simple constant or variable
            self.args = []

    def __repr__ (self) :
        if self.pred == '.' :
            if len(self.args) == 0 : return "[]"
            nxt = self.args[1]
            if nxt.pred == '.' and nxt.args == [] :
                return "[%s]" % str(self.args[0])
            elif nxt.pred == '.' :
                return "[%s,%s]" % (str(self.args[0]),str(self.args[1])[1:-1])
            else :
                return "[%s|%s]" % (str(self.args[0]),str(self.args[1]))
        elif self.args :
            return "<%s(%s)>" % (self.pred,string.join(map(str,self.args),","))
        else : return self.pred

def procRule(sent):
    s = re.sub("#.*","",sent[:-1]) # clip comments and newline
    s = re.sub(" is ","*is*",s)    # protect "is" operator
    s = re.sub(" ", "" ,s)           # remove spaces
    if s[-1] in ['?','.'] : punc=s[-1]; s=s[:-1]
    else                  : punc='.'
    if punc == '?' : return search(Term(s))
    else :
        rules.append(Rule(s))
        # print Rule(s)
        return []

def clearPrologRules():
    global rules
    rules = []


class Rule :
    def __init__ (self, s) :   # expect "term:-term,term,..."
        flds = string.split(s,":-")
        self.head = Term(flds[0])
        self.goals = []
        if len(flds) == 2 :
            flds = split(flds[1],",")
            for fld in flds : self.goals.append(Term(fld))

    def __repr__ (self) :
        return "<Rule: %s :- %s>" % (self.head, self.goals)
        
class Goal :
    def __init__ (self, rule, parent=None, env={}) :
        self.rule = rule
        self.parent = parent
        self.env = copy.deepcopy(env)
        self.inx = 0      # start search with 1st subgoal

    def __repr__ (self) :
        return "<Goal:%s:%d:%s>" % (self.rule,self.inx,self.env)

def main () :
    for file in sys.argv[1:] :
        if file == '.' : return    # early out. no user interaction
        procFile(open(file),'')    # file on the command line
    procFile (sys.stdin,'? ')      # let the user have her say

def procFile (f, prompt) :
    global rules, trace
    env = []
    while 1 :
        if prompt :
            sys.stdout.write(prompt)
            sys.stdout.flush()
        sent = f.readline()
        if sent == "" : break
        s = re.sub("#.*","",sent[:-1]) # clip comments and newline
        s = re.sub(" is ","*is*",s)    # protect "is" operator
        s = re.sub(" ", "" ,s)           # remove spaces
        if s == "" : continue

        if s[-1] in ['?','.'] : punc=s[-1]; s=s[:-1]
        else                  : punc='.'

        if   s == 'trace' : trace = not trace
        elif s == 'dump'  :
            for rule in rules : print rule
        elif punc == '?' : search(Term(s))
        else             : rules.append(Rule(s))
##    for rule in rules : print rule

# A Goal is a rule in at a certain point in its computation. 
# env contains definitions (so far), inx indexes the current term
# being satisfied, parent is another Goal which spawned this one
# and which we will unify back to when this Goal is complete.
#

def unify (src, srcEnv, dest, destEnv) :
    "update dest env from src. return true if unification succeeds"
    global trace, indent
    if trace : print indent, "Unify", src, srcEnv, "to", dest, destEnv
    indent = indent+"  "
    if src.pred == '_' or dest.pred == '_' : return sts(1,"Wildcard")

    if isVariable(src) :
        srcVal = eval(src, srcEnv)
        if not srcVal : return sts(1,"Src unset")
        else : return sts(unify(srcVal,srcEnv,dest,destEnv), "Unify to Src Value")

    if isVariable(dest) :
        destVal = eval(dest, destEnv)           # evaluate destination
        if destVal : return sts(unify(src,srcEnv,destVal,destEnv),"Unify to Dest value")
        else :
            destEnv[dest.pred] = eval(src,srcEnv)
            return sts(1,"Dest updated 1")      # unifies. destination updated

    elif src.pred      != dest.pred      : return sts(0,"Diff predicates")
    elif len(src.args) != len(dest.args) : return sts(0,"Diff # args")
    else :
        dde = copy.deepcopy(destEnv)
        for i in range(len(src.args)) :
            if not unify(src.args[i],srcEnv,dest.args[i],dde) :
                return sts(0,"Arg doesn't unify")
        destEnv.update(dde)
        return sts(1,"All args unify")

def sts(ok, why) :
    global trace, indent
    indent = indent[:-2]
    if trace: print indent, ["No","Yes"][ok], why
    return ok

def search (term) :
    global trace
    res = []
    # pop will take item from end, insert(0,val) will push item onto queue
    goal = Goal(Rule("all(done):-x(y)"))      # Anything- just get a rule object
    goal.rule.goals = [term]                  # target is the single goal
    queue = [goal]                            # Start our search
    while queue :
        c = queue.pop()                       # Next goal to consider
        if trace : print "Deque", c
        if c.inx >= len(c.rule.goals) :       # Is this one finished?
            if c.parent == None :            # Yes. Our original goal?
                if c.env :
                    print  c.env                # Yes. tell user we
                    res.append(c.env)           #
                else     : print "Yes"          # have a solution
                continue
            parent = copy.deepcopy(c.parent)  # Otherwise resume parent goal
            unify (c.rule.head,    c.env,
                   parent.rule.goals[parent.inx],parent.env)
            parent.inx = parent.inx+1         # advance to next goal in body
            queue.insert(0,parent)            # let it wait its turn
            if trace : print "Requeuing", parent
            continue

        # No. more to do with this goal.
        term = c.rule.goals[c.inx]            # What we want to solve

        pred = term.pred                    # Special term?
        if pred in ['*is*', 'cut','fail', 'diff', '<','=='] :
            if pred == '*is*' :
                ques = eval(term.args[0],c.env)
                ans  = eval(term.args[1],c.env)
                if ques == None :
                    c.env[term.args[0].pred] = ans  # Set variable
                elif ques.pred != ans.pred :
                    continue                # Mismatch, fail
            elif pred == 'diff' :
                ques = eval(term.args[0],c.env)
                ans  = eval(term.args[1],c.env)
                if ques.pred == ans.pred :
                    continue             
            elif pred == 'cut' : queue = [] # Zap the competition
            elif pred == 'fail': continue   # Dont succeed
            elif not eval(term,c.env) : continue # Fail if not true
            c.inx = c.inx + 1               # Succeed. resume self.
            queue.insert(0,c)
            continue

        for rule in rules :                   # Not special. Walk rule database
            if rule.head.pred      != term.pred      : continue
            if len(rule.head.args) != len(term.args) : continue
            child = Goal(rule, c)               # A possible subgoal
            ans = unify (term, c.env, rule.head, child.env)
            if ans :                    # if unifies, queue it up
                queue.insert(0,child)
                if trace : print "Queuing", child
    return res

def add (a,b) : return Term(str(int(a.pred)+int(b.pred)),[])
def sub (a,b) : return Term(str(int(a.pred)-int(b.pred)),[])
def mul (a,b) : return Term(str(int(a.pred)*int(b.pred)),[])
def lt  (a,b) : return int(a.pred) <  int(b.pred)
def eq  (a,b) : return int(a.pred) == int(b.pred)

def preport (a) :
    print a
    return 1

operators = {'+': add, '--':sub, '*':mul, '<':lt}

def eval (term, env) :      # eval all variables within a term to constants
    special = operators.get(term.pred)
    if special :
        return special(eval(term.args[0],env),eval(term.args[1],env))
    if isConstant(term) : return term
    if isVariable(term) :
        ans = env.get(term.pred)
        if not ans : return None
        else       : return eval(ans,env)
    args = []
    for arg in term.args : 
        a = eval(arg,env)
        if not a : return None
        args.append(a)
    return Term(term.pred, args)

if __name__ == "__main__" : main()
