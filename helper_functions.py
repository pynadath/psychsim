"""
    PsychSim helper functions for dynamics
"""

from world import *


# setToScaledMatrix(Val_to_set,Val_to_scale,numerator,denominator,knot_size,1) the fourth argument sets knot spacing
def setToScaledKeyMatrix(SetVar, V, numerator, denominator, inc,
                         i=1.0):  # simple switch function to handle whether numerator is staekey or a constant
    if (isinstance(numerator, int) or isinstance(numerator, float)):
        return setToScaledDenKeyMatrix(SetVar, V, numerator + inc / 2, denominator, inc,
                                       i=1.0)  # STACY ADDED THRESHOLD
    else:
        return setToScaledKeysMatrix(SetVar, V, numerator, denominator, inc, i, inc / 2)  # STACY ADDED THRESHOLD


### This assumes numerator is a python number and denominator is a statekey
def setToScaledDenKeyMatrix(SetVar, V, numerator, denominator, inc,
                            i):  # dummbest way (would want line segments or at least a balanced tree)
    if (i < inc):
        return setToConstantMatrix(SetVar, 0)  # supply insufficient so set N to 0
    else:
        return {'if': multiCompareRow({denominator: i}, threshold=numerator),
                # are scaled cases greater than supply
                True: setToScaledDenKeyMatrix(SetVar, V, numerator, denominator, inc, i - inc),
                # recurse with a reduced proportion
                False: setToFeatureMatrix(SetVar, V, i)}  # Scale Nonurgent by i


### This assumes both numerator and denominator are statekeys
def setToScaledKeysMatrix(SetVar, V, numerator, denominator, inc, i=1.0,
                          threshold=0):  # dummbest way (would want line segments or at least a balanced tree)
    if i < inc:
        return setToConstantMatrix(SetVar, 0)  # supply insufficient so set N to 0
    else:
        return {'if': multiCompareRow({denominator: i, numerator: -1.0}, threshold),
                # are scaled cases greater than supply
                True: setToScaledKeysMatrix(SetVar, V, numerator, denominator, inc, i - inc, threshold),
                # recurse with a reduced proportion
                False: setToFeatureMatrix(SetVar, V, i)}  # Scale Nonurgent by i


def setToMinMatrix(Key, Ckey1, Ckey2):
    return {'if': differenceRow(Ckey1, Ckey2, 0.0),
            True: setToFeatureMatrix(Key, Ckey2),
            False: setToFeatureMatrix(Key, Ckey1)}


def setToMaxMatrix(Key, Ckey1, Ckey2):
    return {'if': differenceRow(Ckey1, Ckey2, 0.0),
            True: setToFeatureMatrix(Key, Ckey1),
            False: setToFeatureMatrix(Key, Ckey2)}


# this function just illustrates the guts of conditional tests
def multiCompareRow(ScaledKeys, threshold=0.0):  # scales and sums all the keys and
    # print "scaledcompare", ScaledKeys
    return KeyedPlane(KeyedVector(ScaledKeys), threshold)  # then tests if > threshold


def multiSetMatrix(Key,
                   ScaledKeys):  # scales and sums all the keys in ScaledKeys dict and adds offset if CONSTANT in ScaledKeys
    # print ScaledKeys
    return KeyedMatrix({Key: KeyedVector(
        ScaledKeys)})  # then sets Key which may be in ScaledKeys in which case it is adding to scaled value of Key


def setToDivideMatrix(set_var, numerator, denominator, inc=0.01, i=1.0):
    if i < inc:
        return setToConstantMatrix(set_var, 0)
    else:
        if isinstance(numerator, int) or isinstance(numerator, float):
            div_mat = scaleMatrix(set_var, numerator * i)
        else:
            div_mat = setToFeatureMatrix(set_var, numerator, i)
        return {'if': multiCompareRow({denominator: i}, 1.00000001),
                True: setToDivideMatrix(set_var, numerator, denominator, inc, i - inc),
                False: div_mat}


def setToMultiplyMatrix(set_var, a, b, inc=0.01, i=1.0):
    if i < inc:
        return setToConstantMatrix(set_var, 0)
    else:
        if isinstance(a, int) or isinstance(a, float):
            mul_mat = scaleMatrix(set_var, a * (1 / i))
        else:
            mul_mat = setToFeatureMatrix(set_var, a, 1 / i)
        return {'if': multiCompareRow({b: i}, 1.00000001),
                True: setToMultiplyMatrix(set_var, a, b, inc, i - inc),
                False: mul_mat}


def get_univariate_samples(fnc, min_x, max_x, num_samples):
    samples = []
    step = (max_x - min_x) / float(num_samples)
    for i in range(num_samples):
        x = min_x + (i * step)
        samples.append(tuple((x, fnc(*[x]))))
    return samples


def get_bivariate_samples(fnc, min_x, max_x, min_y, max_y, num_x_samples, num_y_samples):
    samples = []
    step_x = (max_x - min_x) / float(num_x_samples)
    step_y = (max_y - min_y) / float(num_y_samples)
    for i in range(num_x_samples):
        x = min_x + (i * step_x)
        samples_y = []
        for j in range(num_y_samples):
            y = min_y + (j * step_y)
            samples_y.append(tuple((x, y, fnc(*[x, y]))))
        samples.append(samples_y)
    return samples


def tree_from_univariate_samples(set_var, x_var, samples, idx_min, idx_max):
    if idx_min == idx_max:
        return setToConstantMatrix(set_var, samples[idx_max][1])
    idx = ((idx_max + idx_min) / 2)
    x = samples[idx][0]
    return {'if': multiCompareRow({x_var: -1}, -x),
            True: tree_from_univariate_samples(set_var, x_var, samples, idx_min, idx),
            False: tree_from_univariate_samples(set_var, x_var, samples, idx + 1, idx_max)}


def tree_from_bivariate_samples(set_var, x_var, y_var, samples, idx_x_min, idx_x_max, idx_y_min, idx_y_max):
    if idx_x_min == idx_x_max and idx_y_min == idx_y_max:
        return setToConstantMatrix(set_var, samples[idx_x_max][idx_y_max][2])
    if idx_x_min == idx_x_max:
        idx_y = ((idx_y_max + idx_y_min) / 2)
        y = samples[idx_x_max][idx_y][1]
        return {'if': multiCompareRow({y_var: -1}, -y),
                True: tree_from_bivariate_samples(
                    set_var, x_var, y_var, samples, idx_x_min, idx_x_max, idx_y_min, idx_y),
                False: tree_from_bivariate_samples(
                    set_var, x_var, y_var, samples, idx_x_min, idx_x_max, idx_y + 1, idx_y_max)}
    idx_x = ((idx_x_max + idx_x_min) / 2)
    x = samples[idx_x][0][0]
    return {'if': multiCompareRow({x_var: -1}, -x),
            True: tree_from_bivariate_samples(
                set_var, x_var, y_var, samples, idx_x_min, idx_x, idx_y_min, idx_y_max),
            False: tree_from_bivariate_samples(
                set_var, x_var, y_var, samples, idx_x + 1, idx_x_max, idx_y_min, idx_y_max)}


def set_action_legality(agent, action, legality=True, models=[True]):
    """
    Sets legality for an action for the given agent and model
    :param Agent agent: the agent whose models we want to set the action legality
    :param Action action: the action for which to set the legality
    :param bool legality: whether to set this action legal (True) or illegal (False)
    :param list models: the list of models for which to set the action legality
    """
    model_key = modelKey(agent.name)

    # initial tree (end condition is: 'not legality')
    tree = not legality

    # recursively builds legality tree by comparing the model's key with the index of the model in the state/vector
    for model in models:
        tree = {'if': equalRow(model_key, agent.model2index(model)),
                True: legality,
                False: tree}
    agent.setLegal(action, makeTree(tree))


def set_illegal_action(agent, action, models=[True]):
    """
    Sets an illegal action for the given agent model only
    :param Agent agent: the agent whose models we want to set the action legality
    :param Action action: the action for which to set the legality
    :param list models: the list of models for which to set the action legality
    """
    set_action_legality(agent, action, False, models)


def set_legal_action(agent, action, models=[True]):
    """
    Sets a legal action for the given agent model only
    :param Agent agent: the agent whose models we want to set the action legality
    :param Action action: the action for which to set the legality
    :param list models: the list of models for which to set the action legality
    """
    set_action_legality(agent, action, True, models)


def get_current_reward(agent, world, model=True):
    """ Gets the agent's reward for the current state of the world """
    return agent.reward(world.state[None], model)


def get_variable(world, feature):
    """ Gets a feature's full information """
    return world.variables[feature]


def create_discretized_reward_tree(world, feature, num_groups):
    """ Creates a reward tree that returns a discretized value of the given feature. """
    variable = get_variable(world, feature)
    high = variable['hi']
    low = variable['lo']
    samples = get_samples(low, high, num_groups)
    return reward_tree_from_univariate_samples(feature, samples, 0, num_groups)


def reward_tree_from_univariate_samples(x_var, samples, idx_min, idx_max):
    """ Creates a tree that returns the sample that is closest to the current value of the given variable. """
    if idx_min == idx_max:
        return KeyedVector({CONSTANT: samples[idx_max]})
    idx = ((idx_max + idx_min) / 2) + 1
    x = samples[idx]
    return {'if': multiCompareRow({x_var: 1}, x),
            True: reward_tree_from_univariate_samples(x_var, samples, idx, idx_max),
            False: reward_tree_from_univariate_samples(x_var, samples, idx_min, idx - 1)}


def get_samples(min_x, max_x, num_samples):
    """ Gets a list containing the specified number of samples in the given interval. """
    samples = []
    step = (max_x - min_x) / float(num_samples)
    for i in range(num_samples):
        samples.append(min_x + (i * step))
    samples.append(max_x)
    return samples


def discretize_feature(world, feature, num_groups):
    """ Discretizes the given feature's value/distribution according to the number of intended groups """
    variable = get_variable(world, feature)
    high = variable['hi']
    low = variable['lo']
    ran = float(high - low)
    dist = world.getFeature(feature)
    new_dist = Distribution()
    for key in dist:
        val = dist[key]
        key = float(key)
        key = int(round((float(key - low) / ran) * num_groups)) * (ran / num_groups) + low
        new_dist[key] = val
    world.setFeature(feature, new_dist)


def set_discretized_feature(world, feature, value, num_groups):
    """ Discretizes the given value according to the number of intended groups and sets the value to the feature """
    variable = get_variable(world, feature)
    high = variable['hi']
    low = variable['lo']
    ran = high - low
    value = int(round((float(value - low) / ran) * num_groups)) * (ran / num_groups) + low
    world.setFeature(feature, value)


def set_discretized_state(agent, feature, value, num_groups):
    """ Discretizes the given value according to the number of intended groups and sets the value to the feature """
    variable = get_variable(agent.world, stateKey(agent, feature))
    high = variable['hi']
    low = variable['lo']
    ran = high - low
    value = int(round((float(value - low) / ran) * num_groups)) * (ran / num_groups) + low
    agent.setState(feature, value)


def div(x, y):
    if y == 0:
        return 0
    return x / y


def square(x):
    return x * x


def mult(x, y):
    return x * y


class DecisionInfo(object):
    def __init__(self):
        self.value = .0
        self.reward = .0
        self.horizons_left = 0
        self.actions = {}
        self.state = {}


def get_decision_info(step, decision_agent_name):
    # checks no decisions, return empty list
    if len(step) == 0:
        return []

    # collects decision info for the agent
    decision = step[0]['decisions'][decision_agent_name]
    dec_info = DecisionInfo()

    # gets planned action (what agent decided to do)
    action = decision['action']

    # check if agent does not have values (only had one action available)
    if 'V' not in decision:
        # return info about the action
        dec_info.actions[decision_agent_name] = action
        for feat_name, feat_value in step[0]['new'].items():
            dec_info.state[feat_name] = feat_value
        return [dec_info]

    # otherwise, get info on the optimal action by the agent
    action_info = decision['V'][action]

    # gets planning decisions
    projection = [action_info[key] for key in action_info.keys() if key != '__EV__'][0]['projection']

    # checks for no projection (no planning)
    if len(projection) == 0:
        return []

    projection = projection[0]

    # collects actions planned for all agents
    if 'actions' in projection:
        for ag_name, ag_action in projection['actions'].items():
            dec_info.actions[ag_name] = str(next(iter(ag_action)))

    # collects state at this horizon
    for feat_name, feat_value in projection['state'].items():
        dec_info.state[feat_name] = feat_value

    # collects other info
    dec_info.value = float(projection['V'])
    dec_info.reward = float(projection['R'])
    dec_info.horizons_left = int(projection['horizon'])

    # adds next planning horizon
    decision_infos = get_decision_info(projection['projection'], decision_agent_name)
    decision_infos.insert(0, dec_info)
    return decision_infos


IGNORE_FEATURES = {'_model', '_turn'}


def explain_decisions(ag_name, decision_infos):
    print('=============================================')
    print('{}\'s planning ({} steps)'.format(ag_name, len(decision_infos)))

    for i in range(len(decision_infos)):
        dec_info = decision_infos[i]

        print('\t---------------------------------------------')
        print('\tPlan horizon {} ({} left):'.format(i, dec_info.horizons_left))

        print('\t\tProjected agents\' actions:')
        for ag_act_name, ag_action in dec_info.actions.items():
            print('\t\t\t{}: {}'.format(ag_act_name, ag_action))
        print('\t\t---------------------------------------------')
        print('\t\tProjected resulting state:')
        for feat_name, feat_val in dec_info.state.items():
            if feat_name == '' or any(ignore in feat_name for ignore in IGNORE_FEATURES):
                continue
            print('\t\t\t{}: {}'.format(feat_name, feat_val))
        print('\t\t---------------------------------------------')
        print('\t\tReward received (by {}): {}'.format(ag_name, dec_info.reward))
        print('\t\tValue (for {}): {}'.format(ag_name, dec_info.value))
