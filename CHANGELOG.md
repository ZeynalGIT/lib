Changes
=======

##v0.3.0

Bug fixes

    - Fixed numpy array indices to force integer values
    - ``librosa.util.frame`` now warns if the input data is non-contiguous
    - Fixed a formatting error in ``librosa.display.time_ticks()``
    - Added a warning if ``scikits.samplerate`` is not detected

Features

    - New module ``librosa.chord`` for training chord recognition models
    - Parabolic interpolation piptracking ``librosa.feature.piptrack()``
    - ``librosa.localmax()`` now supports multi-dimensional slicing
    - New example scripts
    - Improved documentation
    - Added the ``librosa.util.FeatureExtractor`` class, which allows librosa functions
      to act as feature extraction stages in `sklearn`
    - New module ``librosa.effects`` for time-domain audio processing
    - Added demo notebooks for the ``librosa.effects`` and ``librosa.util.FeatureExtractor``
    - Added a full-track audio example, ``librosa.util.example_audio_file()``
    - Added peak-frequency sorting of basis elements in ``librosa.decompose.decompose()``

Other changes

    - Spectrogram frames are now centered, rather than left-aligned.  This removes the
      need for window correction in ``librosa.frames_to_time()``
    - Accelerated constant-Q transform ``librosa.cqt()``
    - PEP8 compliance
    - Removed normalization from ``librosa.feature.logfsgram()``
    - Efficiency improvements by ensuring memory contiguity 
    - ``librosa.logamplitude()`` now supports functional reference power, in addition
      to scalar values
    - Improved ``librosa.feature.delta()``
    - Additional padding options to ``librosa.feature.stack_memory()``
    - ``librosa.cqt`` and ``librosa.feature.logfsgram`` now use the same parameter
      formats ``(fmin, n_bins, bins_per_octave)``.
    - Updated demo notebook(s) to IPython 2.0
    - Moved ``perceptual_weighting()`` from ``librosa.feature`` into ``librosa.core``
    - Moved ``stack_memory()`` from ``librosa.segment`` into ``librosa.feature``
    - Standardized ``librosa.output.annotation`` input format to match ``mir_eval``
    - Standardized variable names (e.g., ``onset_envelope``).

##v0.2.1

Bug fixes

  - fixed an off-by-one error in ``librosa.onset.onset_strength()``
  - fixed a sign-flip error in ``librosa.output.write_wav()``
  - removed all mutable object default parameters

Features

  - added option ``centering`` to ``librosa.onset.onset_strength()`` to resolve frame-centering issues with sliding window STFT
  - added frame-center correction to ``librosa.core.frames_to_time()`` and ``librosa.core.time_to_frames()``
  - added ``librosa.util.pad_center()``
  - added ``librosa.output.annotation()``
  - added ``librosa.output.times_csv()``
  - accelerated ``librosa.core.stft()`` and ``ifgram()``
  - added ``librosa.util.frame`` for in-place signal framing
  - ``librosa.beat.beat_track`` now supports user-supplied tempo
  - added ``librosa.util.normalize()``
  - added ``librosa.util.find_files()``
  - added ``librosa.util.axis_sort()``
  - new module: ``librosa.util()``
  - ``librosa.filters.constant_q`` now support padding
  - added boolean input support for ``librosa.display.cmap()``
  - speedup in ``librosa.core.cqt()``

Other changes

  - optimized default parameters for ``librosa.onset.onset_detect``
  - set ``librosa.filters.mel`` parameter ``n_mels=128`` by default
  - ``librosa.feature.chromagram()`` and ``logfsgram()`` now use power instead of energy
  - ``librosa.display.specshow()`` with ``y_axis='chroma'`` now labels as ``pitch class``
  - set ``librosa.core.cqt`` parameter ``resolution=2`` by default
  - set ``librosa.feature.chromagram`` parameter ``octwidth=2`` by default

## v0.2.0

Bug fixes

  - fixed default ``librosa.core.stft, istft, ifgram`` to match specification
  - fixed a float->int bug in peak_pick
  - better memory efficiency
  - ``librosa.segment.recurrence_matrix`` corrects for width suppression
  - fixed a divide-by-0 error in the beat tracker
  - fixed a bug in tempo estimation with short windows
  - ``librosa.feature.sync`` now supports 1d arrays
  - fixed a bug in beat trimming
  - fixed a bug in ``librosa.core.stft`` when calculating window size
  - fixed ``librosa.core.resample`` to support stereo signals

Features

  - added filters option to cqt
  - added window function support to istft
  - added an IPython notebook demo
  - added ``librosa.features.delta`` for computing temporal difference features
  - new ``examples`` scripts:  tuning, hpss
  - added optional trimming to ``librosa.segment.stack_memory``
  - ``librosa.onset.onset_strength`` now takes generic spectrogram function ``feature`` 
  - compute reference power directly in ``librosa.core.logamplitude``
  - color-blind-friendly default color maps in ``librosa.display.cmap``
  - ``librosa.core.onset_strength`` now accepts an aggregator
  - added ``librosa.feature.perceptual_weighting``
  - added tuning estimation to ``librosa.feature.chromagram``
  - added ``librosa.core.A_weighting``
  - vectorized frequency converters
  - added ``librosa.core.cqt_frequencies`` to get CQT frequencies
  - ``librosa.core.cqt`` basic constant-Q transform implementation
  - ``librosa.filters.cq_to_chroma`` to convert log-frequency to chroma
  - added ``librosa.core.fft_frequencies``
  - ``librosa.decompose.hpss`` can now return masking matrices
  - added reversal for ``librosa.segment.structure_feature``
  - added ``librosa.core.time_to_frames``
  - added cent notation to ``librosa.core.midi_to_note``
  - added time-series or spectrogram input options to ``chromagram``, ``logfsgram``, ``melspectrogram``, and ``mfcc``
  - new module: ``librosa.display``
  - ``librosa.output.segment_csv`` => ``librosa.output.frames_csv``
  - migrated frequency converters to ``librosa.core``
  - new module: ``librosa.filters``
  - ``librosa.decompose.hpss`` now supports complex-valued STFT matrices
  - ``librosa.decompose.decompose()`` supports ``sklearn`` decomposition objects
  - added ``librosa.core.phase_vocoder``
  - new module: ``librosa.onset``; migrated onset strength from ``librosa.beat``
  - added ``librosa.core.pick_peaks``
  - ``librosa.core.load()`` supports offset and duration parameters
  - ``librosa.core.magphase()`` to separate magnitude and phase from a complex matrix
  - new module: ``librosa.segment``

Other changes

  - ``onset_estimate_bpm => estimate_tempo``
  - removed ``n_fft`` from ``librosa.core.istft()``
  - ``librosa.core.mel_frequencies`` returns ``n_mels`` values by default
  - changed default ``librosa.decompose.hpss`` window to 31
  - disabled onset de-trending by default in ``librosa.onset.onset_strength``
  - added complex-value warning to ``librosa.display.specshow``
  - broke compatibilty with ``ifgram.m``; ``librosa.core.ifgram`` now matches ``stft``
  - changed default beat tracker settings
  - migrated ``hpss`` into ``librosa.decompose``
  - changed default ``librosa.decompose.hpss`` power parameter to ``2.0``
  - ``librosa.core.load()`` now returns single-precision by default
  - standardized ``n_fft=2048``, ``hop_length=512`` for most functions
  - refactored tempo estimator

## v0.1.0

Initial public release.
