
# Instructions for execution/development requirements

## OS, development software and utilities

- Install base OS: Debian Buster 10.4 (from netinst). Standard Gnome desktop and ssh. Used en_US as system-wide locale, then used to set the timezone manually later: timedatectl set-timezone Europe/Madrid

- Post-install packages: apt-get install aptitude open-vm-tools-desktop rsync emacs

- Install Python 3: 

	- sudo apt-get update && sudo apt-get upgrade

	- sudo apt-get install python3.6

- Install pip and venv: sudo apt install python3-venv python3-pip

- Install Jupyter and some other python debs for DS: apt-get install jupyter python-numpy python3-numpy

- Only for development:

	- Install a python IDE. (for ex. PyCharm: https://www.jetbrains.com/help/pycharm/installation-guide.html#requirements)

	- Install python development utilities: apt-get install black flake8 python3-pytest


## Virtual environment creation

- Create the virtual environment: python3 -m venv /path/to/new/virtual/environment

- Activate the virtual environment: source /path/to/new/virtual/environment/bin/activate

Now you should have the name of your virtual environment in parentheses before the username on the command line.

- Deactivate virtual environment: deactivate

- Remove virtual environment: rm -rf /path/to/new/virtual/environment


## Virtual environment configuration (venv must be actived to proceed)

Now, you have a self-contained directory tree that contains a Python installation for a particular version of Python, plus a number of additional packages. All the modifications that you make in this installation (with pip) will not affect the general installation of Python.

- Upgrade pip: python -m pip install --upgrade pip (we use python instead of python3 because in this environment we only have Python 3).

- **Install all Python packages**:

	- pip install pandas

	- pip install lxml

	- pip install plotly

	- pip install frozendict

	- pip install networkx

	- pip install pyvis


## Jupyter Notebooks configuration

To use the virtual environment interpreter in Jupyter Notebooks, we have to do the following steps:

	1. Activate virtual environment source /path/to/new/virtual/environment/bin/activate

	2. Install ipykernel which provides the IPython kernel for Jupyter: pip install ipykernel

	3. Add your virtual environment to Jupyter: python -m ipykernel install --user --name=NAME-OF-INTERPRETER

	4. Open Jupyter and, in Kernel Options, select your new Kernel.


## IDE configuration (only for development)
	
To use the virtual environment interpreter in our IDE we have to open our Python IDE (for example, PyCharm) and go to Interpreter Configuration (in the case of PyCharm, we have the direct option to Add Interpreter). We must choose the option that allows us to add a new interpreter and then, we only have to select the Python interpreter from the path where we have installed the Virtual Environment (in /bin directory).


## Install Dynawo

- Follow the instructions of this website: https://dynawo.github.io/install/

