# Research method category # 
  
Government Data


# Specific question #

We would like to access government records about the circumstances of death of deceased individuals 

1. Timestep of death  
2. When they died were they at home? In a shelter? Evacuated?  
3. Prior to their death, in the most recent hurricane, had the deceased individual chosen to stay home through the storm, evacuate the region, or go to the nearest shelter during the storm.  
4. Was the decedent currently injured prior to the events leading up to their death?
5. What was the category of the hurricane when it reached their region of residence?
6. For the entire past hurricane season, prior to the death of the individual, what was their action for all of the hurricanes: list whether they stayed at home, sheltered, or evacuated for each.  
7. For the entire past hurricane season, prior to the death of the individual, what was their injury status (injured vs not injured) after each hurricane?  
8. We request all government records that pertain to the distribution of aid in each instance. At a minimum we expect to obtain the dates and regions where aid was distributed on each day of the past hurricane season. If amount information on the aid is available include that information in each aid distribution record.  
9. We request all government records that pertain to any taxes or fees that were levied against the population. For each taxation event denote the date of the taxation/feecollection the amount taxed/collected, the individual who was taxed/charged (global unique ID), whether the tax was computed based on wealth/income/flat/feeforservice, and purpose in the case where there is purpose information tied to the taxation or feecollection event.   
10. We request government activity data. This may include any elections held, and actions taken by the government, and meetings or information distributed to the citizenry. These records should contain at a minimum the date of the government event, a description of the action, the targets (global unique ID for agents) of the events or region ID if the target was a region, and any other pertinent available information.  
  

# Sampling strategy #
  
Please provide this data for all agents who died in instances 15, 16, 17, 18 and 19.
  

Give all of these agents unique IDs in the following way: An example name is D112-1, where D stands for died, 112 stands for died on date 112, -1 means they are the 1st person to die that day (another example, D43-5 would be the 5th person to die on day 43).   


For instances 15, 16 and 17, provide additional tables that map the above decedentID to the pre-hurricane survey respondent number or the post-hurricane survey respondent number in the cases where the decedent had filled a pre or post survey for the 2PairedPredictSurveys-RR. You can put these mappings in a relationshipdatatable mapping decedentID to “ActorPre 0” for example.  


For instances 18 and 19, provide additional tables that map the above decedentID to the pre-hurricane survey respondent number or the post-hurricane survey respondent IDs that are used in the 12PairedPosthurricaneSurveys-RR and 13PairedPrehurricaneSurveys-RR in the cases where the decedent had filled pre or post surveys. You can put these mappings in a relationshipdatatable mapping decedentID to the “ActorPre 1 Hurricane 1” for example.  


# Other applicable detail #
  

# Research request identifier #  
14deathandaidPt1