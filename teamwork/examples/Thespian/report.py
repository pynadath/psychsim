import string
import sys


def searchForAct(actions,c,exist=1):
    if exist == 1:
        for action in actions:
            if action.find(c) > -1:
                return 1
        return 0
    else:
        found = 0
        for action in actions:
            if action.find(c) > -1:
                found = 1
                break
            
        if found == 1:
            return 0
        else:
            return 1
    

## by default bad paths are defined as
## 1. the actor performs the same action for more than 60% of the turns
## 2. the actor repeat the same actions for more than 3 times continuously
## 3. 
def selectReport(path,actor,criteria={'hunter-kill-wolf':'0'}):
    path = path.strip('[')
    path = path.strip(']\n')
    actions = string.split(path,', ')
    
    count = {}
    totalStep = 0
    lastAct = LastAct2 = ''
    result = []
    
    ## 2. the actor repeat the same actions for more than 3 times continuously
    for action in actions:
        ## this action is performed by this actor
        if action.find(actor) == 0:
            totalStep += 1

            if action == lastAct and action == lastAct2:
                result.append(2)

            lastAct2 = lastAct
            lastAct = action
        
            if not count.has_key(action):
                count[action] = 1
            else:
                count[action] += 1
                
    ## 1. the actor performs the same action for more than 60% of the turns
    for action in count:
        if count[action] > totalStep*.75:
            result.append(1)

##  assum an AND relationship among criteria
    for c in criteria:
        if criteria[c] == '1':
            res = searchForAct(actions,c,1)
        else:
            res = searchForAct(actions,c,0)
        if res == 0:
            break
    else:
        result.append(3)

    if result == []:
        result.append(0)
    return result

def diff(f1,f2):
    fileHandle = open (f1)

    pathList1 = fileHandle.readlines()

    fileHandle.close()

    fileHandle = open (f2)

    pathList2 = fileHandle.readlines()

    fileHandle.close()

    diff1 = []
    diff2 = []

    for path in pathList1:
        if path[0] == '[':
            if not path in pathList2:
                diff1.append(path)

    for path in pathList2:
        if path[0] == '[':
            if not path in pathList1:
                diff2.append(path)
            

    print 'path in file ',f1,' but not in file ',f2
    print 'totle number: ',len(diff1)

    print 'path in file ',f2,' but not in file ',f1
    print 'totle number: ',len(diff2)

    for i in range(len(diff1)):
        print diff1[i]
    

    
def printResult(totalRecord,distinctRecord,reportList,report):
    print "Total numbers of record in file: ",totalRecord
    print "Total numbers of distinct record in file: ",distinctRecord
    print "Number of record prompt for attention: ",len(reportList)
    print "Number of record selected by default huristics: ", report[4]
    print report[1],report[2]
    print "Number of record selected by plot point: ", report[3]
    print "Number of record satisfy all filtering criteria: ", report[0]
    print
    print

def ProcessResults(fnames):
    totalList = []
    reportList = []
    
    for fname in fnames:
        fileHandle = open (fname)

        pathList = fileHandle.readlines()

        fileHandle.close()

        reportList = []

        totalRecord = 0

        distinctRecord = 0

        criteria={'hunter-kill-wolf':'0','wolf-eat-granny':'1'}
        
        i = 0

        report = [0]*5
        d = 0
        for path in pathList:
            if path.find('red')==0:
                printResult(totalRecord,distinctRecord,reportList,report)
                print path
                totalRecord = 0
                distinctRecord = 0
                report = [0]*5
                reportList = []
                d = pathList.index(path)
            elif path[0] == '[':
                totalRecord += 1
                if pathList[d+1:].index(path) + d + 1 == i:
                    distinctRecord += 1
                    res = selectReport(path,'wolf',criteria)
                    if not 0 in res:
                        if not path in reportList:
                            reportList.append(path)
                        if 1 in res:
                            report[1]+=1
                        if 2 in res:
                            report[2]+=1
                        if 3 in res:
                            report[3]+=1
                        if (1 in res) and (2 in res) and (3 in res):
                            report[0]+=1
                        if (1 in res) or (2 in res):
                            report[4]+=1
            
            i += 1
        printResult(totalRecord,distinctRecord,reportList,report)
    
##        for path in reportList:
##            if not path in totalList:
##                totalList.append(path)

##    print "Total number of paths: ,",len(totalList)


if __name__ == '__main__':
##    ProcessResults('0425result-goodwolf.txt')
##    ProcessResults('result-0425-evil-wolf-depth-2.txt')
##    ProcessResults('0426result-phrygian-bad-wolf-relax-fin.txt')

##    diff('result-0425-evil-wolf-depth-2.txt', '0426result-phrygian-bad-wolf-relax-fin.txt')
##    diff('0426result-phrygian-bad-wolf-depth-2-phrygian.txt', '0426result-phrygian-bad-wolf-relax-fin.txt')

##    ProcessResults('result-0426-good-wolf-boston-fin.txt')
##    ProcessResults('0426result-phrygian-bad-wolf-depth-2-phrygian.txt')

    ProcessResults(['result-0426-good-wolf-boston-fin.txt','0426result-phrygian-bad-wolf-depth-2-phrygian.txt'])
    ProcessResults(['result-0429-varygoal-2-depth-boston.txt'])
    ProcessResults(['0428-vary-goal-bad-wolf.txt'])
