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

       0. Background information (mainly demographic variables)
	i) Tell us the following information
a. Age
b. Gender
c. Ethnicity
d. Religion
e. Number of children
f. Full_time_job (yes/no)
g. Pets (yes/no)
h. Location of residence
i. Wealth (on the day answering our question)
j. The date answering the question
k. Number of family living in the same region as you
l. Number of family living out of your own region, but in the area
m. Number of family living out of the area
n. Number of friends living in the same region as you
o. Number of friends living out of your own region, but in the area
i. Label the region where those friends are in, respectively (e.g. I live in region01, I have two friends living out of region01, one inregion03, another inregion09)
p. Number of friends living out of the area
q. Number of acquaintances living in the same region as you
r. Number of acquaintances living out of your own region, but in the area
 . Label the region where those acquaintances are in, respectively (e.g. I live in region01, I have two acquaintances living out of region01, one inregion03, another inregion09)
s. Number of acquaintances living out of the area
t. Do you have family members other than yourself, and your children?
       ii)How much do you agree with the following sentence (0-6 scale, with 0 for completely disagree, 6 for 100 percent agree)
a. I should receive government aid if I suffer wealth loss
b. I think I’m vulnerable to hurricanes.
c. I’m willing to stay at home (no shelter or evacuation) during hurricane.
        (Following are on aid willingness)
d. I’m willing to give aid to people below 20 year old
e. I’m willing to give aid to people in their 20s
f. I’m willing to give aid to people in their 30s
g. I’m willing to give aid to people in their 40s
h. I’m willing to give aid to people in their 50s
i. I’m willing to give aid to people in their 60s
j. I’m willing to give aid to people in their 70s
k. I’m willing to give aid to people over 80 year-old
l. I’m willing to give aid to female people
m. I’m willing to give aid to male people
n. I’m willing to give aid to people of minority ethnicity
o. I’m willing to give aid to people of majority ethnicity
p. I’m willing to give aid to people of minority religion
q. I’m willing to give aid to people of majority religion
r. I’m willing to give aid to people of none religion
s. I’m willing to give aid to people with no children
t. I’m willing to give aid to people with 1 child
u. I’m willing to give aid to people with 2 children
v. I’m willing to give aid to people with full time job
w. I’m willing to give aid to people without full time job
x. I’m willing to give aid to people with pets
y. I’m willing to give aid to people without pets
z. I’m willing to give aid to people whose wealth level is 5
aa. I’m willing to give aid to people whose wealth level is 4
bb. I’m willing to give aid to people whose wealth level is 3
cc. I’m willing to give aid to people whose wealth level is 2
dd. I’m willing to give aid to people whose wealth level is 1
ee. I’m willing to give aid to people whose wealth level is 0
	  (The following are on social capital variables)
ff. Most people would try to take advantage of me if they got a chance during hurricane
gg. Generally speaking, most people can be trusted during hurricane

1. Identify closeness with other participants.
		For each participant, we ask them to:
a. Describe your relationship with each other participant (e.g. family, friends, acquaintances, strangers)
b. Label your closeness with each other participant (0-6, 0 for least close, 6 for closest)
			* As we will only invite 5% of the total population to join the simulation, it only adds around 10*2 simple questions to each individual, which should be OK, we hope.

	Part II. Hurricane generation
		We don’t specify next hurricane’s location/category/state in the simulation, and expect HoloCane to generate hurricane on its own (It can be as simple as random generation)

	Part III. Government Action
		In our simulation, we want the government to do the following things:
1. Predict hurricane as it does in simulated instance provided by the DARPA team, and spread the prediction in the same way as it does in simulated instance provided by the DARPA team.
2. Collect data and calculate the regional damage on a daily basis, and send aid to the region whose regional damage is the highest among all regions. 
3. Record people’s crime activities during the simulation period (we assume government have enough resources and will record any crime committed by people in simulation). Record the severity and property (e.g. cause others’ injury, cause others’ wealth loss, etc) for each instance.
4. No other actions will be done by the government in our simulation.

	Part III. Shelter
		All policies for shelter remain the same as the last day of the instance provided by the DARPA team, and keep unchanged during our simulation period.


Data collection during simulation

	Part I: Collect data from individual participants

On each day of the simulation, record the following information for each participant

       On each day, record the following information for each participants
a. Date
b. Wealth level (0 - 5, 0 for lowest)
c. Reported risk (same as the one in post-hurricane tabel, 1 - 5, 1 for lowest)
d. Reported severity(same as the one in pre-hurricane table, 1 - 5, 1 for lowest)
e. Reported dissatisfaction (1 - 5, 1 for lowest)
f. Location (shelter, evacute, in its own region but out of its house, in its own region and in its house)
		* Note: Question 1-2 in both f.i and f.ii should be answered only if they shelter/evacuate, but question	3-7 should be answered in any case, since even if they didn’t evacuate/shelter, they can still tell others that they are about to evacuate/shelter.
i. Shelter
1. Do you shelter with your children (NA if no children)
2. Do you shelter with your pets (NA if no pets)
3. Do you tell your friends that you are going to shelter?
4. How likely are you going to tell your friends that you are going to shelter on that day? (regardless of whether you indeed tell them the shelter decision)
5. Do you tell your acquaintances that you are going to shelter?
6. How likely are you going to tell your acquaintances that you are going to shelter on that day? (regardless of whether you indeed tell them the shelter decision)
7. Do you tell strangers that you are going to shelter?
8. How likely are you going to tell strangers that you are going to shelter on that day? (regardless of whether you indeed tell them the shelter decision)
9. Do you post on social media that you are going to evacuate, or tell some news agency(newspaper, ect) that you are going to shelter?
10. How likely are you going to post on social media that you are going to shelter on that day? (regardless of whether you indeed post the shelter decision)
11. Do you tell the government (e.g. report to some government offices) that you are going to shelter?
12. How likely are you going to tell the government that you are going to shelter on that day? (regardless of whether you indeed tell them  the shelter decision)
		ii.   Evacuation
1. Do you evacuate with your children (NA if no children)
2. Do you evacuate with your pets (NA if no pets)
3. Do you tell your friends that you are going to evacuate?
4. How likely are you going to tell your friends that you are going to evacuate on that day? (regardless of whether you indeed tell them the evacuation decision)
5. Do you tell your acquaintances that you are going to evacuate?
6. How likely are you going to tell your acquaintances that you are going to evacuate on that day? (regardless of whether you indeed tell them the evacuation decision)
7. Do you tell strangers that you are going to evacuate?
8. How likely are you going to tell strangers that you are going to evacuate on that day? (regardless of whether you indeed tell them the evacuation decision)
9. Do you post on social media that you are going to evacuate, or tell some news agency(newspaper, ect) that you are going to evacuate?
10. How likely are you going to post on social media that you are going to evacuate on that day? (regardless of whether you indeed post the evacuation decision)
11. Do you tell the government (e.g. report to some government offices) that you are going to evacuate?
12. How likely are you going to tell the government that you are going to evacuate on that day? (regardless of whether you indeed tell them  the evacuation decision)

g. Perceived serious injury possibility(0-6, 0 for lowest)
h. Perceived minor injury possibility(0-6, 0 for lowest)
i. Perceived shelter possibility(0-6, 0 for lowest)
j. Perceived evacuate possibility(0-6, 0 for lowest)
k. Do you receive government aid on this day?
l. Do you receive aid from acquaintances on this day?
m. Do you give aid to acquaintances on this day?
n. Do you receive salary from work on this day?
o. Hurricane location heard from social media on this day (NA if not hear location on this day)
p. Hurricane category heard from social media on this day (NA if not hear location on this day)
q. Hurricane category heard from friends on this day (NA if not hear location on this day)

r. The number of friends newly injured(only serious injury) on that day, heard from social media (exclude directly communicating with friends on social media)
s. The number of friends newly injured(only serious injury) on that day, heard from friends
t. The number of friends in injury state(only serious injury) on that day, heard from social media (exclude directly communicating with friends on social media)
u. The number of friends in injury state(only serious injury) on that day, heard from friends
v. The number of friends newly injured(both serious and minor injury) on that day, heard from social media (exclude directly communicating with friends on social media)
w. The number of friends newly injured(both serious and minor injury) on that day, heard from friends
x. The number of friends in injury state(both serious and minor injury) on that day, heard from social media (exclude directly communicating with friends on social media)
y. The number of friends in injury state(both serious and minor injury) on that day, heard from friends

z. The number of friends going to evacuation on that day, heard from social media(exclude directly communicating with friends on social media)
aa. The number of friends going to evacuation on that day, heard from friends 
bb. The number of friends coming back from evacuation on that day, heard from social media(exclude directly communicating with friends on social media)
cc. The number of friends coming back from evacuation on that day, heard from friends 
dd. The number of friends going to shelter on that day, heard from social media(exclude directly communicating with friends on social media)
ee. The number of friends going to shelter on that day, heard from friends.
ff. The number of friends going to shelter on that day, known by personal observation
gg. The number of friends coming back from shelter on that day, heard from social media(exclude directly communicating with friends on social media)
hh. The number of friends coming back from shelter on that day, heard from friends.
ii. The number of friends coming back from shelter on that day, known by personal observation

jj. The number of acquaintances newly injured(only serious injury) on that day, heard from social media (exclude directly communicating with friends on social media)
kk. The number of acquaintances newly injured(only serious injury) on that day, heard from acquaintances 
ll. The number of acquaintances newly injured(only serious injury) on that day, heard from government broadcast
mm. The number of acquaintances newly injured(only serious injury) on that day, by personal observation

nn. The number of acquaintances in injury state(only serious injury) on that day, heard from social media (exclude directly communicating with friends on social media)
oo. The number of acquaintances in injury state(only serious injury) on that day, heard from acquaintances 
pp. The number of acquaintances in injury state(only serious injury) on that day, heard from government broadcast
qq. The number of acquaintances in injury state(only serious injury) on that day, by personal observation

rr. The number of acquaintances newly injured(both serious and minor injury) on that day, heard from social media (exclude directly communicating with friends on social media)
ss. The number of acquaintances newly injured(both serious and minor injury) on that day, heard from acquaintances 
tt. The number of acquaintances newly injured(both serious and minor injury) on that day, heard from government broadcast
uu. The number of acquaintances newly injured(both serious and minor injury) on that day, by personal observation

vv. The number of acquaintances in injury state(both serious and minor injury) on that day, heard from social media (exclude directly communicating with friends on social media)
ww. The number of acquaintances in injury state(both serious and minor injury) on that day, heard from acquaintances 
xx. The number of acquaintances in injury state(both serious and minor injury) on that day, heard from government broadcast
yy. The number of acquaintances in injury state(both serious and minor injury) on that day, by personal observation

zz. The number of acquaintances going to evacuation on that day, heard from social media (exclude directly communicating with friends on social media)
aaa. The number of acquaintances going to evacuation on that day, heard from government broadcast
bbb. The number of acquaintances going to evacuation on that day, heard from acquaintances
ccc. The number of acquaintances going to evacuation on that day, by personal observation

ddd. The number of acquaintances coming back from evacuation on that day, heard from social media (exclude directly communicating with friends on social media)
eee. The number of acquaintances coming back from evacuation on that day, heard from government broadcast
fff. The number of acquaintances coming back from evacuation on that day, heard from acquaintances
ggg. The number of acquaintances coming back from evacuation on that day, by personal observation

hhh. The number of acquaintances going to shelter on that day, heard from social media (exclude directly communicating with friends on social media)
iii. The number of acquaintances going to shelter on that day, heard from government broadcast
jjj. The number of acquaintances going to shelter on that day, heard from acquaintances
kkk. The number of acquaintances going to shelter on that day, by personal observation

lll. The number of acquaintances coming back from shelter on that day, heard from social media (exclude directly communicating with friends on social media)
mmm. The number of acquaintances coming back from shelter on that day, heard from government broadcast
nnn. The number of acquaintances coming back from shelter on that day, heard from acquaintances
ooo. The number of acquaintances coming back from shelter on that day, by personal observation

ppp. The number of strangers newly injured(only serious injury) on that day, heard from social media (exclude directly communicating with friends on social media)
qqq. The number of strangers newly injured(only serious injury) on that day, heard from strangers 
rrr. The number of strangers newly injured(only serious injury) on that day, heard from government broadcast
sss. The number of strangers newly injured(only serious injury) on that day, by personal observation

ttt. The number of strangers in injury state(only serious injury) on that day, heard from social media (exclude directly communicating with friends on social media)
uuu. The number of strangers in injury state(only serious injury) on that day, heard from strangers 
vvv. The number of strangers in injury state(only serious injury) on that day, heard from government broadcast
www. The number of strangers in injury state(only serious injury) on that day, by personal observation

xxx. The number of strangers newly injured(both serious and minor injury) on that day, heard from social media (exclude directly communicating with friends on social media)
yyy. The number of strangers newly injured(both serious and minor injury) on that day, heard from strangers 
zzz. The number of strangers newly injured(both serious and minor injury) on that day, heard from government broadcast
aaaa. The number of strangers newly injured(both serious and minor injury) on that day, by personal observation

bbbb. The number of strangers in injury state(both serious and minor injury) on that day, heard from social media (exclude directly communicating with friends on social media)
cccc. The number of strangers in injury state(both serious and minor injury) on that day, heard from strangers 
dddd. The number of strangers in injury state(both serious and minor injury) on that day, heard from government broadcast
eeee. The number of strangers in injury state(both serious and minor injury) on that day, by personal observation

ffff. The number of strangers going to evacuation on that day, heard from social media (exclude directly communicating with friends on social media)
gggg. The number of strangers going to evacuation on that day, heard from government broadcast
hhhh. The number of strangers going to evacuation on that day, heard from strangers 
iiii. The number of strangers going to evacuation on that day, by personal observation

jjjj. The number of strangers coming back from evacuation on that day, heard from social media (exclude directly communicating with friends on social media)
kkkk. The number of strangers coming back from evacuation on that day, heard from government broadcast
llll. The number of strangers coming back from evacuation on that day, heard from strangers 
mmmm. The number of strangers coming back from evacuation on that day, by personal observation

nnnn. The number of strangers going to shelter on that day, heard from social media (exclude directly communicating with friends on social media)
oooo. The number of strangers going to shelter on that day, heard from government broadcast
pppp. The number of strangers going to shelter on that day, heard from strangers 
qqqq. The number of strangers going to shelter on that day, by personal observation

rrrr. The number of strangers coming back from shelter on that day, heard from social media (exclude directly communicating with friends on social media)
ssss. The number of strangers coming back from shelter on that day, heard from government broadcast
tttt. The number of strangers coming back from shelter on that day, heard from strangers 
uuuu. The number of strangers coming back from shelter on that day, by personal observation

vvvv. The total number of people dead, heard from social media
wwww. The total number of people dead, heard from government broadcast

xxxx. The total number of people in injury state(only serious injury), heard from social media
yyyy. The total number of people in injury state(only serious injury), heard from government broadcast

zzzz. The total number of people in injury state(both serious and minor injury), heard from social media
aaaaa. The total number of people in injury state(both serious and minor injury), heard from government broadcast

bbbbb. The total number of people in shelter (state), heard from social media
ccccc. The total number of people in shelter (state), heard from government broadcast

ddddd. The total number of people in evacuation(state), heard from social media
eeeee. The total number of people in evacuation(state), heard from government broadcast
* Total number should mean total number in the area

fffff. The total number of people dead in your region, heard from social media
ggggg. The total number of people dead in your region, heard from government broadcast

hhhhh. The total number of people in injury state(only serious injury)in your region, heard from social media
iiiii. The total number of people in injury state(only serious injury)in your region, heard from government broadcast

jjjjj. The total number of people in injury state(both serious and minor injury)in your region, heard from social media
kkkkk. The total number of people in injury state(both serious and minor injury)in your region, heard from government broadcast

lllll. The total number of people in shelter (state)in your region, heard from social media
mmmmm. The total number of people in shelter (state)in your region, heard from government broadcast

nnnnn. The total number of people in evacuation(state)in your region, heard from social media
ooooo. The total number of people in evacuation(state)in your region, heard from government broadcast

ppppp. Regional damage level in your region, heard from social media
qqqqq. Regional damage level in your region, heard from government broadcast
rrrrr. Regional damage level in your region, heard from friends
sssss. Regional damage level in your region, heard from acquaintances
ttttt. Regional damage level in your region, heard from strangers
uuuuu. Regional damage level in your region, by personal observation
vvvvv. Regional damage level in your friends’ region, heard from social media
wwwww. Regional damage level in your friends’ region, heard from government broadcast
xxxxx. Regional damage level in your friends’ region, heard from your friends
yyyyy. Regional damage level in your friends’ region, heard from acquaintances
zzzzz. Regional damage level in your friends’ region, heard from strangers

aaaaaa. A list of hurricane prediction(on which day, the category and location would be what), heard from social media(exclude directly communicating with friends in social media)
bbbbbb. A list of hurricane prediction(on which day, the category and location would be what), heard from government broadcast
cccccc. A list of hurricane prediction(on which day, the category and location would be what), heard from friends
dddddd. A list of hurricane prediction(on which day, the category and location would be what), by personal observation

	*Previously, we know the prediction is only issued once for each hurricane(e.g. Two days before the hurricane lands, prediction states the predicted location and category/state for the next 10 days, which covers the whole hurricane) If the prediction is issued on a daily basis and only predicts the location/category for the next day, the prediction reported should also be a day-to-day base, with category/location from different sources.

eeeeee. Does this person conduct crime on that day(this can be based on researchers’ observation, and if researchers is not sure about his/her judgements, it can also report a confidence level 0 - 6 indicating how confident it is to its judgement on crime, with 6 for 100% certain and 0 for completely unsure).
i. If so, how serious is the crime (1-7 level, 7 for most severe?
ii. Does that crime reduce others’ wealth? If so, use 1-7 to indicate the seriousness of damage(7 for most severe)
iii. Does that crime damage others’ health(cause injury of different level)? If so, use 1-7 to indicate the seriousness of damage(7 for most severe)
iv. Does that crime cause financial regional damage? If so, use 1-7 to indicate the seriousness of damage(7 for most severe)
v. Does that crime cause non-financial regional damage? If so, use 1-7 to indicate the seriousness of damage(7 for most severe)

* For net change level, the range is -5 to 5, with negative number being decrease, positive number being increase, 0 for no change; The level should be adjusted to reflect even the minimal possible change. (E.g. If A’s wealth is 4 on day 1, and 4 on day 2, but indeed A’s wealth increase a little (although the amount is too small to be reflected in wealth level), so the net wealth change should be +2 or something like that to represent the change; if the net change level is 0, it must represent ‘no change at all’ )
ffffff. Net wealth change level comparing with the last day. (-5 to 5)
gggggg. Net dissatisfaction change level comparing with the last day. (-5 to 5)
hhhhhh. Net perceived risk change level comparing with the last day. (-5 to 5)
iiiiii. Net perceived injury possibility change level comparing with the last day. (-5 to 5)
jjjjjj. Net severity change level comparing with the last day (-5 to 5)



	Part II: Collect data from the government

1. 
1. We want to get data on government hurricane prediction, specifically:
a. The content of the prediction
b. When was the prediction made
c. When was the prediction propagate, and in what way/which platform
	   2. We want to get a complete crime record, which records the following information for each crime instance:
a. The unique id of person who conducted such crime
b. The time crime is conducted
c. The severity of this crime
d. Characteristics of this crime (i.e. target of crime - human/non-human, type of crime - robbery, vandalism, etc., extent of injury - physical/financial)
	   3. We want to get a complete record on government calculated regional damage, which records the calculated regional damage on each day, for each region (1-5, with 5 the most severe one)
	   4. A complete list of the destination and amount of aid on each day.

	
# Sampling strategy #
We randomly invite 5% of the population from the simulated world by DARPA, from all instances in Phase I and Phase II.


# Other applicable detail #


# Research request identifier #

TA2A-TA1C-0312-RR



