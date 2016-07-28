
OneRing Installation
-----------------------

Prerequisites
=============================
1. Python 2.7+ required. RHEL 6 ship with python 2.6 and is too old for pip. Recommend to use mac osx.
2. These steps are conducted under your onering directory. Please 'cd /../onering' first.

Install a virtual environment
=============================

Required *only once* to create the virtual environment.  Once you have done this, you can skip this step.

```
pip install --upgrade pip
pip install virtualenv
mkdir ~/virtualenvs
virtualenv ~/virtualenvs/onering
```

Activate virtual Environment
============================

This only needs to be done when you open a new terminal and if you plan to work on onering on that terminal.
```
source ~/virtualenvs/onering/bin/activate
```

Install dependencies
====================

After you activate the virtual environment, you gotta do this once to install any libraries we use.

```
pip install -r requirements.txt
```

Install Package
===============

```
sh ./bin/clean_install.sh
```

Run Samples
===========

```
python example.py
```

(optional) Deactivating virtual Environment
===========================================

This only works in the virtual environment.
```
deactivate
```
