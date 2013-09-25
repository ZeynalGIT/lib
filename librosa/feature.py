#!/usr/bin/env python
"""Feature extraction routines."""

import numpy as np

import librosa.core

#-- Frequency conversions --#
def midi_to_hz( notes ):
    """Get the frequency (Hz) of MIDI note(s)

    :parameters:
      - note_num      : int, np.ndarray
          number of the note(s)

    :returns:
      - frequency     : float, np.ndarray
          frequency of the note in Hz
    """

    return 440.0 * (2.0 ** ((notes - 69)/12.0))

def hz_to_midi( frequency ):
    """Get the closest MIDI note number(s) for given frequencies

    :parameters:
      - frequencies   : float, np.ndarray
          target frequencies

    :returns:
      - note_nums     : int, np.ndarray
          closest MIDI notes

    """

    return 12 * (np.log2(frequency) - np.log2(440.0)) + 69

def hz_to_mel(frequencies, htk=False):
    """Convert Hz to Mels

    :parameters:
      - frequencies   : np.ndarray, float
          scalar or array of frequencies
      - htk           : boolean
          use HTK formula instead of Slaney

    :returns:
      - mels        : np.ndarray
          input frequencies in Mels

    """

    if np.isscalar(frequencies):
        frequencies = np.array([frequencies], dtype=float)
    else:
        frequencies = frequencies.astype(float)

    if htk:
        return 2595.0 * np.log10(1.0 + frequencies / 700.0)
    
    # Fill in the linear part
    f_min   = 0.0
    f_sp    = 200.0 / 3

    mels    = (frequencies - f_min) / f_sp

    # Fill in the log-scale part
    
    min_log_hz  = 1000.0                        # beginning of log region (Hz)
    min_log_mel = (min_log_hz - f_min) / f_sp   # same (Mels)
    logstep     = np.log(6.4) / 27.0            # step size for log region

    log_t       = (frequencies >= min_log_hz)
    mels[log_t] = min_log_mel + np.log(frequencies[log_t]/min_log_hz) / logstep

    return mels

def mel_to_hz(mels, htk=False):
    """Convert mel bin numbers to frequencies

    :parameters:
      - mels          : np.ndarray, float
          mel bins to convert
      - htk           : boolean
          use HTK formula instead of Slaney

    :returns:
      - frequencies   : np.ndarray
          input mels in Hz

    """

    if np.isscalar(mels):
        mels = np.array([mels], dtype=float)
    else:
        mels = mels.astype(float)

    if htk:
        return 700.0 * (10.0**(mels / 2595.0) - 1.0)

    # Fill in the linear scale
    f_min       = 0.0
    f_sp        = 200.0 / 3
    freqs       = f_min + f_sp * mels

    # And now the nonlinear scale
    min_log_hz  = 1000.0                        # beginning of log region (Hz)
    min_log_mel = (min_log_hz - f_min) / f_sp   # same (Mels)
    logstep     = np.log(6.4) / 27.0            # step size for log region
    log_t       = (mels >= min_log_mel)

    freqs[log_t] = min_log_hz * np.exp(logstep * (mels[log_t] - min_log_mel))

    return freqs

def hz_to_octs(frequencies, A440=440.0):
    """Convert frquencies (Hz) to octave numbers

    :parameters:
      - frequencies   : np.ndarray, float
          scalar or vector of frequencies
      - A440          : float
          frequency of A440

    :returns:
      - octaves       : np.ndarray
          octave number for each frequency

    """
    return np.log2(frequencies / (A440 / 16.0))

def octs_to_hz(octs, A440=440.0):
    """Convert octaves numbers to frequencies

    :parameters:
      - octaves       : np.ndarray
          octave number for each frequency
      - A440          : float
          frequency of A440

    :returns:
      - frequencies   : np.ndarray, float
          scalar or vector of frequencies

    """
    return (A440/16)*(2**octs)

#-- Chroma --#
def chromagram(S, sr, method='Ellis', norm='inf', beat_times=None, tuning=0.0, **kwargs):
    """Compute a chromagram from a spectrogram or waveform

    :parameters:
      - S          : np.ndarray
          spectrogram if method='Ellis' 
      OR    
      - S          : np.array
          waveform (1-D) if method='McVicar'   
      - sr         : int
          audio sampling rate of S
      - method     : {'Ellis', 'McVicar'}
          method for computing chromagram. 
          Ellis: http://labrosa.ee.columbia.edu/matlab/chroma-ansyn/
          McVicar: https://patterns.enm.bris.ac.uk/hpa-software-package
      - norm       : {'inf', 1, 2, None}, Ellis Only
          column-wise normalization:

             'inf' :  max norm

             1 :  l_1 norm 
             
             2 :  l_2 norm
             
             None :  do not normalize
     - beat_times : np.ndarray, McVicar only
          estimated beat times (seconds)
     - tuning     : float in [-0.5,0.5], McVicar Only
          estimated tuning in cents             

      - kwargs
          Parameters to build the chroma filterbank and spectrogram
          See chromafb() or stft for details, Ellis Only

    :returns:
      - chromagram  : np.ndarray
          Normalized energy for each chroma bin at each frame.

    :raises:
      - ValueError 
          if an improper value is supplied for norm

    """
    
    # Main rouine switch
    if method == 'Ellis':
                
      n_fft       = (S.shape[0] -1 ) * 2
      spec2chroma = chromafb( sr, n_fft, **kwargs)[:, :S.shape[0]]

      # Compute raw chroma
      raw_chroma  = np.dot(spec2chroma, S)

      # Compute normalization factor for each frame
      if norm == 'inf':
          chroma_norm = np.max(np.abs(raw_chroma), axis=0)
      elif norm == 1:
          chroma_norm = np.sum(np.abs(raw_chroma), axis=0)
      elif norm == 2:
          chroma_norm = np.sum( (raw_chroma**2), axis=0) ** 0.5
      elif norm is None:
          return raw_chroma
      else:
          raise ValueError("norm must be one of: 'inf', 1, 2, None")

      # Tile the normalizer to match raw_chroma's shape
      chroma_norm[chroma_norm == 0] = 1.0
      normal_chroma = raw_chroma / chroma_norm
    else:
    
      # Extract loudness-based chroma
      raw_chroma, normal_chroma, sample_times, tuning = loudness_chroma(S, sr, beat_times, tuning, 
           minFreq=55, maxFreq=1660, resolution_fact=5)
           
    return normal_chroma

def chromafb(sr, n_fft, n_chroma=12, A440=440.0, ctroct=5.0, octwidth=None):
    """Create a Filterbank matrix to convert STFT to chroma

    :parameters:
      - sr        : int
          sampling rate
      - n_fft     : int
          number of FFT components
      - n_chroma  : int
          number of chroma dimensions   
      - A440      : float
          Reference frequency for A
      - ctroct    : float
      - octwidth  : float
          These parameters specify a dominance window - Gaussian
          weighting centered on ctroct (in octs, re A0 = 27.5Hz) and
          with a gaussian half-width of octwidth.  
          Defaults to halfwidth = inf, i.e. flat.

    :returns:
      wts       : ndarray, shape=(n_chroma, n_fft) 
          Chroma filter matrix

    """

    wts         = np.zeros((n_chroma, n_fft))

    fft_res     = float(sr) / n_fft

    frequencies = np.arange(fft_res, sr, fft_res)

    fftfrqbins  = n_chroma * hz_to_octs(frequencies, A440)

    # make up a value for the 0 Hz bin = 1.5 octaves below bin 1
    # (so chroma is 50% rotated from bin 1, and bin width is broad)
    fftfrqbins = np.concatenate( (   [fftfrqbins[0] - 1.5 * n_chroma],
                                        fftfrqbins))

    binwidthbins = np.concatenate(
        (np.maximum(fftfrqbins[1:] - fftfrqbins[:-1], 1.0), [1]))

    D = np.tile(fftfrqbins, (n_chroma, 1))  \
        - np.tile(np.arange(0, n_chroma, dtype='d')[:,np.newaxis], 
        (1,n_fft))

    n_chroma2 = round(n_chroma / 2.0)

    # Project into range -n_chroma/2 .. n_chroma/2
    # add on fixed offset of 10*n_chroma to ensure all values passed to
    # rem are +ve
    D = np.remainder(D + n_chroma2 + 10*n_chroma, n_chroma) - n_chroma2

    # Gaussian bumps - 2*D to make them narrower
    wts = np.exp(-0.5 * (2*D / np.tile(binwidthbins, (n_chroma, 1)))**2)

    # normalize each column
    wts /= np.tile(np.sqrt(np.sum(wts**2, 0)), (n_chroma, 1))

    # Maybe apply scaling for fft bins
    if octwidth is not None:
        wts *= np.tile(
            np.exp(-0.5 * (((fftfrqbins/n_chroma - ctroct)/octwidth)**2)),
            (n_chroma, 1))

    # remove aliasing columns
    wts[:, (1 + n_fft/2):] = 0.0
    return wts

def loudness_chroma(x, sr, beat_times, tuning, minFreq=55.0, maxFreq=1661.0, resolution_fact=5):

    """Compute a loudness-based chromagram, for use in chord estimation 

    :parameters:
      - x : np.ndarray
           audio time-series
      - sr : int
        audio sampling rate of x
      - beat_times: np.ndarray
        estimated beat locations (in seconds). 
      - tuning: float in [-0.5,0.5]
        estimated tuning in cents. 
      - minFreq: float
          minimum frequency of spectrum to consider. Will be rounded to
          Closest pitch frequency in Hz (accounting for tuning)
        maxFreq: float
          maximum frequency of spectrum to consider. For balanced results,
          make this one pitch less than an octave multiple of minFreq
          (for example, default value is 4 octaves + 11 pitches above minFreq = 55)
      - resolution_fact: int
          multiplying factor of power in window (see PhD thesis "A Machine Learning approach
          to automatic chord extraction", Matt McVicar, University of Bristol 2013)

    :returns:
      - raw_chroma : np.ndarray 12 x T
        Loudness-based chromagram, 12 pitches by number of beats + 1
      - normal_chroma: np.ndarray 12 x T
        Normalised chromagram, each row normalised to range [0,1]
      - sample_times: np.ndarray
        start and end points of chroma windows (in seconds)
      - tuning: float in [-0.5,0.5]
        estimated tuning of piece, returned in case None was supplied
                  
      """
      
    # Get hamming windows for convolution
    [hamming_k, half_winLenK, freqBins] = cal_hamming_window(sr,
                   minFreq, maxFreq, resolution_fact,tuning)
      
    # Extract chroma
    raw_chroma, normal_chroma, sample_times = cal_CQ_chroma_loudness(x, 
                   sr, beat_times, hamming_k, half_winLenK, freqBins)

    return raw_chroma, normal_chroma, sample_times, tuning   

def cal_hamming_window(SR, minFreq=55.0, maxFreq=1661.0, resolution_fact=5.0,tuning=0.0):

    """Compute hamming windows for use in loudness chroma

    :parameters:
      - SR : int
           audio sample rate of x
      - beat_times: np.ndarray
        estimated beat locations (in seconds). 
      - minFreq: int
          minimum frequency of spectrum to consider. Will be rounded to
          Closest pitch frequency in Hz (accounting for tuning)
        maxFreq: int
          maximum frequency of spectrum to consider. For balanced results,
          make this one pitch less than an octave multiple of minFreq
          (for example, default value is 4 octaves + 11 pitches above minFreq = 55)
      - resolution_fact: int
          multiplying factor of power in window (see PhD thesis "A Machine Learning approach
          to automatic chord extraction", Matt McVicar, University of Bristol 2013)
      - tuning: float in [-0.5,0.5]
        estimated tuning in cents. 

    :returns:
      - hamming_k: complex array
        hamming windows for each of the k frequencies
      - half_winLenK:
        half of the above
      - freqBins: np.array
        frequency of each window
                  
      """

    # 1. Configuration
    bins=12
    pitchClass=12
    pitchInterval = int(np.true_divide(bins,pitchClass))
    pitchIntervalMap = np.zeros(bins)

    # Map each frequency to a pitch class 
    for i in range(pitchClass):
      pitchIntervalMap[(i-1)*pitchInterval+1:i*pitchInterval+1] = int(i+1)
   
    # 2. Frequency bins
    K = int(np.ceil(np.log2(maxFreq/minFreq))*bins) #The number of bins
    freqBins = np.zeros(K)

    for i in range(0,K-pitchInterval+1,pitchInterval):
      octaveIndex = np.floor(np.true_divide(i,bins))
      binIndex = np.mod(i,bins)
      val = minFreq*2.0**(octaveIndex+(pitchIntervalMap[binIndex]-1.0)/pitchClass)
      freqBins[i:i+pitchInterval+1] = val 

    # Augment using tuning factor
    freqBins = freqBins*2.0**(tuning/bins)

    # 3. Constant Q factor and window size
    Q = 1.0/(2.0**(1.0/bins)-1)*resolution_fact
    winLenK = np.ceil(SR*np.true_divide(Q,freqBins))

    # 4. Construct the hamming window
    half_winLenK = winLenK
    const = 1j*-2.0*np.pi*Q
    expFactor = np.multiply(const,range(int(winLenK[0])+1))
    expFactor = np.conj(expFactor)
    hamming_k = list()
    for k in range(K):
      N = int(winLenK[k])
      half_winLenK[k] = int(np.ceil(N/2.0))
      hamming_k.append(np.hamming(N)* np.true_divide(np.exp(np.true_divide(expFactor[range(N)],N)),N))

    return hamming_k, half_winLenK, freqBins

def cal_CQ_chroma_loudness(x,SR, beat_times, hammingK, half_winLenK, freqK, refLabel='s', A_weightLabel=1,q_value=0):

    """Compute a loudness-based chromagram

    :parameters:
      - x : np.ndarray
           audio time-series
      - SR : int
        audio sampling rate of x
      - beat_times: np.ndarray
        estimated beat locations (in seconds). 
      - hammingK: complex array
        hamming window to use in convolution, generated by cal_hamming_window
      - half_winLenK: complex array
        half the length of the above windows, generated by cal_hamming_window
      - freqK: np.ndarray
        Frequency of the kth window
      - refLabel: {'n','s','mean','median','q'}
        reference power level.
        'n'       - no reference, i.e. 1
        's'       - standard human reference power of 10**-12
        'mean'    - reference of each frequency is the mean of this
                    frequency over the song
        'median'  - as above with median
        'q'       - regard the qth quantile of the signal to be silence
                    (see q_value argument)
      - q_value: float in [0.0,1.0]
        quantile to consider silence if refLabel = 'q'

    :returns:
      - raw_chroma : np.ndarray 12 x T
        Loudness-based chromagram, 12 pitches by number of beats + 1
      - normal_chroma: np.ndarray 12 x T
        Normalised chromagram, each row normalised to range [0,1]
      - sample_times: np.ndarray
        start and end points of chroma windows (in seconds)
      - tuning: float in [-0.5,0.5]
        estimated tuning of piece, returned in case None was supplied
                  
      """
 
    # 1. configuration. Pad x to be a power of 2, get length parameters
    bins = 12
    Nxorig = len(x)
    x = np.hstack([x,np.zeros(2.0**np.ceil(np.log2(Nxorig))-Nxorig)]) # add the end to make the length to be 2^N 
    Nx = len(x)                                                       # length of x
    K = len(hammingK)                                                 # number of frequency bins
    xf = np.fft.fft(x)                                                # full fft of signal

    # check whether hamming window length is > length(xf) and issue a warning
    warningFlag = np.zeros(K)
    for k in range(K):
      if (len(hammingK[k])>Nx):
        print('Warning: signalskye is shorter than one of the analysis windows')
        warningFlag[k]=1

    # Beat-time interval
    beatSR = np.ceil(np.multiply(beat_times,SR));                     # Get the beat time (transform it into sample indices)
    beatSR = np.delete(beatSR, np.nonzero(beatSR>=Nxorig))            # delete those samples that have exceeded the end of the song
 
    # Pad 0 to start, length of song to end
    if beatSR[0] is 0:
      beatSR = np.hstack([beatSR, Nxorig])
    else:
      beatSR = np.hstack([0.0, beatSR, Nxorig])

    numF = len(beatSR)-1
 
    # Process reference powers. Create storage if needed
    if refLabel is 'n':
     refPower          = 1
    elif refLabel is 's':
      refPower=10.0**(-12.0)
    elif refLabel is 'mean':
      meanPowerK       = np.zeros(K)
    elif refLabel is 'median':
      medianPowerK     = np.zeros(K)
    elif refLabel is 'q':
      # Need to store the average power of each frame
      quantile_matrix  = np.zeros(Nxorig)
      if (q_value<0.0 or q_value>1.0):
        raise ValueError("Quantile must be in range [0.1,1.0]")
    else:
      raise ValueError("Reference power must be one of: ['n', 's', 'mean', 'median', 'q']")

    # A-weight parameters
    if A_weightLabel is 1:
      Ap1 = 12200.0**2.0
      Ap2 = 20.6**2.0
      Ap3 = 107.7**2.0
      Ap4 = 737.9**2.0

    # Compute the CQ matrix for each point (row) and each frequency bin (column)
    A_offsets = np.zeros(K);
    CQ = np.zeros([K,numF]);
 
    for k in range(K):
       # Get the constant Q tranformation efficiently via convolution. 
       # First create hamming window for this frequency
       half_len = int(half_winLenK[k])
       w = np.hstack([hammingK[k][half_len-1:], np.zeros(Nx-len(hammingK[k])), hammingK[k][:half_len-1]])

       # Take fft of window and convolve, then invert
       wf = np.fft.fft(w)
       convolf = xf*wf
       convol = np.fft.ifft(convolf)
        
       # add A-weighting value for this frequency?
       if A_weightLabel is 1:
         frequency_k2 = freqK[k]**2.0;
         A_scale = Ap1*frequency_k2**2.0/((frequency_k2+Ap2)*np.sqrt((frequency_k2+Ap3)*(frequency_k2+Ap4))*(frequency_k2+Ap1))
         A_offsets[k] = 2.0+20.0*np.log10(A_scale)
        
       # Reference power and A weighting.
       # Compute abs(X)**2 and calculate offsets if needed
       if refLabel is 'mean':
         convol = np.abs(convol[:Nxorig])**2.0
         meanPowerK[k] = np.mean(convol)
       elif refLabel is 'median':
         convol = np.abs(convol[:Nxorig])**2.0
         medianPowerK[k] = np.median(convol)
       elif refLabel is 'q':
         convol = np.abs(convol[:Nxorig])**2.0
         quantile_matrix = np.add(quantile_matrix,convol)
       else:
         convol = (np.abs(convol[:Nxorig]))**2.0
        
       # Get the beat interval (median)
       for t in range(numF):
         t1 = int(beatSR[t])+1
         t2 = int(beatSR[t+1])
         CQ[k,t] = np.median(convol[t1-1:t2])   
          
    # Add the reference power (for mean/median/q-quantiles)
    if refLabel is 'mean':
      refPower = np.mean(meanPowerK);
      CQ = np.add(10.0*np.log10(CQ),-10.0*np.log10(refPower))
      CQ = np.add(CQ,np.transpose(np.tile(A_offsets,(numF,1))))
    elif refLabel is 'median':
      refPower = np.median(medianPowerK)
      CQ = np.add(10.0*np.log10(CQ),-10.0*np.log10(refPower))
      CQ = np.add(CQ,np.transpose(np.tile(A_offsets,(numF,1))))
    elif refLabel is 'q':
      # sort the values, set reference as the value that falls in the qth quantile
      quantile_value = np.sort(quantile_matrix) 
      refPower = quantile_value[int(np.floor(q_value*Nxorig))-1]/K
      CQ = np.add(10.0*np.log10(CQ),-10*np.log10(refPower))
      CQ = np.add(CQ,np.transpose(np.tile(A_offsets,(numF,1))))
    else:
      CQ = np.add(10.0*np.log10(CQ),-10.0*np.log10(refPower))
      CQ = np.add(CQ,np.transpose(np.tile(A_offsets,(numF,1))))
  
    # Beat synchronise
    chromagram = np.zeros((bins,numF))
    normal_chromagram = np.zeros((bins,numF))
    
    for i in range(bins):
      chromagram[i,:] = np.sum(CQ[i::bins,:],0)
     
    # Normalise
    for i in range(chromagram.shape[1]):
      maxCol = np.max(chromagram[:,i])
      minCol = np.min(chromagram[:,i])
      if (maxCol>minCol):
        normal_chromagram[:,i] = np.true_divide((chromagram[:,i]-minCol),(maxCol-minCol))
      else:
        normal_chromagram[:,i] = 0.0   

    # Shift to be C-based
    shift_pos = round(12.0*np.log2(freqK[0]/27.5)) # The relative position to A0
    shift_pos = int(np.mod(shift_pos,12)-3)        # since A0 should shift -3
    if not (shift_pos is 0):
      chromagram = np.roll(chromagram,shift_pos,0)
      normal_chromagram = np.roll(normal_chromagram,shift_pos,0)

    # 5. return the sample times
    beatSR = beatSR/SR
    sample_times = np.vstack([beatSR[:-1], beatSR[1:]])

    return chromagram, normal_chromagram, sample_times

#-- Tuning --#
def estimate_tuning(d,sr):

    """Estimate tuning of a signal. Create an instantaneous pitch track
       spectrogram, pick peak relative to standard pitch

    :parameters:
      - d: np.ndarray
        audio signal
      - sr : int
           audio sample rate of x

    :returns:
      - semisoff: float in [-0.5,0.5]
        estimated tuning of piece in cents
                  
      """

    # Tuning parameters
    fftlen = 4096
    f_ctr = 400
    f_sd = 1.0

    # Get minimum/maximum frequencies
    fminl = octs_to_hz(hz_to_octs(f_ctr)-2*f_sd)
    fminu = octs_to_hz(hz_to_octs(f_ctr)-f_sd)
    fmaxl = octs_to_hz(hz_to_octs(f_ctr)+f_sd)
    fmaxu = octs_to_hz(hz_to_octs(f_ctr)+2*f_sd)

    # Estimte pitches
    [p,m,S] = isp_ifptrack(d,fftlen,sr,fminl,fminu,fmaxl,fmaxu)
    
    # nzp = linear index of non-zero sinusoids found.
    nzp = p.flatten(1)>0
  
    # Find significantly large magnitudes
    mflat = m.flatten(1)
    gmm = mflat > np.median(mflat[nzp])
  
    # 2. element-multiply large magnitudes with frequencies.
    nzp = nzp * gmm
  
    # get non-zero again.
    nzp = np.nonzero(nzp)[0]
  
    # 3. convert to octaves
    pflat = p.flatten(1)
  
    # I didn't bother vectorising hz2octs....do it in a loop
    temp_hz = pflat[nzp]
    for i in range(len(temp_hz)):
      temp_hz[i] = hz_to_octs(temp_hz[i])
      
    Poctsflat = p.flatten(1)  
    Poctsflat[nzp] = temp_hz
    to_count = Poctsflat[nzp]
  
    # 4. get tuning
    nchr = 12   # size of feature

    # make histogram, resolution is 0.01, from -0.5 to 0.5
    import matplotlib.pyplot as plt
    term_one = nchr*to_count
    term_two = np.array(np.round(nchr*to_count),dtype=np.int)
    bins = [xxx * 0.01 for xxx in range(-50, 51)]
  
    # python uses edges, matlab uses centers so subtract half a bin size
    z = plt.hist(term_one-term_two-0.005,bins)

    hn = z[0]
    hx = z[1]

    # prepend things less than min
    nless = [sum(term_one-term_two-0.005 < -0.5)]
    hn = np.hstack([nless,hn])

    # find peaks
    semisoff = hx[np.argmax(hn)]

    return semisoff

def isp_ifptrack(d,w,sr,fminl = 150.0, fminu = 300.0, fmaxl = 2000.0, fmaxu = 4000.0):
    
    """ Instantaneous pitch frequency tracking spectrogram

    :parameters:
      - d: np.ndarray
        audio signal
      - w: int
        DFT length. FFT length will be half this,
        hop length 1/4
      - sr : int
        audio sample rate of x
      - fminl, fminu, fmaxu, fmaxl: floats
        ramps at the edge of sensitivity      

    :returns:
      - semisoff: float in [-0.5,0.5]
        estimated tuning of piece in cents
                  
      """  
  
    # Only look at bins up to 2 kHz
    maxbin = int(round(fmaxu*float(w)/float(sr)))
  
    # Calculate the inst freq gram
    [I,S] = isp_ifgram(d,w,w/2,w/4,sr, maxbin)
  
    # Find plateaus in ifgram - stretches where delta IF is < thr
    ddif = I[np.hstack([range(1,maxbin),maxbin-1]),:]-I[np.hstack([0,range(0,maxbin-1)]),:]

    # expected increment per bin = sr/w, threshold at 3/4 that
    dgood = abs(ddif) < .75*float(sr)/float(w)

    # delete any single bins (both above and below are zero);
    logic_one = dgood[np.hstack([range(1,maxbin),maxbin-1]),:] > 0
    logic_two = dgood[np.hstack([0,range(0,maxbin-1)]),:] > 0
    dgood = dgood * np.logical_or(logic_one,logic_two)
    
    p = np.zeros(dgood.shape)
    m = np.zeros(dgood.shape)

    # For each frame, extract all harmonic freqs & magnitudes
    lds = np.size(dgood,0)
    for t in range(I.shape[1]):
      ds = dgood[:,t]
            
      # find nonzero regions in this vector
      logic_one = np.hstack([0,ds[range(0,lds-1)]])==0
      logic_two = ds > 0
      logic_oneandtwo = np.logical_and(logic_one,logic_two)
      st = np.nonzero(logic_oneandtwo)[0]
    
      logic_three = np.hstack([ds[range(1,lds)],0])==0
      logic_twoandthree = np.logical_and(logic_two,logic_three)
      en = np.nonzero(logic_twoandthree)[0]

      # Set up inner loop    
      npks = len(st)
      frqs = np.zeros(npks)
      mags = np.zeros(npks)
      for i in range(len(st)):
        bump = np.abs(S[range(st[i],en[i]+1),t])
        mags[i] = sum(bump)
      
        # another long division, split it up
        numer = np.dot(bump,I[range(st[i],en[i]+1),t])
        isz = (mags[i]==0)
        denom = mags[i]+isz.astype(int)
        frqs[i] = numer/denom
                                    
        if frqs[i] > fmaxu:
          mags[i] = 0
          frqs[i] = 0
        elif frqs[i] > fmaxl:
          mags[i] = mags[i] * max(0, (fmaxu - frqs[i])/(fmaxu-fmaxl))

        # downweight magnitudes below? 200 Hz
        if frqs[i] < fminl:
          mags[i] = 0
          frqs[i] = 0
        elif frqs[i] < fminu:
          # 1 octave fade-out
          mags[i] = mags[i] * (frqs[i] - fminl)/(fminu-fminl)

        if frqs[i] < 0: 
          mags[i] = 0
          frqs[i] = 0
          
      # Collect into bins      
      bin = np.round((st+en)/2.0)
      p[bin.astype(int),t] = frqs
      m[bin.astype(int),t] = mags

    return p,m,S
  
def isp_ifgram(X, N=256, W=256, H=256.0/2.0, SR=1, maxbin=1.0+256.0/2.0):
  
    """   Compute the instantaneous frequency (as a proportion of the sampling
    rate) obtained as the time-derivative of the phase of the complex
    spectrum as described by Toshihiro Abe et al in ICASSP'95,
    Eurospeech'97. Calculates regular STFT as side effect.

    :parameters:
      - X: np.ndarray
        audio signal
      - N: int
        FFT length
      - W: int
        window length
      - H: hop length    
      - sr : int
        sampling rate?
      - fminl, fminu, fmaxu, fmaxl: floats
        ramps at the edge of sensitivity
      - maxbin: float
        The index of the maximum bin needed. If specified, unnecessary
        computations are skipped.        

    :returns:
      - F: np.ndarray
        Instantaneous frequency spectrogram
       - D: np.ndarray
        Short time Fourier transform spectrogram               
      """   

    Flen = maxbin
    s = X.size

    # Make a Hanning window 
    win = 0.5*(1-np.cos(np.true_divide(np.arange(W)*2*np.pi,W)))

    # Window for discrete differentiation
    T = float(W)/float(SR)
    dwin = (-np.pi/T)*np.sin(np.true_divide(np.arange(W)*2*np.pi,W))

    # sum(win) takes out integration due to window, 2 compensates for neg frq
    norm = 2/sum(win)

    # How many complete windows?
    nhops = 1 + int(np.floor((s - W)/H))
  
    F = np.zeros((Flen, nhops))
    D = np.zeros((Flen, nhops),dtype=complex)

    nmw1 = int(np.floor((N-W)/2))

    ww = 2*np.pi*np.arange(Flen)*SR/N

    wu = np.zeros(N)
    du = np.zeros(N)
  
    # Main loop
    for h in range(nhops):
      u = X[h*H:(W+h*H)]

      # Pad or truncate samples if N != W
      # Apply windows now, while the length is right
      if N >= W:
        wu[nmw1:(nmw1+W)] = win*u
        du[nmw1:(nmw1+W)] = dwin*u
      elif N < W:
        # Can't make sense of Dan's code here:
        #wu = win[1-nmw1:N-nmw1]*u[1-nmw1:N-nmw1];
        #du = dwin[1-nmw1:N-nmw1]*u[1-nmw1:N-nmw1];
        print 'Error, N must be at least window size'

      # FFTs of straight samples plus differential-weighted ones
      # Replaced call to fftshift with inline version. Jesper Hjvang Jensen, Aug 2007
      # t1 = fft(fftshift(du));
      # t2 = fft(fftshift(wu));
      split = int(np.ceil(du.size/2.0) + 1)
      
      # Need to reverse front and last parts of du and wu      
      temp_du = np.hstack([du[split-1:],du[0:split-1]])
      temp_wu = np.hstack([wu[split-1:],wu[0:split-1]])
      
      t1 = np.fft.fft(temp_du)
      t2 = np.fft.fft(temp_wu)
      
      t1 = t1[0:Flen]
      t2 = t2[0:Flen]
      
      # Scale down to factor out length & window effects
      D[:,h] = t2*norm
      
      # Calculate instantaneous frequency from phase of differential spectrum
      t = t1 + 1j*(ww*t2)
      a = t2.real
      b = t2.imag
      da = t.real
      db = t.imag
      
      # split this confusing divsion into chunks!
      # instf = (1/(2*pi))*(a.*db - b.*da)./((a.*a + b.*b)+(t2==0));
      num_one = 1.0/(2*np.pi)
      num_two = (a*db - b*da)
      denom_one = (a*a + b*b)
      isz = (t2==0)
      instf = np.true_divide(num_one*num_two,denom_one+isz.astype(int))
      F[:,h] = instf
 
    return F, D

#-- Mel spectrogram and MFCCs --#
def dctfb(n_filts, d):
    """Discrete cosine transform basis

    :parameters:
      - n_filts   : int
          number of output components
      - d         : int
          number of input components

    :returns:
      - D         : np.ndarray, shape=(n_filts, d)
          DCT basis vectors

    """

    basis       = np.empty((n_filts, d))
    basis[0, :] = 1.0 / np.sqrt(d)

    samples     = np.arange(1, 2*d, 2) * np.pi / (2.0 * d)

    for i in xrange(1, n_filts):
        basis[i, :] = np.cos(i*samples) * np.sqrt(2.0/d)

    return basis

def mfcc(S, d=20):
    """Mel-frequency cepstral coefficients

    :parameters:
      - S     : np.ndarray
          log-power Mel spectrogram
      - d     : int
          number of MFCCs to return

    :returns:
      - M     : np.ndarray
          MFCC sequence

    """

    return np.dot(dctfb(d, S.shape[0]), S)

def mel_frequencies(n_mels=40, fmin=0.0, fmax=11025.0, htk=False):
    """Compute the center frequencies of mel bands

    :parameters:
      - n_mels    : int
          number of Mel bins  
      - fmin      : float
          minimum frequency (Hz)
      - fmax      : float
          maximum frequency (Hz)
      - htk       : boolean
          use HTK formula instead of Slaney

    :returns:
      - bin_frequencies : ndarray
          ``n_mels+1``-dimensional vector of Mel frequencies

    """

    # 'Center freqs' of mel bands - uniformly spaced between limits
    minmel  = hz_to_mel(fmin, htk=htk)
    maxmel  = hz_to_mel(fmax, htk=htk)

    mels    = np.arange(minmel, maxmel + 1, (maxmel - minmel)/(n_mels + 1.0))
    
    return  mel_to_hz(mels, htk=htk)

def melfb(sr, n_fft, n_mels=40, fmin=0.0, fmax=None, htk=False):
    """Create a Filterbank matrix to combine FFT bins into Mel-frequency bins

    :parameters:
      - sr        : int
          sampling rate of the incoming signal
      - n_fft     : int
          number of FFT components
      - n_mels    : int
          number of Mel bands 
      - fmin      : float
          lowest frequency (in Hz) 
      - fmax      : float
          highest frequency (in Hz)
      - htk       : boolean
          use HTK formula instead of Slaney

    :returns:
      - M         : np.ndarray, shape=(n_mels, n_fft)
          Mel transform matrix

    .. note:: coefficients above 1 + n_fft/2 are set to 0.

    """

    if fmax is None:
        fmax = sr / 2.0

    # Initialize the weights
    weights     = np.zeros( (n_mels, n_fft) )

    # Center freqs of each FFT bin
    size        = 1 + n_fft / 2
    fftfreqs    = np.arange( size, dtype=float ) * sr / n_fft

    # 'Center freqs' of mel bands - uniformly spaced between limits
    freqs       = mel_frequencies(n_mels, fmin, fmax, htk)

    # Slaney-style mel is scaled to be approx constant E per channel
    enorm       = 2.0 / (freqs[2:n_mels+2] - freqs[:n_mels])

    for i in xrange(n_mels):
        # lower and upper slopes for all bins
        lower   = (fftfreqs - freqs[i])     / (freqs[i+1] - freqs[i])
        upper   = (freqs[i+2] - fftfreqs)   / (freqs[i+2] - freqs[i+1])

        # .. then intersect them with each other and zero
        weights[i, :size]   = np.maximum(0, np.minimum(lower, upper)) * enorm[i]
   
    return weights

def melspectrogram(y, sr=22050, n_fft=256, hop_length=128, **kwargs):
    """Compute a mel spectrogram from a time series

    :parameters:
      - y : np.ndarray
          audio time-series
      - sr : int
          audio sampling rate of y  
      - n_fft : int
          number of FFT components
      - hop_length : int
          frames to hop

      - kwargs
          Mel filterbank parameters
          See melfb() documentation for details.

    :returns:
      - S : np.ndarray
          Mel spectrogram

    """

    # Compute the STFT
    powspec     = np.abs(librosa.core.stft(y,   
                                      n_fft       =   n_fft, 
                                      hann_w      =   n_fft, 
                                      hop_length  =   hop_length))**2

    # Build a Mel filter
    mel_basis   = melfb(sr, n_fft, **kwargs)

    # Remove everything past the nyquist frequency
    mel_basis   = mel_basis[:, :(n_fft/ 2  + 1)]
    
    return np.dot(mel_basis, powspec)

#-- miscellaneous utilities --#
def sync(data, frames, aggregate=np.mean):
    """Synchronous aggregation of a feature matrix

    :parameters:
      - data      : np.ndarray, shape=(d, T)
          matrix of features
      - frames    : np.ndarray
          (ordered) array of frame segment boundaries
      - aggregate : function
          aggregation function (defualt: mean)

    :returns:
      - Y         : ndarray 
          ``Y[:, i] = aggregate(data[:, F[i-1]:F[i]], axis=1)``

    .. note:: In order to ensure total coverage, boundary points are added to frames

    """
    if data.ndim < 2:
        data = np.asarray([data])
    elif data.ndim > 2:
        raise ValueError('Synchronized data has ndim=%d, must be 1 or 2.' % data.ndim)

    (dimension, n_frames) = data.shape

    frames      = np.unique(np.concatenate( ([0], frames, [n_frames]) ))

    if min(frames) < 0:
        raise ValueError('Negative frame index.')
    elif max(frames) > n_frames:
        raise ValueError('Frame index exceeds data length.')

    data_agg    = np.empty( (dimension, len(frames)-1) )

    start       = frames[0]

    for (i, end) in enumerate(frames[1:]):
        data_agg[:, i] = aggregate(data[:, start:end], axis=1)
        start = end

    return data_agg
