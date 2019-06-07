# ForkStitcher
Repository for the tool to stitch Talos images annotated in the MAPS viewer



Installation instructions
----------
Dependencies are currently a bit complicated. To be able to run functions from the Stitcher or the MapsXmlParser, you need to do the following:

1. Install pyimage. The installation via pip does not seem to work at the moment, but conda is working. Thus:
```
conda create -n virtualenv_name python=3.7
source activate virtualenv_name
conda config --add channels conda-forge 
conda install -n virtualenv_name pyimagej openjdk=8
```

2. Install other dependencies into virtualenv:
```
conda install -n fork_stitcher sphinx
conda install -n fork_stitcher openpyxl
conda install -n fork_stitcher pyyaml
pip install StyleFrame
```

3. To ensure logging works, either wait until the bug in [jgo](https://github.com/scijava/jgo/pull/39) is fixed or locally install this forked version with the fix to the logging preferences:
```
git clone https://github.com/jluethi/jgo
cd jgo
pip uninstall jgo
pip install .
```

4. Directly call code from within a python script or start the user interfaces by running the gui.py script.

Documentation
----------
To create an updated documentation, run Sphinx in the docs folder:
```
cd docs
make latexpdf
make html
```
