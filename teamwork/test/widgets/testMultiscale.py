from teamwork.math.Keys import *
from teamwork.math.KeyedMatrix import *
from teamwork.math.probability import *

from teamwork.widgets.multiscale import *

import unittest

class TestMultiscale(unittest.TestCase):

    def testBlend(self):
        color = blend('#000000','#a0e040',0.5)
        self.assertEqual(color,'#507020')
    
    def testWidget(self):
        # Set up distribution to display
        self.feature = 'containerDanger'
        self.key = StateKey({'entity':'Shipper','feature':self.feature})
        self.dist = Distribution()
        row = KeyedVector({self.key:0.0})
        self.dist[row] = 0.9
        row = KeyedVector({self.key:0.1})
        self.dist[row] = 0.1
        # Set up Tk
        self.root = Tk()
        Pmw.initialise(self.root)
        # Run widget
        marginal = self.dist.getMarginal(self.key)
        widget = DistributionScale(self.root,tag_text=self.feature,
                                   distribution=marginal)
        widget.pack(fill=X,expand=YES)
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
##        self.assertAlmostEqual(self.dist[row],0.5,9)
        
        
if __name__ == '__main__':
    unittest.main()
        
