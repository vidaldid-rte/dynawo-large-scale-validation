
# Instructions for installation

The requirements for installation are almost the same as those for
setting up a developer environment (see
[Notes_development_environment.md](Notes_development_environment.md)
in this folder), with the exception of a Python IDE and Python
utilities such as flake8, etc.

Nevertheless, these instructions are geared towards non-developers who
want to install and use the software.



## OS-level requirements

- An Ubuntu or Debian-based distro is preferred. We normally
  use Debian stable (currently v11.x). A standard Gnome desktop is
  also nice to have, but not required (you'll need to run Jupyter
  notebooks on a browser, but your browser may be remote to the Linux
  OS).

- A base install of Python 3: 

	- `sudo apt-get update && sudo apt-get upgrade`

	- `sudo apt-get install python3.9 python3-venv python3-pip`

- Optional: the GNU parallel package for parallel execution: `sudo
  apt-get install parallel`

- These other commands are also required but they usually come by
  default with most modern Linux distros: `grep sed find xz`


## Option 1: use the default script (much easier!) 

Run the build_and_install.sh script located at the root of the
directory where all the files are. In this way, a virtual environment
will be created and all the packages necessary to use the tool will be
installed in it. This includes creating the virtual environment, enabling
extensions, building the package, installing the package, etc.

The script can also be re-run at any time in order to update all packages.


## Option 2: manage your venv yourself (manual steps involved) 

### Virtual environment creation

- Create the virtual environment: `python3 -m venv /path/to/new/virtual/environment`

- Activate the virtual environment: `source /path/to/new/virtual/environment/bin/activate`

Now you should have the name of your virtual environment in
parentheses before the username on the command line.

Other:

- Deactivate the virtual environment: `deactivate`

- Remove the virtual environment: `rm -rf /path/to/new/virtual/environment`


### Virtual environment configuration (the venv must be active)

Now, you have a self-contained directory tree that contains a Python
installation for a particular version of Python, plus a number of
additional packages. All the modifications that you make in this
installation (with pip) will not affect the general installation of
Python.

Remember to first **activate** your venv, en then:

- Before you start installing or upgrading anything, update pip &
  friends first: `pip install --upgrade pip wheel setuptools build`

- To upgrade all packages to their newest available versions: `pip
    install -U --upgrade-strategy eager`

- To install all packages required by the software, `pip install -r
    doc/requirements.txt`


### Install dynaflow-validation (the venv must be active)

- Install dynaflow-validation with all its dependencies: `pip install
  dynaflow-validation-RTE-AIA`  
  (when it is published as a publicly available package on PyPI)

- Install dynaflow-validation with all its dependencies manually:

   1. Clone the repo: git clone https://github.com/dynawo/dynawo-validation-AIA
	
   2. Build the package (go to the main directory of the package): `python -m build`
	
   3. Install the package: `pip install dist/dynawo_validation_RTE_AIA-X.Y.Z-py3-none-any.whl`


## Install Dynawo

- Follow the instructions of this website: https://dynawo.github.io/install/


## Install Hades

- To compare between DynaFlow and Hades, it is assumed that you
  already have Hades installed in your environment.


## Install Astre

- To compare between DynaWaltz and Astre, it is assumed that you
  already have Hades installed in your environment.


## Jupyter Notebooks configuration

Nowadays with recent versions of Jupyter Notebook you don't need to
configure anything after instalation, except maybe **register some
widgets which do not automatically do so when installed with
pip**. Currently there are only two, qgrid and ipydatagrid. You
"register" them with (while the venv is active!):
  * `jupyter nbextension enable --py --sys-prefix ipydatagrid`
  * `jupyter nbextension enable --py --sys-prefix qgrid`

Other than this, just open Jupyter Notebook and, in Kernel Options,
select ther Kernel corresponding to your venv, and you're done.

