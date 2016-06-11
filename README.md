librosa
=======
A python package for music and audio analysis.  

[![PyPI](https://img.shields.io/pypi/v/librosa.svg)](https://pypi.python.org/pypi/librosa)
[![License](https://img.shields.io/pypi/l/librosa.svg)](https://github.com/librosa/librosa/blob/master/LICENSE.md)
[![DOI](https://zenodo.org/badge/doi/10.5281/zenodo.32193.svg)](http://dx.doi.org/10.5281/zenodo.32193)

[![Build Status](https://travis-ci.org/librosa/librosa.png?branch=master)](http://travis-ci.org/librosa/librosa?branch=master)
[![Coverage Status](https://coveralls.io/repos/librosa/librosa/badge.svg?branch=master)](https://coveralls.io/r/librosa/librosa?branch=master)


Documentation
-------------
See http://librosa.github.io/librosa/ for a complete reference manual and introductory tutorials.


Demonstration notebooks
-----------------------
What does librosa do?  Here are some quick demonstrations:

* [Introduction notebook](http://nbviewer.ipython.org/github/librosa/librosa/blob/master/examples/LibROSA%20demo.ipynb): a brief introduction to some commonly used features.
* [Decomposition and IPython integration](http://nbviewer.ipython.org/github/librosa/librosa/blob/master/examples/LibROSA%20audio%20effects%20and%20playback.ipynb): an intermediate demonstration, illustrating how to process and play back sound


Installation
------------

The latest stable release is available on PyPI, and you can install it by saying 
```
pip install librosa
```

To build librosa from source, say `python setup.py build`.
Then, to install librosa, say `python setup.py install`.
If all went well, you should be able to execute the demo scripts under `examples/`
(OS X users should follow the installation guide given below).

Alternatively, you can download or clone the repository and use `pip` to handle dependencies:

```
unzip librosa.zip
pip install -e librosa
```
or
```
git clone https://github.com/librosa/librosa.git
pip install -e librosa
```

By calling `pip list` you should see `librosa` now as an installed pacakge:
```
librosa (0.x.x, /path/to/librosa)
```

### Hints for OS X

#### ffmpeg

To fuel `audioread` with more audio-decoding power, you can install *ffmpeg* which
ships with many audio decoders.

You can use *homebrew* to install the programm by calling
`brew install ffmpeg` or get a binary version from their website https://www.ffmpeg.org.

Discussion
----------

Please direct non-development questions and discussion topics to our web forum at 
https://groups.google.com/forum/#!forum/librosa 


Citing
------

Please refer to the Zenodo link below for citation information.
[![DOI](https://zenodo.org/badge/doi/10.5281/zenodo.32193.svg)](http://dx.doi.org/10.5281/zenodo.32193)
