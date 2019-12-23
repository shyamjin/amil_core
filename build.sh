#!/bin/bash

file_name=$1
echo ${file_name}

#-- Find Python interpreter
export PYTHON=$(which python3.6)
if [[ -z ${PYTHON} ]]
then
    echo "Python interpreter not found!"
    echo "Exiting now."
    exit 1
fi
echo "Python executable found at: ${PYTHON}"

# Check Python version is as expected
pyver=$($PYTHON --version 2>&1)
echo "Found version: ${pyver}"
if [[ ! ${pyver} =~ Python\ 3.6* ]]
then
    echo "We require Python version 3.6."
    echo "Exiting now."
    exit 1
fi

#-- Compile core Amily scripts to '.pyc' files, into the same directory and without the '.cpython-36' infix (option -b)
$PYTHON -m compileall \
  Amily_Prod/*.py \
  Amily_Prod/Atoms_core/*.py \
  Amily_Prod/Classification/*.py \
  Self_Service/*.py \
  -f \
  -b

if [[ $? -ne 0 ]] ; then echo "Error compiling Python scripts. Exiting"; exit 1; fi

#-- Create build info file
echo -e "Jenkins: ${BUILD_TAG}\nGit: ${GIT_BRANCH} ${GIT_COMMIT}" > build_info_core.txt

#-- Create zip file package for Value Pack

zip -r ${file_name} \
 Amily_Prod \
 Amily_Test \
 Self_Service \
 amily \
 amily_env_template.sh \
 install.sh \
 uninstall.sh \
 build_info_core.txt \
 -x build.sh \
    \*.git\* \
    Amily_Prod/*.py \
    Amily_Prod/Atoms_core/*.py \
    Amily_Prod/Classification/*.py \
    Self_Service/*.py \
    \
    Amily_Prod/moved_to_impl/\*   \
    Amily_Prod/Pickles/\*.pkl     \
    Amily_Prod/\*.ipynb           \
    \
    Self_Service/Dev_Versions/\*  \
    Self_Service/\*.ipynb

echo "The build is completed"