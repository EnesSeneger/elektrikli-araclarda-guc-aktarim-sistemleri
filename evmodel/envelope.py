"""
Motor tepe tork-hiz zarfi (odev Bolum 1, 3.7).

Basit iki bolgeli zarf:
  n_m <= n_base : T_max = T_peak                  (sabit tork bolgesi)
  n_m >  n_base : T_max = P_peak / omega_m        (sabit guc bolgesi)
  n_m >  n_max  : T_max = 0                       (azami devir asildi)
  n_base = P_peak / T_peak  (rad/s -> rpm)

Tesla icin: 420 Nm, 239 kW -> n_base ~ 5434 rpm, n_max = 16000 rpm [R24].
"""

import numpy as np


def base_speed_rpm(t_peak_nm: float, p_peak_w: float) -> float:
    """Temel hiz: tepe torkun tepe gucle kesistigi devir [rpm]."""
    return p_peak_w / t_peak_nm * 60.0 / (2.0 * np.pi)


def t_max_nm(n_m_rpm: np.ndarray, t_peak_nm: float, p_peak_w: float,
             n_max_rpm: float | None = None) -> np.ndarray:
    """Verilen motor devrinde (rpm) kullanilabilir tepe tork [Nm]."""
    n = np.asarray(n_m_rpm, dtype=float)
    omega = n * 2.0 * np.pi / 60.0
    with np.errstate(divide="ignore"):
        t_power = np.where(omega > 0, p_peak_w / omega, np.inf)
    t = np.minimum(t_peak_nm, t_power)
    if n_max_rpm is not None:
        t = np.where(n > n_max_rpm, 0.0, t)
    return t
