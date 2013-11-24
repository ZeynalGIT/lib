#!/usr/bin/env python
"""Display module for interacting with matplotlib"""

import numpy as np
import matplotlib.image as img
import matplotlib.pyplot as plt

import librosa.core

# TODO:   2013-11-24 11:15:36 by Brian McFeea <brm2132@columbia.edu>
# freq-ticks: factor out ytick logic from specshow

def time_ticks(locs, *args, **kwargs): 
    '''Plot time-formatted axis ticks.

    Example usage:

        time_ticks(beat_times, ...)

        time_ticks(locations, timestamps, ...)


    :parameters:
       - times : array of time stamps

       - n_ticks : int or None
         Show this number of ticks (evenly spaced).
         If none, all ticks are displayed.

       - axis : 'x' or 'y'
         Which axis should the ticks be plotted on?

       - fmt : None or {'ms', 's', 'm', 'h'}
         ms: milliseconds   (eg, 241ms)
         s: seconds         (eg, 1.43s)
         m: minutes         (eg, 1:02)
         h: hours           (eg, 1:02:03)
         
         If none, formatted is automatically selected by the 
         range of the times data.

       - **kwargs : additional keyword arguments
         See `matplotlib.pyplot.xticks` or `yticks` for details.

    :returns:
      - See `matplotlib.pyplot.xticks` or `yticks` for details.
    '''

    n_ticks = kwargs.pop('n_ticks', 5)
    axis    = kwargs.pop('axis', 'x')
    fmt     = kwargs.pop('fmt', None)

    if axis == 'x':
        ticker = plt.xticks
    elif axis == 'y':
        ticker = plt.yticks
    else:
        raise ValueError("axis must be either 'x' or 'y'.")

    if len(args) > 0:
        times = args[0]
    else:
        times = locs
        locs  = range(len(times))

    if n_ticks is not None:
        # Slice the locations and labels
        locs    = locs[::max(1, len(locs)/n_ticks)]
        times   = times[::max(1, len(times)/n_ticks)]

    # Format the labels by time
    formatters = {'ms': lambda t: '%dms' % (1e3 * t),
                  's':  lambda t: '%0.2fs' % t,
                  'm':  lambda t: '%d:%02d' % ( t / 60, np.mod(t, 60)),
                  'h':  lambda t: '%d:%02d:%02d' % (t / 3600, t / 60, np.mod(t, 60))}

    if fmt is None:
        if max(times) > 3600.0:
            fmt = 'h'
        elif max(times) > 60.0:
            fmt = 'm'
        elif max(times) > 1.0:
            fmt = 's'
        else:
            fmt = 'ms'

    elif fmt not in formatters:
        raise ValueError('Invalid format: %s' % fmt)

    times = map(formatters[fmt], times)

    return ticker(locs, times, **kwargs)

def specshow(data, sr=22050, hop_length=512, x_axis=None, y_axis=None, n_xticks=5, n_yticks=5, 
    fmin=None, fmax=None, **kwargs):
    """Display a spectrogram/chromagram/cqt/etc.

    Functions as a drop-in replacement for `~matplotlib.pyplot.imshow`, but with useful defaults.

    :parameters:
      - data : np.ndarray
          Matrix to display (eg, spectrogram)

      - sr : int > 0
          Sample rate. Used to determine time scale in x-axis

      - hop_length : int > 0
          Hop length. Also used to determine time scale in x-axis

      - x_axis : None or {'time', 'frames', 'off'}
          If None or 'off', no x axis is displayed.
          If 'time', markers are shown as milliseconds, seconds, minutes, or hours.
          (see ``time_ticks()`` for details)
          If 'frames', markers are shown as frame counts.

      - y_axis : None or {'linear', 'mel', 'cqt_hz', 'cqt_note', 'chroma', 'off'}
          If None or 'off', no y axis is displayed.
          If 'linear', frequency range is determined by the FFT window and sample rate.
          If 'log', the image is displayed on a vertical log scale.
          If 'mel', frequencies are determined by the mel scale.
          If 'cqt_hz', frequencies are determined by the fmin and fmax values.
          If 'cqt_note', pitches are determined by the fmin and fmax values.
          If 'chroma', pitches are determined by the chroma filters.

     - n_xticks : int > 0
          If x_axis is drawn, the number of ticks to show

     - n_yticks : int > 0
          If y_axis is drawn, the number of ticks to show

     - fmin, fmax : float > 0 or None
          Used for setting the Mel or constantq frequency scales

     - kwargs : dict
          Additional arguments passed through to ``matplotlib.pyplot.imshow``.

    :returns:
     - image : ``matplotlib.image.AxesImage``
          As returned from ``matplotlib.pyplot.imshow``.

    """

    kwargs['aspect']        = kwargs.get('aspect',          'auto')
    kwargs['origin']        = kwargs.get('origin',          'lower')
    kwargs['interpolation'] = kwargs.get('interpolation',   'nearest')

    # Determine the colormap automatically
    # If the data has both positive and negative values, use a diverging colormap.
    # Otherwise, use a sequential map.
    # PuOr and OrRd are chosen to optimize visibility for color-blind people.
    if (data < 0).any() and (data > 0).any():
        kwargs['cmap']          = kwargs.get('cmap',            'PuOr_r')
    else:
        kwargs['cmap']          = kwargs.get('cmap',            'OrRd')

    # NOTE:  2013-11-14 16:15:33 by Brian McFee <brm2132@columbia.edu>pitch 
    #  We draw the image twice here. This is a hack to get around NonUniformImage
    #  not properly setting hooks for color: drawing twice enables things like
    #  colorbar() to work properly.

    axes = plt.imshow(data, **kwargs)

    if y_axis is 'log':
        axes_phantom = plt.gca()

        # Non-uniform imshow doesn't like aspect
        del kwargs['aspect']
        im_phantom   = img.NonUniformImage(axes_phantom, **kwargs)

        y_log = (data.shape[0] - np.logspace( 0, np.log2( data.shape[0] ), data.shape[0], base=2.0))[::-1]
        y_inv = np.arange(len(y_log)+1)
        for i in range(len(y_log)-1):
            y_inv[y_log[i]:y_log[i+1]] = i

        im_phantom.set_data( np.arange(0, data.shape[1]), y_log, data)
        axes_phantom.images.append(im_phantom)
        axes_phantom.set_ylim(0, data.shape[0])
        axes_phantom.set_xlim(0, data.shape[1])

    # Set up the y ticks
    y_pos = np.asarray(np.linspace(0, data.shape[0], n_yticks), dtype=int)

    if y_axis is 'linear':
        y_val = np.asarray(np.linspace(0, 0.5 * sr,  data.shape[0] + 1), dtype=int)

        plt.yticks(y_pos, y_val[y_pos])
        plt.ylabel('Hz')
    
    elif y_axis is 'log':
    
        y_val = np.asarray(np.linspace(0, 0.5 * sr,  data.shape[0] + 1), dtype=int)
        plt.yticks(y_pos, y_val[y_inv[y_pos]])
    
        plt.ylabel('Hz')
    
    elif y_axis is 'cqt_hz':
        y_pos = np.arange(0, data.shape[0], 
                             np.ceil(data.shape[0] / float(n_yticks)), 
                             dtype=int)

        # Get frequencies
        y_val = librosa.core.cqt_frequencies(data.shape[0], 
                                             fmin=fmin, 
                                             bins_per_octave=int(data.shape[0] / np.ceil(np.log2(fmax) - 
                                                        np.log2(fmin))))
        plt.yticks(y_pos, y_val[y_pos].astype(int))
        plt.ylabel('Hz')

    elif y_axis is 'cqt_note':
        y_pos = np.arange(0, data.shape[0], 
                             np.ceil(data.shape[0] / float(n_yticks)), 
                             dtype=int)

        # Get frequencies
        y_val = librosa.core.cqt_frequencies(data.shape[0], 
                                             fmin=fmin, 
                                             bins_per_octave=int(data.shape[0] / np.ceil(np.log2(fmax) - 
                                                        np.log2(fmin))))
        y_val = librosa.core.midi_to_note(librosa.core.hz_to_midi(y_val[y_pos]))
        plt.yticks(y_pos, y_val)
        plt.ylabel('Note')

    elif y_axis is 'mel':
        m_args = {}
        if fmin is not None:
            m_args['fmin'] = fmin
        if fmax is not None:
            m_args['fmax'] = fmax

        y_val = librosa.core.mel_frequencies(data.shape[0], **m_args)[y_pos].astype(np.int)
        plt.yticks(y_pos, y_val)
        plt.ylabel('Hz')
    
    elif y_axis is 'chroma':
        y_pos = np.arange(0, data.shape[0], max(1, data.shape[0] / 12))
        # Labels start at 9 here because chroma starts at A.
        y_val = librosa.core.midi_to_note(range(9, 9+12), octave=False)
        plt.yticks(y_pos, y_val)
        plt.ylabel('Note')
    
    elif y_axis is None or y_axis is 'off':
        plt.yticks([])
        plt.ylabel('')

    else:
        raise ValueError('Unknown y_axis parameter: %s' % y_axis)

    # Set up the x ticks
    x_pos = np.asarray(np.linspace(0, data.shape[1], n_xticks), dtype=int)

    if x_axis is 'time':
        time_ticks( x_pos, 
                    librosa.core.frames_to_time(x_pos, sr=sr, hop_length=hop_length),
                    n_ticks=None, axis='x')

        plt.xlabel('Time')

    elif x_axis is 'frames':
        # Nothing to do here, plot is in frames
        plt.xticks(x_pos, x_pos)
        plt.xlabel('Frames')

    elif x_axis is None or x_axis is 'off':
        plt.xticks([])
        plt.xlabel('')

    else:
        raise ValueError('Unknown x_axis parameter: %s' % x_axis)
    
    return axes

