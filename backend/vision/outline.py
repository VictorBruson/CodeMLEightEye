import numpy as np

DEFAULT_HARMONICS = 20


def _area_centroid(p):
    x, y = p[:, 0], p[:, 1]
    x1, y1 = np.roll(x, -1), np.roll(y, -1)
    cross = x * y1 - x1 * y
    a = cross.sum() / 2.0
    if abs(a) < 1e-9:
        return p.mean(axis=0)
    return np.array([((x + x1) * cross).sum() / (6 * a), ((y + y1) * cross).sum() / (6 * a)])


def fourier_smooth(points, harmonics=DEFAULT_HARMONICS, n=720):
    p = np.asarray(points, dtype=float).reshape(-1, 2)
    cx, cy = _area_centroid(p)
    th = np.arctan2(p[:, 1] - cy, p[:, 0] - cx)
    r = np.hypot(p[:, 0] - cx, p[:, 1] - cy)
    order = np.argsort(th)
    grid = np.linspace(-np.pi, np.pi, n, endpoint=False)
    rg = np.interp(grid, th[order], r[order], period=2 * np.pi)
    spec = np.fft.rfft(rg)
    spec[harmonics + 1:] = 0
    rs = np.fft.irfft(spec, n)
    return np.column_stack([cx + rs * np.cos(grid), cy + rs * np.sin(grid)])


def robust_boxing(points, harmonics=DEFAULT_HARMONICS):
    s = fourier_smooth(points, harmonics)
    return float(np.ptp(s[:, 0])), float(np.ptp(s[:, 1]))
