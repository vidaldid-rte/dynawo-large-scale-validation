
# Instructions for execution/development requirements

## OS, development software and utilities

- Install base OS: Debian 11 (from netinst). Standard Gnome desktop and ssh.

- Install Python 3: 

	- sudo apt-get update && sudo apt-get upgrade

	- sudo apt-get install python3.9

- Install pip and venv: sudo apt install python3-venv python3-pip

- Install Jupyter and some other python debs for DS: apt-get install jupyter python-numpy python3-numpy

- Install parallel package for faster execution: sudo apt-get install parallel

- Only for development:

	- Install a python IDE. (for ex. PyCharm: https://www.jetbrains.com/help/pycharm/installation-guide.html#requirements)

	- Install python development utilities: apt-get install black flake8 python3-pytest
	

## Option 1
## Use the default script 

### Run build_and_install.sh script
Run the build_and_install.sh script located at the root of the directory where all the files are. In this way, a virtual environment will be created and all the packages necessary to use the tool will be installed in it. This includes creating virtual environment, enabling extensions, building the package, installing the package, etc. 


## Option 2
## Do all the steps manually 

### Virtual environment creation

- Create the virtual environment: python3 -m venv /path/to/new/virtual/environment

- Activate the virtual environment: source /path/to/new/virtual/environment/bin/activate

Now you should have the name of your virtual environment in parentheses before the username on the command line.

Others:

- Deactivate virtual environment: deactivate

- Remove virtual environment: rm -rf /path/to/new/virtual/environment


### Virtual environment configuration (venv must be actived to proceed)

Now, you have a self-contained directory tree that contains a Python installation for a particular version of Python, plus a number of additional packages. All the modifications that you make in this installation (with pip) will not affect the general installation of Python.

- Upgrade pip: python -m pip install --upgrade pip (we use python instead of python3 because in this environment we only have Python 3).

### Install dynaflow-validation (venv must be actived to proceed)

- Install dynaflow-validation with all dependencies: pip install dynaflow-validation-RTE-AIA (if in the end it is uploaded as a package )

- Install dynaflow-validation with all dependencies manually:

       1. Clone the repo: git clone https://github.com/dynawo/dynawo-validation-AIA
	
       2. Build the package (go to the main directory of the package): python -m build
	
       3. Install the package: pip install dist/dynawo_validation_RTE_AIA-X.Y.Z-py3-none-any.whl


## Install Dynawo

- Follow the instructions of this website: https://dynawo.github.io/install/


## Install Hades

- To compare between Hades, it is assumed that you already have Hades installed in your environment.
	

## Jupyter Notebooks configuration

To use the virtual environment interpreter in Jupyter Notebooks, we have to do the following steps:

       1. Activate virtual environment source /path/to/new/virtual/environment/bin/activate

       2. Install ipykernel which provides the IPython kernel for Jupyter: pip install ipykernel

       3. Add your virtual environment to Jupyter: python -m ipykernel install --user --name=NAME-OF-INTERPRETER

       4. Run this three commands in order to register this extensions with jupyter: 
        	
                jupyter nbextension enable --py widgetsnbextension
                jupyter nbextension enable --py --sys-prefix qgrid
                jupyter nbextension enable --py --sys-prefix ipydatagrid

       5. Open Jupyter and, in Kernel Options, select your new Kernel.


## IDE configuration (only for development)
	
To use the virtual environment interpreter in our IDE we have to open our Python IDE (for example, PyCharm) and go to Interpreter Configuration (in the case of PyCharm, we have the direct option to Add Interpreter). We must choose the option that allows us to add a new interpreter and then, we only have to select the Python interpreter from the path where we have installed the Virtual Environment (in /bin directory).

