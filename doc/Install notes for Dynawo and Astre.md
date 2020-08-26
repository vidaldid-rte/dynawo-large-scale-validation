
INSTALLATION NOTES FOR DYNAWO AND ASTRE
=======================================


Installing Dynawo
-----------------

Debian 10.x ("Buster"): install the base OS with a standard Gnome
desktop, then add these packages:

```
# Some post-OS-install packages you may want:
apt-get install aptitude open-vm-tools rsync emacs
apt-get install open-vm-tools-desktop  # If it's a VM

# Some packages we like to have:
# (NOTE: Intel's MKL provides libmkl_rt.so, an alternative to both libblas.so.3 and liblapack.so.3)
# (NOTE: default Java in Debian Buster is now OpenJDK 11)
apt-get install intel-mkl default-jre default-jdk

# Dynawo packages, for usage: (Debian Buster already includes: unzip, python, python3)
apt-get install gcc g++ curl cmake python-lxml python3-lxml libxml2-utils

# Dynawo packages, for building from sources:
apt-get install git \
   libcurl4-openssl-dev \
   clang gfortran gcovr lcov \
   lsb-release autoconf pkgconf automake make libtool cmake hwloc patch \
   libncurses5-dev gettext libreadline-dev libdigest-perl-md5-perl \
   libsqlite3-dev libarchive-dev zlib1g-dev \
   libblas-dev liblapack-dev libboost-all-dev liblpsolve55-dev \
   doxygen doxygen-latex \
   libexpat1-dev libxerces-c-dev \
   qt4-qmake qt4-dev-tools \
   python-pip python-psutil \
   texlive-science
```


### Short notes about compiling Dynawo (public version 1.2.0):

Even though we'll be using RTE's private build of Dynawo, it is
interesting to build Dynawo from scratch.

Steps:

  * mkdir $HOME/src && cd $HOME/src && git clone https://github.com/dynawo/dynawo.git

  * edit myEnvDynawo.sh  (just edit DYNAWO_HOME)

  * run: ./myEnvDynawo.sh build-user

  * Build the documentation: cd documentation && ./dynawo_documentation.sh

Tested with public version master (7a00648c), on July 8 2020.




Installing Astre
----------------

IMPORTANT REQUIREMENTS (Astre will coredump if you don't do this):

  * The Korn shell must be available

  * Make sure that /usr/lib64 is symlinked to /lib64 *[EXPLANATION:
    qsss2-c_r, qsss2-c_d are incorrectly linked so that they require the
    interpreter (ld-linux-x86-64.so.2) to be located at /usr/lib64,
    instead of /lib64.  This is non-standard and some Linux systems do
    not have this, in which case Astre fails mysteriously.]*
  
   * TODO: is the locale en_GB really needed?

Just unpack the tgz file provided by RTE, under any system
directory (in our case: `/opt/astre`).

Following the README, we created our own astre launcher (`astre`),
which we placed under a directory that's on the PATH
(`/usr/local/bin`):

   * This launcher sets all the environment variables as done in the
     `enable`file.
	 
   * In addition, we include the conversion of the output XML to CSV,
     using the script `astreToCSV.py`.

