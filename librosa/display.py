#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Display
=======
.. autosummary::
    :toctree: generated/

    specshow
    waveplot
    time_ticks
    cmap
"""

import warnings

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import Formatter, FixedFormatter, Locator

from . import cache
from . import core
from . import util
from .util.exceptions import ParameterError


class TimeFormatter(Formatter):
    '''A tick formatter for time axes.

    Automatically switches between ms, s, minutes:sec, etc.
    '''

    def __init__(self, lag=False):

        self.lag = lag

    def __call__(self, x, pos=None):
        '''Return the time format as pos'''

        _, dmax = self.axis.get_data_interval()
        vmin, vmax = self.axis.get_view_interval()

        # In lag-time axes, anything greater than dmax / 2 is negative time
        if self.lag and x >= dmax * 0.5:
            value = np.abs(x - dmax)
            # Do we need to tweak vmin/vmax here?
            sign = '-'
        else:
            value = x
            sign = ''

        if vmax - vmin > 3.6e3:
            s = '{:d}:{:02d}:{:02d}'.format(int(value / 3.6e3),
                                            int(np.mod(value / 6e1, 6e1)),
                                            int(np.mod(value, 6e1)))
        elif vmax - vmin > 6e1:
            s = '{:d}:{:02d}'.format(int(value / 6e1),
                                     int(np.mod(value, 6e1)))
        elif vmax - vmin > 1.0:
            s = '{:0.2f}s'.format(value)
        else:
            s = '{:g}ms'.format(1e3 * value)

        return '{:s}{:s}'.format(sign, s)


class TempoFormatter(Formatter):
    '''A formatter for tempo'''

    def __init__(self, sr=22050, hop_length=512):

        self.sr = sr
        self.hop_length = hop_length

    def __call__(self, x, pos=None):

        try:
            v = 60.0 * self.sr / (self.hop_length * x)
            return '{:g}'.format(v)

        except ZeroDivisionError:
            pass

        return ''


class NoteFormatter(Formatter):

    def __init__(self, octave=True):

        self.octave = octave

    def __call__(self, x, pos=None):

        if x < core.note_to_hz('C0'):
            return ''

        # Only use cent precision if our vspan is less than an octave
        vmin, vmax = self.axis.get_view_interval()
        cents = vmax < 2 * max(1, vmin)

        return core.hz_to_note(int(x), octave=self.octave, cents=cents)[0]


class ChromaFormatter(Formatter):
    '''A formatter for chroma'''
    def __call__(self, x, pos=None):

        return core.midi_to_note(int(x), octave=False, cents=False)


# A fixed formatter for tonnetz
TONNETZ_FORMATTER = FixedFormatter([r'5$_x$', r'5$_y$',
                                    r'm3$_x$', r'm3$_y$',
                                    r'M3$_x$', r'M3$_y$'])


def frequency_ticks(locs, *args, **kwargs):  # pylint: disable=star-args
    '''Plot frequency-formatted axis ticks.

    Parameters
    ----------
    locations : list or np.ndarray
        Frequency values for tick marks

    n_ticks : int > 0 or None
        Show this number of ticks (evenly spaced).

        If none, all ticks are displayed.

        Default: 5

    axis : 'x' or 'y'
        Which axis should the ticks be plotted on?
        Default: 'x'

    freq_fmt : None or {'mHz', 'Hz', 'kHz', 'MHz', 'GHz'}
        - 'mHz': millihertz
        - 'Hz': hertz
        - 'kHz': kilohertz
        - 'MHz': megahertz
        - 'GHz': gigahertz

        If none, formatted is automatically selected by the
        range of the frequency data.

        Default: None

    kwargs : additional keyword arguments.
        See `matplotlib.pyplot.xticks` or `yticks` for details.


    Returns
    -------
    (locs, labels)
        Locations and labels of tick marks

    label
        Axis label

    See Also
    --------
    matplotlib.pyplot.xticks
    matplotlib.pyplot.yticks


    Examples
    --------
    >>> # Tick at pre-computed beat times
    >>> librosa.display.specshow(S)
    >>> librosa.display.frequency_ticks()

    >>> # Set the locations of the time stamps
    >>> librosa.display.frequency_ticks(locations, frequencies)

    >>> # Format in hertz
    >>> librosa.display.frequency_ticks(frequencies, freq_fmt='Hz')

    >>> # Tick along the y axis
    >>> librosa.display.frequency_ticks(frequencies, axis='y')

    '''

    n_ticks = kwargs.pop('n_ticks', 5)
    axis = kwargs.pop('axis', 'x')
    freq_fmt = kwargs.pop('freq_fmt', None)

    if axis == 'x':
        ticker = plt.xticks
    elif axis == 'y':
        ticker = plt.yticks
    else:
        raise ParameterError("axis must be either 'x' or 'y'.")

    if len(args) > 0:
        freqs = args[0]
    else:
        freqs = locs
        locs = np.arange(len(freqs))

    if n_ticks is not None:
        # Slice the locations and labels evenly between 0 and the last point
        positions = np.linspace(0, len(locs)-1, n_ticks,
                                endpoint=True).astype(int)
        locs = locs[positions]
        freqs = freqs[positions]

    # Format the labels by time
    formats = {'mHz': lambda f: '{:.5g}'.format(f * 1e3),
               'Hz': '{:.5g}'.format,
               'kHz': lambda f: '{:.5g}'.format(f * 1e-3),
               'MHz': lambda f: '{:.5g}'.format(f * 1e-6),
               'GHz': lambda f: '{:.5g}'.format(f * 1e-9)}

    f_max = np.max(freqs)

    if freq_fmt is None:
        if f_max > 1e10:
            freq_fmt = 'GHz'
        elif f_max > 1e7:
            freq_fmt = 'MHz'
        elif f_max > 1e4:
            freq_fmt = 'kHz'
        elif f_max > 1e1:
            freq_fmt = 'Hz'
        else:
            freq_fmt = 'mHz'

    elif freq_fmt not in formats:
        raise ParameterError('Invalid format: {:s}'.format(freq_fmt))

    ticks = [formats[freq_fmt](f) for f in freqs]

    return ticker(locs, ticks, **kwargs), freq_fmt


@cache
def cmap(data, robust=True, cmap_seq='magma', cmap_bool='gray_r', cmap_div='coolwarm'):
    '''Get a default colormap from the given data.

    If the data is boolean, use a black and white colormap.

    If the data has both positive and negative values,
    use a diverging colormap.

    Otherwise, use a sequential colormap.

    Parameters
    ----------
    data : np.ndarray
        Input data

    robust : bool
        If True, discard the top and bottom 2% of data when calculating
        range.

    cmap_seq : str
        The sequential colormap name

    cmap_bool : str
        The boolean colormap name

    cmap_div : str
        The diverging colormap name

    Returns
    -------
    cmap : matplotlib.colors.Colormap
        The colormap to use for `data`

    See Also
    --------
    matplotlib.pyplot.colormaps
    '''

    data = np.atleast_1d(data)

    if data.dtype == 'bool':
        return plt.get_cmap(cmap_bool)

    data = data[np.isfinite(data)]

    if robust:
        min_p, max_p = 2, 98
    else:
        min_p, max_p = 0, 100

    max_val = np.percentile(data, max_p)
    min_val = np.percentile(data, min_p)

    if min_val >= 0 or max_val <= 0:
        return plt.get_cmap(cmap_seq)

    return plt.get_cmap(cmap_div)


def __envelope(x, hop):
    '''Compute the max-envelope of x at a stride/frame length of h'''
    return util.frame(x, hop_length=hop, frame_length=hop).max(axis=0)


def waveplot(y, sr=22050, max_points=5e4, x_axis='time', offset=0.0, max_sr=1000,
             time_fmt=None, **kwargs):
    '''Plot the amplitude envelope of a waveform.

    If `y` is monophonic, a filled curve is drawn between `[-abs(y), abs(y)]`.

    If `y` is stereo, the curve is drawn between `[-abs(y[1]), abs(y[0])]`,
    so that the left and right channels are drawn above and below the axis,
    respectively.

    Long signals (`duration >= max_points`) are down-sampled to at
    most `max_sr` before plotting.

    Parameters
    ----------
    y : np.ndarray [shape=(n,) or (2,n)]
        audio time series (mono or stereo)

    sr : number > 0 [scalar]
        sampling rate of `y`

    max_points : postive number or None
        Maximum number of time-points to plot: if `max_points` exceeds
        the duration of `y`, then `y` is downsampled.

        If `None`, no downsampling is performed.

    x_axis : str {'time', 'off', 'none'} or None
        If 'time', the x-axis is given time tick-marks.

        See also: `time_ticks`

    offset : float
        Horizontal offset (in time) to start the waveform plot

    max_sr : number > 0 [scalar]
        Maximum sampling rate for the visualization

    time_fmt : None or str
        Formatting for time axis.  None (automatic) by default.

        See `time_ticks`.

    kwargs
        Additional keyword arguments to `matplotlib.pyplot.fill_between`

    Returns
    -------
    pc : matplotlib.collections.PolyCollection
        The PolyCollection created by `fill_between`.

    See also
    --------
    time_ticks
    librosa.core.resample
    matplotlib.pyplot.fill_between


    Examples
    --------
    Plot a monophonic waveform

    >>> import matplotlib.pyplot as plt
    >>> y, sr = librosa.load(librosa.util.example_audio_file(), duration=10)
    >>> plt.figure()
    >>> plt.subplot(3, 1, 1)
    >>> librosa.display.waveplot(y, sr=sr)
    >>> plt.title('Monophonic')

    Or a stereo waveform

    >>> y, sr = librosa.load(librosa.util.example_audio_file(),
    ...                      mono=False, duration=10)
    >>> plt.subplot(3, 1, 2)
    >>> librosa.display.waveplot(y, sr=sr)
    >>> plt.title('Stereo')

    Or harmonic and percussive components with transparency

    >>> y, sr = librosa.load(librosa.util.example_audio_file(), duration=10)
    >>> y_harm, y_perc = librosa.effects.hpss(y)
    >>> plt.subplot(3, 1, 3)
    >>> librosa.display.waveplot(y_harm, sr=sr, alpha=0.25)
    >>> librosa.display.waveplot(y_perc, sr=sr, color='r', alpha=0.5)
    >>> plt.title('Harmonic + Percussive')
    >>> plt.tight_layout()
    '''

    util.valid_audio(y, mono=False)

    if not (isinstance(max_sr, int) and max_sr > 0):
        raise ParameterError('max_sr must be a non-negative integer')

    target_sr = sr

    if max_points is not None:
        if max_points <= 0:
            raise ParameterError('max_points must be strictly positive')

        if max_points < y.shape[-1]:
            target_sr = min(max_sr, (sr * y.shape[-1]) // max_points)

        hop_length = sr // target_sr

        if y.ndim == 1:
            y = __envelope(y, hop_length)
        else:
            y = np.vstack([__envelope(_, hop_length) for _ in y])

    if y.ndim > 1:
        y_top = y[0]
        y_bottom = -y[1]
    else:
        y_top = y
        y_bottom = -y

    axes = plt.gca()

    kwargs.setdefault('color', next(axes._get_lines.prop_cycler)['color'])

    sample_off = core.time_to_samples(offset, sr=target_sr)

    locs = np.arange(sample_off, sample_off + len(y_top))
    out = axes.fill_between(locs, y_bottom, y_top, **kwargs)

    plt.xlim([locs[0], locs[-1]])

    if x_axis == 'time':
        time_ticks(locs, core.samples_to_time(locs, sr=target_sr), time_fmt=time_fmt)
    elif x_axis is None or x_axis in ['off', 'none']:
        plt.xticks([])
    else:
        raise ParameterError('Unknown x_axis value: {}'.format(x_axis))

    return out


def specshow(data, x_coords=None, y_coords=None,
             x_axis=None, y_axis=None,
             sr=22050, hop_length=512,
             fmin=None, fmax=None,
             bins_per_octave=12,
             tmin=16, tmax=240,
             **kwargs):
    '''Display a spectrogram/chromagram/cqt/etc.

    Functions as a drop-in replacement for `matplotlib.pyplot.imshow`,
    but with useful defaults.


    Parameters
    ----------
    data : np.ndarray [shape=(d, n)]
        Matrix to display (e.g., spectrogram)

    sr : number > 0 [scalar]
        Sample rate used to determine time scale in x-axis.

    hop_length : int > 0 [scalar]
        Hop length, also used to determine time scale in x-axis

    x_axis : None or str

    y_axis : None or str
        Range for the x- and y-axes.

        Valid types are:

        - None or 'off' : no axis is displayed.

        Frequency types:

        - 'linear' : frequency range is determined by the FFT window
          and sampling rate.
        - 'log' : the image is displayed on a vertical log scale.
        - 'mel' : frequencies are determined by the mel scale.
        - 'cqt_hz' : frequencies are determined by the CQT scale.
        - 'cqt_note' : pitches are determined by the CQT scale.
        - 'chroma' : pitches are determined by the chroma filters.
        - 'tonnetz' : axes are labeled by Tonnetz dimensions

        Time types:

        - 'time' : markers are shown as milliseconds, seconds,
          minutes, or hours
        - 'lag' : like time, but past the half-way point counts
          as negative values.
        - 'frames' : markers are shown as frame counts.
        - 'tempo' : markers are shown as beats-per-minute

    fmin : float > 0 [scalar] or None
        Frequency of the lowest spectrogram bin.  Used for Mel and CQT
        scales.

        If `y_axis` is `cqt_hz` or `cqt_note` and `fmin` is not given,
        it is set by default to `note_to_hz('C1')`.

    fmax : float > 0 [scalar] or None
        Used for setting the Mel frequency scales

    bins_per_octave : int > 0 [scalar]
        Number of bins per octave.  Used for CQT frequency scale.

    tmin : float > 0 [scalar]
    tmax : float > 0 [scalar]
        Minimum and maximum tempi displayed when `_axis='tempo'`,
        as measured in beats per minute.

    kwargs : additional keyword arguments
        Arguments passed through to `matplotlib.pyplot.imshow`.


    Returns
    -------
    image : `matplotlib.image.AxesImage`
        As returned from `matplotlib.pyplot.imshow`.


    See Also
    --------
    cmap : Automatic colormap detection

    matplotlib.pyplot.pcolormesh


    Examples
    --------
    Visualize an STFT power spectrum

    >>> import matplotlib.pyplot as plt
    >>> y, sr = librosa.load(librosa.util.example_audio_file())
    >>> plt.figure(figsize=(12, 8))

    >>> D = librosa.logamplitude(np.abs(librosa.stft(y))**2, ref_power=np.max)
    >>> plt.subplot(4, 2, 1)
    >>> librosa.display.specshow(D, y_axis='linear')
    >>> plt.colorbar(format='%+2.0f dB')
    >>> plt.title('Linear-frequency power spectrogram')


    Or on a logarithmic scale

    >>> plt.subplot(4, 2, 2)
    >>> librosa.display.specshow(D, y_axis='log')
    >>> plt.colorbar(format='%+2.0f dB')
    >>> plt.title('Log-frequency power spectrogram')


    Or use a CQT scale

    >>> CQT = librosa.logamplitude(librosa.cqt(y, sr=sr)**2, ref_power=np.max)
    >>> plt.subplot(4, 2, 3)
    >>> librosa.display.specshow(CQT, y_axis='cqt_note')
    >>> plt.colorbar(format='%+2.0f dB')
    >>> plt.title('Constant-Q power spectrogram (note)')

    >>> plt.subplot(4, 2, 4)
    >>> librosa.display.specshow(CQT, y_axis='cqt_hz')
    >>> plt.colorbar(format='%+2.0f dB')
    >>> plt.title('Constant-Q power spectrogram (Hz)')


    Draw a chromagram with pitch classes

    >>> C = librosa.feature.chroma_cqt(y=y, sr=sr)
    >>> plt.subplot(4, 2, 5)
    >>> librosa.display.specshow(C, y_axis='chroma')
    >>> plt.colorbar()
    >>> plt.title('Chromagram')


    Force a grayscale colormap (white -> black)

    >>> plt.subplot(4, 2, 6)
    >>> librosa.display.specshow(D, cmap='gray_r', y_axis='linear')
    >>> plt.colorbar(format='%+2.0f dB')
    >>> plt.title('Linear power spectrogram (grayscale)')


    Draw time markers automatically

    >>> plt.subplot(4, 2, 7)
    >>> librosa.display.specshow(D, x_axis='time', y_axis='log')
    >>> plt.colorbar(format='%+2.0f dB')
    >>> plt.title('Log power spectrogram')


    Draw a tempogram with BPM markers

    >>> plt.subplot(4, 2, 8)
    >>> oenv = librosa.onset.onset_strength(y=y, sr=sr)
    >>> tempo = librosa.beat.estimate_tempo(oenv, sr=sr)
    >>> Tgram = librosa.feature.tempogram(y=y, sr=sr)
    >>> librosa.display.specshow(Tgram[:100], x_axis='time', y_axis='tempo',
    ...                          tmin=tempo/4, tmax=tempo*2, n_yticks=4)
    >>> plt.colorbar()
    >>> plt.title('Tempogram')
    >>> plt.tight_layout()


    '''

    kwargs.setdefault('shading', 'flat')

    if np.issubdtype(data.dtype, np.complex):
        warnings.warn('Trying to display complex-valued input. '
                      'Showing magnitude instead.')
        data = np.abs(data)

    kwargs.setdefault('cmap', cmap(data))

    all_params = dict(kwargs=kwargs,
                      sr=sr,
                      fmin=fmin,
                      fmax=fmax,
                      bins_per_octave=bins_per_octave,
                      tmin=tmin,
                      tmax=tmax,
                      hop_length=hop_length)

    # Get the x and y coordinates
    y_coords = __mesh_coords(y_axis, y_coords, data.shape[0], **all_params)
    x_coords = __mesh_coords(x_axis, x_coords, data.shape[1], **all_params)

    ax = plt.gca()
    ax.pcolormesh(x_coords, y_coords, data, **kwargs)

    # Set up axis scaling
    __scale_axes(ax, x_axis, 'x')
    __scale_axes(ax, y_axis, 'y')

    # Construct tickers
    #TODO

    return ax


def __mesh_coords(ax_type, coords, n, **kwargs):
    '''Compute axis coordinates'''

    if coords is not None:
        if len(coords) != n:
            raise ParameterError('Coordinate shape mismatch: '
                                 '{}!={}'.format(len(coords), n))
        return coords

    coord_map = {'linear': __coord_fft_hz,
                 'hz': __coord_fft_hz,
                 'log': __coord_fft_hz,
                 'mel': __coord_mel_hz,
                 'cqt': __coord_cqt_hz,
                 'chroma': __coord_chroma,
                 'time': __coord_time,
                 'lag': __coord_time,
                 'tonnetz': __coord_n,
                 'off': __coord_n,
                 'tempo': __coord_n,
                 'frames': __coord_n,
                 None: __coord_n}

    if ax_type not in coord_map:
        raise ParameterError('Unknown axis type: {}'.format(ax_type))

    return coord_map[ax_type](n, **kwargs)


def __scale_axes(axes, ax_type, which):
    '''Set the axis scaling'''

    kwargs = dict()
    if which == 'x':
        thresh = 'linthreshx'
        base = 'basex'
        scale = 'linscalex'
        scaler = axes.set_xscale
    else:
        thresh = 'linthreshy'
        base = 'basey'
        scale = 'linscaley'
        scaler = axes.set_yscale

    if ax_type == 'mel':
        mode = 'symlog'
        kwargs[thresh] = 1000.0
        kwargs[base] = 2

    elif ax_type == 'log':
        mode = 'symlog'
        kwargs[base] = 2
        kwargs[thresh] = core.note_to_hz('C2')
        kwargs[scale] = 0.5

    elif ax_type == 'cqt':
        mode = 'log'
        kwargs[base] = 2
    else:
        return

    scaler(mode, **kwargs)


def __coord_fft_hz(n, sr=22050, **_kwargs):
    '''Get the frequencies for FFT bins'''
    n_fft = 2 * (n - 1)

    return core.fft_frequencies(sr=sr, n_fft=n_fft)


def __coord_mel_hz(n, fmin=0, fmax=11025.0, **_kwargs):
    '''Get the frequencies for Mel bins'''

    return core.mel_frequencies(n, fmin=fmin, fmax=fmax)


def __coord_cqt_hz(n, fmin=None, bins_per_octave=12, **_kwargs):
    '''Get CQT bin frequencies'''

    return core.cqt_frequencies(n, fmin=fmin, bins_per_octave=bins_per_octave)


def __coord_chroma(n, bins_per_octave=12, **_kwargs):
    '''Get chroma bin numbers'''

    return np.linspace(0, (12.0 * n) / bins_per_octave, num=n)


def __coord_n(n, **_kwargs):
    '''Get bare positions'''
    return np.arange(n)


def __coord_time(n, sr=22050, hop_length=512, **_kwargs):
    '''Get time coordinates from frames'''
    return core.frames_to_time(np.arange(n), sr=sr, hop_length=hop_length)
