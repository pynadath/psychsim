# Specific question #

We have observed a possible error in the complete Phase I dataset. From Hurricane 1-5 of Instance I of Phase I, when the nature’s ‘Location’ changes to ‘none’ (the hurricane has left the area), ‘Phase’ should change to ‘none’ as well, and when both ‘Location’ and ‘Phase’ are ‘none’, the value of ‘Category’ should be 0.

However, in Timestep 80, nature’s ‘Phase’ is still ‘active’ despite ‘Location’ being ‘none’ since Timestep 79, and ‘Category’ is 4 from Timesteps 80-82. We believe that ‘Category’ should be 0 for these timesteps if ‘Location’ is ‘none’, since that should have triggered ‘Phase’ to be ‘None’ as well. 

Please confirm whether this is a mistake, and if so, please update the data. The actions/statuses of actors rely on the values that ‘Location’, ‘Phase’, and ‘Category’ take on, so please adjust the related data as well if there are related errors.



# Other applicable details #

# Answer # 

Yes, "Nature's phase" should be "none" and "Nature's category" should be "0" for Timesteps 80-82. There are no other related errors. We are providing a revised data file, but the following are the changed entries:

80	Nature's category	Nature	0	
80	Nature's phase	Nature	none	
81	Nature's category	Nature	0	
81	Nature's phase	Nature	none	
82	Nature's category	Nature	0	
82	Nature's phase	Nature	none	
