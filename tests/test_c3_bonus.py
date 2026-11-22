"""
3C bonus tutarliligi (motor haritasi + G taramasi).

  - Iyimser sinir ("eta_sabit") Tesla G'sinde sabit verimli modelle ayni WLTC tuketimini
    vermeli: params.py'deki eta_m/eta_reg zaten bu haritadan WLTC enerji agirlikli turetildi.
  - Kotumser sinir ("kayip_sabit") iyimserden kucuk olamaz (dusuk torkta kayip daha buyuk).
  - Sabit verimli model G'ye duyarsiz olmali (P_w G'den bagimsiz).
"""

import numpy as np

from analysis.c3_bonus import SCAN_CYCLE, g_upper_for_top_speed, simulate_map
from evmodel.cycles import load_cycle
from evmodel.model import simulate
from evmodel.params import TESLA_M3_SRP

REL_TOL = 1e-6


def test_c3_map_matches_constant_at_tesla_G():
    t, v = load_cycle(SCAN_CYCLE)
    const = simulate(t, v, TESLA_M3_SRP).consumption_wh_km
    opt = simulate_map(t, v, TESLA_M3_SRP, "eta_sabit")["consumption_wh_km"]
    pes = simulate_map(t, v, TESLA_M3_SRP, "kayip_sabit")["consumption_wh_km"]
    assert np.isclose(opt, const, rtol=REL_TOL), (opt, const)
    assert pes >= opt


def test_c3_constant_model_independent_of_G():
    t, v = load_cycle(SCAN_CYCLE)
    a = simulate(t, v, TESLA_M3_SRP.with_(gear_ratio=8.0)).consumption_wh_km
    b = simulate(t, v, TESLA_M3_SRP.with_(gear_ratio=11.0)).consumption_wh_km
    assert np.isclose(a, b, rtol=REL_TOL)


def test_c3_top_speed_bound():
    # Tesla G = 9.04, v_top = 225 km/h ile ulasilabilir olmali
    assert g_upper_for_top_speed() > TESLA_M3_SRP.gear_ratio
