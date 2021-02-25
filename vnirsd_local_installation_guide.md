# vnirsd local installation guide [UNFINISHED, IN PROGRESS]

## introduction

This is a quick walkthrough explaining how to set up and run the VNIRSD on
your own computer. You can use that local installation to browse and view
spectra, edit your copy of the database as you please, and even import your 
own spectra. This is also useful for checking spectra files you plan to submit
to the "official" VNIRSD database.

Please not use this guide to deploy the VNIRSD on a public server. The
settings here are perfectly good for running a local copy for your personal
use, but they are both insecure and inefficient for installations facing the
open internet.

## requirements

### os

The instructions in this guide should work on Windows 10, MacOS 10.13 or
later, and any in-support version of any major distribution of Linux. The
VNIRSD can probably be made to run on several other operating systems,
including sandboxed/virtualized environments like Linux for Chrome OS or
Windows Subsystem for Linux, but these cases are not covered by this guide.

You will also need permission to install software, and some unusual firewall
or anti-malware software settings may interfere with the VNIRSD. You should
talk to a system administrator before attempting to install the VNIRSD in a
secure environment.

### hardware

For reasonable performance that also allows some other apps to run alongside
the VNIRSD, we recommend at least:
* 4 GB RAM
* x64-compatible processor, i3-4005U or better
* 10 GB free drive space

The in-browser graph viewer is the most resource-intensive part of the 
application. The faster your computer, the more smoothly this viewer will run,
especially if you are viewing several spectra at once. The database backend 
itself will run with fewer resources than these (unless you import many, many 
additional spectra).

### helper software

The VNIRSD has some functions that work in non-interactive mode, but a web
browser is required to use most of its functions. Firefox, Chrome, Safari, and
close Chrome relatives like Chromium and Edge are officially supported, but
other browsers may work. You will probably get the best performance from the
graphing interface in Chrome or a Chrome relative.

If you want to import your own spectra or work with exported spectra, it may
also be useful to have a spreadsheet program like Microsoft Excel, iWork
Numbers, or LibreOffice Calc installed. However, any other method of
manipulating or viewing CSV files will also work.

## step 1: install conda

*If you already have Anaconda or Miniconda installed on your computer, you can
skip this step.*

The official method of installing the VNIRSD uses the Python package manager
```conda``` to handle dependencies.
[You can get it here as part of the Miniconda distribution of Python.](https://docs.conda.io/projects/continuumio-conda/en/latest/user-guide/install/index.html).
Download the 64-bit version of the installer for your operating system and
follow the instructions on that website to set up your environment. Make sure
you download Miniconda3, not Miniconda2. The VNIRSD is not compatible with
Python 2.

## step 2: create conda environment

Now that you have ```conda``` installed, you can set up a Python environment
to run the VNIRSD. First, download the [local_install.yml](local_install.yml)
file from this repository. Next, open up a terminal: Anaconda Prompt on
Windows, Terminal on MacOS, or your console emulator of choice on Linux.
Navigate to the directory where you downloaded local_install.yml and run the
command:
```conda env create -f local_install.yml```

 The run:
```conda env list```

You should see ```vnirsd``` in the list of environments.

**Important:** now that you've created this this environment, you should 
always have it active whenever you work with the VNIRSD from the command line.
In particular, anything you try to do with the ```manage.py``` application 
without first running ```conda activate vnirsd``` will probably fail.

## step 3: download the VNIRSD software

Now navigate in the terminal to the location on your system you would like
to install the VNIRSD. Run:
```conda activate vnirsd```
Then run:
```git clone https://github.com/MillionConcepts/wwu_spec.git```
to download the VNIRSD software to your computer.

## step 4: generate settings file

Make a copy of the file
```wwu_spec/vnirsd/wwu_spec/local_settings_template.py```. Rename it to
```settings.py``` (make sure it's still in the ```wwu_spec/vnirsd/wwu_spec/``` 
directory).

## step 5: get database file

The VNIRSD is backed by a SQLite database. SQLite databases are structured as
single monolithic files. The "official" VNIRSD database file is not versioned
on GitHub because it's too large. In lieu of a better solution, we are currently
serving it from Google Drive. Place this file (```db.sqlite3```) in the 
```wwu_spec/vnirsd``` directory.

### alternative: make an empty database
If you **only** want to use spectra you import yourself and aren't interested
in the lab spectra in the official database, you can skip grabbing this file.
Instead, go to the ```wwu_spec/vnirsd/``` directory and run:
```python manage.py makemigrations```
```python manage.py migrate```

This will create a ```db.sqlite3``` file structured correctly for the VNIRSD
but containing no spectra or other information.

## step 6: make an admin user

This will allow you to upload your own spectra and use the admin console to
edit the database. Navigate to the ```wwu_spec/vnirsd/``` directory and run
```python manage.py createsuperuser```. Enter your username and password at
the prompts (the other information is optional).

## step 7: launch the server

*Reminder: if you get error messages, make sure you have activated the 
```conda``` environment by running ```conda activate vnirsd```.*
