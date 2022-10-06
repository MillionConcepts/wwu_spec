# visor local installation guide v0.2a (2022-10-05)

## introduction

This is a quick walkthrough explaining how to set up and run VISOR on
your own computer. You can use that local installation to browse and view
spectra, edit your copy of the database as you please, and even import your 
own spectra. This is also useful for checking spectra files you plan to submit
to the "official" VISOR database.

**Please do not use this guide to deploy VISOR on a public server. The
settings here are perfectly good for running a local copy for your personal
use, but they are both insecure and inefficient for installations facing the
open internet.**

## requirements

### os

The instructions in this guide should work on Windows 10, macOS 10.13 or
later, and any in-support version of any major distribution of Linux. They 
should also work on most sandboxed/virtualized versions of those 
environments, specifically including Windows Subsystem for Linux.

You will also need permission to install software, and some unusual firewall
or anti-malware software settings may interfere with VISOR. You should
talk to your system administrator before attempting to install VISOR in a
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

## step 0: clone the repository to your computer

If you have `git` installed on your computer, navigate in a terminal emulator to wherever you'd 
like to place the software and run `git clone https://github.com/MillionConcepts/wwu_spec.git`.
If you don't, and you are on Windows or MacOS, we recommend using 
[GitHub Desktop](https://desktop.github.com/). Install that program, run it, 
log in to your account, choose "clone a repository from the Internet," click the "URL" tab,
paste `https://github.com/MillionConcepts/wwu_spec.git` into the 'Repository URL' field,
and click 'Clone'.

## step 1: install conda

*Note: If you already have Anaconda or Miniconda installed on your computer, you can
skip this step. If it's very old or not working well, you should uninstall it first.
We **definitely** don't recommend installing multiple versions of `conda`
unless you have a strong and specific reason to do so.*

We recommend using [Mambaforge](https://github.com/conda-forge/miniforge). 
Download the appropriate version of the installer for your operating system and 
processor architecture (in most cases 64-bit). If you are on Windows, just double-click
the .exe to start installation; on MacOS or Linux, navigate to wherever you downloaded
the file in a terminal and run "sudo chmod +x name_of_file.sh" followed by 
"./name_of_file.sh". If this doesn't work, try running the commands in that website.

It you don't want to use Mambaforge, 
[you can get `conda` here as part of the Miniconda distribution of Python](https://docs.conda.io/projects/continuumio-conda/en/latest/user-guide/install/index.html).
Download the appropriate version of the installer and follow the instructions on that 
website to set up your `conda` installation. Make sure you download Miniconda3, not 
Miniconda2. VISOR is not compatible with Python 2.

**IMPORTANT: If you install Miniconda, replace `mamba` in all the commands below with `conda`.**

If you have trouble installing `conda`, check "common gotchas" below. If they don't help, 
there are a multitude of helpful tutorials online. [Here is one.](https://www.youtube.com/watch?v=zL65J9c5_KU))

## step 2: create conda environment

Now that you have `conda` installed, you can set up a Python environment
to use VISOR. Open a terminal window: Anaconda Prompt on Windows, Terminal on macOS,
or your terminal emulator of choice on Linux. (Windows might name the prompt "Miniconda Prompt" 
or something instead; just search for "prompt" in the Start Menu.)

Navigate to the directory where you put the repository and run the command:
`mamba env create -f local_install.yml`

## step 3: activate conda environment

Say yes at the prompts and let the installation finish. Then run:

`mamba env list`

You should see `visor` in the list of environments. Now run:

`conda activate visor`

and you will be in a Python environment that contains all the packages
VISOR needs. 

**Important:** now that you've created this environment, you should 
always have it active whenever you work with VISOR.

## step 4: create settings file

Make a copy of the file
```wwu_spec/wwu_spec/local_settings_template.py```. Rename it to
```settings.py``` (make sure it's still in the ```wwu_spec/wwu_spec/``` 
directory).

## step 5: get database files

VISOR is backed by SQLite databases. SQLite databases are contained in
single monolithic files. These files are too large to conveniently version 
on GitHub. [You can retrieve them from Google Drive.](https://drive.google.com/drive/folders/1lAMBXFL2t0oGhbD0pGXGW7lLSLQGa3Zz/)

Download the three files in this folder, unzip them, and place the unzipped 
files (`spectra.sqlite3`, `backend.sqlite3`, and `filtersets.sqlite3`) in 
the `data` subdirectory of the `wwu_spec` directory you cloned. If you are 
not sure you have the right directory, check to see if it contains a 
README.md file telling you to put database files in it. We recommend keeping
backups of these files, especially 
if you plan to edit or add spectra / filtersets yourself. That way, you can 
reverse any unintended changes just by copying your backup over the 
corresponding file in the installation root directory -- even while the
application is running!

### alternative: make an empty database
If you **only** want to use spectra you import yourself and aren't interested
in the lab spectra in the official database, you can skip grabbing 
these files. Instead, go to the `wwu_spec` (installation root) directory 
and run:

`python manage.py migrate`
`python manage.py migrate --database spectra`
`python manage.py migrate --database filtersets`

This will create files structured correctly for VISOR but empty of data.

## step 6: make an admin user [optional]

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
simply terminate that process (with CTRL/CMD+C or by closing the terminal) 
-- it doesn't need to be closed in any especially graceful way.

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
