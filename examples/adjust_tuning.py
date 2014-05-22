#!/usr/bin/env python
'''
CREATED:2014-05-22 16:43:44 by Brian McFee <brm2132@columbia.edu>
 
Pitch-shift a recording to be in A440 tuning.

Usage: ./retune.py [-h] input_file output_file
'''

import argparse
import sys
import librosa

def adjust_tuning(input_file, output_file):
    print 'Loading ', input_file
    y, sr = librosa.load(input_file)

    print 'Separating harmonic component ... '
    y_harm = librosa.effects.harmonic(y)

    print 'Estimating tuning ... '
    # Just track the pitches associated with high magnitude
    tuning = librosa.feature.estimate_tuning(y=y_harm, sr=sr)

    print '%+0.2f cents' % (100 * tuning)
    print 'Applying pitch-correction of %+0.2f cents' % (-100 * tuning)
    y_tuned = librosa.effects.pitch_shift(y, sr, -tuning)

    print 'Saving tuned audio to: ', output_file
    librosa.output.write_wav(output_file, y_tuned, sr)

def process_arguments():
    '''Argparse function to get the program parameters'''

    parser = argparse.ArgumentParser(description='librosa tuning adjustment example')

    parser.add_argument(    'input_file',
                            action      =   'store',
                            help        =   'path to the input file (wav, mp3, etc)')

    parser.add_argument(    'output_file',
                            action      =   'store',
                            help        =   'path to store the output wav')

    return vars(parser.parse_args(sys.argv[1:]))
   
if __name__ == '__main__':
    # Get the parameters
    parameters = process_arguments()

    # Run the beat tracker
    adjust_tuning(parameters['input_file'], parameters['output_file'])
