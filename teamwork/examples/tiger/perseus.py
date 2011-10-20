def parseADD(filename):
    # Store results in a table
    pomdp = {'data': {},
             'actions': {}}
    phase = None     # Keep track of what POMDP component we're parsing
    variable = None  # Keep track of the variable name we're parsing
    # Iterate through file
    import fileinput
    for raw in fileinput.input(filename):
        line = raw.strip()
        words = line.split()
        words = map(lambda w: w.strip(),words)
        if words[0] == '//':
            # Comment
            pass
        elif words[0] == '(variables':
            # S
            assert not pomdp.has_key('state')
            pomdp['state'] = {}
            phase = 'state'
        elif words[0] == ')':
            # End of something
            if phase == 'state':
                phase = None
        elif phase == 'state':
            # New state feature
            name = words[0][1:]
            assert not pomdp['state'].has_key(name)
            pomdp['state'][name] = raw
        elif words[0] == '(observations':
            # Omega
            assert not pomdp.has_key('omega')
            pomdp['omega'] = raw
        elif words[0] == 'init':
            # b0
            assert not pomdp.has_key('b0')
            pomdp['b0'] = raw
        elif words[0] == 'dd':
            # New decision diagram
            data = words[1]
            assert not pomdp['data'].has_key(data)
            pomdp['data'][data] = raw
            phase = 'data'
            variable = data
        elif phase == 'data':
            pomdp[phase][variable] += raw
            if words[0] == 'enddd':
                # End of decision diagram
                phase = None
                variable = None
        elif words[0] == 'action':
            # A
            assert phase is None
            phase = 'actions'
            variable = words[1]
            assert not pomdp[phase].has_key(variable)
            pomdp[phase][variable] = raw
        elif phase == 'actions':
            pomdp[phase][variable] += raw
            if words[0] == 'endaction':
                # End of action
                phase = None
                variable = None
        elif words[0] == 'reward':
            # R
            pomdp[words[0]] = raw
        elif words[0] == 'discount':
            # discount factor
            pomdp[words[0]] = raw
        elif words[0] == 'horizon':
            # horizon
            pomdp[words[0]] = raw
    return pomdp

if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser()
    # Optional argument that specifies the pomdp file
    parser.add_option('-f','--file',action='store',type='string',
                      dest='file',default=None,
                      help='POMDP ADD file')
    (options, args) = parser.parse_args()
    if options.file is None:
        parser.error('no POMDP file specified')
    pomdp = parseADD(options.file)
    # Set up Perseus
    import subprocess
    args = ['/usr/bin/java','Solver',
            options.file,'-g','-r,','1']
    proc = subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout,stderr = proc.communicate()
    proc.wait()
    # Parse results
    V = {}
    result = {}
    beliefs = {}
    phase = 'policy'
    lines = stderr.split('\n')
    row = 1
    while row < len(lines):
        if phase == 'policy':
            # Value function
            action = lines[row].strip()
            if len(action) > 0:
                if not V.has_key(action):
                    V[action] = {}
                row += 1
                feature = lines[row].split()[0].strip()
                try:
                    V[action][feature].append({})
                except KeyError:
                    V[action][feature] = [{}]
                row += 1
                while lines[row]:
                    elements = lines[row].split()
                    V[action][feature][-1][elements[0].strip()[:-1]] = float(elements[1])
                    row += 1
                row += 1
            else:
                phase = 'result'
                row += 1
        elif phase == 'result':
            # Final stats
            result['V'] = float(lines[row].split('=')[1])
            row += 1
            elements = lines[row].split()
            result['horizon'] = int(elements[0].split('=')[1])
            result['runs'] = int(elements[1].split('=')[1][:-1])
            row += 1
            result['ER'] = float(lines[row].split('=')[1])
            row += 2
            phase = 'beliefs'
        elif phase == 'beliefs':
            # Reachable belief states
#            print lines[row]
            row += 1
#     listen = V['listen']
#     openL = V['open_left']
#     openR = V['open_right']
#     for feature,vectors in openL.items():
#         if feature == 'tiger_loc':
#             for openV in vectors:
#                 for listenV in listen[feature]:
#                     if listenV['right'] > 0.:
#                         numerator = listenV['right'] - openV['right']
#                         denominator = openV['left'] - openV['right'] - listenV['left'] + listenV['right']
#                         print 'open_left if P(L) < %5.3f' % (numerator/denominator)
#     for feature,vectors in openR.items():
#         if feature == 'tiger_loc':
#             for openV in vectors:
#                 for listenV in listen[feature]:
#                     if listenV['left'] > 0.:
#                         numerator = listenV['left'] - openV['left']
#                         denominator = openV['right'] - openV['left'] - listenV['right'] + listenV['left']
#                         print 'open_right if P(R) < %5.3f' % (numerator/denominator)
    print result
