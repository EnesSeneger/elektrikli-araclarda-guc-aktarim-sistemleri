"""
Asama 2 tutarlilik testi: params.TESLA_M3_SRP'deki yol yuku parametreleri,
analysis/p2_road_load.py yontem b) EKK ile yeniden hesaplanan degerlerle ayni olmali.

Amac: biri ileride kutleyi (veya rho'yu) degistirip f_r'yi yeniden turetmeyi
unutursa bu test kirmizi olur. Kural: f_r * m * g = A (EKK sabit terimi) sabit kalir.

Calistirma:  pytest tests/   veya   python run_all.py
"""

import numpy as np

from analysis.p2_road_load import G, MASS_KG, RHO, method_least_squares, to_model_params, F0, F2
from evmodel.params import TESLA_M3_SRP, TESLA_SOURCED

RTOL = 1e-6  # goreli tolerans (degerler params.py'ye tam hassasiyetle yazildi)


def _close(x, ref):
    return np.isclose(x, ref, rtol=RTOL, atol=0.0)


def test_p2_tesla_road_load_params():
    p = TESLA_M3_SRP
    ref = method_least_squares()

    # turetmede kullanilan kutle, rho ve g modeldekiyle ayni olmali
    assert _close(p.m_kg, MASS_KG), (p.m_kg, MASS_KG)
    assert _close(p.rho_kgm3, RHO), (p.rho_kgm3, RHO)
    assert _close(p.g_ms2, G), (p.g_ms2, G)

    # f_r ve C_d*A_f, EKK sonucuyla ayni olmali
    assert _close(p.fr, ref["fr"]), (p.fr, ref["fr"])
    assert _close(p.cd * p.af_m2, ref["cda"]), (p.cd * p.af_m2, ref["cda"])

    # asil fiziksel kosul: modeldeki f_r*m*g, EKK'deki A katsayisina esit
    assert _close(p.fr * p.m_kg * p.g_ms2, ref["A"]), (p.fr * p.m_kg * p.g_ms2, ref["A"])
    # ve 1/2*rho*C_d*A_f (N/(m/s)^2) -> N/(km/h)^2, EKK'deki B katsayisina esit
    b_model = 0.5 * p.rho_kgm3 * p.cd * p.af_m2 / 3.6 ** 2
    assert _close(b_model, ref["B"]), (b_model, ref["B"])


ETA_ATOL = 1e-4  # esdeger verimler: params.py ile yeniden hesap arasindaki mutlak tolerans


def test_p2_tesla_efficiencies():
    """params.py'deki eta_m/eta_reg, [R24] haritasindan WLTC esdeger verimleriyle ayni olmali."""
    from analysis.p2_efficiency import ref_cycle_efficiencies

    eta_m, eta_reg = ref_cycle_efficiencies(TESLA_M3_SRP)
    assert np.isclose(TESLA_M3_SRP.eta_m, eta_m, rtol=0.0, atol=ETA_ATOL), (TESLA_M3_SRP.eta_m, eta_m)
    assert np.isclose(TESLA_M3_SRP.eta_reg, eta_reg, rtol=0.0, atol=ETA_ATOL), \
        (TESLA_M3_SRP.eta_reg, eta_reg)


def test_p2_aux_power():
    """P_aux, [R24] Sekil 8 hesabiyla (en yakin W'a yuvarlanmis) tutarli olmali."""
    from analysis.p2_efficiency import aux_power_from_r24
    from evmodel.cycles import load_cycle

    p_aux = aux_power_from_r24(*load_cycle("WLTC_3b"))["P_aux_W"]
    assert abs(TESLA_M3_SRP.p_aux_w - p_aux) <= 0.5, (TESLA_M3_SRP.p_aux_w, p_aux)


def test_p2_sourced_info_fields():
    """TESLA_SOURCED'daki bilgi amacli C_d*A_f alanlari turetmeyle tutarli."""
    assert _close(TESLA_SOURCED["cda_equivalent_m2"], method_least_squares()["cda"])
    assert _close(TESLA_SOURCED["cda_physical_m2"], to_model_params(F0, F2)["cda"])
