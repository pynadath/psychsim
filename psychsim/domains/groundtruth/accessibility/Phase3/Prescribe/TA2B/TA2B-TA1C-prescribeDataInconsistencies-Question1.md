# Specific question #


Q1. 
In Instance 25, the RelationshipDataTable includes memberOf, friendOf, marriedTo, neighborOf relationships


In instance 26, the RelationshipDataTable.tsv only includes memberOf relationships. Please provide the missing data. 




Q2.
We believe a number of key variables are missing from the Instance 26 data files. 
In Instance 25, the RunDataTable.tsv includes the following fields:


            "Actor's horizon",
            "Actor's ethnicGroup",
            "Actor's religion",
            "Actor's home",
            "Actor's priority of health",
            "Actor's priority of resources",
            "Actor's priority of neighbors",
            "Actor's information distortion",
            "Actor's priority of childrenHealth",
            "Actor's priority of pets"


            "Group's beliefAggregation",
            "Group's magnification",
            "Group's horizon"


The above variables are all missing from the instance 26 RunDataTable.tsv. Please provide the missing data.


Q3.


In Instance 25, the RunDataTable.tsv has multiple ‘copies’ of fields, for the same timestep, variable name, ActorID. For example, in RunDataTable.tsv, on line 16933, we see:


1    Actor's employed    Actor0001    True    
1    Actor's employed    Actor0002    False    
1    Actor's employed    Actor0003    True    
…


And what appears to be a copy of the same data, starting on line 1999516. This occurs for several dynamic variables. Please clarify the meaning behind the “repeated” data.






# Other applicable details #




# Answer #

Apologies, it appears that an error in merging timestamped and non-timestamped values led to issues with both instances. We have uploaded corrected data labeled as R1. 