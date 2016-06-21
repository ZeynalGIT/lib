#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Sequence Alignment with Dynamic Time Warping."""

import numpy as np
from scipy.spatial.distance import cdist
from librosa.util.decorators import optional_jit
from ..util.exceptions import ParameterError

__all__ = ['dtw']


@optional_jit
def band_mask(radius, mask):
    """Construct band-around-diagonal mask (Sakoe-Chiba band).  When
    ``mask.shape[0] != mask.shape[1]``, the radius will be expanded so that
    ``mask[-1, -1] = 1`` always.

    `mask` will be modified in place.

    Parameters
    ----------
    radius : float
        The band radius (1/2 of the width) will be
        ``int(radius*min(mask.shape))``.
    mask : np.ndarray
        Pre-allocated boolean matrix of zeros.

    Examples
    --------
    >>> mask = np.zeros((8, 8), dtype=np.bool)
    >>> band_mask(0.25, mask)
    >>> mask.astype(int)
    array([[1, 1, 0, 0, 0, 0, 0, 0],
           [1, 1, 1, 0, 0, 0, 0, 0],
           [0, 1, 1, 1, 0, 0, 0, 0],
           [0, 0, 1, 1, 1, 0, 0, 0],
           [0, 0, 0, 1, 1, 1, 0, 0],
           [0, 0, 0, 0, 1, 1, 1, 0],
           [0, 0, 0, 0, 0, 1, 1, 1],
           [0, 0, 0, 0, 0, 0, 1, 1]])
    >>> mask = np.zeros((8, 12), dtype=np.bool)
    >>> band_mask(0.25, mask)
    >>> mask.astype(int)
    array([[1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0],
           [1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
           [0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
           [0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
           [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0],
           [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0],
           [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1],
           [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1]])
    """
    nx, ny = mask.shape

    # The logic will be different depending on whether there are more rows
    # or columns in the mask.  Coding it this way results in some code
    # duplication but it's the most efficient way with numba
    if nx < ny:
        # Calculate the radius in indices, rather than proportion
        radius = int(round(nx*radius))
        # Force radius to be at least one
        radius = 1 if radius == 0 else radius
        for i in range(nx):
            for j in range(ny):
                # If this i, j falls within the band
                if i - j + (nx - radius) < nx and j - i + (nx - radius) < ny:
                    # Set the mask to 1 here
                    mask[i, j] = 1
    # Same exact approach with ny/ny and i/j switched.
    else:
        radius = int(round(ny*radius))
        radius = 1 if radius == 0 else radius
        for i in range(nx):
            for j in range(ny):
                if j - i + (ny - radius) < ny and i - j + (ny - radius) < nx:
                    mask[i, j] = 1


def dtw(X, Y, dist='euclidean', step_sizes_sigma=None,
        weights_add=None, weights_mul=None, subseq=False, backtrack=True,
        mask=False, mask_rad=0.25):
    '''Dynamic time warping (DTW).

    This function performs a DTW and path backtracking on two sequences.
    We follow the nomenclature and algorithmic approach as described in [1].

    .. [1] Meinard Mueller
           Fundamentals of Music Processing — Audio, Analysis, Algorithms, Applications
           Springer Verlag, ISBN: 978-3-319-21944-8, 2015.

    Parameters
    ----------
    X : np.ndarray [shape=(K, N)]
        audio feature matrix (e.g., chroma features)

    Y : np.ndarray [shape=(K, M)]
        audio feature matrix (e.g., chroma features)

    dist : str
        Identifier for the cost-function as documented
        in `scipy.spatial.cdist()`

    step_sizes_sigma : np.ndarray [shape=[n, 2]]
        Specifies allowed step sizes as used by the dtw.

    weights_add : np.ndarray [shape=[n, ]]
        Additive weights to penalize certain step sizes.

    weights_mul : np.ndarray [shape=[n, ]]
        Multiplicative weights to penalize certain step sizes.

    subseq : binary
        Enable subsequence DTW, e.g., for retrieval tasks.

    backtrack : binary
        Enable backtracking in accumulated cost matrix.

    mask : binary
        Construct band-around-diagonal mask (Sakoe-Chiba band).

    mask_rad : float
        The band radius (1/2 of the width) will be
        ``int(radius*min(C.shape))``.

    Returns
    -------
    D : np.ndarray [shape=(N,M)]
        accumulated cost matrix.
        D[N,M] is the total alignment cost.
        When doing subsequence DTW, D[N,:] indicates a matching function.

    wp : np.ndarray [shape=(N,2)]
        Warping path with index pairs.
        Each row of the array contains an index pair n,m).
        Only returned when ``backtrack`` is True.

    Raises
    ------
    ParameterError
        If you are doing diagonal matching and Y is shorter than X

    Examples
    --------
    >>> import numpy as np
    >>> import matplotlib.pyplot as plt
    >>> y, sr = librosa.load(librosa.util.example_audio_file(), offset=10, duration=15)
    >>> X = librosa.feature.chroma_cens(y=y, sr=sr)
    >>> noise = np.random.rand(X.shape[0], 200)
    >>> Y = np.concatenate((noise, noise, X, noise), axis=1)
    >>> D, wp = librosa.dtw(X, Y, subseq=True)
    >>> f, axarr = plt.subplots(2)
    >>> axarr[0].imshow(D, cmap=plt.get_cmap('gray_r'),
    ...                 origin='lower', interpolation='nearest', aspect='auto')
    >>> axarr[0].set_title('Database Excerpt')
    >>> axarr[0].plot(wp[:, 1], wp[:, 0], label='Optimal path', marker='o', color='r')
    >>> axarr[0].set_xlim([0, Y.shape[1]])
    >>> axarr[0].set_ylim([0, X.shape[1]])
    >>> axarr[0].legend()
    >>> axarr[1].plot(D[-1, :] / wp.shape[0])
    >>> axarr[1].set_xlim([0, Y.shape[1]])
    >>> axarr[1].set_ylim([0, 2])
    >>> axarr[1].set_title('Matching Function')
    '''
    # Default Parameters
    if step_sizes_sigma is None:
        step_sizes_sigma = np.array([[1, 1], [0, 1], [1, 0]])
    if weights_add is None:
        weights_add=np.array([0, 0, 0])
    if weights_mul is None:
        weights_mul=np.array([1, 1, 1])

    # take care of dimensions
    X = np.atleast_2d(X)
    Y = np.atleast_2d(Y)

    # if diagonal matching, Y has to be longer than X
    # (X simply cannot be contained in Y)
    if np.array_equal(step_sizes_sigma, np.array([[1, 1]])) and (X.shape[1] > Y.shape[1]):
        raise ParameterError('For diagonal matching: Y.shape[1] >= X.shape[1]')

    max_0 = step_sizes_sigma[:, 0].max()
    max_1 = step_sizes_sigma[:, 1].max()

    # calculate pair-wise distances
    C = cdist(X.T, Y.T, dist)

    if mask:
        my_mask = np.zeros_like(C, dtype=np.bool)
        band_mask(mask_rad, my_mask)

        # set cost to infinity where the mask is True
        C[my_mask == 0] = np.inf

    # initialize whole matrix with infinity values
    D = np.ones(C.shape + np.array([max_0, max_1])) * np.inf

    # set starting point to C[0, 0]
    D[max_0, max_1] = C[0, 0]

    if subseq:
        D[max_0, max_1:] = C[0, :]

    D_steps = np.empty(D.shape, dtype=np.int)

    # calculate accumulated cost matrix
    D, D_steps = calc_accu_cost(C, D, D_steps,
                                step_sizes_sigma,
                                weights_mul, weights_add,
                                max_0, max_1)

    # delete infinity rows and columns
    D = D[max_0:, max_1:]
    D_steps = D_steps[max_0:, max_1:]

    if backtrack:
        if subseq:
            # search for global minimum in last row of D-matrix
            wp_end_idx = np.argmin(D[-1, :]) + 1
            wp = backtracking(D_steps[:, :wp_end_idx], step_sizes_sigma)
        else:
            # perform warping path backtracking
            wp = backtracking(D_steps, step_sizes_sigma)

        return D, np.asarray(wp, dtype=int)
    else:
        return D


# @optional_jit
def calc_accu_cost(C, D, D_steps, step_sizes_sigma,
                   weights_mul, weights_add, max_0, max_1):
    '''Calculate the accumulated cost matrix D.

    Use dynamic programming to calculate the accumulated costs.

    Parameters
    ----------
    C : np.ndarray [shape=(N, M)]
        pre-computed cost matrix

    D : np.ndarray [shape=(N, M)]
        accumulated cost matrix

    D_steps : np.ndarray [shape=(N, M)]
        steps which were used for calculating D

    step_sizes_sigma : np.ndarray [shape=[n, 2]]
        Specifies allowed step sizes as used by the dtw.

    weights_add : np.ndarray [shape=[n, ]]
        Additive weights to penalize certain step sizes.

    weights_mul : np.ndarray [shape=[n, ]]
        Multiplicative weights to penalize certain step sizes.

    max_0 : int
        maximum number of steps in step_sizes_sigma in dim 0.

    max_1 : int
        maximum number of steps in step_sizes_sigma in dim 1.

    Returns
    -------
    D : np.ndarray [shape=(N,M)]
        accumulated cost matrix.
        D[N,M] is the total alignment cost.
        When doing subsequence DTW, D[N,:] indicates a matching function.

    D_steps : np.ndarray [shape=(N,M)]
        steps which were used for calculating D.

    See Also
    --------
    dtw
    '''
    for cur_n in range(max_0, D.shape[0]):
        for cur_m in range(max_1, D.shape[1]):
            # accumulate costs
            for cur_step_idx, cur_w_add, cur_w_mul in zip(range(step_sizes_sigma.shape[0]),
                                                          weights_add, weights_mul):
                cur_D = D[cur_n-step_sizes_sigma[cur_step_idx, 0],
                          cur_m-step_sizes_sigma[cur_step_idx, 1]]
                cur_C = cur_w_mul * C[cur_n-max_0, cur_m-max_1]
                cur_C += cur_w_add
                cur_cost = cur_D + cur_C

                # check if cur_cost is smaller than the one stored in D
                if cur_cost < D[cur_n, cur_m]:
                    D[cur_n, cur_m] = cur_cost

                    # save step-index
                    D_steps[cur_n, cur_m] = cur_step_idx

    return D, D_steps


@optional_jit
def backtracking(D_steps, step_sizes_sigma):
    '''Backtrack optimal warping path.

    Uses the saved step sizes from the cost accumulation
    step to backtrack the index pairs for an optimal
    warping path.


    Parameters
    ----------
    D_steps : np.ndarray [shape=(N, M)]
        Saved indices of the used steps used in the calculation of D.

    step_sizes_sigma : np.ndarray [shape=[n, 2]]
        Specifies allowed step sizes as used by the dtw.

    Returns
    -------
    wp : list [shape=(N,)]
        Warping path with index pairs.
        Each list entry contains an index pair
        (n,m) as a tuple

    See Also
    --------
    dtw
    '''
    wp = []
    # Set starting point D(N,M) and append it to the path
    cur_idx = np.asarray(D_steps.shape) - 1
    wp.append((cur_idx[0], cur_idx[1]))

    # Loop backwards.
    # Stop criteria:
    # Setting it to (0, 0) does not work for the subsequence dtw,
    # so we only ask to reach the first row of the matrix.
    while cur_idx[0]:
        cur_step_idx = D_steps[(cur_idx[0], cur_idx[1])]

        # save tuple with minimal acc. cost in path
        cur_idx = np.asarray(cur_idx) - step_sizes_sigma[cur_step_idx]

        # append to warping path
        wp.append((cur_idx[0], cur_idx[1]))

    return wp
