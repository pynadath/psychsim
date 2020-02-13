# coding=utf-8import randomfrom agent import Agentfrom world import Worldfrom helper_functions import get_bivariate_samples, tree_from_bivariate_samplesfrom pwl import makeTreedef mean(samples):    sum_samples = 0.0    for sample_y in samples:        for sample in sample_y:            sum_samples += sample[2]    return sum_samples / len(samples)class BivariateExample:    def __init__(self, name, symbol, func, max_x, max_y, num_samples):        self.max_x = max_x        self.max_y = max_y        self.symbol = symbol        self.func = func        self.name = name        self.world = World()        self.agent = Agent('The Agent')        self.world.addAgent(self.agent)        self.world.setOrder([self.agent])        self.var_x = self.world.defineState(self.agent.name, 'var_x', float, lo=0, hi=max_x)        self.var_y = self.world.defineState(self.agent.name, 'var_y', float, lo=0, hi=max_y)        self.result = self.world.defineState(self.agent.name, 'result', float, lo=0, hi=func(max_x, max_y))        self.world.addDependency(self.result, self.var_x)        self.world.addDependency(self.result, self.var_y)        action = self.agent.addAction({'verb': 'operation', 'action': name})        samples = get_bivariate_samples(            func, 0, self.max_x, 0, self.max_y, num_samples, num_samples)        self.sample_mean = mean(samples)        tree = makeTree(tree_from_bivariate_samples(            self.result, self.var_x, self.var_y, samples, 0, num_samples - 1, 0, num_samples - 1))        self.world.setDynamics(self.result, action, tree)    def run_it(self):        se = 0.0        max_se = 0.0        print "*************************************"        print "Testing " + self.name + " function"        for d in range(self.max_x):            x = random.random() * self.max_x            self.world.setFeature(self.var_x, x)            y = random.random() * self.max_y            self.world.setFeature(self.var_y, y)            self.world.step()            print "_____________________________________"            print "Calculating:     " + str(x) + " " + self.symbol + " " + str(y)            real = self.func(x, y)            print "Expected result: " + str(real)            psych = float(str(self.world.getFeature(self.result)).replace("100%\t", ""))            print "PsychSim result: " + str(psych)            se += (real - psych) ** 2            max_se += (real - self.sample_mean) ** 2        num_samples = self.max_x * self.max_y        rmse = (se / num_samples) ** 0.5        max_rmse = (max_se / num_samples) ** 0.5        print "====================================="        print "RMSE      = " + str(rmse)        print "RMSE_MAX  = " + str(max_rmse)        print "_____________________________________"        print "RMSE_NORM = " + str(rmse / max_rmse)        print "*************************************"def div(x, y):    if y == 0: return float('nan')    return x / ydef mul(x, y):    return x * yBivariateExample("division", '/', div, 20, 20, 100).run_it()BivariateExample("multiplication", '*', mul, 20, 20, 100).run_it()BivariateExample("power", '^', pow, 20, 20, 100).run_it()