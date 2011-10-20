import math

def prob(options,beta=1.):
    for myKey,myVal in options.items():
        denominator = 1.
        for yourKey,yourVal in options.items():
            if myKey != yourKey:
                delta = yourVal['value']-myVal['value']
                try:
                    denominator += math.exp(beta*delta)
                except OverflowError:
                    myVal['probability'] = 0.
                    break
        else:
            myVal['probability'] = 1./denominator
    return options

if __name__ == '__main__':
    import sys

    beta = float(sys.argv[1])*1000.
    options = {'punish':{'value':0.1390},
               'wait':{'value':0.1280}}
    print prob(options,beta)
