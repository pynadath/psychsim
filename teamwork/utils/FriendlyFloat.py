"""Conversion of float values to hide the scary scary numbers"""

# User friendly strings for thresholds
levelStrings = {-.6: 'strong negative',
                -.3: 'negative',
                0.0: 'weak negative',
                0.3: 'weak positive',
                0.6: 'positive',
                1.0: 'strong positive'
                }
_levels = levelStrings.keys()
_levels.sort()

def getLevels():
    return _levels

def simpleFloat(value):
    for level in _levels:
        if value <= level:
            return levelStrings[level]
    else:
        return 'very high'
##        raise ValueError,'Value exceeds maximum level: %5.3f' % (value)
    

    
