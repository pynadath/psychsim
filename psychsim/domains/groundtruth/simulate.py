from argparse import ArgumentParser
import csv
import logging
import os.path
from threading import Thread, current_thread
import sys
from psychsim.domains.groundtruth.simulation.data import mapFromTandE,reverseLikert
from psychsim.domains.groundtruth.simulation.create import getConfig
from psychsim.domains.groundtruth.simulation.execute import runInstance
from psychsim.domains.groundtruth.simulation.visualize import initVisualization, vizUpdateLoop
import queue



def simulateMain(sysargs,debug=False):
    if debug: print(sysargs)
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',default='WARNING',help='Level of logging detail')
    parser.add_argument('-r','--runs',default=1,type=int,help='Number of runs to run')
    parser.add_argument('--singlerun',action='store_true',help='Run only the specified run')
    parser.add_argument('-p','--profile',action='store_true',help='Profile simulation step')
    parser.add_argument('-c','--compile',action='store_true',help='Pre-compile agent policies')
    parser.add_argument('-w','--write',action='store_true',help='Write simulation definition tables')
    parser.add_argument('-v','--visualize',default=None,help='Visualization feature')
    parser.add_argument('-m','--multiprocessing',action='store_true',help='Use multiprocessing')
    parser.add_argument('--max',action='store_true',help='Select most likely outcomes')
    parser.add_argument('--hurricane',help='File containing hurricane track(s)')
    parser.add_argument('--prescription',help='File containing system-level prescription')
    parser.add_argument('--tax',action='append',help='Actor to be taxed on start')
    parser.add_argument('--aid',action='append',help='Region to be aided every day')
    parser.add_argument('--target',action='append',nargs=2,metavar=('actor','filename'),help='Prescription for individual actors')
    parser.add_argument('--TA2BTA1C10',action='store_true',help='Generate surveys as specified in TA2B-TA1C-10')
    parser.add_argument('--phase1predictshort',action='store_true',help='Apply Phase 1 Short-term Prediction Counterfactual')
    parser.add_argument('--phase1predictlong',action='store_true',help='Apply Phase 1 Long-term Prediction Counterfactual')
    parser.add_argument('--phase2predictshort',action='store_true',help='Apply Phase 2 Short-term Prediction Counterfactual')
    parser.add_argument('--phase2predictlong',action='store_true',help='Apply Phase 2 Long-term Prediction Counterfactual')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-n','--number',default=None,type=int,help='Number of hurricanes to run')
    group.add_argument('--seasons',default=None,type=int,help='Number of seasons to run')
    group.add_argument('--days',default=None,type=int,help='Number of days to run')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--rerun',action='store_true',help='Run instance, even if previously saved')
    group.add_argument('--reload',type=int,default=0,help='Pick up where instance/run left off')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--pickle',action='store_true',help='Use Python pickle, not XML, to save scenario')
    group.add_argument('--xml',action='store_true',help='Save scenario as XML')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-i','--instance',default=None,type=int,help='Instance number')
    group.add_argument('-s','--samples',default=None,help='File of sample parameter settings')
    args = vars(parser.parse_args(sysargs))
    if debug: print(args)
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logging.basicConfig(level=level)

    if args['samples']:
        with open(args['samples']) as csvfile:
            base = int(os.path.splitext(os.path.split(args['samples'])[1])[0])
            config = getConfig(base)
            reader = csv.DictReader(csvfile,delimiter='\t')
            for row in reader:
                shelters = []
                risks = []
                pets = []
                healths = []
                wealths = []
                for key,value in row.items():
                    key = key.strip()
                    if key == 'Sample ID':
                        instance = base+int(row[key])
                    elif key == '\'Actor’s distribution over gender\'':
                        value = int(value)
                        if value == 1:
                            config.set('Actors','male_prob',str(0.5))
                        elif value == 2:
                            config.set('Actors','male_prob',str(0.4))
                        else:
                            assert value == 3
                            config.set('Actors','male_prob',str(0.6))
                    elif key[:6] == 'Region' and key[-9:] == ' shelter\'':
                        if value == '1':
                            shelters.append(int(key[6:-9]))
                            config.set('Shelter','exists','yes')
                            config.set('Shelter','region','%s' % (','.join(['%02d' % (r)
                                                                            for r in shelters])))
                    elif key[:7] == 'Shelter' and key[-22:] == 'initial level of risk\'':
                        region = int(key[7:-22])
                        if region in shelters:
                            risks.append(reverseLikert[value])
                            config.set('Shelter','risk',','.join(risks))
                    elif key[:7] == 'Shelter' and key[-11:] == 'pet policy\'':
                        region = int(key[7:-11])
                        if region in shelters:
                            if value == '0':
                                pets.append('no')
                            else:
                                assert value == '1'
                                pets.append('yes')
                            config.set('Shelter','pets',','.join(pets))
                    elif key[:-2] == '\'Actor’s distribution over health: group ':
                        healths.append(str(max(min(1.,float(value)),0.2)))
                        assert int(key[-2:-1]) == len(healths)
                        config.set('Actors','health_value_age',','.join(healths))
                    elif key[:-2] == '\'Actor’s distribution over resources: group ':
                        wealths.append(str(max(min(1.,float(value)),0.2)))
                        assert int(key[-2:-1]) == len(wealths)
                        config.set('Actors','wealth_value_age',','.join(wealths))
                    else:
                        section,option,fun = mapFromTandE[key]
                        if fun is not None:
                            value = fun[value]
                        if section == 'Regions':
                            value = str(max(min(1.,float(value)),0.2))
                        config.set(section,option,value)
                with open(os.path.join(os.path.dirname(__file__),'config',
                                       '%06d.ini' % (instance)),'w') as csvfile:
                    config.write(csvfile)
                if args['visualize']:
                    myname = current_thread().name.replace("-consumer","")
                    
                    t = Thread(name=myname, target=runInstance, args=(instance,args,config,args['rerun']))
                    t.daemon = True
                    t.start()
                    #runInstance(instance,args,config,args['rerun'])
                    print("Parent Thread name is %s Child Thread name is %s"%(current_thread().name, t.name))
                else:
                    runInstance(instance,args,config,args['rerun'])
    else:
        config = getConfig(args['instance'])
        if args['visualize']:
            
            myname = current_thread().name.replace("-consumer","")

            t = Thread(name=myname,target=runInstance, args=(args['instance'],args,config,args['rerun']))
            t.daemon = True
            t.start()

            #runInstance(args['instance'],args,config,args['rerun'])
            print("Parent Thread name is %s Child Thread name is %s"%(current_thread().name, t.name))

        else:
            runInstance(args['instance'],args,config,args['rerun'])
    
    if args['visualize']:
        vizUpdateLoop()
        #exit()
        
        
if __name__ == '__main__':

    simulateMain(sys.argv[1:])