import os.path
import subprocess

from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
	for instance in range(9,15):
		entry = accessibility.instances[instance-1]
		cmd = ' '.join(['python3',os.path.join(os.path.dirname(__file__),'..','..','..','Explain','TA2B','TA2B-TA1C-13','TA2B-TA1C-13.py'),
			'-i','%d' % (entry['instance']),'-r','1','--day','%d' % (entry['span']),'-o','TA2B-TA1C-51.tsv','--directory',
			os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0')])
		print(cmd)

