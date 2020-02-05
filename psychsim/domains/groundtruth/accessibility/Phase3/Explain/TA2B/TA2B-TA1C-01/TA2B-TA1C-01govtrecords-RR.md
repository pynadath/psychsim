# Research method category #
Government Data


# Specific question #
We would like to access government records about the circumstances of death of deceased individuals, both the heads of households and their dependents, as well as about distribution of aid, taxes, and government actions. Please distinguish between the individuals being reported and provide an ID for the head of household corresponding to each dependent death. In the cases where a head of household dies, but there are surviving dependents, please provide records regarding the placement of the dependents. 
1. Timestep of death and a death ID indicating head-of-household vs dependent status
2. When they died were they at home? In a shelter? Evacuated?
3. Was the decedent currently injured prior to the events leading up to their death?
4. What was the category of the hurricane when it reached their region of residence?
5. For the entire past hurricane season, prior to the death of the individual, what was their action for all of the hurricanes: list whether they stayed at home, sheltered, or evacuated for each?
6. For the entire past hurricane season, prior to the death of the individual, how many of their friends performed the same action as the individual (stay at home, shelter, evacuate), broken down by hurricane?
7. For the entire past hurricane season, prior to the death of the individual, what was their injury status (injured vs not injured) after each hurricane?
8. We request all government records that pertain to the distribution of aid in each instance. At a minimum we expect to obtain the dates and regions where aid was distributed on each day of the past hurricane season. If amount information on the aid is available include that information in each aid distribution record.
9. We request all government records that pertain to any taxes or fees that were levied against the population. For each taxation event denote the date of the taxation/feecollection the amount taxed/collected, the individual who was taxed/charged (global unique ID), whether the tax was computed based on wealth/income/flat/feeforservice, and purpose in the case where there is purpose information tied to the taxation or feecollection event. 
10. We request government activity data. This may include any elections held, any voting records collected for municipal districts as well as the legislative actions or office candidacies considered in each election, and actions taken by the government, and meetings or information distributed to the citizenry. These records should contain at a minimum the date of the government event, a description of the action, the targets (global unique ID for agents) of the events or region ID if the target was a region, and any other pertinent available information.


# Sampling strategy #
Please provide this data for all agents who died in this instance.


Give all of the agents that are heads of households who die unique IDs in the following way: An example name is D112-1, where D stands for died, 112 stands for died on date 112, -1 means they are the 1st person to die that day (another example, D43-5 would be the 5th person to die on day 43). For any dependents that die give them the name C110-1-D112-1 if they are the first dependent to die on day 110 from a headofhousehold that died on day 112. If the dependent death is to a person who is still alive then give them a name C110-1-A834, A834 is just a unique ID telling us this head of household is still alive.


For any heads of households who are respondents in the IDP, provide a linking mapping to the ID for these records to the IDP survey ID.




# Other applicable detail #


# Research request identifier #
01govtrecords-RR