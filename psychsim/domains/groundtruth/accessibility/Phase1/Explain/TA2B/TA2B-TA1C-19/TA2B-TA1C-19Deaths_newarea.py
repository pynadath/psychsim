"""
**Research method category**: Government Data


**Specific question**:
We would like to collect government data about the demographics, location, and evacuation / sheltered status of individuals who have died as a result of the hurricane, broken down by hurricane, for the new area (we did not receive data on deaths in the original area). Such data might be available via coroners’ or police reports, obituaries, death certificates, etc, but notionally might be identical across all these sources. 


**Other applicable detail**: Please provide whichever sources of relevant data on this that is available. 


**Research request identifier**: 19Deaths_newarea
"""
from psychsim.pwl.keys import *

from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    parser = accessibility.createParser(output='TA2B-TA1C-19Deaths_newarea.tsv')
    args = accessibility.parseArgs(parser)
    data = accessibility.loadRunData(args['instance'],args['run'])
    demos = accessibility.readDemographics(data)
    output = []
    fields = ['Timestep']+sorted(accessibility.demographics)+['Location']
    for name in data:
        key = stateKey(name,'alive')
        if key in data[name]:
            for day,alive in data[name][key].items():
                if not alive:
                    record = demos[name]
                    record['Location'] = data[name][stateKey(name,'location')][day]
                    record['Timestep'] = day
                    output.append(record)
                    break
    output.sort(key=lambda r: r['Timestep'])
    accessibility.writeOutput(args,output,fields)