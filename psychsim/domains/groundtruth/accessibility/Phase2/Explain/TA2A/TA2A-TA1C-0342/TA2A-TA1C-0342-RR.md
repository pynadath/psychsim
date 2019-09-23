# Research method category #
HoloCane simulation

# Specific question #
We want to invite people to join a simulation in HoloCane, and run the simulation for the next hurricane (the simulation period starts two days before the next hurricane forms, and 3 days after the last hurricane leaves); during the process, record their attitudes and interpersonal interaction on each day.
	Please pay attention that only participants invited to the simulation exist in the simulated world, which means we are not simulating behaviors in the ground truth instance, but simulating behaviors in a different world, where it only has a population the same as 5% of original population in each instance. (and it’s indeed possible that some region has no residency in our simulation)

Data collection/preparation before simulation begins

	Part I. Individual 
       We assign an unique id (can be as simple as a participant number) to each person participating in this project. We will use this unique id to refer to people in our simulation.
For every participant, we first collect data for the
       following questions:
1. List of demographic information, and the date when information is reported, including:
a. Date
b. Age
c. Gender
d. Ethnicity
e. Pets
f. Full_time_job
g. Religion
h. Residency
2. Interpersonal relationship
		Describe your relationship with each of the other participants in the simulation(e.g. Asking participant 3 his/her relationship to participant 5, the answer is friend). 
		(If N people participant in the simulation, we should get N*(N-1) pairs of relationship)
	Part II. Hurricane generation
		We don’t specify next hurricane’s location/category/state in the simulation, and expect HoloCane to generate hurricane on its own (It can be as simple as random generation)

	Part III. Government Action
		In our simulation, we want the government to do the following things:
a. Predict hurricane as it does in simulated instance provided by the DARPA team, and spread (i.e. notify public about) the prediction in the same way as it does in simulated instance provided by the DARPA team.
b. Collect data and calculate the regional damage on a daily basis, and send aid to the region whose regional damage is the highest among all regions. 
c. Record people’s crime activities during the simulation period (we assume government have enough resources and will record any crime committed by people in simulation). Record the severity and property (e.g. cause others’ injury, cause others’ wealth loss, etc) for each instance.
d. No other actions will be done by the government in our simulation.

	Part IV. Shelter
		All policies for shelter remain the same as the last day of the instance provided by the DARPA team, and keep unchanged during our simulation period.


Data collection during simulation

	Part I: Collect data from individual participants

On each day of the simulation, record the following information for each participant

	1. Individual’s location on that day(e.g. shelter, evacuation)
	2. Whether individual hasan injury due to the hurricane (minor or serious, so the answer would be ‘Minor injury’/’Serious Injury’/’None’ on that day.
	3. Wealth net change on that day (-5 to 5)	
       4. Perceived regional damage on that day (1 to 5, 1 for lowest)


	Part II: Collect data from the government

1. We want to get data on government hurricane prediction, specifically:
a. The content of the prediction
b. When was the prediction made
c. When was the prediction propagated, and in what way/which platform
3. We want to get a complete crime record, which records the following information for each crime instance:
a. The unique id of person who conducted such crime
b. The time crime is conducted
c. The severity of this crime
d. Characteristics of this crime (i.e. target of crime - human/non-human, type of crime - robbery, vandalism, etc., extent of injury - physical/financial)
	   3. We want to get a complete record on government calculated regional damage, which records the calculated regional damage on each day, for each region (1-5, with 5 the most severe one)
	   4. A complete list of the destination and amount of aid(1 to 5 level, 5 for the most) on each day.

	
# Sampling strategy #

We randomly invite 5% of the population from the simulated world by DARPA, from all instances in Phase I and Phase II.
	(We have 2 questions in Data collection before hurricane arrives(Part I), 4 questions in Part I of Data collection during hurricane, 4 questions in Part II of Data collection during hurricane, which sum up to 10)



# Other applicable detail #

# Research request identifier #
TA2A-TA1C-0342-RR



