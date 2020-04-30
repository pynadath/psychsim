# Specific question #


Q1.
The RunDataTable.tsv has a variable name “Actor’s Expected Reward”. In instance 23, this spans from timesteps 110 to 165. In instance 24, this data spans from timestep 2 to 71.  


However, the data on hurricanes in instances 23 and 24 span from timesteps 1-165 and 1-88, respectively. We would like to clarify: Is the data about actor’s expected rewards only computed on a subset of the simulation timesteps, or is there data about Actor’s Expected Reward that is missing from the RunDataTable.tsv ?  




# Other applicable details #




# Answer #

We will upload a revised RunDataTable (R2) with the missing values for Instance 23.

However, Instance 24 is complete, as the timeline beyond step 71 is intended for prediction, so only the hurricane data are provided. We provide an updated RunDataTable for Instance 24 as some of the actors' expected reward entries had the correct EntityIdx, but were labeled as "Group's Expected Reward" instead of "Actor's"