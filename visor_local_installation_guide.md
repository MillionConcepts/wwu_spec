# visor local installation guide v0.1a (2021-03-19)

## introduction

This is a quick walkthrough explaining how to set up and run VISOR on
your own computer. You can use that local installation to browse and view
spectra, edit your copy of the database as you please, and even import your 
own spectra. This is also useful for checking spectra files you plan to submit
to the "official" VISOR database.

Please do not use this guide to deploy VISOR on a public server. The
settings here are perfectly good for running a local copy for your personal
use, but they are both insecure and inefficient for installations facing the
open internet.

## requirements

### os

The instructions in this guide should work on Windows 10, macOS 10.13 or
later, and any in-support version of any major distribution of Linux. The
VISOR can probably be made to run on several other operating systems,
including sandboxed/virtualized environments like Linux for Chrome OS or
Windows Subsystem for Linux, but these cases are not covered by this guide.

You will also need permission to install software, and some unusual firewall
or anti-malware software settings may interfere with VISOR. You should
talk to a system administrator before attempting to install VISOR in a
secure environment.

### hardware

For reasonable performance that also allows some other apps to run alongside
VISOR, we recommend at least:
* 4 GB RAM
* x64-compatible processor, i3-4005U or better
* 10 GB free drive space

The in-browser graph viewer is the most resource-intensive part of the 
application. The faster your computer, the more smoothly this viewer will run,
especially if you are viewing several spectra at once. The database backend 
itself will run with fewer resources than these (unless you import many, many 
additional spectra).

### helper software

VISOR has some functions that work in non-interactive mode, but a web
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
skip this step. If it's very old and not working well, you should uninstall it first.
We **definitely** don't recommend installing multiple versions of ```conda```
unless you have a really strong need to do so.*

[You can get ```conda``` here as part of the Miniconda distribution of Python](https://docs.conda.io/projects/continuumio-conda/en/latest/user-guide/install/index.html).
Download the 64-bit version of the installer for your operating system and
follow the instructions on that website to set up your environment. Make sure
you download Miniconda3, not Miniconda2. VISOR is not compatible with
Python 2.

## step 2: create conda environment

Now that you have ```conda``` installed, you can set up a Python environment
to run VISOR. First, download the 
[local_install.yml](https://drive.google.com/file/d/1ptrTI_qbJdaEYLwq5bMtv-AfXdBL_1D5/)
file. Next, open up a terminal: Anaconda Prompt on Windows, Terminal on macOS,
or your console emulator of choice on Linux. Navigate to the directory where
you put local_install.yml and run the command:

```conda env create -f local_install.yml```

Say yes at the prompts and let the installation finish. Then run:

```conda env list```

You should see ```VISOR``` in the list of environments. Now run:

```conda activate visor```

and you will be in a Python environment that contains all the packages
VISOR needs to run. 

**Important:** now that you've created this environment, you should 
always have it active whenever you work with VISOR from the command line.
In particular, anything you try to do with the ```manage.py``` application 
without first running ```conda activate visor``` will probably fail.

If you can't activate the environment, see 'common gotchas' below.


## step 3: download the VISOR software

Navigate to wherever on your computer you'd like to install VISOR and run
```git clone https://github.com/MillionConcepts/wwu_spec.git```. This will
make a directory named ```wwu_spec``` with subdirectories containing other
parts of the application. For the remainder of the guide, ```wwu_spec``` will
just refer to that installation root directory, which will be wherever on your
system you installed it at this step.

## step 4: create settings file

Make a copy of the file
```wwu_spec/wwu_spec/local_settings_template.py```. Rename it to
```settings.py``` (make sure it's still in the ```wwu_spec/wwu_spec/``` 
directory).

## step 5: get database file

VISOR is backed by a SQLite database. SQLite databases are contained in
single monolithic files. The "official" VISOR database file is not versioned
on GitHub because it's too large. We are
[currently serving it from Google Drive.](https://drive.google.com/file/d/1ODiwwN1k2wkggcDWuMiZFppYFuRtM8z5/)
(This is a 'clean' version of the database with no user accounts or samples
marked out for QA.) Unzip this and place the unzipped file (```db.sqlite3```) 
in the ```wwu_spec```  (installation root) directory. We recommend keeping a 
backup of this file somewhere outside the working directory, especially if 
you plan to edit or add spectra yourself. That way, you can reverse any 
unintended changes to the database just by copying your backup over the 
```db.sqlite3``` file in the installation root directory -- even while the
application is running.

### alternative: make an empty database
If you **only** want to use spectra you import yourself and aren't interested
in the lab spectra in the official database, you can skip grabbing this file.
Instead, go to the ```wwu_spec``` (installation root) directory and run:

```python manage.py migrate```

This will create a ```db.sqlite3``` file structured correctly for VISOR
but containing no spectra or other information.

## step 6: make an admin user

This will allow you to upload your own spectra and use the admin console to
edit the database. Navigate to the ```wwu_spec``` (installation root) 
directory and run ```python manage.py createsuperuser```. Enter your username 
and password at the prompts (the other information is optional).

## step 7: launch the server

Run the server by navigating to the ```wwu_spec``` (installation root) 
directory and running ```python manage.py runserver```. You can then navigate
to ```127.0.0.1:8000``` in your browser of choice to use VISOR. Don't
close that terminal while you're still using VISOR, or the application
will also close. When you're ready to close or restart VISOR, you can
simply terminate that process (with CTRL/CMD+C or by closing the terminal) -- it
doesn't need to be closed in any especially graceful way.

# common gotchas

* If you get error messages when running the server, make sure you have activated 
the```conda``` environment by running ```conda activate visor```.
* If you use multiple shells on macOS or Linux, ```conda``` will only 
automatically set up the one it detects as your system default. If you can't
activate the environment, check a different shell.
* If you've already got an installed version of ```conda``` on your system, installing
an additional version without uninstalling the old one may make environment setup very
challenging. We do not recommend installing multiple versions+ of ```conda``` at once
unless you really need to.
