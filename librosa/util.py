#!/usr/bin/env python
"""Utility functions"""

import numpy as np
import os, glob

def axis_sort(S, axis=-1, value=np.argmax): 
    '''Sort an array along its rows or columns.
    
    :usage:
        >>> # Visualize NMF output for a spectrogram S
        >>> # Sort the columns of W by peak frequency bin
        >>> W, H = librosa.decompose.decompose(S)
        >>> W_sort = librosa.util.axis_sort(W)

        >>> # Or sort by the lowest frequency bin
        >>> W_sort = librosa.util.axis_sort(W, value=np.argmin)

        >>> # Or sort the rows instead of the columns
        >>> W_sort_rows = librosa.util.axis_sort(W, axis=0)

    :parameters:
      - S : np.ndarray, ndim=2
        Matrix to sort
        
      - axis : int
        The axis along which to sort.  
        
        - `axis=0` to sort rows by peak column index
        - `axis=1` to sort columns by peak row index
        
      - value : function
        function to return the index corresponding to the sort order.
        Default: `np.argmax`.

    :raises:
      - ValueError
        If `S` does not have 2 dimensions.
    '''
    
    if S.ndim != 2:
        raise ValueError('axis_sort is only defined for 2-dimensional arrays.')
        
    bin_idx = value(S, axis=np.mod(1-axis, S.ndim))
    idx     = np.argsort(bin_idx)
    
    if axis == 0:
        return S[idx, :]
    
    return S[:, idx]

def get_audio_files(directory, ext=None, recurse=True, case_sensitive=False, limit=None, offset=0):
    '''Get a sorted list of audio files in a directory or directory sub-tree.
    
    :usage:
       >>> # Get all audio files in a directory sub-tree
       >>> files = librosa.util.get_audio_files('~/Music')
       
       >>> # Look only within a specific directory, not the sub-tree
       >>> files = librosa.util.get_audio_files('~/Music', recurse=False)
       
       >>> # Only look for mp3 files
       >>> files = librosa.util.get_audio_files('~/Music', ext='mp3')
       
       >>> # Or just mp3 and ogg
       >>> files = librosa.util.get_audio_files('~/Music', ext=['mp3', 'ogg'])
       
       >>> # Only get the first 10 files
       >>> files = librosa.util.get_audio_files('~/Music', limit=10)
       
       >>> # Or last 10 files
       >>> files = librosa.util.get_audio_files('~/Music', offset=-10)
       
    :parameters:
      - directory : str
        Path to look for files
        
      - ext : str or list of str
        A file extension or list of file extensions to include in the search.
        Default: `['aac', 'au', 'flac', 'm4a', 'mp3', 'ogg', 'wav']`
        
      - recurse : boolean
        If `True`, then all subfolders of `directory` will be searched.
        Otherwise, only `directory` will be searched.
        
      - case_sensitive : boolean
        If `False`, files matching upper-case version of extensions will be included.
        
      - limit : int >0 or None
        Return at most `limit` files. If `None`, all files are returned.
        
      - offset : int
        Return files starting at `offset` within the list.
        Use negative values to offset from the end of the list.
        
    :returns:
      - files, list of str
        The list of audio files.
    '''
    
    def _get_files(D, extensions):
        '''Helper function to get files in a single directory'''

        # Expand out the directory
        D = os.path.abspath(os.path.expanduser(D))
        
        myfiles = []
        for sub_ext in extensions:
            globstr = os.path.join(D, '*' + os.path.extsep + sub_ext)
            myfiles.extend(glob.glob(globstr))
        
        return myfiles
            
    if ext is None:
        ext = ['aac', 'au', 'flac', 'm4a', 'mp3', 'ogg', 'wav']
        
    elif isinstance(ext, str):
        if not case_sensitive:
            ext = ext.lower()
        ext = [ext]
        
    # Generate upper-case versions
    if not case_sensitive:
        for i in range(len(ext)):
            ext.append(ext[i].upper())
    
    files = []
    
    if recurse:
        for walk in os.walk(directory):
            files.extend(_get_files(walk[0], ext))
    else:
        files = _get_files(directory, ext)
    
    files.sort()
    files = files[offset:]
    if limit is not None:
        files = files[:limit]
    
    return files
