
# Setting up a development environment for working on this code

## OS-level development software and utilities

- Install the base OS on a VM. We recommend Debian or Ubuntu (we used Debian
  11, installed from a standard "netinst" image). You will probably
  want to install a standard desktop environment (we use Gnome).
  
- Other interesting packages, such as ssh, rsync, and your preferred
  system utilities:
    - `sudo apt-get install aptitude open-vm-tools-desktop ssh rsync emacs`

- You do need a base install of Python 3 in the OS:
	- `sudo apt-get update && sudo apt-get upgrade`

	- `sudo apt-get install python3.9 python3-venv python3-pip`

- But the rest of all Python packages can be installed under a virtual
  environment in the $HOME of the user account that you will be
  using. This is all taken care of when you clone the code from this
  repo and install the package, as shown in the
  [README_INSTALLATION.md](/src/dynawo_validation/doc/README_INSTALLATION.md)
  under the general doc folder. You can peek inside the script
  [build_and_install.sh](/build_and_install.sh) if you want to see how
  it creates a virtual env and installs the package and all of its
  dependencies.


- Non-python stuff: you need to install GNU parallel if you want to be
  able to run contingencies in parallel and thus benefit from multiple
  CPU cores: `sudo apt-get install parallel`


- For developing Python code:

	- Install a python IDE (for example, PyCharm:
      https://www.jetbrains.com/help/pycharm/installation-guide.html#requirements)

	- Install these important Python development utilities: `apt-get
        install black flake8 python3-pytest`



## Python virtual environments

If you don't like the way the script
[build_and_install.sh](/build_and_install.sh) does things and you want
to manage your Python virtualenv your way, here's a quick reminder:

- Create the virtualenv: `python3 -m venv /path/to/new/virtual/environment`

- Activate the virtualenv: `source /path/to/new/virtual/environment/bin/activate`  
  (Now you should have the name of your virtual environment in
  parentheses before the username on the command line.)

- Deactivate virtualenv: `deactivate`

- Remove the virtualenv: `rm -rf /path/to/new/virtual/environment`



## Virtual environment configuration/maintenance (venv must be actived to proceed)

Again, configuration and upgrades to the venv are automatically taken
care of by re-runnuning periodically the script
[build_and_install.sh](/build_and_install.sh) at the root of the
repo. But if you prefer to do some of this manually, read on.

A virtualenv is a directory tree that contains a self-contained Python
installation (for a particular version of Python), plus a number of
additional packages. All the modifications that you make in this
installation (with pip) will not affect the general installation of
Python on the OS.

Remember to first **activate** your venv, en then:

- Before you start installing or upgrading anything, update pip &
  friends first: `pip install --upgrade pip wheel setuptools build`

- To upgrade all packages to their newest available versions: `pip
    install -U --upgrade-strategy eager`

- To install all packages required by the software, `pip install -r
    doc/requirements.txt`


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



## IDE configuration
	
To use the virtual environment's Python interpreter in our IDE, we may
have to configure our IDE to explicitly tell it so.  For example, in
PyCharm: go to Interpreter Configuration, choose the option that
allows you to add a new interpreter, and then select the Python
interpreter from the path where we have installed the Virtual
Environment (it's inside the bin directory).


## Install Dynawo

- Follow the instructions of this website: https://dynawo.github.io/install/


## Install Hades

- To compare between DynaFlow and Hades, it is assumed that you
  already have Hades installed in your environment.

## Install Astre

- To compare between DynaWaltz and Astre, it is assumed that you
  already have Hades installed in your environment.

