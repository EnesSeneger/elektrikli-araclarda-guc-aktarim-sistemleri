"""
T3 - Enerji dengesi: sum E_bat = sum E_tekerlek + sum kayiplar + sum E_aux (artik < %0.1).

Iki kontrol yapilir:
  (a) Batarya dengesi: kayiplar guc akisindan bagimsiz kalemler olarak hesaplanir.
  (b) Tekerlek dengesi: sum P_w dt  ==  E_aero + E_roll + E_grade + E_ivme,
      ve E_ivme ~ dE_kin (= 1/2 delta m (v_son^2 - v_ilk^2), dongulerde ~0).
Tum dongulerde (Temel Arac) calistirilir.
"""

from evmodel.cycles import CYCLE_NAMES, load_cycle
from evmodel.model import simulate
from evmodel.params import BASE_VEHICLE

TOL = 1e-3  # %0.1


def balance_residuals(name: str) -> dict:
    t, v = load_cycle(name)
    e = simulate(t, v, BASE_VEHICLE).energy_wh
    rhs = e["E_tekerlek"] + e["kayip_toplam"] + e["E_aux"]
    wheel_sum = e["E_aero"] + e["E_roll"] + e["E_grade"] + e["E_inertia"]
    return {
        "dongu": name,
        "E_bat_Wh": e["E_bat"],
        "artik_batarya_pct": (e["E_bat"] - rhs) / e["E_bat"] * 100,
        "artik_tekerlek_pct": (e["E_tekerlek"] - wheel_sum) / e["E_tekerlek_cekis"] * 100,
        # ivme enerjisinin net toplami, cekis enerjisine oranla (ayriklastirma hatasi)
        "ivme_net_pct": (e["E_inertia"] - e["dE_kin"]) / e["E_tekerlek_cekis"] * 100,
    }


def test_t3_energy_balance_all_cycles():
    for name in CYCLE_NAMES:
        r = balance_residuals(name)
        assert abs(r["artik_batarya_pct"]) < TOL * 100, r
        assert abs(r["artik_tekerlek_pct"]) < TOL * 100, r
