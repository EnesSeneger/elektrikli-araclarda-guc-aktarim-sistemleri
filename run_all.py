"""
Tek komutla calistirma:  python run_all.py

Sira: (1) T4 veri kontrolu  (2) T1-T4 dogrulama testleri + rapor tablosu
      (2b) PNG grafikleri   (3) analiz scriptleri (3A, 3B, 3C - hazir olanlar)
pytest kurulu olmasa da calisir (test fonksiyonlarini dogrudan cagirir).
Grafikleri atlamak icin:  python run_all.py --no-figures
"""

import argparse
import importlib
import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from evmodel.cycles import cycle_summary  # noqa: E402

TABLES = ROOT / "results" / "tables"
SANKEY_PNG_CYCLES = ["WLTC_3b", "US06"]  # rapor icin Sankey PNG'si uretilen donguler
TABLES.mkdir(parents=True, exist_ok=True)


def run_tests() -> bool:
    """tests/ altindaki test_* fonksiyonlarini calistirir."""
    ok = True
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        mod = importlib.import_module(f"tests.{path.stem}")
        for name in sorted(n for n in dir(mod) if n.startswith("test_")):
            try:
                getattr(mod, name)()
                print(f"  GECTI   {path.stem}::{name}")
            except KeyboardInterrupt:
                raise
            except BaseException as err:  # pytest.skip Exception'dan turemez
                if type(err).__name__ in ("Skipped", "SkipTest"):
                    print(f"  ATLANDI {path.stem}::{name} ({err})")
                    continue
                ok = False
                print(f"  KALDI   {path.stem}::{name}")
                traceback.print_exc()
    return ok


def validation_table() -> pd.DataFrame:
    """Rapordaki dogrulama tablosu: test | beklenen | model | sapma."""
    from tests.test_t1_t2 import run_t1, run_t2
    from tests.test_t3_balance import balance_residuals
    from evmodel.cycles import CYCLE_NAMES

    r1, r1b, r2 = run_t1(0.0), run_t1(400.0), run_t2()
    e2_trapz = np.trapezoid(r2.p_bat_w, r2.t_s) / 3600.0
    rows = [
        ("T1 tuketim [Wh/km]", 143.5, r1.consumption_wh_km),
        ("T1 F_trac [N]", 451.5, r1.f_trac_n[1800]),
        ("T1 P_bat [kW]", 12.9, r1.p_bat_w[1800] / 1e3),
        ("T1b tuketim [Wh/km]", 147.9, r1b.consumption_wh_km),
        ("T2 E_bat yamuk [Wh]", 63.1, e2_trapz),
        ("T2 E_bat dikdortgen [Wh] (bilgi)", np.nan, r2.e_bat_wh),
        ("T2 P_bat(10 s) [kW]", 46.1, r2.p_bat_w[-1] / 1e3),
    ]
    df = pd.DataFrame(rows, columns=["test", "beklenen", "model"])
    df["sapma_pct"] = (df["model"] - df["beklenen"]) / df["beklenen"] * 100

    t3 = pd.DataFrame([balance_residuals(n) for n in CYCLE_NAMES])
    return df.round(4), t3  # T3 artiklari ~1e-15: yuvarlanmadan bilimsel gosterim

def make_figures() -> None:
    """Dongu hiz grafikleri + Temel Arac batarya gucu grafikleri."""
    from evmodel.cycles import load_all_cycles
    from evmodel.model import simulate
    from evmodel.params import BASE_VEHICLE
    from evmodel.plotting import plot_power_profiles, plot_speed_profiles

    cycles = load_all_cycles()
    print("  ", plot_speed_profiles(cycles))

    results = {name: simulate(t, v, BASE_VEHICLE) for name, (t, v) in cycles.items()}
    p_reg = BASE_VEHICLE.p_reg_max_w
    print("  ", plot_power_profiles(results, p_reg, 200, "guc_zaman_ilk200s_temel_arac"))
    print("  ", plot_power_profiles(results, p_reg, None, "guc_zaman_tum_temel_arac"))
    from evmodel.plotting import plot_wltc_check
    print("  ", plot_wltc_check(results["WLTC_3b"], "kontrol20_wltc3b_temel_arac"))

    # Rapor gorselleri: dogrulama karnesi, 3A ozeti, WLTP selalesi, 3B senaryolari
    from analysis import a3_cycles as a3, b3_sensitivity as b3
    from analysis.kontrol_20kasim import TOL, run_all_checks
    from evmodel.cycles import load_cycle
    from evmodel.params import TESLA_M3_SRP, TESLA_SOURCED
    from evmodel.plotting import (plot_a3_summary, plot_b3_scenarios, plot_validation_scorecard,
                                  plot_wltp_waterfall)
    t12, _ = validation_table()
    chk = run_all_checks()["kontrol_tablosu"]
    rows = [(r["test"], r["sapma_pct"]) for _, r in t12.dropna().iterrows()]
    rows += [(f"20 Kasım · {r['kontrol']}", r["fark_pct"]) for _, r in chk.iloc[12:].iterrows()
             if np.isfinite(r["fark_pct"]) and "zamanı" not in r["kontrol"]]
    print("  ", plot_validation_scorecard(rows, TOL * 100, "dogrulama_karnesi"))
    tesla_res = {n: simulate(t, v, TESLA_M3_SRP) for n, (t, v) in cycles.items()}
    ct = a3.cycle_table(tesla_res, TESLA_M3_SRP)
    cc = a3.CYCLE_COLS
    print("  ", plot_a3_summary(ct, "a3_tuketim_menzil", cc["range"], cc["cons"], cc["cycle"]))
    print("  ", plot_wltp_waterfall(a3.wltp_chain(tesla_res[a3.WLTP_CYCLE].consumption_wh_km),
                                    "a3_wltp_selale"))
    b3_tabs = {c: b3.scenario_table(*load_cycle(c)) for c in b3.CYCLES_3B}
    print("  ", plot_b3_scenarios(b3_tabs, "b3_senaryolar", b3.SCENARIO_COLS["scenario"],
                                  b3.SCENARIO_COLS["cons_change"]))

    # 3A (Tesla): enerji dagilimi Wh/km ve batarya gucu ilk 200 s
    from analysis.a3_cycles import energy_flows
    from evmodel.params import TESLA_M3_SRP
    from evmodel.plotting import plot_energy_breakdown

    tesla = {name: simulate(t, v, TESLA_M3_SRP) for name, (t, v) in cycles.items()}
    flows = {name: energy_flows(r, TESLA_M3_SRP) for name, r in tesla.items()}
    print("  ", plot_energy_breakdown(
        flows, "enerji_dagilimi_tesla_Whkm",
        "Tesla Model 3 SR+ – enerji dağılımı [Wh/km]: brüt çekilen, geri kazanılan ve net"))
    print("  ", plot_power_profiles(tesla, TESLA_M3_SRP.p_reg_max_w, 200,
                                    "guc_zaman_ilk200s_tesla"))

    # 3A (Tesla): enerji akis (Sankey) diyagramlari - Plotly + kaleido (yoksa atlanir)
    from evmodel.interactive import fig_energy_sankey
    from evmodel.plotting import save_plotly_png

    for cyc in SANKEY_PNG_CYCLES:
        path = save_plotly_png(fig_energy_sankey(flows[cyc], cyc, per_km=True),
                               f"sankey_tesla_{cyc}")
        if path is not None:
            print("  ", path)
def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="T4 + T1-T4 testleri + grafikler + analizler")
    parser.add_argument("--no-figures", action="store_true",
                        help="results/figures altindaki PNG grafiklerini uretme (hizli calistirma)")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    print("=" * 70, "\n(1) T4 - dongu mesafeleri\n", "=" * 70, sep="")
    t4 = cycle_summary()
    print(t4.to_string(index=False))
    t4.to_csv(TABLES / "t4_dongu_mesafeleri.csv", index=False)

    print("=" * 70, "\n(2) Dogrulama testleri\n", "=" * 70, sep="")
    ok = run_tests()
    t12, t3 = validation_table()
    print("\nT1/T2 tablosu:\n" + t12.to_string(index=False))
    print("\nT3 enerji dengesi (Temel Arac):\n" + t3.to_string(index=False))
    t12.to_csv(TABLES / "t1_t2_dogrulama.csv", index=False)
    t3.to_csv(TABLES / "t3_enerji_dengesi.csv", index=False)
    if not ok:
        print("\nDogrulama basarisiz -> analizler calistirilmadi.")
        return 1
    print("=" * 70, "\n(2b) Grafikler\n", "=" * 70, sep="")
    if args.no_figures:
        print("  ATLANDI (--no-figures)")
    else:
        make_figures()
    print("=" * 70, "\n(3) Analizler\n", "=" * 70, sep="")
    for script in ["kontrol_20kasim", "p2_road_load", "p2_efficiency", "a3_cycles",
                   "b3_sensitivity", "c3_bonus"]:
        mod = importlib.import_module(f"analysis.{script}")
        if script in ("p2_road_load", "c3_bonus"):
            mod.main(figures=not args.no_figures)  # tablo + PNG
        elif hasattr(mod, "main"):
            mod.main()
        else:
            print(f"  TODO    analysis/{script}.py henuz yazilmadi")
    print("\nTamam. Tablolar: results/tables/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
