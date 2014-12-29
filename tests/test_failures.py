#!/usr/bin/env python
# CREATED:2014-12-29 10:52:23 by Brian McFee <brian.mcfee@nyu.edu>
# unit tests for ill-formed inputs

# Disable cache
import os
try:
    os.environ.pop('LIBROSA_CACHE_DIR')
except:
    pass

import numpy as np
import librosa
from nose.tools import raises


@raises(ValueError)
def test_mono_valid_stereo():
    '''valid_audio: mono=True,  y.ndim==2'''
    y = np.zeros((2, 1000))
    librosa.util.valid_audio(y, mono=True)


def test_valid_stereo_or_mono():
    '''valid_audio: mono=False, y.ndim==1'''
    y = np.zeros(1000)
    librosa.util.valid_audio(y, mono=False)


def test_valid_mono():
    '''valid_audio: mono=True,  y.ndim==1'''
    y = np.zeros(1000)
    librosa.util.valid_audio(y, mono=True)


def test_valid_stereo():
    '''valid_audio: mono=False, y.ndim==2'''
    y = np.zeros((2, 1000))
    librosa.util.valid_audio(y, mono=False)


@raises(ValueError)
def test_valid_audio_type():
    '''valid_audio: list input'''
    y = list(np.zeros(1000))
    librosa.util.valid_audio(y)


@raises(ValueError)
def test_valid_audio_nan():
    '''valid_audio: NaN'''
    y = np.zeros(1000)
    y[10] = np.NaN
    librosa.util.valid_audio(y)


@raises(ValueError)
def test_valid_audio_inf():
    '''valid_audio: Inf'''
    y = np.zeros(1000)
    y[10] = np.inf
    librosa.util.valid_audio(y)


@raises(ValueError)
def test_frame_hop():
    '''frame: hop_length=0'''
    y = np.zeros(128)
    librosa.util.frame(y, frame_length=10, hop_length=0)


@raises(ValueError)
def test_frame_discontiguous():
    '''frame: discontiguous input'''
    y = np.zeros((128, 2)).T
    librosa.util.frame(y[0], frame_length=64, hop_length=64)


def test_frame_contiguous():
    '''frame: discontiguous input'''
    y = np.zeros((2, 128))
    librosa.util.frame(y[0], frame_length=64, hop_length=64)


@raises(ValueError)
def test_frame_size():
    '''frame: len(y) == 128, frame_length==256, hop_length=128'''
    y = np.zeros(64)
    librosa.util.frame(y, frame_length=256, hop_length=128)
