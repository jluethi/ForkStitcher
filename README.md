# ForkStitcher
Repository for the tool to stitch Talos images annotated in the MAPS viewer



Installation instructions
----------
Dependencies are currently a bit complicated. To be able to run functions from the Stitcher or the MapsXmlParser, you need to do the following:

1. Clone the repository. If your machine does not have git installed, install git bash from here: https://gitforwindows.org. Then open the git bash program:
```
git clone https://github.com/jluethi/ForkStitcher
```

2. If you don't already have it, install Miniconda on your system. Follow the instructions here: https://docs.conda.io/en/latest/miniconda.html

3. Start the Anaconda Prompt program and install all dependencies there.

4. Install pyimage. The installation via pip does not seem to work at the moment, but conda is working. Thus:
```
conda create -n fork_stitcher python=3.7
conda activate fork_stitcher
conda config --add channels conda-forge 
conda install -n fork_stitcher pyimagej openjdk=8
```

5. Install other dependencies into virtualenv:
```
conda install -n fork_stitcher sphinx
conda install -n fork_stitcher openpyxl
conda install -n fork_stitcher pyyaml
pip install StyleFrame
```

6. Directly call code from within a python script or start the user interfaces by running the gui.py script.
**Warning: When importing stitch_MAPS_annotations for the first time, it takes a while (minutes) to get the ImageJ Fiji distribution from Maven. It doesn't print anything during that, just wait for it to get the ImageJ distribution.** On later runs, it takes a few seconds to initialize the ImageJ environment


Quick run
----------
1. Start the Anaconda Prompt program and activate your virtual environment:
```
conda activate fork_stitcher
```

2. Go to the ForkStitcher\fork-stitcher folder and type:
```
cd ForkStitcher
cd fork-stitcher
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
You need to install all dependencies for the Stitcher as described above. I recommend testing whether everything is working by using the Quick run instructions afterwards.

**For Windows:**

Edit the Stitcher.spec file:
- change pathex to your local path of the git directory
- datas needs to contain 3 paths. Change the source (the first of the two entries) to where those are on your local system and leave the target.
  1. Path to pyjnius.jar. You can run the following from python (within your conda virtualenv) to find the pyjnius.jar (should be somewhere in your virtualenv):
  ```
  import logging
  logging.basicConfig(level=logging.DEBUG)
  import scyjava
  ```
  2. Path to an openjdk 8. I recommend downloading the zip version for your system from here: https://adoptopenjdk.net/releases.html#x64_win
  
  3. Path to maven. I recommend downloading the binary zip from here: https://maven.apache.org/download.cgi 
  
To create an executable:
```
conda activate fork_stitcher
cd path\to\ForkStitcher
pyinstaller Stitcher.spec
```

**IMPORTANT**: Go into the dist\Stitcher folder. Manually delete the jvm.dll file. Then, you have a working Stitcher.exe in the dist\Stitcher folder. Just don't move the .exe file out of the folder (Shortcuts are fine though).


**For Mac:**

The User Interface does not work on Mac because of an issue with pyimage and tkinter. See here for details and ideas on how to work around it: https://github.com/imagej/pyimagej/issues/39
```
pyinstaller -p fork-stitcher --add-data '/miniconda3/envs/fork_stitcher/share/pyjnius/pyjnius.jar:./share/pyjnius/' fork-stitcher/run_stitching_batches.py
```
Where --add-data path points to where the pyjnius JAR file is located on the local machine

