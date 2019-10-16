import argparse
import pygraphml
import logging
import os.path

import openpyxl

TA2A = {'n0': 'Dis',
    'n1': 'G_aid',
    'n10': 'Sta',
    'n11': 'Eth',
    'n12': 'Rel',
    'n13': 'Reg',
    'n14': 'Sal_f',
    'n15': '#Chi',
    'n16': 'Acq',
    'n17': 'Fri',
    'n18': 'Pet',
    'n19': 'Age',
    'n2': ' Ind',
    'n20': 'Gen',
    'n21': 'Rt',
    'n22': 'Rd',
    'n23': 'Wr',
    'n24': 'Loc',
    'n25': 'Sta',
    'n26': 'Ar',
    'n27': 'I_Rd',
    'n28': 'She',
    'n29': 'Eva',
    'n3': ' Gov',
    'n30': 'Wea',
    'n31': 'I_cat',
    'n32': 'I_rd',
    'n33': 'Sev',
    'n4': ' Media',
    'n5': ' Hur',
    'n6': ' Cate',
    'n7': ' I_Cate',
    'n8': ' I_Loc',
    'n9': ' Ris'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('workbook',default=None,help='Input Excel file')
    parser.add_argument('-d','--debug',default='INFO',help='Level of logging detail')
    args = vars(parser.parse_args())
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logging.basicConfig(level=level,filename='%s.log' % (os.path.splitext(__file__)[0]))
    wb = openpyxl.load_workbook(args['workbook'])
    parser = pygraphml.GraphMLParser()
    graphs = {team: parser.parse('%s.graphml' % (team)) for team in ['TA2A','TA2B']}
    for sheet in wb:
        team,objs = sheet.title.split()
        row = 2
        if objs == 'Nodes':
            try:
                nodes = sorted(graphs[team].nodes(),key=lambda n: int(n['label'][1:]))
            except ValueError:
                nodes = graphs[team].nodes()
            for node in nodes:
                sheet['A%d' % (row)] = node['label']
                try:
                    sheet['B%d' % (row)] = node['v_name']
                except:
                    try:
                        sheet['B%d' % (row)] = TA2A[node['label']]
                    except KeyError:
                        try:
                            sheet['A%d' % (row)] = node.id
                            sheet['B%d' % (row)] = node['name']
                        except:
                            # PNNL version
                            sheet['A%d' % (row)] = '%d' % (row-1)
                            sheet['B%d' % (row)] = node.id
                row += 1
        else:
            for edge in graphs[team].edges():
                sheet['A%d' % (row)] = edge.id
                try:
                    sheet['B%d' % (row)] = edge.node1['v_name']
                    sheet['C%d' % (row)] = edge.node2['v_name']
                except:
                    try:
                        sheet['B%d' % (row)] = TA2A[edge.node1['label']]
                        sheet['C%d' % (row)] = TA2A[edge.node2['label']]
                    except KeyError:
                        try:
                            sheet['A%d' % (row)] = edge['SUID']
                            sheet['B%d' % (row)] = edge.node1['name']
                            sheet['C%d' % (row)] = edge.node2['name']
                        except:
                            # PNNL
                            sheet['B%d' % (row)] = edge.node1.id
                            sheet['C%d' % (row)] = edge.node2.id                        
                row += 1
    wb.save('%s TA1C%s' % os.path.splitext(args['workbook']))