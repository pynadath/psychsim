# Specific question #


Q1. 
Please clarify the interpretation of values such as “Pr(0.20000000000000004)=1.000”


Q2.
The Phase3_Explain_IDP_Full_TA1C RunDataTable contains non-unique and conflicting values for the variables "ActorBeliefOfRegion's risk" and "ActorBeliefOfRegion's shelterRisk"


For example within the RunDataTable.tsv file, there are multiple values for a given Timestep and EntityIdx combination. Some are duplicate values, while others are conflicting. Further, there are a non-identical number of entries for each Actor (e.g. Actor0001 has 2 entries for ActorBeliefOfRegion's risk at Timestep 2, while Actor0003 has 1).


Could you please clarify the meaning when the Timestep and EntityIdx and VariableName appear multiple times. Are these cases where an actor engages in a sequence of values all on the same date or are some of these duplicates and, if so, which of the conflicting values should be used? In particular, please clarify how to interpret duplicate/conflicting values, providing guidance on whether or not these are co-occurring events, sequential events (if sequential please provide sub-Timesteps in the Notes field for appropriate sequencing). If Actor state persists for some number of sub-Timesteps please provide this data as well.


For your convenience, we have pasted a sample of the original duplicates/conflicting values below:
       Timestep                VariableName  EntityIdx                          Value
      2.0  ActorBeliefOfRegion's risk  Actor0001  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0001  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0002  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0002  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0003  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0005  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0006  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0007  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0007  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0009  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0011  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0011  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0012  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0012  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0012  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0014  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0014  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0016  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0016  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0017  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0018  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0018  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0019  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0019  Pr(0.20000000000000004)=1.000
      2.0  ActorBeliefOfRegion's risk  Actor0020  Pr(0.20000000000000004)=1.000






# Other applicable details #




# Answer #

We apologize for the ambiguity. In our translation into CDF, the specific region of interest was lost. We have updated the data packages, both the full data for the Explain instance and the IDP for the Predict instances. The new archives include a README, but we include the text here, as they answer your questions above:

We have updated the representation of two variables: ActorBeliefOfRegion's risk and ActorBeliefOfRegin's shelterRisk, as these pertain to multiple regions for some actors. The new representation uses a single record for each variable, with the value being a comma-separated list of probability values. For example, an entry of the form "Pr(Region13's risk=0.6)=1.000" would mean a 100% probability that Region13's risk is 0.6.

For the other beliefs, where there is no ambiguity about the entity being referred to, we put simply the value for the variable and omit the variable name. For example, an entry of the form "Pr(0)=1.000" for ActorBeliefOfNature's category would mean a 100% probability that Nature's category is 0.