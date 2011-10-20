from math import sqrt
from cvxopt.base import matrix
from cvxopt.blas import dot 
from cvxopt.solvers import qp
##import pylab

p = matrix([[2,0],
            [0,8]],tc='d')
q = matrix([-8,-16],tc='d')
G = matrix([[1,1,1],
            [1,0,-1],
            ],tc='d')
h = matrix([5,3,2],tc='d')

##print type(p)

res = qp(p,q,G,h)

##options['show_progress'] = False
# Problem data.
##n = 4
##S = matrix([[ 4e-2,  6e-3, -4e-3,    0.0 ], 
##            [ 6e-3,  1e-2,  0.0,     0.0 ],
##            [-4e-3,  0.0,   2.5e-3,  0.0 ],
##            [ 0.0,   0.0,   0.0,     0.0 ]])
##pbar = matrix([.12, .10, .07, .03])
##G = matrix(0.0, (n,n))
##G[::n+1] = -1.0
##h = matrix(0.0, (n,1))
##A = matrix(1.0, (1,n))
##b = matrix(1.0)
##
##print qp(S, -pbar, G, h, A, b)['y']

# Plot trade-off curve and optimal allocations.
##pylab.figure(1, facecolor='w')
##pylab.plot(risks, returns)
##pylab.xlabel('standard deviation')
##pylab.ylabel('expected return')
##pylab.axis([0, 0.2, 0, 0.15])
##pylab.title('Risk-return trade-off curve (fig 4.12)')
##pylab.yticks([0.00, 0.05, 0.10, 0.15])
##
##pylab.figure(2, facecolor='w')
##c1 = [ x[0] for x in portfolios ] 
##c2 = [ x[0] + x[1] for x in portfolios ]
##c3 = [ x[0] + x[1] + x[2] for x in portfolios ] 
##c4 = [ x[0] + x[1] + x[2] + x[3] for x in portfolios ]
##pylab.fill(risks + [.20], c1 + [0.0], '#F0F0F0') 
##pylab.fill(risks[-1::-1] + risks, c2[-1::-1] + c1, '#D0D0D0') 
##pylab.fill(risks[-1::-1] + risks, c3[-1::-1] + c2, '#F0F0F0') 
##pylab.fill(risks[-1::-1] + risks, c4[-1::-1] + c3, '#D0D0D0') 
##pylab.axis([0.0, 0.2, 0.0, 1.0])
##pylab.xlabel('standard deviation')
##pylab.ylabel('allocation')
##pylab.text(.15,.5,'x1')
##pylab.text(.10,.7,'x2')
##pylab.text(.05,.7,'x3')
##pylab.text(.01,.7,'x4')
##pylab.title('Optimal allocations (fig 4.12)')
##pylab.show()
