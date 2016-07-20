import librosa
import numpy as np


def test_dtw_global():
    # Example taken from:
    # Meinard Mueller, Fundamentals of Music Processing
    X = np.array([[1, 3, 3, 8, 1]])
    Y = np.array([[2, 0, 0, 8, 7, 2]])

    gt_D = np.array([[1., 2., 3., 10., 16., 17.],
                     [2., 4., 5., 8., 12., 13.],
                     [3., 5., 7., 10., 12., 13.],
                     [9., 11., 13., 7., 8., 14.],
                     [10, 10., 11., 14., 13., 9.]])

    mut_D, _ = librosa.dtw(X, Y)

    assert np.array_equal(gt_D, mut_D)


def test_dtw_global_diagonal():
    # query is a linear ramp
    X = np.linspace(0.1, 1, 10)
    Y = X

    gt_wp = list(zip(list(range(10)), list(range(10))))[::-1]

    mut_D, mut_wp = librosa.dtw(X, Y, subseq=True, dist='cosine',
                                step_sizes_sigma=np.array([[1, 1]]),
                                weights_mul=np.array([1, ]))

    assert np.array_equal(np.asarray(gt_wp), np.asarray(mut_wp))


def test_dtw_subseq():
    # query is a linear ramp
    X = np.linspace(0, 1, 100)

    # database is query surrounded by noise
    noise_len = 200
    noise = np.random.rand(noise_len)
    Y = np.concatenate((noise, noise, X, noise))

    _, mut_wp = librosa.dtw(X, Y, subseq=True)

    # estimated sequence has to match original sequence
    # note the +1 due to python indexing
    mut_X = Y[mut_wp[-1][1]:mut_wp[0][1]+1]
    assert np.array_equal(X, mut_X)


def test_dtw_band_mask():
    # Case 1: Square matrix (N=M)
    mut_x = np.ones((8, 8))
    librosa.band_mask(mut_x, 0.25)

    gt_x = np.array([[1, 1, 0, 0, 0, 0, 0, 0],
                     [1, 1, 1, 0, 0, 0, 0, 0],
                     [0, 1, 1, 1, 0, 0, 0, 0],
                     [0, 0, 1, 1, 1, 0, 0, 0],
                     [0, 0, 0, 1, 1, 1, 0, 0],
                     [0, 0, 0, 0, 1, 1, 1, 0],
                     [0, 0, 0, 0, 0, 1, 1, 1],
                     [0, 0, 0, 0, 0, 0, 1, 1]])

    assert np.array_equal(mut_x, gt_x)

    # Case 2: N!=M
    mut_x = np.ones((8, 12))
    librosa.band_mask(mut_x, 0.25)

    gt_x = np.array([[1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0],
                     [1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0],
                     [0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
                     [0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
                     [0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0],
                     [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0],
                     [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1],
                     [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1]])

    assert np.array_equal(mut_x, gt_x)

    # Case 3: (N!=M).T
    mut_x = np.ones((8, 12)).T
    librosa.band_mask(mut_x, 0.25)

    assert np.array_equal(mut_x, gt_x.T)
