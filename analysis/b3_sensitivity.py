"""
3B - Parametre duyarlilik analizi (Temel Arac, WLTC_3b; karsilastirma icin HWFET ve US06).

Her senaryo BASE_VEHICLE.with_(...) ile turetilir [ODEV 3B]:
  Baseline : m=1800, Cd=0.28, E_nom=60
  S1       : m=2160
  S2       : Cd=0.336
  S3       : E_nom=72 ve m=1900
  S4       : P_reg_max=30 kW

Tablo fonksiyonlari hem run_all.py (main) hem web arayuzu (app.py) tarafindan cagrilir.
  scenario_table   : Wh/km, baseline'a gore % degisim, menzil (Soru 1-4)
  phase_energy     : faz basina tepe rejen. gucu, geri kazanim, surtunmeli fren,
                     P_reg siniri, Wh/km (Soru 5)
  phase_comparison : Baseline - S4 karsilastirmasi; WLTC_3b'de faz faz + tum dongu,
                     EPA dongulerinde (faz etiketi yok) yalnizca tum dongu

Faz hesabi yalnizca simulate() zaman serilerinden (p_trac_w, p_w_w, v_ms) yapilir;
faz toplamlari SimResult ozetleriyle birebir tutmali (main icinde kontrol edilir).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evmodel.cycles import load_cycle, load_phases  # noqa: E402
from evmodel.model import simulate  # noqa: E402
from evmodel.params import BASE_VEHICLE, VehicleParams  # noqa: E402

TABLES = ROOT / "results" / "tables"
CYCLES_3B = ["WLTC_3b", "HWFET", "US06"]

# Senaryolar [ODEV 3B]: ad -> (aciklama, BASE_VEHICLE'a uygulanan degisiklikler, SI)
SCENARIOS = {
    "Baseline": ("ödev değerleri", {}),
    "S1": ("m = 2160 kg", {"m_kg": 2160.0}),
    "S2": ("C_d = 0.336", {"cd": 0.336}),
    "S3": ("E_nom = 72 kWh, m = 1900 kg", {"e_nom_kwh": 72.0, "m_kg": 1900.0}),
    "S4": ("P_reg,max = 30 kW", {"p_reg_max_w": 30e3}),
}


# ---------------------------------------------------------------------------
# Tablo sutun adlari: TEK kaynak. app.py ve diger tuketiciler bu sabitleri kullanir,
# sutun adini metin olarak yeniden yazmaz.
# ---------------------------------------------------------------------------
SCENARIO_COLS = {
    "scenario": "senaryo",
    "change": "degisiklik",
    "cons": "tuketim_Wh_km",
    "cons_change": "tuketim_degisim_pct",
    "e_bat": "E_bat_Wh",
    "regen_share": "rejen_payi_pct",
    "limit_steps": "P_reg_sinir_adim",
    "range": "menzil_km",
    "range_change": "menzil_degisim_pct",
}

# Frenleme (faz) tablosu: temel olcutler
PHASE = "faz"
DISTANCE = "mesafe_km"
PEAK_REGEN = "maks_rejen_kW"
P_REG_LIMIT = "P_reg,max_kW"
MARGIN = "esik_payi_kW"
LIMIT_STEPS = "P_reg_sinir_adim"
REGEN = "rejen_geri_kazanim_Wh"
FRICTION = "surtunmeli_fren_Wh"
CONS = "tuketim_Wh_km"
WHOLE_CYCLE = "TÜM DÖNGÜ"  # faz etiketi olmayan donguler ve toplam satiri (ekranda gorunur)
BRAKE_METRICS = [LIMIT_STEPS, REGEN, FRICTION, CONS]


def col(metric: str, scenario: str) -> str:
    """Senaryoya ait sutun: 'olcut [senaryo]'."""
    return f"{metric} [{scenario}]"


def col_diff(metric: str, a: str, b: str) -> str:
    """Fark sutunu: 'olcut [fark b-a]'."""
    return f"{metric} [fark {b}-{a}]"


def brake_table_columns(a: str = "Baseline", b: str = "S4") -> dict:
    """phase_comparison(a, b) tablosunun sutun adlari (tuketiciler icin)."""
    return {
        "phase": PHASE,
        "distance": DISTANCE,
        "peak_a": col(PEAK_REGEN, a),
        "peak_b": col(PEAK_REGEN, b),
        "limit_a": col(P_REG_LIMIT, a),
        "limit_b": col(P_REG_LIMIT, b),
        "margin": col(MARGIN, b),
        "steps_b": col(LIMIT_STEPS, b),
        "regen_diff": col_diff(REGEN, a, b),
        "friction_diff": col_diff(FRICTION, a, b),
        "cons_diff": col_diff(CONS, a, b),
        "diffs": [col_diff(m, a, b) for m in BRAKE_METRICS],
    }


def scenario_params(name: str, base: VehicleParams = BASE_VEHICLE) -> VehicleParams:
    """Senaryo adindan parametre seti."""
    return base.with_(**SCENARIOS[name][1])


def scenario_table(t_s, v_kmh, base: VehicleParams = BASE_VEHICLE) -> pd.DataFrame:
    """Tum senaryolari ayni dongude calistirir; baseline'a gore % degisim."""
    c = SCENARIO_COLS
    rows = []
    for name, (desc, _) in SCENARIOS.items():
        r = simulate(t_s, v_kmh, scenario_params(name, base))
        rows.append({
            c["scenario"]: name,
            c["change"]: desc,
            c["cons"]: r.consumption_wh_km,
            c["e_bat"]: r.e_bat_wh,
            c["regen_share"]: r.regen_share * 100,
            c["limit_steps"]: r.n_reg_limited,
            c["range"]: r.range_km,
        })
    df = pd.DataFrame(rows)
    b = df.iloc[0]
    df.insert(3, c["cons_change"], (df[c["cons"]] / b[c["cons"]] - 1) * 100)
    df[c["range_change"]] = (df[c["range"]] / b[c["range"]] - 1) * 100
    return df


def _braking_split(r, p: VehicleParams) -> dict:
    """Frenleme adimlari icin zaman serileri (W ve maske), simulate() ciktisindan.

    rejen [W]      : bataryaya donen guc = -P_trac (P_trac < 0 adimlari)
    surtunme [W]   : tekerlekteki frenleme gucunun geri kazanilamayan kismi
                     = -P_w - (-P_trac)/(eta_t eta_reg)   (P_w < 0 adimlari)
    sinir [maske]  : P_reg,max sinirina takilan adimlar (P_trac = -P_reg,max)
    """
    braking = r.p_w_w < 0
    regen_w = np.where(r.p_trac_w < 0, -r.p_trac_w, 0.0)
    friction_w = np.where(braking, -r.p_w_w - regen_w / (p.eta_t * p.eta_reg), 0.0)
    limited = (braking & (r.v_ms >= p.v_min_ms)
               & np.isclose(r.p_trac_w, -p.p_reg_max_w, rtol=0.0, atol=1e-6))
    return {"rejen_w": regen_w, "surtunme_w": friction_w, "sinir": limited}


def phase_energy(r, phases: np.ndarray, p: VehicleParams) -> pd.DataFrame:
    """Faz basina frenleme ozeti (simulate() zaman serilerinden).

    maks_rejen_kW         : fazdaki en buyuk geri kazanim gucu (batarya tarafi, -P_trac)
    rejen_geri_kazanim_Wh : bataryaya donen enerji
    surtunmeli_fren_Wh    : surtunmeli frende kaybolan tekerlek enerjisi
    P_reg_sinir_adim      : P_reg,max sinirina takilan adim sayisi
    tuketim_Wh_km         : faz icindeki E_bat / mesafe
    """
    dt_h = float(r.t_s[1] - r.t_s[0]) / 3600.0
    s = _braking_split(r, p)
    rows = []
    for ph in dict.fromkeys(phases):  # Excel'deki sirayi koru
        m = phases == ph
        dist_km = float(np.sum(r.v_ms[m]) * dt_h * 3.6)
        rows.append({
            PHASE: ph,
            DISTANCE: dist_km,
            PEAK_REGEN: float(s["rejen_w"][m].max() / 1e3),
            LIMIT_STEPS: int(s["sinir"][m].sum()),
            REGEN: float(s["rejen_w"][m].sum() * dt_h),
            FRICTION: float(s["surtunme_w"][m].sum() * dt_h),
            CONS: float(r.e_step_wh[m].sum() / dist_km) if dist_km > 0 else np.nan,
        })
    return pd.DataFrame(rows)


def check_phase_totals(r, df: pd.DataFrame) -> None:
    """Faz toplamlari simulate() ozetleriyle tutmali (hesap ayni kaynaktan mi?)."""
    e_regen = -float(np.sum(r.p_trac_w[r.p_trac_w < 0])) * (r.t_s[1] - r.t_s[0]) / 3600.0
    assert np.isclose(df[REGEN].sum(), e_regen), "faz rejen toplami tutmuyor"
    assert np.isclose(df[FRICTION].sum(), r.energy_wh["kayip_surtunmeli_fren"]), \
        "faz surtunmeli fren toplami tutmuyor"
    assert df[LIMIT_STEPS].sum() == r.n_reg_limited, "faz P_reg siniri toplami tutmuyor"


def phase_comparison(t_s, v_kmh, phases: np.ndarray | None = None, a: str = "Baseline",
                     b: str = "S4", base: VehicleParams = BASE_VEHICLE) -> pd.DataFrame:
    """Iki senaryonun frenleme ozetini faz faz (varsa) ve tum dongu icin yan yana koyar.

    Sutunlar:
      maks_rejen_kW [a], [b]   : faz tepe geri kazanim gucu
      P_reg,max_kW [a], [b]    : senaryolarin sinir degeri
      esik_payi_kW [b]         : P_reg,max[b] - maks_rejen[a]; > 0 ise b'nin siniri bu fazda
                                 hic devreye girmez (a sinirsiz kaldigi surece talep = maks_rejen[a])
      <olcut> [a], [b], [fark b-a] : BRAKE_METRICS icin
    phases None ise (EPA donguleri) yalnizca TUM DONGU satiri uretilir.
    """
    sims = {}
    for name in (a, b):
        p = scenario_params(name, base)
        sims[name] = (p, simulate(t_s, v_kmh, p))

    labelsets = [np.full(len(t_s), WHOLE_CYCLE, dtype=object)]
    if phases is not None:
        labelsets.insert(0, phases)
    blocks = []
    for labels in labelsets:
        per = {}
        for name, (p, r) in sims.items():
            df = phase_energy(r, labels, p)
            check_phase_totals(r, df)
            per[name] = df.set_index(PHASE)
        out = pd.DataFrame({PHASE: per[a].index, DISTANCE: per[a][DISTANCE].to_numpy()})
        for name in (a, b):
            out[col(PEAK_REGEN, name)] = per[name][PEAK_REGEN].to_numpy()
        for name in (a, b):
            out[col(P_REG_LIMIT, name)] = sims[name][0].p_reg_max_w / 1e3
        out[col(MARGIN, b)] = out[col(P_REG_LIMIT, b)] - out[col(PEAK_REGEN, a)]
        for metric in BRAKE_METRICS:
            out[col(metric, a)] = per[a][metric].to_numpy()
            out[col(metric, b)] = per[b][metric].to_numpy()
            out[col_diff(metric, a, b)] = out[col(metric, b)] - out[col(metric, a)]
        blocks.append(out)
    return pd.concat(blocks, ignore_index=True)


def main() -> dict:
    """3B tablolarini hesaplar, results/tables altina CSV yazar ve dondurur."""
    tables = {}
    for cyc in CYCLES_3B:
        t, v = load_cycle(cyc)
        tables[f"b3_senaryolar_{cyc}"] = scenario_table(t, v)
        tables[f"b3_frenleme_baseline_S4_{cyc}"] = phase_comparison(t, v, load_phases(cyc))

    TABLES.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(TABLES / f"{name}.csv", index=False)
        # frenleme tablolari genis: ekranda fazlar sutun olacak sekilde devrik yazilir
        is_brake = PHASE in df.columns
        shown = df.set_index(PHASE).T if is_brake else df
        print(f"\n{name}:\n" + shown.round(3).to_string(index=is_brake))
    return tables


if __name__ == "__main__":
    main()
