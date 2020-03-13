## Synopsis

USC Ground Truth simulation code.

## Installation

1. Install Python 3: https://www.python.org/downloads/
2. Download PsychSim from GitHub repository: https://github.com/pynadath/psychsim
   a. git clone https://github.com/pynadath/psychsim.git
   b. git checkout hri
   c. Alternative to a&b, but harder to get future updates: download and extract https://github.com/pynadath/psychsim/archive/hri.zip
3. Download Ground Truth code: https://drive.google.com/open?id=1UlgnonDmt2lhviml1kK18eyUAnidWIor
   a. Unzip code, preferably in psychsim/domains, but anywhere will work.
   b. Modify groundtruth/gt.sh in the unzipped directory to point to your specific paths
      i. PYTHONPATH should be set to the directory where installed PsychSim in Step 2.
      ii. Change the path in the final command to point to the groundtruth directory you installed in Step 3a.
4. Run "sh groundtruth/gt.sh 24 -n 1" to run the simulation for a single hurricane using configuration file "groundtruth/config/000024.ini"
   a. Run "sh groundtruth/gt.sh --help" to see the list of possible execution options


## License

MIT License