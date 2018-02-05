#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Feature manipulation utilities"""

import numpy as np
import scipy.signal

from .. import cache
from ..util.exceptions import ParameterError
from ..util.deprecation import Deprecated
__all__ = ['delta', 'stack_memory']


@cache(level=40)
def delta(data, width=9, order=1, axis=-1, trim=Deprecated()):
    r'''Compute delta features: local estimate of the derivative
    of the input data along the selected axis.


    Parameters
    ----------
    data      : np.ndarray
        the input data matrix (eg, spectrogram)

    width     : int >= 3, odd [scalar]
        Number of frames over which to compute the delta feature

    order     : int > 0 [scalar]
        the order of the difference operator.
        1 for first derivative, 2 for second, etc.

    axis      : int [scalar]
        the axis along which to compute deltas.
        Default is -1 (columns).

    trim      : bool [DEPRECATED]
        This parameter is deprecated in 0.6.0 and will be removed
        in 0.7.0.

    Returns
    -------
    delta_data   : np.ndarray [shape=(d, t)]
        delta matrix of `data` at specified order

    Notes
    -----
    This function caches at level 40.

    Examples
    --------
    Compute MFCC deltas, delta-deltas

    >>> y, sr = librosa.load(librosa.util.example_audio_file())
    >>> mfcc = librosa.feature.mfcc(y=y, sr=sr)
    >>> mfcc_delta = librosa.feature.delta(mfcc)
    >>> mfcc_delta
    array([[ 29.278,  30.896, ...,  -0.   ,  -0.   ],
           [ 22.27 ,  25.54 , ...,   0.   ,   0.   ],
           ..., 
           [ -1.198,  -0.613, ...,   0.   ,   0.   ],
           [ -0.529,  -0.204, ...,   0.   ,   0.   ]])

    >>> mfcc_delta2 = librosa.feature.delta(mfcc, order=2)
    >>> mfcc_delta2
    array([[-0.992, -2.336, ..., -0.   , -0.   ],
           [-0.024, -0.986, ...,  0.   ,  0.   ],
           ..., 
           [ 0.258,  0.341, ...,  0.   ,  0.   ],
           [ 0.158,  0.198, ...,  0.   ,  0.   ]])

    >>> import matplotlib.pyplot as plt
    >>> plt.subplot(3, 1, 1)
    >>> librosa.display.specshow(mfcc)
    >>> plt.title('MFCC')
    >>> plt.colorbar()
    >>> plt.subplot(3, 1, 2)
    >>> librosa.display.specshow(mfcc_delta)
    >>> plt.title(r'MFCC-$\Delta$')
    >>> plt.colorbar()
    >>> plt.subplot(3, 1, 3)
    >>> librosa.display.specshow(mfcc_delta2, x_axis='time')
    >>> plt.title(r'MFCC-$\Delta^2$')
    >>> plt.colorbar()
    >>> plt.tight_layout()

    '''

    data = np.atleast_1d(data)

    if width < 3 or np.mod(width, 2) != 1:
        raise ParameterError('width must be an odd integer >= 3')

    if order <= 0 or not isinstance(order, int):
        raise ParameterError('order must be a positive integer')

    half_length = 1 + int(width // 2)
    window = np.arange(half_length - 1., -half_length, -1.)

    # Normalize the window so we're scale-invariant
    window /= np.sum(np.abs(window)**2)

    delta_x = data
    for _ in range(order):
        delta_x = scipy.ndimage.convolve1d(delta_x,
                                           window,
                                           axis=axis,
                                           mode='nearest')

    return delta_x


@cache(level=40)
def stack_memory(data, n_steps=2, delay=1, **kwargs):
    """Short-term history embedding: vertically concatenate a data
    vector or matrix with delayed copies of itself.

    Each column `data[:, i]` is mapped to::

        data[:, i] ->  [data[:, i],
                        data[:, i - delay],
                        ...
                        data[:, i - (n_steps-1)*delay]]

    For columns `i < (n_steps - 1) * delay` , the data will be padded.
    By default, the data is padded with zeros, but this behavior can be
    overridden by supplying additional keyword arguments which are passed
    to `np.pad()`.


    Parameters
    ----------
    data : np.ndarray [shape=(t,) or (d, t)]
        Input data matrix.  If `data` is a vector (`data.ndim == 1`),
        it will be interpreted as a row matrix and reshaped to `(1, t)`.

    n_steps : int > 0 [scalar]
        embedding dimension, the number of steps back in time to stack

    delay : int != 0 [scalar]
        the number of columns to step.

        Positive values embed from the past (previous columns).

        Negative values embed from the future (subsequent columns).

    kwargs : additional keyword arguments
      Additional arguments to pass to `np.pad`.

    Returns
    -------
    data_history : np.ndarray [shape=(m * d, t)]
        data augmented with lagged copies of itself,
        where `m == n_steps - 1`.

    Notes
    -----
    This function caches at level 40.


    Examples
    --------
    Keep two steps (current and previous)

    >>> data = np.arange(-3, 3)
    >>> librosa.feature.stack_memory(data)
    array([[-3, -2, -1,  0,  1,  2],
           [ 0, -3, -2, -1,  0,  1]])

    Or three steps

    >>> librosa.feature.stack_memory(data, n_steps=3)
    array([[-3, -2, -1,  0,  1,  2],
           [ 0, -3, -2, -1,  0,  1],
           [ 0,  0, -3, -2, -1,  0]])

    Use reflection padding instead of zero-padding

    >>> librosa.feature.stack_memory(data, n_steps=3, mode='reflect')
    array([[-3, -2, -1,  0,  1,  2],
           [-2, -3, -2, -1,  0,  1],
           [-1, -2, -3, -2, -1,  0]])

    Or pad with edge-values, and delay by 2

    >>> librosa.feature.stack_memory(data, n_steps=3, delay=2, mode='edge')
    array([[-3, -2, -1,  0,  1,  2],
           [-3, -3, -3, -2, -1,  0],
           [-3, -3, -3, -3, -3, -2]])

    Stack time-lagged beat-synchronous chroma edge padding

    >>> y, sr = librosa.load(librosa.util.example_audio_file())
    >>> chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    >>> tempo, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=512)
    >>> beats = librosa.util.fix_frames(beats, x_min=0, x_max=chroma.shape[1])
    >>> chroma_sync = librosa.util.sync(chroma, beats)
    >>> chroma_lag = librosa.feature.stack_memory(chroma_sync, n_steps=3,
    ...                                           mode='edge')

    Plot the result

    >>> import matplotlib.pyplot as plt
    >>> beat_times = librosa.frames_to_time(beats, sr=sr, hop_length=512)
    >>> librosa.display.specshow(chroma_lag, y_axis='chroma', x_axis='time',
    ...                          x_coords=beat_times)
    >>> plt.yticks([0, 12, 24], ['Lag=0', 'Lag=1', 'Lag=2'])
    >>> plt.title('Time-lagged chroma')
    >>> plt.colorbar()
    >>> plt.tight_layout()
    """

    if n_steps < 1:
        raise ParameterError('n_steps must be a positive integer')

    if delay == 0:
        raise ParameterError('delay must be a non-zero integer')

    data = np.atleast_2d(data)

    t = data.shape[1]
    kwargs.setdefault('mode', 'constant')

    if kwargs['mode'] == 'constant':
        kwargs.setdefault('constant_values', [0])

    # Pad the end with zeros, which will roll to the front below
    if delay > 0:
        padding = (int((n_steps - 1) * delay), 0)
    else:
        padding = (0, int((n_steps - 1) * -delay))

    data = np.pad(data, [(0, 0), padding], **kwargs)

    history = data

    for i in range(1, n_steps):
        history = np.vstack([np.roll(data, -i * delay, axis=1), history])

    # Trim to original width
    if delay > 0:
        history = history[:, :t]
    else:
        history = history[:, -t:]

    # Make contiguous
    return np.ascontiguousarray(history.T).T
