if __name__ == '__main__':
    from simulation.create import getConfig
else:
    from .simulation.create import getConfig
import csv
import sys

if __name__ == '__main__':
    configs = {int(arg): getConfig(int(arg)) for arg in sys.argv[1:]}
    instances = sorted(list(configs.keys()))
    fields = ['Section','Option']+instances
    with open('parameters.tsv','w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for section in sorted(configs[instances[0]].sections()):
            for option in sorted(configs[instances[0]].options(section)):
                record = {'Section': section,
                          'Option': option}
                for instance,config in sorted(configs.items()):
                    record[instance] = config.get(section,option,fallback=None)
                writer.writerow(record)
                
