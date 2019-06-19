# ForkStitcher
Repository for the tool to stitch Talos images annotated in the MAPS viewer



Installation instructions
----------
Dependencies are currently a bit complicated. To be able to run functions from the Stitcher or the MapsXmlParser, you need to do the following:

1. If you don't already have it, install Miniconda on your system. Follow the instructions here: https://docs.conda.io/en/latest/miniconda.html

2. Start the Anaconda Prompt program and install all dependencies there.

3. Install pyimage. The installation via pip does not seem to work at the moment, but conda is working. Thus:
```
conda create -n fork_stitcher python=3.7
conda activate fork_stitcher
conda config --add channels conda-forge 
conda install -n fork_stitcher pyimagej openjdk=8
```

4. Install other dependencies into virtualenv:
```
conda install -n fork_stitcher sphinx
conda install -n fork_stitcher openpyxl
conda install -n fork_stitcher pyyaml
pip install StyleFrame
```

5. Directly call code from within a python script or start the user interfaces by running the gui.py script.
**Warning: When importing stitch_MAPS_annotations for the first time, it takes a while (minutes) to get the ImageJ Fiji distribution from Maven. It doesn't print anything during that, just wait for it to get the ImageJ distribution.** On later runs, it takes a few seconds to initialize the ImageJ environment


Quick run
----------
1. Start the Anaconda Prompt program and activate your virtual environment:
```
conda activate fork_stitcher
```

2. Go to the ForkStitcher\fork-stitcher folder and type:
```
python gui.py
```



Documentation
----------
To create an updated documentation, run Sphinx in the docs folder:
```
cd docs
make latexpdf
make html
```

Building a standalone application for stitcher
----------
Example for Windows:
```
pyinstaller --onefile -p fork-stitcher --add-data C:\Users\j.luethi\AppData\Local\Continuum\miniconda3\envs\fork_stitcher\share\pyjnius\pyjnius.jar;.\share\pyjnius\pyjnius.jar fork-stitcher/gui.py
```

Where --add-data path points to where the pyjnius JAR file is located on the local machine, followed by .\share\pyjnius\pyjnius.jar
To find the location of pyjnius on your machine, use:

```
import logging
logging.basicConfig(level=logging.DEBUG)
import scyjava
```

Including an icon:
```
pyinstaller --onefile --icon stitchericon_1_EYC_icon.ico -p fork-stitcher --add-data C:\Users\j.luethi\AppData\Local\Continuum\miniconda3\envs\fork_stitcher\share\pyjnius\pyjnius.jar;.\share\pyjnius\pyjnius.jar fork-stitcher/gui.py
```


On Mac:
: instead of ; in the --add-data path and '' around the path
Folder version:
```
pyinstaller -p fork-stitcher --add-data '/miniconda3/envs/fork_stitcher/share/pyjnius/pyjnius.jar:./share/pyjnius/' fork-stitcher/run_stitching_batches.py
```

One File Option:
```
pyinstaller --onefile -p fork-stitcher --add-data '/miniconda3/envs/fork_stitcher/share/pyjnius/pyjnius.jar:./share/pyjnius/' fork-stitcher/run_stitching_batches.py
```
