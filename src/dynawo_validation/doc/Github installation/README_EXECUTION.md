
# Instructions for creation and execution of contingency cases

## Venv must be actived to proceed

## How to create contingency cases 

- Get the dynawo validation repository and save it wherever you want: git clone **TODO:URL repository**

- Get a prepared base case and store it where you prefer

- Go to your base case directory: cd /your/directory

- Manual execution:

	- Create the contingency case: $HOME/.../dynawo-validation-AIA/dynaflow/pipeline/create_gen_contg.py base_case [element1 element2 element3 ...]

- Automatic execution:

	- Create the contingency cases you need: $HOME/..../dynawo-validation-AIA/dynaflow/pipeline/create_gen_contg.py base_case [element1 element2 element3 ...]


## How to run contingency cases

- Go to your base case directory: cd /your/directory

- Manual execution:

	- **TODO:Execution and data preparation**

- Automatic execution:

	- Run one contingency case: $HOME/..../dynawo-validation-AIA/dynaflow/pipeline/run_one_contg.sh [OPTIONS] BASECASE CONTINGENCY_CASE

	- Run all contingency cases: $HOME/..../dynawo-validation-AIA/dynaflow/pipeline/run_all_contg.sh [OPTIONS] CASE_DIR BASECASE CASE_PREFIX


## How to see the results of the executions 

- Run Jupyter Notebook

- Open the prepared notebook: **TODO:Jupyter notebook name and usage**


