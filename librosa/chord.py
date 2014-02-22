#!/usr/bin/env python
"""Chord model and helper utilities"""

import librosa
import itertools
import sklearn
import sklearn.hmm

import numpy as np

def beats_to_chords(beat_times, chord_times, chord_labels):
    '''Propagate lab-style annotations to a list of beat timings.
              
    :parameters:
      - beat_times : ndarray, shape=(n, 2)
          The time range for beat intervals.
          The `i`th beat spans time `beat_times[i, 0]` to `beat_times[i, 1]`.
          `beat_times[0, 0]` should be 0, `beat_times[-1, 1]` should be the track duration.
          
      - chord_times : ndarray, shape=(m, 2)
          The time range for the `i`th annotation is `chord_times[i,0]` to `chord_times[i, 1]`.
          `chord_times[0, 0]` should be 0, `chord_times[-1, 1]` should be the track duration.
          
      - chord_labels : list of str, shape=(m,)
          List of annotation strings associated with `chord_times`
          
    :returns:
      - beat_labels : list of str, shape=(n,)
          Chord annotations at the beat level.
    '''
    
    interval_map = librosa.util.match_intervals(beat_times, chord_times)

    return [chord_labels[c] for c in interval_map]

class ChordHMM(sklearn.hmm.GaussianHMM):
    '''Gaussian-HMM chord model'''
    def __init__(self, 
                 chord_names, 
                 covariance_type='full', 
                 startprob=None, 
                 transmat=None, 
                 startprob_prior=None, 
                 transmat_prior=None, 
                 algorithm='viterbi', 
                 means_prior=None, 
                 means_weight=0, 
                 covars_prior=0.01, 
                 covars_weight=1, 
                 random_state=None):
        '''Construct a new Gaussian-HMM chord model.

        :parameters:
          - chord_names : list of str
              List of the names of chords in the model

          - remaining parameters:
              See ``sklearn.hmm.GaussianHMM``
        '''
        
        n_components = len(chord_names)
            
        sklearn.hmm.GaussianHMM.__init__(self, 
                                         n_components=n_components,
                                         covariance_type=covariance_type, 
                                         startprob=startprob, 
                                         transmat=transmat, 
                                         startprob_prior=startprob_prior, 
                                         transmat_prior=transmat_prior, 
                                         algorithm=algorithm, 
                                         means_prior=means_prior, 
                                         means_weight=means_weight, 
                                         covars_prior=covars_prior, 
                                         covars_weight=covars_weight, 
                                         random_state=random_state)
        
        # Build the chord mappings
        self.chord_to_id_ = {}
        self.id_to_chord_ = []
        
        for i, v in enumerate(chord_names):
            self.chord_to_id_[v] = i
            self.id_to_chord_.append(v)
    
    def predict_chords(self, X):
        '''Predict chords from an observation sequence
        
        :parameters:
          - X : np.ndarray, shape=(n, d)
            Observation sequence, e.g., transposed beat-synchronous chromagram.

        :returns:
          - Y : list of str, shape=(n,)
            For each row of ``X``, the most likely chord label.

        '''
        
        return [self.id_to_chord_[s] for s in self.decode(X)[1]]
    
    def fit(self, X, Y):
        '''Supervised training
        
        - X : list-like (n_songs) | X[i] : ndarray (n_beats, n_features)
          A collection of feature observations, 
          e.g., chromagrams for a collection of songs
          
        - Y : list-like (n_songs) | Y[i] list-like, (n_beats) | Y[i][t] str
          labels for each observation
        '''
        
        
        self.n_features = X[0].shape[1]

        sklearn.hmm.GaussianHMM._init(self, X, 'stmc')
        stats     = sklearn.hmm.GaussianHMM._initialize_sufficient_statistics(self)
        
        for obs_i, chords_i in itertools.izip(X, Y):
            # Synthesize a deterministic frame log-probability 
            framelogprob = np.empty( (obs_i.shape[0], self.n_components) )
            posteriors   = np.empty_like(framelogprob)
            
            framelogprob.fill(-np.log(sklearn.hmm.EPS))
            posteriors.fill(sklearn.hmm.EPS)
            
            for t, c in enumerate(chords_i):
                state = self.chord_to_id_[c]
                
                framelogprob[t, state] = -sklearn.hmm.EPS
                posteriors[t, state]   = 1.0
                
            lpr, fwdlattice = self._do_forward_pass(framelogprob)
            bwdlattice      = self._do_backward_pass(framelogprob)
            
            self._accumulate_sufficient_statistics(stats, 
                                                   obs_i, 
                                                   framelogprob, 
                                                   posteriors, 
                                                   fwdlattice, 
                                                   bwdlattice, 
                                                   'stmc')
            
        self._do_mstep(stats, params='stmc')


