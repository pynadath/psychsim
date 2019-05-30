import csv
import logging
import os.path
import random
import statistics

from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename=os.path.join(os.path.dirname(__file__),'TA2B-TA1C-49.log'))
    random.seed(49)
    fields = ['Timestep','Participant']+sorted(accessibility.demographics.keys())+['MoreGov','MoreMeansTestedGov',
        'MoreTaxes','MoreTaxesAndMoreDist','UnequalGovEthnicity','UnequalGovIncome', 'UnequalGovReligion', 'UnequalGovRegion']
    for instance in range(1,15):
        logging.info('Instance %d' % (instance))
        args = accessibility.instances[instance-1]
        data = accessibility.loadRunData(args['instance'],args['run'],args['span'],subs=['Input'] if instance > 2 else [None])
        demos = accessibility.readDemographics(data,last=args['span'])
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run'],'Input' if instance > 2 else None) 
            if h['End'] < args['span']]
        # Get survey pool
        if instance > 2:
            participants = accessibility.readParticipants(args['instance'],args['run'],os.path.join('Input','psychsim.log'))['ActorPostTable']
        else:
            participants = accessibility.readParticipants(args['instance'],args['run'])['ActorPostTable']
        population = accessibility.getPopulation(data)
        pool = random.sample([name for name in population if name in participants.values()],16)
        # Get some stats for later use
        aid = [action['object'] for action in data['System'][actionKey('System')].values()]
        residents = {region: {name for name in population if demos[name]['Residence'] == region} for region in data if region[:6] == 'Region'}
        residents = {region: people for region,people in residents.items() if people}
        risk = {region: sum(data[region][stateKey(region,'risk')].values()) for region in residents}
        resources = {region: sum([data[name][stateKey(name,'resources')][args['span']-1] for name in residents[region]])/\
            len(residents[region]) for region in residents}
        # Sort the regions by number of residents in each group. Then see how often aid is given to regions in the top half.        
        ethnicSplit = {'minority': sorted(list(residents.keys()),key=lambda r: -len([name for name in residents[r] if demos[name]['Ethnicity'] == 'minority'])),
            'majority': sorted(list(residents.keys()),key=lambda r: -len([name for name in residents[r] if demos[name]['Ethnicity'] == 'majority']))}
        ethnicAid = {'minority': len([obj for obj in aid if obj in ethnicSplit['minority'][:len(ethnicSplit['minority'])//2]]),
            'majority': len([obj for obj in aid if obj in ethnicSplit['majority'][:len(ethnicSplit['majority'])//2]])}
        ethnicSkew = (max(ethnicAid.values())/sum(ethnicAid.values()),'majority' if ethnicAid['majority'] > ethnicAid['minority'] else 'minority')
        wealthSplit = {'hi': sorted(list(residents.keys()),key=lambda r: -len([name for name in residents[r] if demos[name]['Wealth'] < 3])),
            'lo': sorted(list(residents.keys()),key=lambda r: -len([name for name in residents[r] if demos[name]['Wealth'] > 3]))}
        wealthAid = {'hi': len([obj for obj in aid if obj in wealthSplit['hi'][:len(wealthSplit['hi'])//2]]),
            'lo': len([obj for obj in aid if obj in wealthSplit['lo'][:len(wealthSplit['lo'])//2]])}
        wealthSkew = (max(wealthAid.values())/sum(wealthAid.values()),'hi' if wealthAid['hi'] > wealthAid['lo'] else 'lo')
        religSplit = {'minority': sorted(list(residents.keys()),key=lambda r: -len([name for name in residents[r] if demos[name]['Religion'] == 'minority'])),
            'majority': sorted(list(residents.keys()),key=lambda r: -len([name for name in residents[r] if demos[name]['Religion'] == 'majority']))}
        religAid = {value: len([obj for obj in aid if obj in regions[:len(regions)//2]]) for value,regions in religSplit.items()}
        religSkew = (max(religAid.values())/sum(religAid.values()),'majority' if religAid['majority'] > religAid['minority'] else 'minority')
        regionSplit = sorted(list(residents.keys()),key=lambda r: -aid.count(r))
        regionSkew = statistics.pstdev([aid.count(region)/len(population) for region in residents])
        logging.info('Ethnic Skew: %s' % (str(ethnicSkew)))
        logging.info('Class Skew: %s' % (str(wealthSkew)))
        logging.info('Religious Skew: %s' % (str(religSkew)))
        logging.info('Region Skew: %f' % (regionSkew))
        output = []
        cache = {'MoreGov': {},'MoreMeansTestedGov':{},'MoreTaxes':{},'MoreTaxesAndMoreDist':{},'UnequalGovEthnicity':{},
            'UnequalGovIncome': {}, 'UnequalGovReligion': {}, 'UnequalGovRegion': {}}
        for name in pool:
            participantID = accessibility.getParticipantID(name,participants)
            logging.info('Participant %d: %s' % (participantID,name))
            record = {'Timestep': args['span'],'Participant': participantID}
            record.update(demos[name])
            # 1.d.i
            try:
                record['MoreGov'] = cache['MoreGov'][demos[name]['Residence']]
            except KeyError:
                impact = (max(risk.values())-risk[demos[name]['Residence']])/(max(risk.values())-min(risk.values()))
                record['MoreGov'] = accessibility.toLikert(1.-impact)
                cache['MoreGov'][demos[name]['Residence']] = record['MoreGov']
            # 1.d.i (2nd one)
            try:
                record['MoreMeansTestedGov'] = cache['MoreMeansTestedGov'][demos[name]['Residence']]
            except KeyError:
                impact = (resources[demos[name]['Residence']]-min(resources.values()))/(max(resources.values())-min(resources.values()))
                record['MoreMeansTestedGov'] = accessibility.toLikert(1.-impact)
                cache['MoreMeansTestedGov'][demos[name]['Residence']] = record['MoreMeansTestedGov']
            # 1.d.ii
            try:
                record['MoreTaxes'] = cache['MoreTaxes'][demos[name]['Residence']]
            except KeyError:
                impact = aid.count(demos[name]['Residence'])/len(aid)
                record['MoreTaxes'] = accessibility.toLikert(impact)
                cache['MoreTaxes'][demos[name]['Residence']] = record['MoreTaxes']
            # 1.d.iii
            try:
                record['MoreTaxesAndMoreDist'] = cache['MoreTaxesAndMoreDist'][demos[name]['Residence']]
            except KeyError:
                impact = aid.count(demos[name]['Residence'])/len(aid)
                record['MoreTaxesAndMoreDist'] = accessibility.toLikert(1.-impact)
                cache['MoreTaxesAndMoreDist'][demos[name]['Residence']] = record['MoreTaxesAndMoreDist']
            # 1.d.iv
            try:
                record['UnequalGovEthnicity'] = cache['UnequalGovEthnicity'][demos[name]['Residence']]
            except KeyError:
                if demos[name]['Residence'] in ethnicSplit[ethnicSkew[1]][:len(ethnicSplit[ethnicSkew[1]])//2]:
                    # The skew favors my region
                    record['UnequalGovEthnicity'] = accessibility.toLikert(1.-ethnicSkew[0])
                else:
                    # The skew does not favor my region
                    record['UnequalGovEthnicity'] = accessibility.toLikert(ethnicSkew[0])
                cache['UnequalGovEthnicity'][demos[name]['Residence']] = record['UnequalGovEthnicity']
            # 1.d.v
            try:
                record['UnequalGovIncome'] = cache['UnequalGovIncome'][demos[name]['Residence']]
            except KeyError:
                if demos[name]['Residence'] in wealthSplit[wealthSkew[1]][:len(wealthSplit[wealthSkew[1]])//2]:
                    # The skew favors my region
                    record['UnequalGovIncome'] = accessibility.toLikert(1.-wealthSkew[0])
                else:
                    # The skew does not favor my region
                    record['UnequalGovIncome'] = accessibility.toLikert(wealthSkew[0])
                cache['UnequalGovIncome'][demos[name]['Residence']] = record['UnequalGovIncome']
            # 1.d.vi
            try:
                record['UnequalGovReligion'] = cache['UnequalGovReligion'][demos[name]['Residence']]
            except KeyError:
                if demos[name]['Residence'] in religSplit[religSkew[1]][:len(religSplit[religSkew[1]])//2]:
                    # The skew favors my region
                    record['UnequalGovReligion'] = accessibility.toLikert(1.-religSkew[0])
                else:
                    # The skew does not favor my region
                    record['UnequalGovReligion'] = accessibility.toLikert(religSkew[0])
                cache['UnequalGovReligion'][demos[name]['Residence']] = record['UnequalGovReligion']
            # 1.d.vii
            try:
                record['UnequalGovRegion'] = cache['UnequalGovRegion'][demos[name]['Residence']]
            except KeyError:
                if demos[name]['Residence'] in regionSplit[:len(regionSplit)//2]:
                    # The skew favors my region
                    record['UnequalGovRegion'] = accessibility.toLikert(.5-regionSkew)
                else:
                    # The skew does not favor my region
                    record['UnequalGovRegion'] = accessibility.toLikert(.5+regionSkew)
                cache['UnequalGovRegion'][demos[name]['Residence']] = record['UnequalGovRegion']
            output.append(record)
        accessibility.writeOutput(args,output,fields,'TA2B-TA1C-49govtapproval.tsv',
            os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
