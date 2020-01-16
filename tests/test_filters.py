#!/usr/bin/env python
# CREATED:2013-03-08 15:25:18 by Brian McFee <brm2132@columbia.edu>
#  unit tests for librosa.filters
#
# This test suite verifies that librosa core routines match (numerically) the output
# of various DPWE matlab implementations on a broad range of input parameters.
#
# All test data is generated by the Matlab script "makeTestData.m".
# Each test loads in a .mat file which contains the input and desired output for a given
# function.  The test then runs the librosa implementation and verifies the results
# against the desired output, typically via numpy.allclose().
#

# Disable cache
import os
try:
    os.environ.pop('LIBROSA_CACHE_DIR')
except KeyError:
    pass

import glob
import numpy as np
import scipy.io

import pytest

import librosa


# -- utilities --#
def files(pattern):
    test_files = glob.glob(pattern)
    test_files.sort()
    return test_files


def load(infile):
    DATA = scipy.io.loadmat(infile, chars_as_strings=True)
    return DATA
# --           --#


# -- Tests     --#
def test_hz_to_mel():
    def __test_to_mel(infile):
        DATA = load(infile)
        z = librosa.hz_to_mel(DATA['f'], DATA['htk'])

        assert np.allclose(z, DATA['result'])

    for infile in files(os.path.join('tests', 'data', 'feature-hz_to_mel-*.mat')):
        yield (__test_to_mel, infile)

    pass


def test_mel_to_hz():

    def __test_to_hz(infile):
        DATA = load(infile)
        z = librosa.mel_to_hz(DATA['f'], DATA['htk'])

        assert np.allclose(z, DATA['result'])

    for infile in files(os.path.join('tests', 'data', 'feature-mel_to_hz-*.mat')):
        yield (__test_to_hz, infile)

    pass


def test_hz_to_octs():
    def __test_to_octs(infile):
        DATA = load(infile)
        z = librosa.hz_to_octs(DATA['f'])

        assert np.allclose(z, DATA['result'])

    for infile in files(os.path.join('tests', 'data', 'feature-hz_to_octs-*.mat')):
        yield (__test_to_octs, infile)

    pass


def test_melfb():

    def __test_default_norm(infile):
        DATA = load(infile)

        wts = librosa.filters.mel(DATA['sr'][0, 0],
                                  DATA['nfft'][0, 0],
                                  n_mels=DATA['nfilts'][0, 0],
                                  fmin=DATA['fmin'][0, 0],
                                  fmax=DATA['fmax'][0, 0],
                                  htk=DATA['htk'][0, 0])

        # Our version only returns the real-valued part.
        # Pad out.
        wts = np.pad(wts, [(0, 0),
                           (0, int(DATA['nfft'][0]//2 - 1))],
                     mode='constant')

        assert wts.shape == DATA['wts'].shape
        assert np.allclose(wts, DATA['wts'])

    for infile in files(os.path.join('tests', 'data', 'feature-melfb-*.mat')):
        yield (__test_default_norm, infile)

    def __test_with_norm(infile):
        DATA = load(infile)
        # if DATA['norm'] is empty, pass None.
        if DATA['norm'].shape[-1] == 0:
            norm = None
        else:
            norm = DATA['norm'][0, 0]
            if norm == 1:
                norm = 'slaney'
        wts = librosa.filters.mel(DATA['sr'][0, 0],
                                  DATA['nfft'][0, 0],
                                  n_mels=DATA['nfilts'][0, 0],
                                  fmin=DATA['fmin'][0, 0],
                                  fmax=DATA['fmax'][0, 0],
                                  htk=DATA['htk'][0, 0],
                                  norm=norm)
        # Pad out.
        wts = np.pad(wts, [(0, 0),
                           (0, int(DATA['nfft'][0]//2 - 1))],
                     mode='constant')

        assert wts.shape == DATA['wts'].shape
        assert np.allclose(wts, DATA['wts'])

    for infile in files(os.path.join('tests', 'data', 'feature-melfbnorm-*.mat')):
        yield (__test_with_norm, infile)


@pytest.mark.parametrize('norm', [1, np.inf])
def test_mel_norm1(norm):

    # Check that calling with norm=1 triggers a warning
    # This should be removed in 0.8.0
    with pytest.warns(FutureWarning, match='compatibility'):
        librosa.filters.mel(22050, 2048, norm=norm)


def test_mel_gap():

    # This configuration should trigger some empty filters
    sr = 44100
    n_fft = 1024
    fmin = 0
    fmax = 2000
    n_mels = 128
    htk = True

    with pytest.warns(UserWarning, match='Empty filters'):
        librosa.filters.mel(sr, n_fft, n_mels=n_mels,
                            fmin=fmin, fmax=fmax, htk=htk)


def test_chromafb():

    def __test(infile):
        DATA = load(infile)

        octwidth = DATA['octwidth'][0, 0]
        if octwidth == 0:
            octwidth = None

        # Convert A440 parameter to tuning parameter
        A440 = DATA['a440'][0, 0]

        tuning = DATA['nchroma'][0, 0] * (np.log2(A440) - np.log2(440.0))

        wts = librosa.filters.chroma(DATA['sr'][0, 0],
                                     DATA['nfft'][0, 0],
                                     DATA['nchroma'][0, 0],
                                     tuning=tuning,
                                     ctroct=DATA['ctroct'][0, 0],
                                     octwidth=octwidth,
                                     norm=2,
                                     base_c=False)

        # Our version only returns the real-valued part.
        # Pad out.
        wts = np.pad(wts, [(0, 0),
                           (0, int(DATA['nfft'][0, 0]//2 - 1))],
                     mode='constant')

        assert wts.shape == DATA['wts'].shape
        assert np.allclose(wts, DATA['wts'])

    for infile in files(os.path.join('tests', 'data', 'feature-chromafb-*.mat')):
        yield (__test, infile)


def test__window():

    def __test(n, window):

        wdec = librosa.filters.__float_window(window)

        if n == int(n):
            n = int(n)
            assert np.allclose(wdec(n), window(n))
        else:
            wf = wdec(n)
            fn = int(np.floor(n))
            assert not np.any(wf[fn:])

    for n in [16, 16.0, 16.25, 16.75]:
        for window_name in ['barthann', 'bartlett', 'blackman',
                            'blackmanharris', 'bohman', 'boxcar', 'cosine',
                            'flattop', 'hamming', 'hann', 'hanning',
                            'nuttall', 'parzen', 'triang']:
            window = getattr(scipy.signal.windows, window_name)
            yield __test, n, window


def test_constant_q():

    def __test(sr, fmin, n_bins, bins_per_octave, filter_scale,
               pad_fft, norm):

        F, lengths = librosa.filters.constant_q(sr,
                                                fmin=fmin,
                                                n_bins=n_bins,
                                                bins_per_octave=bins_per_octave,
                                                filter_scale=filter_scale,
                                                pad_fft=pad_fft,
                                                norm=norm)

        assert np.all(lengths <= F.shape[1])

        assert len(F) == n_bins

        if not pad_fft:
            return

        assert np.mod(np.log2(F.shape[1]), 1.0) == 0.0

        # Check for vanishing negative frequencies
        F_fft = np.abs(np.fft.fft(F, axis=1))
        # Normalize by row-wise peak
        F_fft = F_fft / np.max(F_fft, axis=1, keepdims=True)
        assert not np.any(F_fft[:, -F_fft.shape[1]//2:] > 1e-4)

    sr = 11025

    # Try to make a cq basis too close to nyquist
    tf = pytest.mark.xfail(__test, raises=librosa.ParameterError)
    yield (tf, sr, sr/2.0, 1, 12, 1, True, 1)

    # with negative fmin
    yield (tf, sr, -60, 1, 12, 1, True, 1)

    # with negative bins_per_octave
    yield (tf, sr, 60, 1, -12, 1, True, 1)

    # with negative bins
    yield (tf, sr, 60, -1, 12, 1, True, 1)

    # with negative filter_scale
    yield (tf, sr, 60, 1, 12, -1, True, 1)

    # with negative norm
    yield (tf, sr, 60, 1, 12, 1, True, -1)

    for fmin in [None, librosa.note_to_hz('C3')]:
        for n_bins in [12, 24]:
            for bins_per_octave in [12, 24]:
                for filter_scale in [1, 2]:
                    for norm in [1, 2]:
                        for pad_fft in [False, True]:
                            yield (__test, sr, fmin, n_bins,
                                    bins_per_octave, filter_scale, pad_fft,
                                    norm)


def test_window_bandwidth():

    hann_bw = librosa.filters.window_bandwidth('hann')
    hann_scipy_bw = librosa.filters.window_bandwidth(scipy.signal.hann)
    assert hann_bw == hann_scipy_bw


def test_window_bandwidth_dynamic():

    # Test with a window constructor guaranteed to not exist in
    # the dictionary.
    # should behave like a box filter, which has enbw == 1
    assert librosa.filters.window_bandwidth(lambda n: np.ones(n)) == 1


@pytest.mark.xfail(raises=ValueError)
def test_window_bandwidth_missing():
    librosa.filters.window_bandwidth('made up window name')


def binstr(m):

    out = []
    for row in m:
        line = [' '] * len(row)
        for i in np.flatnonzero(row):
            line[i] = '.'
        out.append(''.join(line))
    return '\n'.join(out)


def test_cq_to_chroma():

    def __test(n_bins, bins_per_octave, n_chroma, fmin, base_c, window):
        # Fake up a cqt matrix with the corresponding midi notes

        if fmin is None:
            midi_base = 24  # C2
        else:
            midi_base = librosa.hz_to_midi(fmin)

        midi_notes = np.linspace(midi_base,
                                 midi_base + n_bins * 12.0 / bins_per_octave,
                                 endpoint=False,
                                 num=n_bins)
        #  We don't care past 2 decimals here.
        # the log2 inside hz_to_midi can cause problems though.
        midi_notes = np.around(midi_notes, decimals=2)
        C = np.diag(midi_notes)

        cq2chr = librosa.filters.cq_to_chroma(n_input=C.shape[0],
                                              bins_per_octave=bins_per_octave,
                                              n_chroma=n_chroma,
                                              fmin=fmin,
                                              base_c=base_c,
                                              window=window)

        chroma = cq2chr.dot(C)
        for i in range(n_chroma):
            v = chroma[i][chroma[i] != 0]
            v = np.around(v, decimals=2)

            if base_c:
                resid = np.mod(v, 12)
            else:
                resid = np.mod(v - 9, 12)

            resid = np.round(resid * n_chroma / 12.0)
            assert np.allclose(np.mod(i - resid, 12), 0.0), i-resid

    for n_octaves in [2, 3, 4]:
        for semitones in [1, 3]:
            for n_chroma in 12 * np.arange(1, 1 + semitones):
                for fmin in [None] + list(librosa.midi_to_hz(range(48, 61))):
                    for base_c in [False, True]:
                        for window in [None, [1]]:
                            bins_per_octave = 12 * semitones
                            n_bins = n_octaves * bins_per_octave

                            if np.mod(bins_per_octave, n_chroma) != 0:
                                tf = pytest.mark.xfail(__test, raises=librosa.ParameterError)
                            else:
                                tf = __test
                            yield (tf, n_bins, bins_per_octave,
                                   n_chroma, fmin, base_c, window)


@pytest.mark.xfail(raises=librosa.ParameterError)
def test_get_window_fail():

    librosa.filters.get_window(None, 32)


def test_get_window():

    def __test(window):

        w1 = librosa.filters.get_window(window, 32)
        w2 = scipy.signal.get_window(window, 32)

        assert np.allclose(w1, w2)

    for window in ['hann', u'hann', 4.0, ('kaiser', 4.0)]:
        yield __test, window


def test_get_window_func():

    w1 = librosa.filters.get_window(scipy.signal.boxcar, 32)
    w2 = scipy.signal.get_window('boxcar', 32)
    assert np.allclose(w1, w2)


def test_get_window_pre():
    def __test(pre_win):
        win = librosa.filters.get_window(pre_win, len(pre_win))
        assert np.allclose(win, pre_win)

    yield __test, scipy.signal.hann(16)
    yield __test, list(scipy.signal.hann(16))
    yield __test, [1, 1, 1]


def test_semitone_filterbank():
    # We test against Chroma Toolbox' elliptical semitone filterbank
    # load data from chroma toolbox
    gt_fb = scipy.io.loadmat(os.path.join('tests', 'data', 'filter-muliratefb-MIDI_FB_ellip_pitch_60_96_22050_Q25'),
                             squeeze_me=True)['h']

    # standard parameters reproduce settings from chroma toolbox
    mut_ft_ba, mut_srs_ba = librosa.filters.semitone_filterbank(flayout='ba')
    mut_ft_sos, mut_srs_sos = librosa.filters.semitone_filterbank(flayout='sos')

    for cur_filter_id in range(len(mut_ft_ba)):
        cur_filter_gt = gt_fb[cur_filter_id + 23]
        cur_filter_mut = mut_ft_ba[cur_filter_id]
        cur_filter_mut_sos = scipy.signal.sos2tf(mut_ft_sos[cur_filter_id])

        cur_a_gt = cur_filter_gt[0]
        cur_b_gt = cur_filter_gt[1]
        cur_a_mut = cur_filter_mut[1]
        cur_b_mut = cur_filter_mut[0]
        cur_a_mut_sos = cur_filter_mut_sos[1]
        cur_b_mut_sos = cur_filter_mut_sos[0]

        # we deviate from the chroma toolboxes for pitches 94 and 95
        # (filters 70 and 71) by processing them with a higher samplerate
        if (cur_filter_id != 70) and (cur_filter_id != 71):
            assert np.allclose(cur_a_gt, cur_a_mut)
            assert np.allclose(cur_b_gt, cur_b_mut, atol=1e-4)

            assert np.allclose(cur_a_gt, cur_a_mut_sos)
            assert np.allclose(cur_b_gt, cur_b_mut_sos, atol=1e-4)


@pytest.mark.parametrize('n', [9, 17])
@pytest.mark.parametrize('window', ['hann', 'rect'])
@pytest.mark.parametrize('angle', [None, np.pi/4, np.pi/6])
@pytest.mark.parametrize('slope', [1, 2, 0.5])
@pytest.mark.parametrize('zero_mean', [False, True])
def test_diagonal_filter(n, window, angle, slope, zero_mean):

    kernel = librosa.filters.diagonal_filter(window, n,
                                             slope=slope,
                                             angle=angle,
                                             zero_mean=zero_mean)

    # In the no-rotation case, check that the filter is shaped correctly
    if angle == np.pi / 4 and not zero_mean:
        win_unnorm = librosa.filters.get_window(window, n, fftbins=False)
        win_unnorm /= win_unnorm.sum()
        assert np.allclose(np.diag(kernel), win_unnorm)

    # First check: zero-mean
    if zero_mean:
        assert np.isclose(kernel.sum(), 0)
    else:
        assert np.isclose(kernel.sum(), 1) and np.all(kernel >= 0)

    # Now check if the angle transposes correctly
    if angle is None:
        # If we're using the slope API, then the transposed kernel
        # will have slope 1/slope
        k2 = librosa.filters.diagonal_filter(window, n,
                                             slope=1./slope,
                                             angle=angle,
                                             zero_mean=zero_mean)
    else:
        # If we're using the angle API, then the transposed kernel
        # will have angle pi/2 - angle
        k2 = librosa.filters.diagonal_filter(window, n,
                                             slope=slope,
                                             angle=np.pi/2 - angle,
                                             zero_mean=zero_mean)

    assert np.allclose(k2, kernel.T)
