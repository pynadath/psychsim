import copy

def makeValues(total,num):
    interval = total/num
    return map(lambda x:x*interval,range(num+1))    

def generateCombo(total,keys,values,comboList=[{}]):
    if len(keys) > 1:
        for combo in comboList[:]:
            comboList.remove(combo)
            for value in values:
                newCombo = copy.copy(combo)
                newCombo[keys[0]] = value
                if sum(newCombo.values()) <= total:
                    comboList.append(newCombo)
        return generateCombo(total,keys[1:],values,comboList)
    else:
        for combo in comboList[:]:
            value = total - sum(combo.values())
            if not value in values:
                raise ValueError
            combo[keys[0]] = value
        return comboList
    
if __name__ == '__main__':
    import os
    
    agentCount = 100
    keys = ['OO','OP','PO','PP']
    root = os.environ['HOME']+'/python/teamwork/examples/games/PublicGood.py'
    for combo in generateCombo(agentCount,keys,
                               makeValues(agentCount,len(keys))):
        print combo
        cmd = 'python %s -l 8' % root
        for key,value in combo.items():
            cmd += ' --%s %d' % (key,value)
        output = os.popen(cmd,'r')
        data = output.read()
        output.close()
