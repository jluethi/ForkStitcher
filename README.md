# ForkStitcher
Repository for the tool to stitch Talos images annotated in the MAPS viewer



Installation instructions
----------
Dependencies are currently a bit complicated. To be able to run functions from the Stitcher or the MapsXmlParser, you need to do the following (replace virtualenv_name with the name that you want for your virtual environment):

1. Install pyimage. The installation via pip does not seem to work at the moment, but conda is working. Thus:
```
conda create -n virtualenv_name python=3.7
conda activate virtualenv_name
conda config --add channels conda-forge 
conda install -n virtualenv_name pyimagej openjdk=8
```

2. Install other dependencies into virtualenv:
```
conda install -n virtualenv_name sphinx
conda install -n virtualenv_name openpyxl
conda install -n virtualenv_name pyyaml
pip install StyleFrame
```

3. Directly call code from within a python script or start the user interfaces by running the gui.py script.
**Warning: When importing stitch_MAPS_annotations for the first time, it takes a while (minutes) to get the ImageJ Fiji distribution from Maven. It doesn't print anything during that, just wait for it to get the ImageJ distribution.** On later runs, it takes a few seconds to initialize the ImageJ environment

Documentation
----------
To create an updated documentation, run Sphinx in the docs folder:
```
cd docs
make latexpdf
make html
```
