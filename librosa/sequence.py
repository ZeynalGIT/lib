#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
Sequential modeling
===================

Viterbi decoding
----------------
.. autosummary::
    :toctree: generated/

    viterbi
    viterbi_discriminative
    viterbi_binary

Transition matrices
-------------------
.. autosummary::
    :toctree: generated/

    transition_uniform
    transition_loop
    transition_cycle
    transition_local
'''

import numpy as np
from numba import jit
from .util import pad_center
from .util.exceptions import ParameterError
from .filters import get_window

__all__ = ['viterbi', 'viterbi_discriminative', 'viterbi_binary',
           'transition_uniform',
           'transition_loop',
           'transition_cycle',
           'transition_local']


@jit(nopython=True)
def _viterbi(log_prob, log_trans, log_p_init, state, value, ptr):  # pragma: no cover
    '''Core Viterbi algorithm.

    This is intended for internal use only.

    Parameters
    ----------
    log_prob : np.ndarray, shape=(T, m)
        `log_prob[t, s]` is the conditional log-likelihood
        log P[X = X(t) | State(t) = s]

    log_trans : np.ndarray, shape=(m, m)
        The log transition matrix
        `log_trans[i, j]` = log P[State(t+1) = j | State(t) = i]

    log_p_init : np.ndarray, shape=(m,)
        log of the initial state distribution

    state : np.ndarray, shape=(T,), int
        Pre-allocated state index array

    value : np.ndarray, shape=(T, m), float
        Pre-allocated value array

    ptr : np.ndarray, shape=(T, m), int
        Pre-allocated pointer array

    Returns
    -------
    None
        All computations are performed in-place on `state, value, ptr`.
    '''
    n_steps, n_states = log_prob.shape

    # factor in initial state distribution
    value[0] = log_prob[0] + log_p_init

    for t in range(1, n_steps):
        # Want V[t, j] <- p[t, j] * max_k V[t-1, k] * A[k, j]
        #    assume at time t-1 we were in state k
        #    transition k -> j

        # Broadcast over rows:
        #    Tout[k, j] = V[t-1, k] * A[k, j]
        #    then take the max over columns
        # We'll do this in log-space for stability

        trans_out = value[t - 1] + log_trans.T

        # Unroll the max/argmax loop to enable numba support
        for j in range(n_states):
            ptr[t, j] = np.argmax(trans_out[j])
            # value[t, j] = log_prob[t, j] + np.max(trans_out[j])
            value[t, j] = log_prob[t, j] + trans_out[j, ptr[t][j]]

    # Now roll backward

    # Get the last state
    state[-1] = np.argmax(value[-1])

    for t in range(n_steps - 2, -1, -1):
        state[t] = ptr[t+1, state[t+1]]
    # Done.


def viterbi(prob, transition, p_init=None, return_logp=False):
    '''Viterbi decoding from observation likelihoods.

    Given a sequence of observation likelihoods `prob[s, t]`,
    indicating the conditional likelihood of seeing the observation
    at time `t` from state `s`, and a transition matrix
    `transition[i, j]` which encodes the conditional probability of
    moving from state `i` to state `j`, the Viterbi algorithm computes
    the most likely sequence of states from the observations.

    Parameters
    ----------
    prob : np.ndarray [shape=(n_states, n_steps)], non-negative
        `prob[s, t]` is the probability of observation at time `t`
        being generated by state `s`.

    transition : np.ndarray [shape=(n_states, n_states)], non-negative
        `transition[i, j]` is the probability of a transition from i->j.
        Each row must sum to 1.

    p_init : np.ndarray [shape=(n_states,)]
        Optional: initial state distribution.
        If not provided, a uniform distribution is assumed.

    return_logp : bool
        If `True`, return the log-likelihood of the state sequence.

    Returns
    -------
    Either `states` or `(states, logp)`:

    states : np.ndarray [shape=(n_steps,)]
        The most likely state sequence.

    logp : scalar [float]
        If `return_logp=True`, the log probability of `states` given
        the observations.

    See Also
    --------
    viterbi_discriminative : Viterbi decoding from state likelihoods
    '''

    n_states, n_steps = prob.shape

    if transition.shape != (n_states, n_states):
        raise ParameterError('transition.shape={}, must be '
                             '(n_states, n_states)={}'.format(transition.shape,
                                                              (n_states, n_states)))

    if np.any(transition < 0) or not np.allclose(transition.sum(axis=1), 1):
        raise ParameterError('Invalid transition matrix: must be non-negative '
                             'and sum to 1 on each row.')

    if np.any(prob < 0) or np.any(prob > 1):
        raise ParameterError('Invalid probability values: must be between 0 and 1.')

    states = np.zeros(n_steps, dtype=int)
    values = np.zeros((n_steps, n_states), dtype=float)
    ptr = np.zeros((n_steps, n_states), dtype=int)

    # Compute log-likelihoods while avoiding log-underflow
    epsilon = np.finfo(prob.dtype).tiny
    log_trans = np.log(transition + epsilon)
    log_prob = np.log(prob.T + epsilon)

    if p_init is None:
        p_init = np.empty(n_states)
        p_init.fill(1./n_states)
    elif np.any(p_init < 0) or not np.allclose(p_init.sum(), 1):
        raise ParameterError('Invalid initial state distribution: '
                             'p_init={}'.format(p_init))

    log_p_init = np.log(p_init + epsilon)

    _viterbi(log_prob, log_trans, log_p_init, states, values, ptr)

    if return_logp:
        return states, values[-1, states[-1]]

    return states


def viterbi_discriminative(prob, transition, p_state=None, p_init=None, return_logp=False):
    '''Viterbi decoding from discriminative state predictions.

    Given a sequence of conditional state predictions `prob[s, t]`,
    indicating the conditional likelihood of state `s` given the
    observation at time `t`, and a transition matrix `transition[i, j]`
    which encodes the conditional probability of moving from state `i`
    to state `j`, the Viterbi algorithm computes the most likely sequence
    of states from the observations.

    This implementation uses the standard Viterbi decoding algorithm
    for observation likelihood sequences, under the assumption that
    `P[Obs(t) | State(t) = s]` is proportional to
    `P[State(t) = s | Obs(t)] / P[State(t) = s]`, where the denominator
    is the marginal probability of state `s` occurring as given by `p_state`.

    Parameters
    ----------
    prob : np.ndarray [shape=(n_states, n_steps)], non-negative
        `prob[s, t]` is the probability of state `s` conditional on
        the observation at time `t`.
        Must be non-negative and sum to 1 along each column.

    transition : np.ndarray [shape=(n_states, n_states)], non-negative
        `transition[i, j]` is the probability of a transition from i->j.
        Each row must sum to 1.

    p_state : np.ndarray [shape=(n_states,)]
        Optional: marginal probability distribution over states,
        must be non-negative and sum to 1.
        If not provided, a uniform distribution is assumed.

    p_init : np.ndarray [shape=(n_states,)]
        Optional: initial state distribution.
        If not provided, it is assumed to be uniform.

    return_logp : bool
        If `True`, return the log-likelihood of the state sequence.

    Returns
    -------
    Either `states` or `(states, logp)`:

    states : np.ndarray [shape=(n_steps,)]
        The most likely state sequence.

    logp : scalar [float]
        If `return_logp=True`, the log probability of `states` given
        the observations.

    See Also
    --------
    viterbi : Viterbi decoding from observation likelihoods
    viterbi_binary: Viterbi decoding for multi-label, conditional state likelihoods
    '''

    n_states, n_steps = prob.shape

    if transition.shape != (n_states, n_states):
        raise ParameterError('transition.shape={}, must be '
                             '(n_states, n_states)={}'.format(transition.shape,
                                                              (n_states, n_states)))

    if np.any(transition < 0) or not np.allclose(transition.sum(axis=1), 1):
        raise ParameterError('Invalid transition matrix: must be non-negative '
                             'and sum to 1 on each row.')

    if np.any(prob < 0) or not np.allclose(prob.sum(axis=0), 1):
        raise ParameterError('Invalid probability values: each column must '
                             'sum to 1 and be non-negative')

    states = np.zeros(n_steps, dtype=int)
    values = np.zeros((n_steps, n_states), dtype=float)
    ptr = np.zeros((n_steps, n_states), dtype=int)

    # Compute log-likelihoods while avoiding log-underflow
    epsilon = np.finfo(prob.dtype).tiny

    # Compute marginal log probabilities while avoiding underflow
    if p_state is None:
        p_state = np.empty(n_states)
        p_state.fill(1./n_states)
    elif p_state.shape != (n_states,):
        raise ParameterError('Marginal distribution p_state must have shape (n_states,). '
                             'Got p_state.shape={}'.format(p_state.shape))
    elif np.any(p_state < 0) or not np.allclose(p_state.sum(axis=-1), 1):
        raise ParameterError('Invalid marginal state distribution: '
                             'p_state={}'.format(p_state))

    log_trans = np.log(transition + epsilon)
    log_marginal = np.log(p_state + epsilon)

    # By Bayes' rule, P[X | Y] * P[Y] = P[Y | X] * P[X]
    # P[X] is constant for the sake of maximum likelihood inference
    # and P[Y] is given by the marginal distribution p_state.
    #
    # So we have P[X | y] \propto P[Y | x] / P[Y]
    log_prob = np.log(prob.T + epsilon) - log_marginal

    if p_init is None:
        p_init = np.empty(n_states)
        p_init.fill(1./n_states)
    elif np.any(p_init < 0) or not np.allclose(p_init.sum(), 1):
        raise ParameterError('Invalid initial state distribution: '
                             'p_init={}'.format(p_init))

    log_p_init = np.log(p_init + epsilon)

    _viterbi(log_prob, log_trans, log_p_init, states, values, ptr)

    if return_logp:
        return states, values[-1, states[-1]]

    return states


def viterbi_binary(prob, transition, p_state=None, p_init=None, return_logp=False):
    '''Viterbi decoding from binary (multi-label), discriminative state predictions.

    Given a sequence of conditional state predictions `prob[s, t]`,
    indicating the conditional likelihood of state `s` being active
    conditional on observation at time `t`, and a 2*2 transition matrix
    `transition` which encodes the conditional probability of moving from
    state `s` to state `~s` (not-`s`), the Viterbi algorithm computes the
    most likely sequence of states from the observations.

    This function differs from `viterbi_discriminative` in that it does not assume the
    states to be mutually exclusive.  `viterbi_binary` is implemented by
    transforming the multi-label decoding problem to a collection
    of binary Viterbi problems (one for each *state* or label).

    The output is a binary matrix `states[s, t]` indicating whether each
    state `s` is active at time `t`.

    Parameters
    ----------
    prob : np.ndarray [shape=(n_steps,) or (n_states, n_steps)], non-negative
        `prob[s, t]` is the probability of state `s` being active
        conditional on the observation at time `t`.
        Must be non-negative and less than 1.

        If `prob` is 1-dimensional, it is expanded to shape `(1, n_steps)`.

    transition : np.ndarray [shape=(2, 2) or (n_states, 2, 2)], non-negative
        If 2-dimensional, the same transition matrix is applied to each sub-problem.
        `transition[0, i]` is the probability of the state going from inactive to `i`,
        `transition[1, i]` is the probability of the state going from active to `i`.
        Each row must sum to 1.

        If 3-dimensional, `transition[s]` is interpreted as the 2x2 transition matrix
        for state label `s`.

    p_state : np.ndarray [shape=(n_states,)]
        Optional: marginal probability for each state (between [0,1]).
        If not provided, a uniform distribution (0.5 for each state)
        is assumed.

    p_init : np.ndarray [shape=(n_states,)]
        Optional: initial state distribution.
        If not provided, it is assumed to be uniform.

    return_logp : bool
        If `True`, return the log-likelihood of the state sequence.

    Returns
    -------
    Either `states` or `(states, logp)`:

    states : np.ndarray [shape=(n_states, n_steps)]
        The most likely state sequence.

    logp : np.ndarray [shape=(n_states,)]
        If `return_logp=True`, the log probability of each state activation
        sequence `states`

    See Also
    --------
    viterbi : Viterbi decoding from observation likelihoods
    viterbi_discriminative : Viterbi decoding for discriminative (mutually exclusive) state predictions
    '''

    prob = np.atleast_2d(prob)

    n_states, n_steps = prob.shape

    if transition.shape == (2, 2):
        transition = np.tile(transition, (n_states, 1, 1))
    elif transition.shape != (n_states, 2, 2):
        raise ParameterError('transition.shape={}, must be (2,2) or '
                             '(n_states, 2, 2)={}'.format(transition.shape, (n_states)))

    if np.any(transition < 0) or not np.allclose(transition.sum(axis=-1), 1):
        raise ParameterError('Invalid transition matrix: must be non-negative '
                             'and sum to 1 on each row.')

    if np.any(prob < 0) or np.any(prob > 1):
        raise ParameterError('Invalid probability values: prob must be between [0, 1]')

    if p_state is None:
        p_state = np.empty(n_states)
        p_state.fill(0.5)
    else:
        p_state = np.atleast_1d(p_state)

    if p_state.shape != (n_states,) or np.any(p_state < 0) or np.any(p_state > 1):
        raise ParameterError('Invalid marginal state distributions: p_state={}'.format(p_state))

    if p_init is None:
        p_init = np.empty(n_states)
        p_init.fill(1./n_states)
    else:
        p_init = np.atleast_1d(p_init)

    if p_init.shape != (n_states,) or np.any(p_init < 0) or np.any(p_init > 1):
        raise ParameterError('Invalid initial state distributions: p_init={}'.format(p_init))

    states = np.empty((n_states, n_steps), dtype=int)
    logp = np.empty(n_states)

    prob_binary = np.empty((2, n_steps))
    p_state_binary = np.empty(2)
    p_init_binary = np.empty(2)

    for state in range(n_states):
        prob_binary[0] = 1 - prob[state]
        prob_binary[1] = prob[state]

        p_state_binary[0] = 1 - p_state[state]
        p_state_binary[1] = p_state[state]

        p_init_binary[0] = 1 - p_init[state]
        p_init_binary[1] = p_init[state]

        states[state, :], logp[state] = viterbi_discriminative(prob_binary,
                                                  transition[state],
                                                  p_state=p_state_binary,
                                                  p_init=p_init_binary,
                                                  return_logp=True)

    if return_logp:
        return states, logp

    return states


def transition_uniform(n_states):
    '''Construct a uniform transition matrix over `n_states`.

    Parameters
    ----------
    n_states : int > 0
        The number of states

    Returns
    -------
    transition : np.ndarray, shape=(n_states, n_states)
        `transition[i, j] = 1./n_states`

    Examples
    --------

    >>> librosa.sequence.transition_uniform(3)
    array([[0.333, 0.333, 0.333],
           [0.333, 0.333, 0.333],
           [0.333, 0.333, 0.333]])
    '''

    if not isinstance(n_states, int) or n_states <= 0:
        raise ParameterError('n_states={} must be a positive integer')

    transition = np.empty((n_states, n_states), dtype=np.float)
    transition.fill(1./n_states)
    return transition


def transition_loop(n_states, prob):
    '''Construct a self-loop transition matrix over `n_states`.

    The transition matrix will have the following properties:

        - `transition[i, i] = p` for all i
        - `transition[i, j] = (1 - p) / (n_states - 1)` for all `j != i`

    This type of transition matrix is appropriate when states tend to be
    locally stable, and there is no additional structure between different
    states.  This is primarily useful for de-noising frame-wise predictions.

    Parameters
    ----------
    n_states : int > 1
        The number of states

    prob : float in [0, 1] or iterable, length=n_states
        If a scalar, this is the probability of a self-transition.

        If a vector of length `n_states`, `p[i]` is the probability of state `i`'s self-transition.

    Returns
    -------
    transition : np.ndarray, shape=(n_states, n_states)
        The transition matrix

    Examples
    --------
    >>> librosa.sequence.transition_loop(3, 0.5)
    array([[0.5 , 0.25, 0.25],
           [0.25, 0.5 , 0.25],
           [0.25, 0.25, 0.5 ]])

    >>> librosa.sequence.transition_loop(3, [0.8, 0.5, 0.25])
    array([[0.8  , 0.1  , 0.1  ],
           [0.25 , 0.5  , 0.25 ],
           [0.375, 0.375, 0.25 ]])
    '''

    if not isinstance(n_states, int) or n_states <= 1:
        raise ParameterError('n_states={} must be a positive integer > 1')

    transition = np.empty((n_states, n_states), dtype=np.float)

    # if it's a float, make it a vector
    prob = np.asarray(prob, dtype=np.float)

    if prob.ndim == 0:
        prob = np.tile(prob, n_states)

    if prob.shape != (n_states,):
        raise ParameterError('prob={} must have length equal to n_states={}'.format(prob, n_states))

    if np.any(prob < 0) or np.any(prob > 1):
        raise ParameterError('prob={} must have values in the range [0, 1]'.format(prob))

    for i, prob_i in enumerate(prob):
        transition[i] = (1. - prob_i) / (n_states - 1)
        transition[i, i] = prob_i

    return transition


def transition_cycle(n_states, prob):
    '''Construct a cyclic transition matrix over `n_states`.

    The transition matrix will have the following properties:

        - `transition[i, i] = p`
        - `transition[i, i + 1] = (1 - p)`

    This type of transition matrix is appropriate for state spaces
    with cyclical structure, such as metrical position within a bar.
    For example, a song in 4/4 time has state transitions of the form

        1->{1, 2}, 2->{2, 3}, 3->{3, 4}, 4->{4, 1}.

    Parameters
    ----------
    n_states : int > 1
        The number of states

    prob : float in [0, 1] or iterable, length=n_states
        If a scalar, this is the probability of a self-transition.

        If a vector of length `n_states`, `p[i]` is the probability of state
        `i`'s self-transition.

    Returns
    -------
    transition : np.ndarray, shape=(n_states, n_states)
        The transition matrix

    Examples
    --------
    >>> librosa.sequence.transition_cycle(4, 0.9)
    array([[0.9, 0.1, 0. , 0. ],
           [0. , 0.9, 0.1, 0. ],
           [0. , 0. , 0.9, 0.1],
           [0.1, 0. , 0. , 0.9]])
    '''

    if not isinstance(n_states, int) or n_states <= 1:
        raise ParameterError('n_states={} must be a positive integer > 1')

    transition = np.zeros((n_states, n_states), dtype=np.float)

    # if it's a float, make it a vector
    prob = np.asarray(prob, dtype=np.float)

    if prob.ndim == 0:
        prob = np.tile(prob, n_states)

    if prob.shape != (n_states,):
        raise ParameterError('prob={} must have length equal to n_states={}'.format(prob, n_states))

    if np.any(prob < 0) or np.any(prob > 1):
        raise ParameterError('prob={} must have values in the range [0, 1]'.format(prob))

    for i, prob_i in enumerate(prob):
        transition[i, np.mod(i + 1, n_states)] = 1. - prob_i
        transition[i, i] = prob_i

    return transition


def transition_local(n_states, width, window='triangle', wrap=False):
    '''Construct a localized transition matrix.

    The transition matrix will have the following properties:

        - `transition[i, j] = 0` if `|i - j| > width`
        - `transition[i, i]` is maximal
        - `transition[i, i - width//2 : i + width//2]` has shape `window`

    This type of transition matrix is appropriate for state spaces
    that discretely approximate continuous variables, such as in fundamental
    frequency estimation.

    Parameters
    ----------
    n_states : int > 1
        The number of states

    width : int >= 1 or iterable
        The maximum number of states to treat as "local".
        If iterable, it should have length equal to `n_states`,
        and specify the width independently for each state.

    window : str, callable, or window specification
        The window function to determine the shape of the "local" distribution.

        Any window specification supported by `filters.get_window` will work here.

        .. note:: Certain windows (e.g., 'hann') are identically 0 at the boundaries,
            so and effectively have `width-2` non-zero values.  You may have to expand
            `width` to get the desired behavior.


    wrap : bool
        If `True`, then state locality `|i - j|` is computed modulo `n_states`.
        If `False` (default), then locality is absolute.

    See Also
    --------
    filters.get_window

    Returns
    -------
    transition : np.ndarray, shape=(n_states, n_states)
        The transition matrix

    Examples
    --------

    Triangular distributions with and without wrapping

    >>> librosa.sequence.transition_local(5, 3, window='triangle', wrap=False)
    array([[0.667, 0.333, 0.   , 0.   , 0.   ],
           [0.25 , 0.5  , 0.25 , 0.   , 0.   ],
           [0.   , 0.25 , 0.5  , 0.25 , 0.   ],
           [0.   , 0.   , 0.25 , 0.5  , 0.25 ],
           [0.   , 0.   , 0.   , 0.333, 0.667]])

    >>> librosa.sequence.transition_local(5, 3, window='triangle', wrap=True)
    array([[0.5 , 0.25, 0.  , 0.  , 0.25],
           [0.25, 0.5 , 0.25, 0.  , 0.  ],
           [0.  , 0.25, 0.5 , 0.25, 0.  ],
           [0.  , 0.  , 0.25, 0.5 , 0.25],
           [0.25, 0.  , 0.  , 0.25, 0.5 ]])

    Uniform local distributions with variable widths and no wrapping

    >>> librosa.sequence.transition_local(5, [1, 2, 3, 3, 1], window='ones', wrap=False)
    array([[1.   , 0.   , 0.   , 0.   , 0.   ],
           [0.5  , 0.5  , 0.   , 0.   , 0.   ],
           [0.   , 0.333, 0.333, 0.333, 0.   ],
           [0.   , 0.   , 0.333, 0.333, 0.333],
           [0.   , 0.   , 0.   , 0.   , 1.   ]])
    '''

    if not isinstance(n_states, int) or n_states <= 1:
        raise ParameterError('n_states={} must be a positive integer > 1')

    width = np.asarray(width, dtype=int)
    if width.ndim == 0:
        width = np.tile(width, n_states)

    if width.shape != (n_states,):
        raise ParameterError('width={} must have length equal to n_states={}'.format(width, n_states))

    if np.any(width < 1):
        raise ParameterError('width={} must be at least 1')

    transition = np.zeros((n_states, n_states), dtype=np.float)

    # Fill in the widths.  This is inefficient, but simple
    for i, width_i in enumerate(width):
        trans_row = pad_center(get_window(window, width_i, fftbins=False), n_states)
        trans_row = np.roll(trans_row, n_states//2 + i + 1)

        if not wrap:
            # Knock out the off-diagonal-band elements
            trans_row[min(n_states, i + width_i//2 + 1):] = 0
            trans_row[:max(0, i - width_i//2)] = 0

        transition[i] = trans_row

    # Row-normalize
    transition /= transition.sum(axis=1, keepdims=True)

    return transition
