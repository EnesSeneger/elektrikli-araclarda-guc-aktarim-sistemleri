"""
T4 - Dongu mesafesi: Excel'den okunan her dongu icin sum(v_kmh)/3600 referansla
%1 icinde olmali (model calistirilmadan once yapilan veri kontrolu).
"""

from evmodel.cycles import CYCLE_NAMES, REFERENCE_DISTANCES_KM, cycle_distance_km, load_cycle


def test_t4_cycle_distances():
    for name in CYCLE_NAMES:
        _, v = load_cycle(name)
        s = cycle_distance_km(v)
        ref = REFERENCE_DISTANCES_KM[name]
        assert abs(s - ref) / ref < 0.01, f"{name}: {s:.3f} km, referans {ref} km"
