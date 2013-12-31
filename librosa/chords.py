#!/usr/bin/env python
"""Chord estimation"""

# Add paths
import cPickle as pickle
from sklearn.hmm import GaussianHMM

def load_model(model):
    r'''Loads an HMM-based chord estimation model from file

    :usage:
        >>> Model = librosa.chords.load_model( model )

    :parameters:
      - model          : string
          full path to .p extension HMM model, which is a dictionary
          named 'Chord_Parameters' with the following keys/values:

            'chord_names' - list of string chord names of length n_states
            'Trans'       - (n_states, n_states) np.ndarray chord transition matrix
            'Init'        - (n_states,) tuple of initial chord distribution
            'Mu'          - (n_states, 12) np.ndarray of mean pitch class energy for 
                            each chord (n_states) and pitch class (12)
            'Sigma'       - (n_states, 12, 12) np.ndarray covariance matrix for each 
                            chord 

          all probabilities should be in normal (non-log) form                                   

    :returns: 
      - Model : dictionary
          Model parameters as above
    '''	

    # Un-pickle the saved parameters
    with open(model, 'r') as f:
        Chord_Parameters = pickle.load(f)

    # Set up in sklearn's framework
    Chord_symbols = Chord_Parameters[ 'chord_names' ]

    # number of chords = number of symbols
    n_states = len( Chord_symbols )

    # assume full covariance
    HMM = GaussianHMM(n_components     = n_states,
	                  covariance_type  = 'full')

    # set trans, init, mu, sigma
    HMM.transmat_  = Chord_Parameters['Trans']
    HMM.startprob_ = Chord_Parameters['Init']
    HMM.means_     = Chord_Parameters['Mu']
    HMM.covars_    = Chord_Parameters['Sigma']   

    HMM.state_labels = Chord_symbols

    return HMM 

def predict_chords( chromagram, HMM ):   
    r'''Predicts chords from a chromagram and HMM

    :usage:
        >>> chords, likelihood = librosa.chords.predict_chords( chromagram, model )

    :parameters:
      - chromagram          : np.ndarray
          (12, tmax) chromagram representing pitch salience
          for each time

      - states              : list
          list of chord names 

      - HMM                 : sklearn.GaussianHMM
          HMM model with the following model parameters:
          HMM.transmat_
          HMM.startprob_
          HMM.means_
          HMM.covars_
          HMM.state_labels 

          for a description of the format for the HMM parameters, see:

          http://scikit-learn.org/stable/modules/generated/sklearn.hmm.GaussianHMM.html               

          HMM.state_labels should be a list of chord names (strings), in the order
          used internall by HMM.transmat_ etc. 

    :returns: 
      - chords              : list
        chord symbol list of length t_max

      - likelihood          : maximum chord likelihood  
    '''	 

    # Run HMM decoder (sklearn likes the chroma to be transposed)
    likelihood, Raw_Sequence = HMM.decode( chromagram.T, algorithm='viterbi')

    # Convert back to chord symbols
    chords = [ HMM.state_labels[ s ] for s in Raw_Sequence ]

    return chords, likelihood 

def write_chords( chords, start_times, end_times, outfile ):
    r'''Writes chord prediction to file

    :usage:
        >>> librosa.chords.write_chords( chords, times, method='beat' )

    :parameters:
      - chords              : list
        chord symbol list of length t_max
      - start_times         : np.ndarray or list
          array of chord start times in seconds
      - end_times         : np.ndarray or list
          array of chord end times in seconds
      - outfile             : string
          path of file to write to (including extension)

    :returns: 
      - None
    '''	 

    # only print when the chord changes
    current_chord = chords[ 0 ]
    t = 0.0

    with open(outfile, 'w') as f:
        for chord, start, end in zip( chords, start_times, end_times ):
            if chord != current_chord:
                # chord has changed
                f.write( ' '.join( [ str( t ), str ( end ), str( current_chord ), '\n' ]) )
                current_chord = chord
                t = end
        # write last chord
        f.write( ' '.join( [ str( t ), str ( end ), str( current_chord )]) )

    
