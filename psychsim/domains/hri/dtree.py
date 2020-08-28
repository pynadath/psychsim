import numpy as np
import pandas as pd
from collections import defaultdict
from pprint import pprint
import pydotplus
import os
from datetime import date


def preprocess(table):
    dic = defaultdict(list)
    # Categories
    # cat = ['NBCsensor', 'camera', 'microphone','action']
    # Preprocessing of Data
    for key in table:
        for i in key:
            dic[i[0]].append(i[1])
        dic['action'].append("Protected" if np.argmax(np.asarray(table[key])) == 0 else "Unprotected")
    return pd.DataFrame(data=dic)



# Structure of tree
class dtree:
    def __init__(self):
        self.name = 'Unassigned'
        self.child = {}
        self.parent = None
        # self.distrib = defaultdict(dict)

# Calculate Entropy
def entropy(data, attr):
    unique_vals = data[attr].unique()
    ent = 0
    for val in unique_vals:
        prob = data[attr].value_counts()[val] / data[attr].count()
        ent -= np.multiply(prob, np.log2(prob))
    return ent


# Calculate Information Gain
def info_gain(data, attr, label):
    unique_vals = data[attr].unique()
    ig = entropy(data, label)
    for val in unique_vals:
        is_val = data[(data[attr] == val)]
        ig -= np.divide(np.multiply(data[attr].value_counts()[val], entropy(is_val, label)), data[attr].count())
    return ig


# Assert if tree should terminate here
def termination(data, attr, label):
    unique_vals = data[attr].unique()
    for val in unique_vals:
        is_val = data[(data[attr] == val)]
        if len(is_val[label].unique()) > 1:
            return False
    return True


# Construction of tree
def con(data, cat, label, node,uv ,db ):
    best = float('-inf')
    best_cat = None
    for c in cat:
        ic = info_gain(data, c, label)
        if ic > best:
            best = ic
            best_cat = c
    node.name = best_cat
    bc_vals = data[best_cat].unique()
    for val in bc_vals:
        n_val = data[(data[best_cat]==val)]
        # node.distrib[val]["Protected"] = n_val[n_val.action == 'Protected'].shape[0]
        # node.distrib[val]["Unprotected"] = n_val[n_val.action == 'Unprotected'].shape[0]
    # node.distrib = dict(node.distrib)
    end = termination(data, best_cat, label)
    if end == True or len(cat) <= 1:
        for vals in uv[node.name]:
            is_val = data[(data[node.name] == vals)]
            if len(is_val) == 0:
                is_val = db[(db[node.name] == vals)]
            node.child[vals] = is_val[label].mode()[0]
        return node
    cat.remove(best_cat)
    for val in uv[node.name]:
        is_val = data[(data[node.name] == val)]
        if len(is_val) == 0:
            is_val = db[(db[node.name] == val)]
            node.child[val] = is_val[label].mode()[0]
            continue
        if len(is_val[label].unique().tolist()) == 1:
            node.child[val] = is_val[label].mode()[0]
            continue
        nnode = dtree()
        node.child[val] = con(is_val, cat[:], label, nnode,uv,db)
        nnode.parent = node.name
    return node


# Query the tree
def query(q, node,l_vals):
    if node.child[q[node.name]] not in l_vals:
        name = query(q, node.child[q[node.name]],l_vals)
    else:
        name = node.child[q[node.name]]
    return name

def nodesDTree(nodes,node,l_vals):
    nodes.add(node.name)
    for c in node.child:
        if node.child[c] not in l_vals:
            nodesDTree(nodes,node.child[c],l_vals)
    return nodes

def represent(node,l_vals):
    dic_temp = {}
    for c in node.child:
        if node.child[c] in l_vals:
            dic_temp[c] = node.child[c]
        else:
            dic_temp[c] = represent(node.child[c],l_vals)
    # return {node.name: [node.distrib,dic_temp]}
    return {node.name: dic_temp}

def representChanges(node,l_vals,arr):
    dic_temp = {}
    for c in node.child:
        if node.child[c] in l_vals:
            dic_temp[c] = node.child[c]
        else:
            dic_temp[c] = representChanges(node.child[c],l_vals,arr)
    # return {node.name: [node.distrib,dic_temp]}
    x=node.name
    if node in arr:
        x=node.name.upper()
    return {x: dic_temp}
    
def visit(graph,dic, parent=None,changed = False,edge = False):
    for k,v in dic.items():
        if not changed:
            change = True if str(k).isupper() else False
        else:
            change = True
        if isinstance(v, dict):
            if parent:
                if str(k) in {'True','False','nobody','suspicious','friendly'}:
                    graph.add_node(pydotplus.Node(str(parent) + '_' + str(k) + '_' + str(list(v.keys())[0]), label=str(list(v.keys())[0]),
                                                  shape= 'ellipse'))
                    graph.add_edge(
                        pydotplus.Edge(str(parent), str(parent) + '_' + str(k) + '_'+str(list(v.keys())[0]), color='red' if change else 'black',
                                       label=str(k)))
                    visit(graph,v, str(parent) + '_' + str(k) + '_' + str(list(v.keys())[0]),changed=change)
                else:
                    visit(graph,v, str(parent),changed=change)
            else:
                if str(k) not in {'True', 'False', 'nobody', 'suspicious', 'friendly'}:
                    graph.add_node(pydotplus.Node(str(k), label=str(k)))
                visit(graph,v, str(k),changed=change)
        else:
            # graph.add_node(pydotplus.Node(str(parent) + '_' + str(k), label=str(k),shape = 'box' if str(k) in {'True','False','nobody','suspicious','friendly'} else 'ellipse'))
            graph.add_node(pydotplus.Node(str(parent) + '_' + str(k) + '_' + str(v), label=str(v)))
            # graph.add_edge(pydotplus.Edge(str(parent), str(parent) + '_' + str(k),color = 'red' if change else 'black'))
            graph.add_edge(pydotplus.Edge(str(parent),str(parent) + '_' + str(k) + '_' + str(v),color = 'pink' if change else 'green',label = str(k)))



def visualizeTree(dic,name,type,changed = False,cwd = None,username = "autotest"):
    graph = pydotplus.Dot(graph_type='graph')
    print(dic)
    visit(graph,dic)
    if not cwd:
        cwd = os.getcwd()
    if not os.path.isdir(cwd + "\\" + "media"):
        os.mkdir(cwd + "\\" + "media")
    today = str(date.today())
    if not os.path.isdir(cwd + "\\" + "media" + '\\' + 'dtree'):
        os.mkdir(cwd + "\\" + "media" + '\\' + 'dtree')
    if not os.path.isdir(cwd + "\\" + "media"+ '\\' + 'dtree' + "\\"+username):
        os.mkdir(cwd + "\\" + "media"+ '\\' + 'dtree' + "\\"+username)
    if not os.path.isdir(cwd + "\\" + "media"+ '\\' + 'dtree' + "\\"+username + '\\' + type):
        os.mkdir(cwd + "\\" + "media"+ '\\' + 'dtree' + "\\"+username+ '\\' + type)
    if changed:
        if not os.path.isdir(cwd + "\\" + "media"+ '\\' + 'dtree' + "\\"+username+ '\\' + type+ "\\" + "changed"):
            os.mkdir(cwd + "\\" + "media"+ '\\' + 'dtree' + "\\"+username+ '\\' + type + "\\" + "changed")
        graph.write_png(
            cwd + "\\" + "media"+ '\\' + 'dtree' + "\\"+username+ '\\' + type +  "\\" + "changed" + "\\" + str(name) + '.png')
    graph.write_png( cwd + "\\" + "media"+ '\\' + 'dtree' + "\\"+ username+ '\\' + type +"\\"+ str(name) + '.png')
    return ( '/dtree/'+ username+ '/' + type +"/"+ str(name) + '.png')




def create_dtree(table):
    # Structure of tree
    root = dtree()
    db = preprocess(table)
    label = 'action'
    cat = ['NBCsensor','camera','microphone'] if len(next(iter(table))) == 3 else ['NBCsensor','camera','microphone','location']
    # print(cat)
    uv = {}
    for c in cat:
        uv[c] = db[c].unique().tolist()
    l_vals = db[label].unique().tolist()

    # Actual construction of Tree
    con(db.copy(), cat[:], label, root,uv,db)

    # # Query params
    # q = {'Occupied': 'Moderate', 'Price': 'Cheap', 'Music': 'Loud', 'Location': 'City-Center', 'VIP': 'No',
    #      'Favorite Beer': 'No'}
    # print('Query: ' + str(query(q, root,l_vals)))

    # Finding Error Rate
    mismatch = 0
    count = 0
    for i, rows in db.iterrows():
        ans = query(rows, root,l_vals)
        if ans != rows[label]:
            mismatch += 1
        count = i
    count += 1
    print("Error " + str(mismatch / count))

    # Printing the Tree
    # dec_tree = represent(root,l_vals)
    # pprint(dec_tree)
    return root
