"""
T1, T1b, T2 - odev Bolum 2 dogrulama testleri (Temel Arac).

Calistirma:  pytest tests/   veya   python run_all.py
"""

import numpy as np

from evmodel.model import simulate
from evmodel.params import BASE_VEHICLE

TOL = 0.005  # %0.5 bagil tolerans (beklenen degerler 1 ondalikla verilmis)


def rel_err(x, ref):
    return abs(x - ref) / abs(ref)


def run_t1(p_aux_w: float):
    """90 km/h sabit, 3600 s (t = 0..3600)."""
    t = np.arange(0, 3601)
    v = np.full(t.shape, 90.0)
    return simulate(t, v, BASE_VEHICLE.with_(p_aux_w=p_aux_w))


def test_t1_constant_speed():
    r = run_t1(p_aux_w=0.0)
    assert rel_err(r.consumption_wh_km, 143.5) < TOL, r.consumption_wh_km
    assert rel_err(r.f_trac_n[1800], 451.5) < TOL, r.f_trac_n[1800]
    assert rel_err(r.p_bat_w[1800], 12.9e3) < TOL, r.p_bat_w[1800]


def test_t1b_aux_load():
    r = run_t1(p_aux_w=400.0)
    assert rel_err(r.consumption_wh_km, 147.9) < TOL, r.consumption_wh_km


def run_t2():
    """10 s'de 0->50 km/h sabit ivme (t = 0..10, 11 nokta), P_aux = 0."""
    t = np.arange(0, 11)
    v = np.linspace(0.0, 50.0, 11)
    return simulate(t, v, BASE_VEHICLE.with_(p_aux_w=0.0))


def test_t2_acceleration():
    """
    Beklenen 63.1 Wh, P_bat'in 0-10 s arasindaki YAMUK integraline karsilik gelir.
    Odevdeki dikdortgen toplam (E_adim = P_bat dt/3600) bu kisa profilde ~69.5 Wh
    verir; fark = P_bat(10 s) * dt / 2 / 3600 ~ 6.4 Wh (son ornegin yarisi).
    Uclarinda hiz sifir olan surus donguleri icin iki yontem pratikte ayni sonucu verir.
    """
    r = run_t2()
    e_trapz = np.trapezoid(r.p_bat_w, r.t_s) / 3600.0
    e_rect = r.e_bat_wh
    assert rel_err(e_trapz, 63.1) < TOL, e_trapz
    assert rel_err(r.p_bat_w[-1], 46.1e3) < TOL, r.p_bat_w[-1]
    # dikdortgen - yamuk farki tam olarak son ornegin yarisi olmali
    assert np.isclose(e_rect - e_trapz, r.p_bat_w[-1] / 2 / 3600.0)
