
# Intro

The validation pipelines for DynaFlow and DynaWaltz are launched by using these scripts:

   - **dynaflow_run_validation**

   - **dynawaltz_run_validation**

Their usage and options are very similar. We will show examples using DynaFlow, but everything works the same for the case of DynaWaltz.

As with many other scripts in the pipeline, just run the command with no arguments or options at all to get a quick reminder:

	$ dynaflow_run_validation

	usage: dynaflow_run_validation [-h] [-A LAUNCHERA] [-B LAUNCHERB] [-a] [-s] [-d] [-c] [-l REGEXLIST] [-w WEIGHTS] [-r] [-p RANDOMSEED] base_case results_dir
	
	dynaflow_run_validation: error: the following arguments are required: base_case, results_dir

Or run it with **-h / --help** in order to get a more detailed description of each option and argument.



# Command line options

	usage: dynaflow_run_validation [-h] [-A LAUNCHERA] [-B LAUNCHERB] [-a] [-s] [-d] [-c] [-l REGEXLIST] [-w WEIGHTS] [-r] [-p RANDOMSEED] base_case results_dir

	positional arguments:
	  base_case
	  results_dir

	optional arguments:
	  -h, --help            show this help message and exit
	  -A LAUNCHERA, --launcherA LAUNCHERA
		                defines the launcher of simulator A
	  -B LAUNCHERB, --launcherB LAUNCHERB
		                defines the launcher of simulator B
	  -a, --allcontg        run all the contingencies
	  -s, --sequential      run jobs sequentially (default is parallel)
	  -d, --debug           more debug messages
	  -c, --cleanup         delete input cases after getting the results
	  -l REGEXLIST, --regexlist REGEXLIST
		                enter regular expressions or contingencies in text (.txt) form, by default, all possible contingencies will be generated (if below MAX_NCASES; otherwise a random sample is generated)
	  -w WEIGHTS, --weights WEIGHTS
		                file containing personalized weights for computing scores (format should follow the template)
	  -r, --random          run a different random sample of contingencies
	  -p RANDOMSEED, --randomseed RANDOMSEED
		                run a different random sample of contingencies with a seed


## base_case (required)

The directory that contains the BASECASE. Either as an absolute path, or a relative one (relative to the directory where we’re executing the pipeline from).

## results_dir (required)

The directory that will store the results (it will be created if it does not exist). Either as an absolute path, or a relative one.

## -A LAUNCHERA, --launcherA LAUNCHERA (default launcher: dynawo.sh)

Executable to be used as “Simulator A”. Never use relative paths here. Either use an absolute path to the executable, or make sure it is on your $PATH.

## -B LAUNCHERA, --launcherB LAUNCHERB (default launcher: dynawo.sh)

Executable to be used as “Simulator B”. Never use relative paths here. Either use an absolute path to the executable, or make sure it is on your $PATH.

## -a, --allcontg

This will create and run all possible network contingencies, for all available types (shunts, generators, loads and branches).

## -l REGEXLIST, --regexlist REGEXLIST

This will create and run the contingencies that match any of the regular expressions listed in a text file REGEXLIST (each line is a regex).

## -s, --sequential

The contingencies will be executed sequentially, thus using a single CPU core. If GNU parallel is not installed, this option will also be used. Otherwise, by default contingencies
are run in parallel, using all available CPU cores (jobs being managed by GNU parallel).

## -d, --debug

Obtain more detailed information messages from the execution of the pipeline.

## -c, --cleanup

With this option all input cases (the contingency cases) will be eliminated after having been executed, in order to save on disk storage. Note that they can be easily
recovered via the diffs w.r.t. the BASECASE, which are always kept under results_dir/casediffs.

## -w WEIGHTS, --weights WEIGHTS

Using a template file found in the Dynaflow repo folder, custom weights can be passed to calculate the scores and define the thresholds used, thus overriding the default
values.

## -r, --random

Runs only a small random sample of contingencies of each type. A different RNG seed is chosen every time you use this option. If you want repeatable results, you’d better
use option –p. However, on start-up the script will show on standard output the RNG seed it used.

## -p RANDOMSEED, --randomseed RANDOMSEED

Runs only a small random sample of contingencies of each type. The RNG will use the provided seed (an integer). Use this if you want repeatable runs.


# Execution of all contingencies:

When executing the pipeline for a long run, you want to keep the console output and also make the execution robust against disconnections (e.g. when you are working from home and
your VPN goes down):

	nohup dynaflow_run_validation –A dynawo.sh –B hades –a Prepared_BASECASE_name Results_dir > output.txt 2>&1 &
	

   - **nohup** 🡪 nohup is a POSIX command which means "no hang up". Its purpose is to execute a command such that it ignores the HUP (hangup) signal and therefore does not stop when the
user logs out, or gets disconnected from his ssh session, or the VPN goes down, etc.

   - **>** 🡪 Redirects stdout to a file.

   - **output.txt** 🡪 Output file (choose any name).

   - **2>&1** 🡪 Redirects stderr (“unit 2”) to a file (in this case “&1” is an alias to standard error, which by now is the file “output.txt”)

   - **&** 🡪 This final ampersand is just used to push the execution into the background, to recover the shell prompt. At this point you could then, for instance, just exit from the shell and the
pipeline will continue running without a problem.

**Best practice, in summary:**

   1. Launch the pipeline with: nohup dynaflow_run_validation … > output.txt 2>&1 &

   2. Monitor the file for a few seconds to check that everything progresses fine: tail –f output.txt (press Ctrl-C when done)

   3. Exit or disconnect from the shell. Log back in when you think it is done,


# Other examples:

	dynaflow_run_validation –s -r Prepared_BASECASE_name Results_dir

   In this example the pipeline runs sequentially (1 thread) a small random sample of contingencies. Default launchers will be used.

	dynaflow_run_validation –A dynawo.sh –B hades –d –p 67 Prepared_BASECASE_name Results_dir

   Runs a random sample of contingencies (using seed 67 for the RNG), using all possible CPU cores, with the provided launchers (which should be on our $PATH), and
showing DEBUG information in the output messages to the console.

	dynaflow_run_validation –w weights.txt Prepared_BASECASE_name Results_dir

   Runs a random sample of contingencies (using a randomly chosen seed), with the default launchers and using all possible CPU cores. In addition, the values to calculate
the scores and define the thresholds will be read from the provided file “weights.txt”, instead of using the default ones.

	dynaflow_run_validation –A dynawo.sh –B hades –l regex.txt Prepared_BASECASE_name Results_dir

   Runs a set of contingencies defined through regular expressions defined in the regex.txt file, with the provided launchers, and using all possible CPU cores.

