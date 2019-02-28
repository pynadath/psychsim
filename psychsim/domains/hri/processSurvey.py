import argparse

import xlrd
import unicodedata
from collections import OrderedDict
import numpy as np


def generate_label(dictionary):
    list_fields = ['pred','human','robot_current','robot_prev','PredispositionToTrust','PropensityToTrust','ComplacencyPotential','NARS','EmotionalUncertainty','DesireForChange','CognitiveUncertainty','M1ExplanationType']
    string = ''
    for key in list_fields:
        # print 'order',key
        if key in dictionary:
            # print 'accessed',key
            string = string + str(dictionary[key]) + ' '
    # print'\n'


    # string += str(dictionary['pred'])
    # string += ' '
    # string += str(dictionary['human'])
    # string += ' '
    # string += str(dictionary['robot'])
    # string += ' '
    # string += str(dictionary['PredispositionToTrust'])
    # string += ' '
    # string += str(dictionary['PropensityToTrust'])
    # string += ' '
    # string += str(dictionary['ComplacencyPotential'])
    # string += ' '
    # string += str(dictionary['NARS'])
    # string += ' '
    # string += str(dictionary['EmotionalUncertainty'])
    # string += ' '
    # string += str(dictionary['DesireForChange'])
    # string += ' '
    # string += str(dictionary['CognitiveUncertainty'])
    # string += ' '
    # string += str(dictionary['M1ExplanationType'])
    # for key in dictionary:
    #     str += dictionary[key]
    return string[:-1]

# def marginalize(lis):
#     list_fields = ['pred','human','robot','PredispositionToTrust','PropensityToTrust','ComplacencyPotential','NARS','EmotionalUncertainty','DesireForChange','CognitiveUncertainty','M1ExplanationType']
#     indices = []
#     for i in lis:
#         ind = list_fields.index(i)
#         indices.append(ind)
#     labels = []
#     for


#Open workbook
workbook = xlrd.open_workbook('Survey_Log_All_WP.xlsx')
sheet = workbook.sheet_by_name('Sheet1')
num_rows = sheet.nrows
field_names = {}
columns = [0,5,6,7,8,9,10,11,12,13,14,15,16,17,22]
vals = {'confidence':1,'none':0}
data = {}
for row in range(num_rows):
    name = None
    for column in columns:
        if row == 0:
            field_names[column] = unicodedata.normalize('NFKD', sheet.cell(row,column).value).encode('ascii','ignore')
            # print type(unicodedata.normalize('NFKD', sheet.cell(row,column).value).encode('ascii','ignore'))
            continue
        if column == 0:
            # print len(field_names)
            data[unicodedata.normalize('NFKD', sheet.cell(row,column).value).encode('ascii','ignore')] = {}
            name = unicodedata.normalize('NFKD', sheet.cell(row,column).value).encode('ascii','ignore')
            # print (name,type(name))
        elif column < 11:
            continue
            data[name][field_names[column]] = unicodedata.normalize('NFKD', sheet.cell(row,column).value).encode('ascii','ignore')
        else:
            if column == 22 and name in data:
                data[name][field_names[column]] = vals[unicodedata.normalize('NFKD', sheet.cell(row,column).value).encode('ascii','ignore')]
                continue
            if isinstance(sheet.cell(row,column).value,str):
                if name in data:
                    print('No info for:',name)
                    del data[name]
                continue
            if name == 'WP023':
                if name in data:
                    print('Outlier:',name)
                    del data[name]
                continue
            data[name][field_names[column]] = sheet.cell(row,column).value

print(field_names)
print('\n\n')
import pprint
pp = pprint.PrettyPrinter()
# pp.pprint(data)

print(len(data))
print(sorted(data.keys()))

# Checking file
# f_check = open('checker.csv','w')
# cntr = 0
# for dummy in sorted(data.keys()):
#     str_write = str(dummy)+','
#     str_dum = 'ID,'
#     for dummy2 in sorted(data[dummy].keys()):
#         if cntr == 0:
#             str_dum = str_dum + str(dummy2) + ','
#         str_write = str_write + str(data[dummy][dummy2])+','
#
#     if cntr == 0:
#         f_check.write(str_dum[:-1]+'\n')
#     f_check.write(str_write[:-1]+'\n')
#     cntr+= 1
# f_check.close()



Map = {'WP071':'WP011',
        'WP075':'WP074',
        'WP102':'WP102/TO105',
        'WP047':'wp047'                 }
# Now get the corresponding sequences in the game
#Open WPdata file
fil = open('wpdata.csv','r')
check = list(data.keys())
lines = fil.readlines()
seq_data = {}
for num in lines[1:]:
    line = num.strip().split(',')
    if line[0] in Map:
        n = Map[line[0]]
    else:
        n = line[0]
    if n in check:
        if line[2] == '1': # Checking the data only for the first mission
            seq_data[n] = line[8]



for name in sorted(data.keys()):
    if name in seq_data:
        data[name]['sequence'] = seq_data[name]
        print(name,'     ',seq_data[name])


# Create probabilities
discretize = {}
for main_key in sorted(data[list(data.keys())[0]].keys()):
    discretize[main_key] = []
    for key in sorted(data.keys()):
        discretize[main_key].append(data[key][main_key])
# pp.pprint(discretize)


discretization_values = {}
for key in list(discretize.keys()):
    if key == 'sequence' or key == 'M1ExplanationType':
        continue
    discretization_values[key] = np.median(discretize[key])

# print discretization_values



# Now dicretize the values in the data dictionary
data_discretized = dict(data)
for key in sorted(data_discretized.keys()):
    for second_key in discretization_values:
        if data_discretized[key][second_key] < discretization_values[second_key]:
            data_discretized[key][second_key] = 0
        else:
            data_discretized[key][second_key] = 1

# pp.pprint(data_discretized)


#checking file after discretization
# f_check = open('checker_discrete.csv','w')
# cntr = 0
# for dummy in sorted(data_discretized.keys()):
#     str_write = str(dummy)+','
#     str_dum = 'ID,'
#     for dummy2 in sorted(data_discretized[dummy].keys()):
#         if cntr == 0:
#             str_dum = str_dum + str(dummy2) + ','
#         str_write = str_write + str(data_discretized[dummy][dummy2])+','
#
#     if cntr == 0:
#         f_check.write(str_dum[:-1]+'\n')
#     f_check.write(str_write[:-1]+'\n')
#     cntr+= 1
# f_check.close()



# Generate probabilities for single step
# mission1_robot_prev = [0,0,0,0,0,0,0,1,0,1,0,1,0,0]
select_measures = ['PredispositionToTrust']
Total_features = ['PredispositionToTrust','PropensityToTrust','ComplacencyPotential','NARS','EmotionalUncertainty','DesireForChange','CognitiveUncertainty','M1ExplanationType']

def analyze_measure(select_measures,step):
    mission1_robot_current = [0,0,0,0,0,0,0,1,0,1,0,1,0,0,2]
    probs_one = {}
    value_human = {'f':1,'i':0}
    robot_strmap = {0:'Sc',1:'Ui',2:'Uc'}
    total_count = 0
    previous_flag = step>0
    prev_len = step
    features_flag = True
    cntr = 1
    main_features = ['M1ExplanationType']
    #if you are trying to enter multiple measures please enter them in the same order as mentioned in Total_features comment above
    for key in sorted(data_discretized.keys()):
        # print 'accessing the data for:',key
        if features_flag:
            new_dict = OrderedDict(data_discretized[key])
            # print new_dict.keys()
            for key_del in new_dict:
                if key_del not in main_features:
                    del new_dict[key_del]
                else:
                    if cntr == 1:
                        print(key_del)
            cntr += 1
        else:
            new_dict = OrderedDict()
        prev = None
        for start in range(len(data_discretized[key]['sequence'])):
            if previous_flag:
                if prev is None:
                    if prev_len == start:
                        prev = data_discretized[key]['sequence'][start-prev_len:start][::-1]
                    else:
                        continue

            total_count += 1.0
            # new_dict['pred'] = value_human[data_discretized[key]['sequence'][start]]
            # new_dict['pred'] = data_discretized[key]['sequence'][start]
            if previous_flag:
                new_dict['human'] = ''
                for char in prev:
                    # new_dict['human'] += str(value_human[char])
                    new_dict['human'] += char
            # new_dict['robot_current'] = mission1_robot_current[start]
            new_dict['robot_current'] = robot_strmap[mission1_robot_current[start]]
            if previous_flag:
                if prev is not None:
                    # new_dict['robot_prev'] = mission1_robot_prev[start-1]
                    new_dict['robot_prev'] = ''
                    for value_recom in mission1_robot_current[start-prev_len:start][::-1]:
                        new_dict['robot_prev'] += robot_strmap[value_recom]

            # print new_dict
            label = generate_label(new_dict)
            if label in probs_one:
                if len(select_measures) == 0:
                    probs_one[label] += 1.0
                else:
                    measure_string = data_discretized[key]['sequence'][start] + ' '
                    for measure in select_measures:
                        measure_string = measure_string + str(data_discretized[key][measure]) + ' '
                    if measure_string[:-1] in probs_one[label]:
                        probs_one[label][measure_string[:-1]] += 1.0
                    else:
                        probs_one[label][measure_string[:-1]] = 1.0
                    # for measure in select_measures:
                    #     if data_discretized[key][measure] == 1:
                    #         probs_one[label][measure] += 1.0
                    #     else:
                    #         probs_one[label]['~'+measure] += 1.0
            else:
                if len(select_measures) == 0:
                    probs_one[label] = 1.0
                else:
                    probs_one[label] = OrderedDict()
                    measure_string = data_discretized[key]['sequence'][start] + ' '
                    for measure in select_measures:
                        measure_string = measure_string + str(data_discretized[key][measure]) + ' '
                    probs_one[label][measure_string[:-1]] = 1.0
                        # if data_discretized[key][measure] == 1:
                        #     probs_one[label][measure] = 1.0
                        #     probs_one[label]['~'+measure] = 0.0
                        # else:
                        #     probs_one[label][measure] = 0.0
                        #     probs_one[label]['~'+measure] = 1.0

            prev = data_discretized[key]['sequence'][start-prev_len+1:start+1][::-1]
    return probs_one
# break

def process_dict(dummy_probs):
    result = {}
    for dummy_key in sorted(dummy_probs.keys()):
        result[dummy_key] = {}
        # Accessing the specific meaure
        print('Accessing measure',dummy_key)
        for record in dummy_probs[dummy_key]:
            result[dummy_key][record] = []
            #get all the values for each row of records
            values =  dummy_probs[dummy_key][record]
            total_low = 0.0
            total_high = 0.0
            high_value_follow = 0.0
            low_value_follow = 0.0
            for pointers in values:
                pointers_split = pointers.split(' ')
                if pointers_split[1] == '0':
                    if pointers_split[0] == 'f':
                         low_value_follow += dummy_probs[dummy_key][record][pointers]
                    total_low += dummy_probs[dummy_key][record][pointers]
                elif pointers_split[1] == '1':
                    if pointers_split[0] == 'f':
                         high_value_follow += dummy_probs[dummy_key][record][pointers]
                    total_high += dummy_probs[dummy_key][record][pointers]
                else:
                    print('invalid_record')





                if total_low == 0:
                    result[dummy_key][record] = [abs((high_value_follow/total_high)),total_high+total_low,'low is zero']

                elif total_high == 0:
                    result[dummy_key][record] = [abs((low_value_follow/total_low)),total_high+total_low,'high is zero']

                else:

                    if (high_value_follow/total_high) > (low_value_follow/total_low):
                        # high greater than low
                        temp_val = 'high'
                    elif (high_value_follow/total_high) == (low_value_follow/total_low):
                        temp_val = 'equal'
                    else:
                        temp_val = 'low'

                    result[dummy_key][record] = [abs((high_value_follow/total_high)-(low_value_follow/total_low)),total_high+total_low,temp_val]


    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-l','--length',default=0,type=int,
                        help='length of prior history [default: %(default)s]')
    args = vars(parser.parse_args())

    all_dicts = {}
    step = args['length']
    file = open('Anaalysis_step='+str(step)+'.csv','w')
    for i in Total_features:
        probs_one = analyze_measure([i],step)
        print('\n\n\n')
        print('The one step probabilities')
        list_fields = ['pred','human','robot_current','robot_prev','PredispositionToTrust','PropensityToTrust','ComplacencyPotential','NARS','EmotionalUncertainty','DesireForChange','CognitiveUncertainty','M1ExplanationType']
        # print 'These are the fields in order that appear in the label:',select_features
        print(i)
        pp.pprint(probs_one)
        all_dicts[i] = dict(probs_one)
    pr = process_dict(all_dicts)
    pp.pprint(process_dict(all_dicts))
    file.write('measure,event,difference,total people,Direction\n')
    for temp in pr:
        for rows in sorted(pr[temp].keys()):
            file.write(str(temp)+','+str(rows)+','+str(pr[temp][rows][0])+','+str(pr[temp][rows][1])+','+pr[temp][rows][2]+'\n')
        file.write('\n')
    file.close()
        # for temp in probs_one:
        #     probs_one[temp] = probs_one[temp]/total_count
        # print total_count
        # pp.pprint(probs_one)
