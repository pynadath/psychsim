import fileinput
import os
if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('--solver',action='store',type='string',
                      dest='solver',default='~/Downloads/zmdp-1.1.7/bin/darwin9/zmdp',
                      help='POMDP solver directory [default: %default]')
    parser.add_option('-d','--discount',action='store',type='string',
                      dest='discount',default='1.0',
                      help='Evaluation discount factor [default: %default]')
    (options, args) = parser.parse_args()
    if len(args) < 1:
        raise UserWarning,'No .decpomdp file provided'
    elif len(args) < 2:
        raise UserWarning,'No action specified'
    decpomdp = args[0]
    policy = args[1]
    suffix = '.dpomdp'
    if decpomdp[-len(suffix):] == suffix:
        root = decpomdp[:-len(suffix)]
    else:
        root = decpomdp
    f = open('%s.pomdp' % (root),'w')
    phase = None
    O = {}
    for line in fileinput.input(decpomdp):
        elements = line.split()
        if line[0] == '#':
            pass
        elif line.strip() == '':
            pass
        elif elements[0] == 'agents:':
            num = int(elements[1])
            assert num == 2,'Unable to handle Dec-POMDPs with more than 2 agents'
        elif elements[0] in ['discount:','values:','states:','start:']:
            f.write(line)
        elif elements[0] == 'actions:':
            phase = 'actions'
            count = 0
        elif phase == 'actions':
            if count == 0:
                f.write('actions: %s' % (line))
                count += 1
            else:
                policyIndex = str(elements.index(policy))
                phase = None
        elif elements[0] == 'observations:':
            phase = 'observations'
            count = 0
        elif phase == 'observations':
            if count == 0:
                f.write('observations: %s' % (line))
                count += 1
            else:
                phase = None
        elif elements[0] == 'T:':
            if elements[2] == policy or elements[2] == policyIndex:
                del elements[7]
                del elements[2]
                f.write('%s\n' % (' '.join(elements)))
        elif elements[0] == 'O:':
            if elements[1] == '*':
                del elements[7]
                del elements[6]
                key = ' '.join(elements[:-1])
                try:
                    O[key] += float(elements[-1])
                except KeyError:
                    O[key] = float(elements[-1])
            elif elements[2] == policy or elements[2] == policyIndex:
                del elements[8]
                del elements[7]
                del elements[2]
                key = ' '.join(elements[:-1])
                try:
                    O[key] += float(elements[-1])
                except KeyError:
                    O[key] = float(elements[-1])
        elif elements[0] == 'R:':
            if O:
                for key,value in O.items():
                    f.write('%s %f\n' % (key,value))
                O.clear()
            if elements[1] == '*':
                del elements[8]
                f.write('%s\n' % (' '.join(elements)))
            elif elements[2] == policy or elements[2] == policyIndex:
                del elements[9]
                del elements[2]
                f.write('%s\n' % (' '.join(elements)))
        else:
            print line
            break
    f.close()
    os.system('%s solve -o %s.policy %s.pomdp' % \
                  (options.solver,root,root))
    f = open('%s.pomdp' % (root),'r')
    data = f.read()
    f.close()
    f = open('%s.pomdp' % (root),'w')
    f.write('discount: %s\n' % (options.discount))
    f.write(data[data.find('\n'):])
    f.close()
    os.system('%s eval --evaluationMaxStepsPerTrial 100 --evaluationTrialsPerEpoch 1000 --policyInputFile %s.policy %s.pomdp' % \
                  (options.solver,root,root))
    os.system('%s eval --evaluationMaxStepsPerTrial 1000 --evaluationTrialsPerEpoch 1000 --policyInputFile %s.policy %s.pomdp' % \
                  (options.solver,root,root))
