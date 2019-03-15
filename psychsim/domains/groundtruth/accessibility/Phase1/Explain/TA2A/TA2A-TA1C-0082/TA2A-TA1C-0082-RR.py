"""

Research method category:
Simulated Experiment

Specific Question:
A group of researchers in this world will run a simulated hurricane experiment. Residents of the world will “experience” one hurricane lasting 8 days (including the landing time and before landing time, which is similar in length to hurricanes 1 and 6 in the actual world, and which is also the shortest among all known hurricanes), as described in the vignette detailed below. We will also consider 5 days after the hurricane leaves. This is a total of 13 days in our simulated vignette experiment. The detailed setting of the experiment is provided below:

0) The game is hosted at timestep 82. All of the timesteps listed in our simulation file is an offset to timestep 82 (e.g. timestep 1 is indeed timestep 83, calculated as 82 + 1）

1) All residents will be informed that they should consider themselves beginning the simulated event with a risk level 1 and dissatisfaction level 1 in the simulation. The simulation starts at time step 1, ends at time step 12. All residents should consider their wealth level staying the same when they participate in the simulation (which they will report in part 2). We assume no one has any injury, no one is in the evacuation state at time step 1) 

2) Before the simulation begins, all participants in the simulation should fill out a form, providing basic information about themselves, they should provide this information exactly the same way that they provide the true information in the real world (world created by TA1). This information includes:
    i) All Demographic information(Age, gender, ethnicity, religion, pets, number of children, full time job [also report the salary volume, level 1 to 5, 5 for the most] each time they receive it, and the frequency they get paybacks), residence)
    ii) How many acquaintances do they have in the actual world; how many close friends do they have in the actual world; if there are other identities in one’s social network except for close friends/acquaintances/families, please specify and tell us the number of people with this identity there are in the actual world.
(We now know the number of friends/acquaintances can be dynamic, so people need to report their current social network when they participate in the simulation)
    iii) How many acquaintances do they have among the people participating in our simulation? How many close friends do they have among the people participating in our simulation? Tell us the unique IDs of all their acquaintances in this simulation, and specify whether you give and receive support from them and the frequency for giving/receiving support as it would occur in the actual world. Tell us the unique IDs of all their close friends in this simulation, and specify whether you exchange information (e.g. hurricane category, etc.) with them and the frequency for information exchange as it is in the actual world. If people report other types of identities in the social network and if these people participate in our simulation, tell us the number and unique ID (This will be done as such: all participants in the simulation will be given a unique ID in the world, one’s ID is known to all other participants, and each person will only need to write down the ID to tell us who his/her acquaintances/close friends are.)

3) After that, we will begin our simulation. 
The information needed for individuals to make decision/change attitudes are specified below:

File 1. Simulated Hurricane

Describe the hurricane category and location in the simulated world.

Time    Category    Location    Landed
1   2   Region05    no
2   2   Region05    no
3   3   Region05    no
4   3   Region05    yes
5   3   Region06    yes
6   3   Region07    yes
7   3   Region07    yes
8   3   Region03    leaving

File 2. SimulatedAid

Describe the government in the simulated world.
Timestep    Region
1   None
2   None
3   None
4   None
5   None
6   None
7   None
8   None
9   Region06
10  Region06
11  Region06
12  Region06
13  Region09

1. None stands for no aid at corresponding time step
2. For Region0X, we will randomly select one people in that region to provide aid(We will record the unique ID of people who receives that aid at each timestep)
3. The strength of aid is the same for all aids.

File 3. SimulatedInjury

Record all minor/serious injuries caused by hurricane in our simulated world.
Timestep    Injury in Region06  Injury in Region09  
1   No  injuries            No injuries 
2   No  injuries            No injuries 
3   No  injuries            No injuries 
4   One minor injury for an adult in Region06   No injuries 
5   Another single minor injury for an adult in Region06    One serious injury for an adult in Region09 
6   No injuries Another single minor injury for an adult in Region09    
7   No injuries Another single minor injury for a child in Region09 
8   Another single minor injury for a child in Region06 No any injuries 
9   No injuries No injuries 
10  No injuries No injuries 
11  No injuries No injuries 
12  No injuries No injuries 
13  No injuries No injuries 
            
            
This table simulates how many and how serious the injuries are for people caused by hurricane strike, there is no other injuries caused by any reason in this simulated world except for those written in this table)           
1. Any minor/serious injury will only last for one day in the simulation (They get hurt at time t, and fully recover/gets out of the hospital at time t+1)          
2. When we say one minor/seriuos injury for adult/child in Region0X, we mean we randomly select one adult/child to suffer injury in our simulated world, and of course we will record the unique ID of people suffering minor/serious injury(If it's child, record the ID of their parent(If they have 2 parenets participating in the game, record both with a note)           
3. Minor injury stated here means injury that doesn't require hospitalization; Serious injury stated here means injury which requires hospitalization           
4. Injury states at each timestep means how many people "get" injured at that time, not how many people "are still" injuried at that time           

    
File 4. SimulatedAssetLoss
Record all asset loss caused by hurricane in our simulated world.
Timestep    Wealth Decrease in Region06 Wealth Decrease in Region09 
1   No wealth loss  No wealth loss  
2   No wealth loss  No wealth loss  
3   No wealth loss  No wealth loss  
4   No wealth loss  No wealth loss  
5   No wealth loss  No wealth loss  
6   Wealth decrease by 1 for 1 adult in Region06    No wealth loss  
7   Another wealth decrease by 1 for 1 adult in Region06    No wealth loss  
8   No wealth loss  Wealth decrease by 2 for 1 adult in Region09    
9   No wealth loss  No wealth loss  
10  No wealth loss  No wealth loss  
11  No wealth loss  No wealth loss  
12  No wealth loss  No wealth loss  
13  No wealth loss  No wealth loss  
            
            
This table describes all wealth loss caused by the hurricane in our simulated world. It doesn't include the wealth loss caused by spending money on evacuation, hospitalization or other reasons.           
1. When we say wealth decrease by X for Y adult in Region0Z, we mean that we randomly select one people in the region(whose wealth is higher than X), and decrease their wealth by X. We will record the unique ID of person who is chosen to loss asset in the simulation.         

File 5. SimulatedWeatherPrediction

Record weather prediction provided by the government.
       Timestep Hurricane   Predicted Timestep  Location
       1    1   3   Region05
       1    1   4   Region06
       1    1   5   Region07
       1    1   6   Region08
       1    1   7   none(leaving)
       1. Timestep stands for the time when the prediction is conducted, location is the predicted hurricane location at the predicted timestep
       2. Government will publicize the prediction at time step 1, and use any possible ways to spread this prediction so that more people can know
       3. Hurricane category is predicted to be of category 2 for all timesteps.

File 6. SimulatedRegionalDamage
Simulated regional damage will be as follows:
Timestep    Region  DamageLevel
1   Region06    none
2   Region06    none
3   Region06    none
4   Region06    1
5   Region06    1
6   Region06    3
7   Region06    4
8   Region06    5
9   Region06    5
10  Region06    4
11  Region06    3
12  Region06    2
13  Region06    1
1   Region09    none
2   Region09    none
3   Region09    none
4   Region09    1
5   Region09    2
6   Region09    3
7   Region09    4
8   Region09    5
9   Region09    5
10  Region09    4
11  Region09    3
12  Region09    2
13  Region09    1

File 7. Simulated Social information(Not really a file, just a description)
    Every single timestep, we have public social outlets broadcast the hurricane category, hurricane location, regional damage level, government regional aid. The values for this information is exactly the same as the simulated value in File 1-6. 

       Regional damage will be recorded and collected by the government, and broadcast to the public daily, the location and category of hurricanes, which we also know will be broadcasted daily by government, will be exactly the same as the simulated hurricane location and category on each day in our simulated world.
Important, please note:
i) For other information which is not stated in our simulation, we want participants to assume that it runs following the same rule as in the actual world(the world created by TA1). 
E.g. We don’t state how often people get paid and what is the salary in our simulation; people should assume that it is the same as salary in the actual world. If they have trouble doing that, please report in part 5.
ii) Because we now know that even if the “level number” is the same for risk injury, wealth and some other variables, the exact number can be different. Thus, for any variables whose initial value is specified by us, we assume that the exact number is a possible minimal value for the specified level. 
E.g. We say all individuals start with dissatisfaction level 1. If the exact number of dissatisfaction is 1 to 100, with 1 - 20 defined as level 1, all individual should start with exact dissatisfaction value 1, which is the minimal possible exact value for dissatisfaction level 1.

4) We want to ask following questions about people’s opinions before the simulation begins:

Part 1) How do you agree with the following sentences:[All answers are on a 1 to 5 scale, 1 for strongly disagree, 5 for strongly agree]
1. I am sensitive to the (potential) physical injury the hurricane would cause when I make a decision about whether to evacuate or not.
2. I am sensitive to (potential) asset loss the hurricane would cause when I make decision about whether to evacuate or not.
   c) I believe that the government should provide me with aid if I suffer wealth loss during the previous hurricane.
   d) I believe that the government should provide me with aid if I incur a minor injury (not requiring evacuation) during the previous hurricane.
   e) I believe that the government should provide me with aid if I incur a serious injury (requiring evacuation) during the previous hurricane.
   f) I believe that the government should provide me with aid if my children incur minor injuries (not requiring evacuation) during the previous hurricane.
   g) I believe that the government should provide me with aid if my children incur serious injuries (requiring evacuation) during the previous hurricane.
   h) I am willing to provide my acquaintances with financial support.
   i) I am willing to provide my acquaintances with non-financial support.
   j) I would frequently ask my acquaintances for support.
   k) I would frequently seek information about the hurricane from the social sources.
   l) I would frequently seek information about the hurricane from my friends.
   

5) We want to collect the following information from all simulation participants during the simulation:
    i) Unique ID of the information provider.
    ii) How well prepared(e.g. Reinforce the house, store food and clean water, etc.) does this person think he/she is for the incoming hurricane at each time step before the hurricane lands. (Range 1 - 5, with 5 being the most well-prepared)
    iii) The number of friends and acquaintances at each timestep.
    iv) The frequency for them to receive salary (e.g. Every X days), and the amount of salary received at each time (e.g., on a 1 to 10 scale, corresponds to wealth level 1 - 5, if salary is 2, it means every X days, they receive a salary that can improve their wealth level by 1. If they have a salary, but it’s lower than level 1, they should say “less than 1”; if they have no salary, they should say no; We also ask these questions to those who do not have a full-time job in the world).
    v) If a friend of yours asks you the hurricane category, what would you say to them? Record the answer for each timestep.
    vi) Whether this person is at evacuation state (Not asking whether they evacuated before) at each time step.
vii) Whether this person suffers from minor injury (not
requiring hospitalization) at each timestep; Whether this person suffers from serious injury (requiring hospitalization) at each timestep? (Both pieces of information are provided at each time step, and note all injury in our world only lasts for 1 day, which means one cannot be in an “injured state” for consecutive days)
    viii) The wealth level of this person at each time step. 
    ix) The dissatisfaction level of this person at each time step.
    x) The risk/severity level of this person at each time step.(Severity for pre-hurricane strike, risk for post/during hurricane strike)
    xi) Whether this person chooses to be in the shelter(not asking whether they went there before) at each time step.
xii) Questions about the money people choose to spend (All information is requested at each timestep):
     -- How much does this person spend on evacuation at the current timestep(range 1-15, 15 for the most money spent, N/A if no money is spent).
     -- How much does this person spend on hospitalization at the current timestep(range 1-15, 15 for the most money spent, N/A if no money is spent).
     -- How much does this person spend on treating minor injury at the current timestep(excluding the money spent on hospitalization, range 1-15, 15 for the most money spent, N/A if no money is spent).
     -- How much does the hurricane cause asset damage to this person at the current timestep (range 1-15, 15 for the most money spent, N/A if no asset damage occurs).
        Note: The expense scale(1-15) should be reported based on the objective amount of net asset loss, and has nothing to do with people’s subjective opinion(e.g. poor people may think $1000 is a big amount of money and report a high scale expense while the rich people do not report it as such).
            Answers of expense scale for all questions should be on the same basis and their report should be comparable. (e.g. $1000 spent on evacuation/hospitalization should all be reported as X (X is one of 1-15 or N/A), it cannot be the case that $1000 for evacuation is measured as 7 while $1000 for hospitalization is measured as 4).
    xiii) Record all instance of “making new friends/acquaintances” or “losing new friends/acquaintances” at each timestep. Use the following format for recording:


T8, player ID 0001 becomes acquainted with player ID 0008.

6) We want to collect the following information after the simulation
    i)The unique ID representing the person we select to 
          -- suffer physical injury (list minor and serious injury differently)
          -- suffer asset loss (and also list the level of asset loss, e.g. reduce by 2)
          -- receive government aid 
      at each time step.
    ii) For all participants, we ask what information is missing in the simulation which makes it hard for them to answer/report certain values. Please describe with as much detail as possible.



Sampling Strategy:
    We want to find people in region 09 and region 06 to conduct the simulation(9 adults in total, almost 5% of the overall population).


Other applicable detail:

Research request identifier: TA2A-TA1C-0082-RR
"""
import logging
import os.path
import random
from psychsim.pwl.keys import *
from psychsim.agent import Agent
from psychsim.domains.groundtruth import accessibility

nature = [{'category': 2, 'location': 'Region05', 'phase': 'approaching'},
    {'category': 2, 'location': 'Region05', 'phase': 'approaching'},
    {'category': 3, 'location': 'Region05', 'phase': 'approaching'},
    {'category': 3, 'location': 'Region05', 'phase': 'active'},
    {'category': 3, 'location': 'Region06', 'phase': 'active'},
    {'category': 3, 'location': 'Region07', 'phase': 'active'},
    {'category': 3, 'location': 'Region07', 'phase': 'active'},
    {'category': 3, 'location': 'Region03', 'phase': 'active'},
    {'category': 0, 'location': 'none', 'phase': 'none'},
    {'category': 0, 'location': 'none', 'phase': 'none'},
    {'category': 0, 'location': 'none', 'phase': 'none'},
    {'category': 0, 'location': 'none', 'phase': 'none'},
    {'category': 0, 'location': 'none', 'phase': 'none'},
    ]

system = ['doNothing','doNothing','doNothing','doNothing','doNothing','doNothing','doNothing','doNothing',
    'Region01','Region01','Region01','Region01','Region05']

injuries = [{},{},{},{'Region01': {'minor': 1}},
    {'Region01': {'minor': 2}, 'Region05': {'serious': 1}},
    {'Region05': {'serious': 1,'minor': 1}},
    {'Region05': {'serious': 1,'minor': 1,'child': 1}},
    {'Region01': {'child': 1}},{},{},{},{},{},
    ]

damage = {'Region01': [0,0,0,1,1,3,4,5,5,4,3,2,1],
    'Region05': [0,0,0,1,2,3,4,5,5,4,3,2,1]}

prediction = [{},{},{'perceivedCenter': 'Region05','perceivedCategory': 2}]
if __name__ == '__main__':
    parser = accessibility.createParser(output='TA2A-TA1C-0082-RR.tsv',seed=True)
    args = accessibility.parseArgs(parser,'%s.log' % (os.path.splitext(__file__)[0]))
    random.seed(args['seed'])
    world = accessibility.loadPickle(args['instance'],args['run'],82)
    world.agents['System'].addAction({'verb': 'doNothing'})

    data = accessibility.loadRunData(args['instance'],args['run'],82)
    network = accessibility.readNetwork(args['instance'],args['run'])
    census = accessibility.readDemographics(data)
    population = {name for name in world.agents if name[:5] == 'Actor' and world.getState(name,'alive').first()}
    pool = random.sample(population,8)
    participant = {pool[i]: i+1 for i in range(len(pool))}
    # 2 & 4
    aidConditions = ['Wealth Loss','Minor Injury','Serious Injury','Children Minor Injury','Children Serious Injury']
    aidItems = ['Aid If %s' % (c) for c in aidConditions]
    fields = ['Participant']+sorted(list(accessibility.demographics.keys()))+\
        ['Friends','Acquaintances','Injury Sensitivity','Asset Loss Sensitivity']+aidItems+\
        ['Provide Financial','Provide Non-Financial','Ask for Support','Info from Social','Info from Friends']
    output = []
    for name in pool:
        agent = world.agents[name]
        assert agent.getState('health').first() == float(data[name][stateKey(name,'health')][82])
        record = {'Participant': participant[name]}
        logging.info('Participant %d: %s' % (participant[name],name))
        record.update(census[name])
        record['Friends'] = len(network['friendOf'].get(name,set()))
        record['Acquaintances'] = len(network['neighbor'].get(name,set()))
        # Evacuation decision
        record['Injury Sensitivity'] = accessibility.toLikert(agent.Rweights['health']/sum(agent.Rweights.values()))
        record['Asset Loss Sensitivity'] = accessibility.toLikert(agent.Rweights['resources']/sum(agent.Rweights.values()))
        # Government aid
        value = accessibility.toLikert(sum([agent.Rweights[k] for k in ['health','childrenHealth','neighbors']])/sum(agent.Rweights.values()))
        for field in aidItems:
            record[field] = value
        # Provide support
        record['Provide Financial'] = 1
        record['Provide Non-Financial'] = accessibility.toLikert(agent.Rweights['neighbors']/sum(agent.Rweights.values()))
        record['Ask for Support'] = 1
        record['Info from Social'] = 1
        record['Info from Friends'] = 1
        output.append(record)
    accessibility.writeOutput(args,output,fields,'TA2A-TA1C-0082-Participants.tsv')
    # Simulation
    output = []
    fields = ['Timestep','Participant','Preparedness','Friends','Acquaintances','Category to Friend','Evacuated',
        'Minor Injury','Serious Injury','Wealth','Dissatisfaction','Risk/Severity','At Shelter',
        'Evacuation Spending','Hospitalization Spending','Minor Injury Spending','Asset Damage']
    for name in pool:
        agent = world.agents[name]
        belief = agent.getBelief()
        assert len(belief) == 1
        model,belief = next(iter(belief.items()))
        health = stateKey(name,'health')
        if float(belief[health]) < 0.4:
            world.setFeature(health,0.4,belief)
        wealth = stateKey(name,'resources')
        oldWealth = accessibility.toLikert(float(world.getFeature(wealth,belief)))
        for t in range(len(nature)):
            for turn in ['Actor','System','Nature']:
                print(t+1,turn)
                if turn == 'Actor':
                    V = []
                    for action in agent.getActions(belief):
                        V.append((agent.value(belief,action,model,updateBeliefs=False)['__EV__'],action))
                    action = max(V)[1]
                    result = world.step(actions={name: action},state=belief,keySubset=belief.keys())
                elif turn == 'System':
                    for action in world.agents[turn].getActions(belief):
                        if system[t] == 'doNothing':
                            if action['verb'] == system[t]:
                                break
                        elif action['verb'] == 'allocate' and action['object'] == system[t]:
                            break
                    else:
                        raise ValueError('Unable to find action: %s' % (system[t]))
                    world.step({turn: action},belief,keySubset=belief.keys())
                elif turn == 'Nature':
                    world.step(state=belief,keySubset=belief.keys())
                    # Simulated Hurricanes
                    for feature,value in nature[t].items():
                        key = stateKey(turn,feature)
                        if world.value2float(key,value) in belief[key].domain():
                            belief[key] = world.value2float(key,value)
                        else:
                            world.setFeature(key,value,belief)
                else:
                    raise NameError(turn)
                for dist in belief.distributions.values():
                    dist.prune(agent.epsilon)
                if False:
                    # Simulated injuries
                    injuryCount = injuries[t].get(agent.home,{})
                    value = max(belief[health].domain())
                    if value < 0.2 and injuryCount.get('serious',0) == 0:
                        # No serious injuries!
                        world.setFeature(health,0.2,belief)
                    elif value < 0.4 and injuryCount.get('minor',0) == 0:
                        # No minor injuries!
                        world.setFeature(health,0.4,belief)
                    else:
                        dist = belief.distributions[belief.keyMap[health]]
                        for vector in dist.domain():
                            if vector[health] < 0.2:
                                if injuryCount.get('serious',0) == 0:
                                    del dist[vector]
                            elif vector[health] < 0.4:
                                if injuryCount.get('minor',0) == 0:
                                    del dist[vector]
                        dist.normalize()
                    key = stateKey(name,'childrenHealth')
                    if key in belief:
                        dist = belief.distributions[belief.keyMap[key]]
                        for vector in dist.domain():
                            if vector[key] < 0.4:
                                if injuryCount.get('child',0) == 0:
                                    del dist[vector]
                        dist.normalize()
                        assert len(dist) > 0
                # Simulated Asset Loss
                value = accessibility.toLikert(float(world.getFeature(wealth,belief)))
                assert value == oldWealth
                oldWealth = value
                # Simulated Weather Prediction
                if t == 0 and turn == 'Nature':
                    omega = stateKey(name,'perceivedCategory')
                    assert 2 in belief[omega].domain()
                    belief[omega] = 2
                    omega = stateKey(name,'perceivedCenter')
                    assert world.value2float(omega,'Region05') in belief[omega].domain()
                    belief[omega] = world.value2float(omega,'Region05')
                # Simulated Regional Damage
                if agent.home in damage:
                    value = damage[agent.home][t]
                    key = stateKey(agent.home,'risk')
                    if value == 0:
                        if float(belief[key]) > 0.:
                            world.setFeature(key,0.,belief)
                    elif accessibility.toLikert(float(belief[key])) != value:
                        world.setFeature(key,accessibility.likert[5][value-1],belief)
                # 5
                if turn == 'Nature':
                    record = {'Timestep': t+1,
                        'Participant': participant[name],
                        'Preparedness': 6-accessibility.toLikert(float(belief[stateKey(name,'risk')])),
                        'Friends': len(network['friendOf'].get(name,set())),
                        'Acquaintances': len(network['neighbor'].get(name,set()))}
                    dist = world.getState('Nature','category',belief)
                    if len(dist) == 1:
                        record['Category to Friend'] = dist.first()
                    else:
                        record['Category to Friend'] = int(round(dist.expectation()))
                    if record['Category to Friend'] == 0:
                        record['Category to Friend'] = 'N/A'
                    assert len(belief[stateKey(name,'location')]) == 1
                    record['Evacuated'] = 'yes' if belief[stateKey(name,'location')].first() == 'evacuated' else 'no'
                    dist = belief[health]
                    prob = sum([dist[v] for v in dist.domain() if 0.2 <= v < 0.4])
                    record['Minor Injury'] = 'yes' if prob > 0.5 else 'no'
                    prob = sum([dist[v] for v in dist.domain() if v < 0.2])
                    record['Serious Injury'] = 'yes' if prob > 0.5 else 'no'
                    output.append(record)
                    record['Wealth'] = accessibility.toLikert(belief[stateKey(name,'resources')].expectation())
                    record['Dissatisfaction'] = accessibility.toLikert(belief[stateKey(name,'grievance')].expectation())
                    raise NotImplementedError('There is a bug in the test of "approaching" that needs to be fixed')
                    if nature[t]['category'] == 'approaching':
                        record['Risk/Severity'] = record['Category to Friend']
                    else:
                        record['Risk/Severity'] = accessibility.toLikert(belief[stateKey(name,'risk')].expectation())
                    record['At Shelter'] = 'yes' if belief[stateKey(name,'location')].first() == 'shelter11' else 'no'
                    record['Evacuation Spending'] = 'N/A'
                    record['Hospitalization Spending'] = 'N/A'
                    record['Minor Injury Spending'] = 'N/A'
                    record['Asset Damage'] = 'N/A'
                    record['Friend Change'] = 'none'
                    record['Acquaintance Change'] = 'none'
    output.sort(key=lambda r: (int(r['Timestep']),int(r['Participant'])))
    accessibility.writeOutput(args,output,fields)
