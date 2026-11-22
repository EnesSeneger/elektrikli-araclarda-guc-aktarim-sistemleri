"""
"MKTS5081 · 20 Kasim - Kendi Modelini Kontrol Et" (Cihat, 19.11.2026) belgesinin tamamini
modelle otomatik karsilastirir. Belge: Temel Arac + WLTC 3b; kabul olcutu
|model / referans - 1| <= %1 (T3 artigi icin |artik| <= %0,1).

Bolumler (belgedeki sirayla):
  1 kontrol tablosu   : T4, T1, T1b, T2, WLTC 3b ozetleri (E, Wh/km, rho_reg, tepeler, SoC, menzil,
                        7 km/h alti fren suresi, tepe T_w / T_m / n_m)
  2 faz sonu          : t = 589, 1022, 1477, 1800 s'de kumulatif E ve km
  3 kontrol saniyeleri: t = 18, 96, 100, 796, 1542, 1682 s satirlari (v, a, F, P_w, P_tr, P_bat, E, km)
  4 T3 kalemleri      : enerji dengesi kalemleri (Wh)
  5 sert fren testi   : v = 100 - 25 t km/h, t = 0..4 s
  + ogrenci_kontrol.py ciktisi (belgenin betigiyle ayni bicim)

Referans degerler belgeden aynen alinmistir (REF_* sabitleri). Model kodu degistirilmez.
Calistirma:  python -m analysis.kontrol_20kasim
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evmodel.cycles import cycle_distance_km, load_cycle  # noqa: E402
from evmodel.model import simulate  # noqa: E402
from evmodel.params import BASE_VEHICLE  # noqa: E402

TABLES = ROOT / "results" / "tables"
CYCLE = "WLTC_3b"
TOL = 0.01            # belge: |sizin / referans - 1| <= 0,01
T3_TOL = 0.001        # T3 artigi: %0,1
ZERO_ABS = {"a": 0.0015, "F": 0.15, "P": 0.006}  # referansi 0 olan hucreler icin mutlak tolerans
                                                  # (belgedeki yuvarlamanin yarisi)

# --- 1. Kontrol tablosu (belge s. 1-2) ---
REF_TABLE = [
    # (adim, kontrol, referans)
    ("1 · Veri", "T4 · WLTC 3b mesafesi [km]", 23.266),
    ("2 · Sabit hız", "T1 · F [N] (90 km/h)", 451.5),
    ("2 · Sabit hız", "T1 · F_aero [N]", 257.3),
    ("2 · Sabit hız", "T1 · F_roll [N]", 194.2),
    ("2 · Sabit hız", "T1 · P_bat [kW]", 12.91),
    ("2 · Sabit hız", "T1 · tüketim [Wh/km] (P_aux = 0)", 143.49),
    ("2 · Sabit hız", "T1b · tüketim [Wh/km] (P_aux = 400 W)", 147.94),
    ("2 · Sabit hız", "T1b − T1 [Wh/km]", 4.44),
    ("3 · İvmelenme", "T2 · a [m/s²]", 1.389),
    ("3 · İvmelenme", "T2 · P_bat(t = 10 s) [kW]", 46.06),
    ("3 · İvmelenme", "T2 · E [Wh] (yamuk integral)", 63.10),
    ("3 · İvmelenme", "T2 · E [Wh] (Δt = 1 s sağ uç toplam)", 69.51),
    ("4 · WLTC 3b", "Σ E_bat [Wh]", 3633.5),
    ("4 · WLTC 3b", "tüketim [Wh/km]", 156.17),
    ("4 · WLTC 3b", "ρ_reg [%] (P_tr ile)", 19.62),
    ("4 · WLTC 3b", "ρ_reg [%] (P_bat ile)", 17.94),
    ("4 · WLTC 3b", "en büyük P_bat [kW]", 55.33),
    ("4 · WLTC 3b", "en büyük P_bat zamanı [s]", 1542),
    ("4 · WLTC 3b", "en büyük geri kazanım P_tr [kW]", -28.14),
    ("4 · WLTC 3b", "en büyük geri kazanım zamanı [s]", 796),
    ("4 · WLTC 3b", "7 km/h altı frenleme [s]", 21),
    ("4 · WLTC 3b", "döngü sonu SoC [%]", 83.94),
    ("4 · WLTC 3b", "menzil [km]", 307.4),
    ("4 · WLTC 3b", "en büyük T_w [N·m]", 1053.9),
    ("4 · WLTC 3b", "en büyük T_m [N·m]", 123.3),
    ("4 · WLTC 3b", "en büyük n_m [d/dk]", 9499),
    ("4 · WLTC 3b", "P_reg,max sınırlanan adım", 0),
]

# --- 2. Faz sonu kumulatifleri (belge s. 2): faz -> (son saniye, Sigma E Wh, Sigma km) ---
REF_PHASES = {"Düşük": (589, 388.9, 3.095), "Orta": (1022, 1005.5, 7.850),
              "Yüksek": (1477, 2020.8, 15.012), "Çok yüksek": (1800, 3633.5, 23.266)}

# --- 3. Alti kontrol saniyesi (belge s. 2-3) ---
CHECK_COLS = ["v_kmh", "a", "F", "P_w_kW", "P_tr_kW", "P_bat_kW", "E_Wh", "km"]
REF_SECONDS = {
    18: ("şehir içi hızlanma", 21.7, 1.264, 2597.9, 15.66, 17.92, 18.32, 16.4, 0.019),
    96: ("7 km/h altı fren", 5.8, -0.764, -1248.4, -2.01, 0.00, 0.40, 75.8, 0.612),
    100: ("durma", 0.0, 0.000, 0.0, 0.00, 0.00, 0.40, 76.3, 0.614),
    796: ("en büyük geri kazanım", 54.6, -1.444, -2441.1, -37.02, -28.14, -27.74, 707.9, 5.149),
    1542: ("en büyük çekiş", 81.8, 0.903, 2113.0, 48.01, 54.93, 55.33, 2288.9, 15.919),
    1682: ("yüksek hızda seyir", 125.6, -0.014, 669.0, 23.34, 26.71, 27.11, 3350.8, 20.283),
}

# --- 4. T3 kalemleri (belge s. 3-4), Wh ---
REF_T3 = {
    "Çekişte bataryadan": 4271.2, "Tekerleğe verilen (Σ E_w+)": 3733.0, "Çekiş kaybı": 538.2,
    "Aerodinamik iş": 1369.5, "Yuvarlanma işi": 1255.3,
    "Frenlemede tekerlekten (−Σ E_w−)": 1108.2, "Bataryaya dönen": 837.9,
    "Rejenerasyon kaybı": 264.6, "Sürtünme freni (7 km/h altı)": 5.8,
    "Yardımcı yük (400 W × 1801 s)": 200.1, "Tekerlek net (aero + yuvarlanma)": 2624.8,
    "Σ E_bat": 3633.5,
}

# --- 5. Sert fren testi (belge s. 5): v = 100 - 25 t, t = 0..4 s ---
BRAKE_V0_KMH, BRAKE_DECEL_KMH_S, BRAKE_T_END_S = 100.0, 25.0, 4.0
REF_BRAKE = {"P_tr_kW (t=0-3 s)": -60.0, "P_bat_kW (t=0-3 s)": -59.6,
             "P_tr_kW (t=4 s)": 0.0, "P_bat_kW (t=4 s)": 0.4}

# T1/T2 profilleri (odev Bolum 2)
T1_V_KMH, T1_DUR_S = 90.0, 3600
T2_V_END_KMH, T2_DUR_S = 50.0, 10


def _status(model: float, ref: float, abs_tol: float | None = None) -> tuple[float, str]:
    if ref == 0:
        dev = np.nan
        ok = abs(model) <= (abs_tol if abs_tol is not None else 1e-9)
    else:
        dev = (model / ref - 1) * 100
        ok = abs(model / ref - 1) <= TOL
    return dev, "tutuyor" if ok else "TUTMUYOR"


def _profile_const(v_kmh: float, dur_s: int):
    t = np.arange(dur_s + 1, dtype=float)
    return t, np.full_like(t, v_kmh)


def _profile_ramp(v_end_kmh: float, dur_s: int):
    t = np.arange(dur_s + 1, dtype=float)
    return t, v_end_kmh * t / dur_s


def model_values() -> dict:
    """Belgedeki tum buyuklukler, modelden (Temel Arac)."""
    p = BASE_VEHICLE
    t1, v1 = _profile_const(T1_V_KMH, T1_DUR_S)
    r1 = simulate(t1, v1, p.with_(p_aux_w=0.0))
    r1b = simulate(t1, v1, p)
    t2, v2 = _profile_ramp(T2_V_END_KMH, T2_DUR_S)
    r2 = simulate(t2, v2, p.with_(p_aux_w=0.0))
    t, v = load_cycle(CYCLE)
    r = simulate(t, v, p)
    mid = len(t1) // 2
    dt_h = float(t[1] - t[0]) / 3600.0
    e_pos = r.p_trac_w[r.p_trac_w > 0].sum() * dt_h
    e_neg = -r.p_trac_w[r.p_trac_w < 0].sum() * dt_h
    e_bat_pos = r.p_bat_w[r.p_bat_w > 0].sum() * dt_h
    e_bat_neg = -r.p_bat_w[r.p_bat_w < 0].sum() * dt_h
    low_brake = (r.v_ms < p.v_min_ms) & (r.p_w_w < 0)
    t_w = r.f_trac_n * p.rw_m
    i_pmax, i_reg = int(np.argmax(r.p_bat_w)), int(np.argmin(r.p_trac_w))
    return {
        "r": r, "p": p,
        "T4 · WLTC 3b mesafesi [km]": cycle_distance_km(v),
        "T1 · F [N] (90 km/h)": r1.f_trac_n[mid],
        "T1 · F_aero [N]": r1.f_aero_n[mid],
        "T1 · F_roll [N]": r1.f_roll_n[mid],
        "T1 · P_bat [kW]": r1.p_bat_w[mid] / 1e3,
        "T1 · tüketim [Wh/km] (P_aux = 0)": r1.consumption_wh_km,
        "T1b · tüketim [Wh/km] (P_aux = 400 W)": r1b.consumption_wh_km,
        "T1b − T1 [Wh/km]": r1b.consumption_wh_km - r1.consumption_wh_km,
        "T2 · a [m/s²]": r2.a_ms2[T2_DUR_S // 2],
        "T2 · P_bat(t = 10 s) [kW]": r2.p_bat_w[-1] / 1e3,
        "T2 · E [Wh] (yamuk integral)": np.trapezoid(r2.p_bat_w, r2.t_s) / 3600.0,
        "T2 · E [Wh] (Δt = 1 s sağ uç toplam)": r2.e_bat_wh,
        "Σ E_bat [Wh]": r.e_bat_wh,
        "tüketim [Wh/km]": r.consumption_wh_km,
        "ρ_reg [%] (P_tr ile)": r.regen_share * 100,
        "ρ_reg [%] (P_bat ile)": e_bat_neg / e_bat_pos * 100,
        "en büyük P_bat [kW]": r.p_bat_w[i_pmax] / 1e3,
        "en büyük P_bat zamanı [s]": r.t_s[i_pmax],
        "en büyük geri kazanım P_tr [kW]": r.p_trac_w[i_reg] / 1e3,
        "en büyük geri kazanım zamanı [s]": r.t_s[i_reg],
        "7 km/h altı frenleme [s]": float(low_brake.sum()),
        "döngü sonu SoC [%]": r.soc_pct[-1],
        "menzil [km]": r.range_km,
        "en büyük T_w [N·m]": float(t_w.max()),
        "en büyük T_m [N·m]": float(r.t_m_nm.max()),
        "en büyük n_m [d/dk]": float(r.n_m_rpm.max()),
        "P_reg,max sınırlanan adım": float(r.n_reg_limited),
        "_e_pos": e_pos, "_e_neg": e_neg,
    }


def control_table(m: dict) -> pd.DataFrame:
    rows = []
    for step, name, ref in REF_TABLE:
        dev, st = _status(m[name], ref)
        rows.append({"adim": step, "kontrol": name, "referans": ref, "model": m[name],
                     "fark_pct": dev, "durum": st})
    return pd.DataFrame(rows)


def phase_table(r) -> pd.DataFrame:
    e_cum = np.cumsum(r.e_step_wh)
    km_cum = np.cumsum(r.v_ms) * float(r.t_s[1] - r.t_s[0]) / 1000.0
    rows = []
    for ph, (t_end, e_ref, km_ref) in REF_PHASES.items():
        k = int(np.where(r.t_s == t_end)[0][0])
        de, se = _status(e_cum[k], e_ref)
        dk, sk = _status(km_cum[k], km_ref)
        rows.append({"faz": ph, "t_son_s": t_end, "E_ref_Wh": e_ref, "E_model_Wh": e_cum[k],
                     "E_fark_pct": de, "km_ref": km_ref, "km_model": km_cum[k], "km_fark_pct": dk,
                     "durum": "tutuyor" if se == sk == "tutuyor" else "TUTMUYOR"})
    return pd.DataFrame(rows)


def seconds_table(r) -> pd.DataFrame:
    e_cum = np.cumsum(r.e_step_wh)
    km_cum = np.cumsum(r.v_ms) * float(r.t_s[1] - r.t_s[0]) / 1000.0
    rows = []
    for ts, (desc, *ref) in REF_SECONDS.items():
        k = int(np.where(r.t_s == ts)[0][0])
        mod = [r.v_ms[k] * 3.6, r.a_ms2[k], r.f_trac_n[k], r.p_w_w[k] / 1e3, r.p_trac_w[k] / 1e3,
               r.p_bat_w[k] / 1e3, e_cum[k], km_cum[k]]
        first_bad = ""
        for col, mv, rv in zip(CHECK_COLS, mod, ref):
            kind = "a" if col == "a" else ("F" if col == "F" else "P")
            _, st = _status(mv, rv, ZERO_ABS[kind])
            if st != "tutuyor" and not first_bad:
                first_bad = col
        row = {"t_s": ts, "durum_aciklama": desc}
        for col, mv, rv in zip(CHECK_COLS, mod, ref):
            row[f"{col}_ref"], row[f"{col}_model"] = rv, mv
        row["ilk_tutmayan_sutun"] = first_bad or "—"
        row["durum"] = "tutuyor" if not first_bad else "TUTMUYOR"
        rows.append(row)
    return pd.DataFrame(rows)


def t3_table(m: dict) -> pd.DataFrame:
    r, p = m["r"], m["p"]
    e = r.energy_wh
    loss_trac = e["kayip_aktarma"] + e["kayip_motor_cekis"] - (
        e["kayip_aktarma"] - e["E_tekerlek_cekis"] * (1 / p.eta_t - 1))  # yalniz cekis tarafi
    loss_regen_side = e["kayip_rejen"] + (e["kayip_aktarma"]
                                          - e["E_tekerlek_cekis"] * (1 / p.eta_t - 1))
    mod = {
        "Çekişte bataryadan": m["_e_pos"],
        "Tekerleğe verilen (Σ E_w+)": e["E_tekerlek_cekis"],
        "Çekiş kaybı": loss_trac,
        "Aerodinamik iş": e["E_aero"],
        "Yuvarlanma işi": e["E_roll"],
        "Frenlemede tekerlekten (−Σ E_w−)": -e["E_tekerlek_fren"],
        "Bataryaya dönen": m["_e_neg"],
        "Rejenerasyon kaybı": loss_regen_side,
        "Sürtünme freni (7 km/h altı)": e["kayip_surtunmeli_fren"],
        "Yardımcı yük (400 W × 1801 s)": e["E_aux"],
        "Tekerlek net (aero + yuvarlanma)": e["E_aero"] + e["E_roll"],
        "Σ E_bat": e["E_bat"],
    }
    rows = []
    for k, ref in REF_T3.items():
        dev, st = _status(mod[k], ref)
        rows.append({"kalem": k, "referans_Wh": ref, "model_Wh": mod[k], "fark_pct": dev,
                     "durum": st})
    df = pd.DataFrame(rows)
    # Saglama (belge): tekerlek net + cekis kaybi + rejen kaybi + surtunme + yardimci = E_bat
    resid = (mod["Σ E_bat"] - (mod["Tekerlek net (aero + yuvarlanma)"] + mod["Çekiş kaybı"]
                               + mod["Rejenerasyon kaybı"] + mod["Sürtünme freni (7 km/h altı)"]
                               + mod["Yardımcı yük (400 W × 1801 s)"] + e["E_inertia"]))
    df.attrs["artik_Wh"] = resid
    return df


def brake_test() -> pd.DataFrame:
    t = np.arange(0, BRAKE_T_END_S + 1, dtype=float)
    v = BRAKE_V0_KMH - BRAKE_DECEL_KMH_S * t
    r = simulate(t, v, BASE_VEHICLE)
    mod = {"P_tr_kW (t=0-3 s)": r.p_trac_w[:-1] / 1e3, "P_bat_kW (t=0-3 s)": r.p_bat_w[:-1] / 1e3,
           "P_tr_kW (t=4 s)": np.array([r.p_trac_w[-1] / 1e3]),
           "P_bat_kW (t=4 s)": np.array([r.p_bat_w[-1] / 1e3])}
    rows = []
    for k, ref in REF_BRAKE.items():
        vals = mod[k]
        worst = vals[np.argmax(np.abs(vals - ref))]
        _, st = _status(float(worst), ref, ZERO_ABS["P"])
        rows.append({"kontrol": k, "referans_kW": ref, "model_kW": ", ".join(f"{x:.2f}" for x in vals),
                     "durum": st})
    return pd.DataFrame(rows)


def ogrenci_kontrol(m: dict, phases: pd.DataFrame, resid_wh: float) -> pd.DataFrame:
    """Belgedeki ogrenci_kontrol.py betiginin ayni karsilastirmasi (benim = model)."""
    benim = {"T4_WLTC_km": m["T4 · WLTC 3b mesafesi [km]"],
             "T1_Whkm": m["T1 · tüketim [Wh/km] (P_aux = 0)"],
             "T1b_Whkm": m["T1b · tüketim [Wh/km] (P_aux = 400 W)"],
             "T2_Wh": m["T2 · E [Wh] (yamuk integral)"],
             "WLTC_Wh": m["Σ E_bat [Wh]"], "WLTC_Whkm": m["tüketim [Wh/km]"],
             "rho_reg_yuzde": m["ρ_reg [%] (P_tr ile)"],
             "faz_SigmaE_Wh": list(phases["E_model_Wh"])}
    ref = {"T4_WLTC_km": 23.266, "T1_Whkm": 143.49, "T1b_Whkm": 147.94, "T2_Wh": 63.10,
           "WLTC_Wh": 3633.5, "WLTC_Whkm": 156.17, "rho_reg_yuzde": 19.62,
           "faz_SigmaE_Wh": [388.9, 1005.5, 2020.8, 3633.5]}
    rows = []
    for ad, r_all in ref.items():
        x_all = benim[ad]
        if not isinstance(r_all, list):
            r_all, x_all = [r_all], [x_all]
        for j, (x, r) in enumerate(zip(x_all, r_all)):
            label = f"{ad}({j + 1})" if len(r_all) > 1 else ad
            rows.append({"Kontrol": label, "sizin": x, "referans": r,
                         "durum": "tutuyor" if abs(x / r - 1) <= TOL
                         else f"tutmuyor ({100 * (x / r - 1):+.1f} %)"})
    rows.append({"Kontrol": "T3_artik_Wh", "sizin": resid_wh, "referans": 0.0,
                 "durum": "tutuyor (|artık| ≤ %0,1)" if abs(resid_wh) <= T3_TOL * 3633.5
                 else f"tutmuyor: {resid_wh:.1f} Wh"})
    return pd.DataFrame(rows)


def run_all_checks() -> dict:
    m = model_values()
    phases = phase_table(m["r"])
    t3 = t3_table(m)
    return {"kontrol_tablosu": control_table(m), "faz_sonu": phases,
            "kontrol_saniyeleri": seconds_table(m["r"]), "t3_kalemleri": t3,
            "sert_fren": brake_test(),
            "ogrenci_kontrol": ogrenci_kontrol(m, phases, t3.attrs["artik_Wh"])}


def all_pass(tables: dict) -> bool:
    return all((~df["durum"].astype(str).str.startswith(("TUTMUYOR", "tutmuyor"))).all()
               for df in tables.values())


def main() -> dict:
    tables = run_all_checks()
    TABLES.mkdir(parents=True, exist_ok=True)
    with pd.option_context("display.width", 250, "display.max_columns", 40):
        for name, df in tables.items():
            df.to_csv(TABLES / f"kontrol20_{name}.csv", index=False)
            print(f"\nkontrol20 · {name}:\n" + df.round(4).to_string(index=False))
    n_rows = sum(len(df) for df in tables.values())
    print(f"\n20 Kasım kontrolü: {n_rows} satır · "
          + ("HEPSİ TUTUYOR" if all_pass(tables) else "TUTMAYAN SATIR VAR"))
    return tables


if __name__ == "__main__":
    main()
