"""
"20 Kasim - Kendi Modelini Kontrol Et" belgesi: tum satirlar |model/ref - 1| <= %1,
T3 artigi <= %0,1. Ayrintili tablo: python -m analysis.kontrol_20kasim
"""

from analysis.kontrol_20kasim import all_pass, run_all_checks


def test_kontrol_20kasim_hepsi_tutuyor():
    tables = run_all_checks()
    bad = {name: df[df["durum"].astype(str).str.lower().str.startswith("tutmuyor")]
           for name, df in tables.items()}
    bad = {k: v for k, v in bad.items() if not v.empty}
    assert all_pass(tables), bad
