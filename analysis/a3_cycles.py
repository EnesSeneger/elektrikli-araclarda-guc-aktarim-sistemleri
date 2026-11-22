"""
3A - Surus dongusu analizi (gercek arac: Tesla Model 3 SR+).

Donguler: WLTC_3b, NEDC, UDDS, HWFET, US06 (Excel sayfalari). CLTC-P kullanilmiyor.

Tablo fonksiyonlari hem run_all.py (main) hem web arayuzu (app.py) tarafindan
cagrilir; boylece ayni sayilar iki yerde de gorunur.

  cycle_table          : dongu basina mesafe, ort. hiz, Wh/km, rejen. payi, P_reg siniri,
                         zarf disi adim, menzil (SoC_0->SoC_min ve tam batarya 100->0)
  energy_flows         : enerji akisi (cubuk grafik + Sankey ortak kaynagi, dengeler assert'li)
  energy_flow_table    : enerji akisi tablosu, Wh/km ve brut cekilene gore %
  q1_wheel_shares      : Soru 1 - cekis adimlarinda tekerlek enerjisi paylari, geri kazanim,
                         surtunmeli fren, ivmelenme enerjisinin geri kazanilan orani
  q2_peak_power        : Soru 2 - tepe cekis / rejenerasyon gucu, P_reg,max'a pay
  q2_phase_peaks       : Soru 2 - WLTC_3b ve NEDC faz bazinda tepe rejenerasyon gucu
  wltp_chain_table     : WLTP karsilastirma zinciri: batarya uc tarafi -> + batarya ic
                         kayiplari -> / eta_sarj -> sebeke tarafi -> resmi WLTP
  wltp_band_table      : eta_sarj belirsizlik bandi
  wltp_sensitivity     : kalan fark icin duyarlilik (Soru 4)

main() Tesla parametreleri eksikse (params.py'de None) tablo URETMEZ; eksikleri listeler.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evmodel.cycles import cycle_summary, load_all_cycles, load_phases  # noqa: E402
from evmodel.model import simulate  # noqa: E402
from evmodel.params import KMH, TESLA_M3_SRP, TESLA_SOURCED, VehicleParams  # noqa: E402

TABLES = ROOT / "results" / "tables"
WLTP_CYCLE = "WLTC_3b"
PHASE_CYCLES = ["WLTC_3b", "NEDC"]   # faz etiketi olan donguler (Soru 2 faz tablosu)

# WLTP zinciri girdileri (hepsi TESLA_SOURCED'dan; kaynaklar docs/kaynaklar.md)
ETA_CHARGE = TESLA_SOURCED["eta_charge_ac11"]                      # [ADAC26] Model Y, 11 kW
ETA_CHARGE_RANGE = TESLA_SOURCED["eta_charge_ac11_range"]          # [ADAC26] bes arac
BATT_LOSS_SHARE = TESLA_SOURCED["r24_fig8_wltp_shares"]["batarya"]  # [R24] Sekil 8, s. 16
WLTP_OFFICIAL = TESLA_SOURCED["wltp_consumption_wh_km"]             # [EEA] alan Z
# WLTC satirinda gosterilen menzil referanslari
RANGE_REFS = {"ref_coc": TESLA_SOURCED["wltp_range_km"],            # CoC WLTP menzili
              "ref_r24": TESLA_SOURCED["wltp_dyno_range_km"]}       # [R24] dinamometre

# Soru 4 duyarlilik adimlari: fiziksel deger degil, analiz tanimi
SENS_P_AUX_STEP_W = 100.0            # P_aux +-100 W
SENS_ETA_T_VALUES = (0.96, 0.98)     # eta_t
SENS_V_MIN_KMH = (5.0, 10.0)         # v_min
SENS_BATT_LOSS_STEP = 0.01           # batarya kayip payi +-1 yuzde puan (0.041 -> 0.031 / 0.051)


# ---------------------------------------------------------------------------
# Tablo sutun adlari: TEK kaynak. app.py ve diger tuketiciler bu sabitleri kullanir.
# ---------------------------------------------------------------------------
# SimResult.summary() anahtarlari (model.py); cycle_table() uyustugunu kontrol eder.
_SUMMARY_KEYS = {"mesafe_km", "ort_hiz_kmh", "E_bat_Wh", "tuketim_Wh_km", "rejen_payi_pct",
                 "P_reg_sinir_adim", "zarf_disi_adim", "menzil_km"}
CYCLE_COLS = {
    "cycle": "dongu",
    "distance": "mesafe_km",
    "avg_speed": "ort_hiz_kmh",
    "e_bat": "E_bat_Wh",
    "cons": "tuketim_Wh_km",
    "regen_share": "rejen_payi_pct",
    "limit_steps": "P_reg_sinir_adim",
    "envelope": "zarf_disi_adim",
    "range": "menzil_SoC0_SoCmin_km",        # summary() 'menzil_km': E_nom (SoC_0 - SoC_min)/e
    "range_full": "menzil_tam_SoC100_0_km",  # E_nom / e (resmi menzil tanimina yakin)
    "ref_coc": "ref_CoC_WLTP_km",
    "ref_r24": "ref_R24_dinamometre_km",
}
Q1_COLS = {
    "cycle": "dongu",
    "aero": "aero_cekis_Wh_km",
    "roll": "yuvarlanma_cekis_Wh_km",
    "acc": "ivmelenme_cekis_Wh_km",
    "aero_pct": "aero_pct",
    "roll_pct": "yuvarlanma_pct",
    "acc_pct": "ivmelenme_pct",
    "regen": "geri_kazanilan_Wh_km",
    "friction": "surtunmeli_fren_Wh_km",
    "acc_recovered": "ivme_enerjisinin_geri_kazanilan_pct",
}
Q2_COLS = {
    "cycle": "dongu",
    "p_bat_max": "P_bat_maks_kW",
    "regen_peak": "tepe_rejen_kW",
    "p_reg_max": "P_reg_max_kW",
    "margin": "sinira_pay_kW",
    "limit_steps": "P_reg_sinir_adim",
    "phase": "faz",
}
CHAIN_COLS = {"step": "adim", "desc": "tanim", "whkm": "Wh_km", "pct": "fark_pct"}
BAND_COLS = {"eta": "eta_sarj", "grid": "model_sebeke_Wh_km", "wltp": "resmi_WLTP_Wh_km",
             "diff": "fark_Wh_km", "diff_pct": "fark_pct"}
SENS_REFERENCE = "referans"  # duyarlilik tablosunun params.py degerleriyle hesaplanan satiri
SENS_COLS = {"param": "parametre", "value": "deger", "note": "aciklama",
             "grid": "sebeke_Wh_km", "change": "degisim_Wh_km", "diff_pct": "resmi_degere_fark_pct"}

OVERVIEW_COLS = {
    "cycle": "dongu",
    "duration": "sure_s",
    "distance": "mesafe_km",
    "avg_speed": "ort_hiz_kmh",
    "max_speed": "maks_hiz_kmh",
    "idle": "rolanti_pct",
}


def cycle_overview(cycles: dict | None = None) -> pd.DataFrame:
    """Dongu tanitim tablosu: cycle_summary() + rolanti orani (v = 0 orneklerinin payi, %)."""
    c = OVERVIEW_COLS
    cycles = load_all_cycles() if cycles is None else cycles
    df = cycle_summary()[[c["cycle"], c["duration"], c["distance"], c["avg_speed"],
                          c["max_speed"]]].copy()
    idle = {name: float(np.mean(v == 0) * 100) for name, (_, v) in cycles.items()}
    df[c["idle"]] = df[c["cycle"]].map(idle)
    return df


def _dt_h(r) -> float:
    return float(r.t_s[1] - r.t_s[0]) / 3600.0


def _regen_wh(r) -> float:
    """Bataryaya geri kazanilan enerji [Wh] (P_trac < 0 adimlari)."""
    return -float(r.p_trac_w[r.p_trac_w < 0].sum()) * _dt_h(r)


# ---------------------------------------------------------------------------
# Dongu tablosu + menzil
# ---------------------------------------------------------------------------
def cycle_table(results: dict, p: VehicleParams, range_refs: dict | None = None) -> pd.DataFrame:
    """{dongu: SimResult} -> dongu basina ozet tablo.

    Menzil iki tanimla: SoC_0 -> SoC_min (SimResult.range_km) ve tam batarya
    E_nom / e (SoC 100 -> 0). range_refs ({"ref_coc": km, "ref_r24": km}) verilirse
    yalnizca WLTP_CYCLE satirina yazilir.
    """
    c = CYCLE_COLS
    rows = [{c["cycle"]: name, **r.summary()} for name, r in results.items()]
    df = pd.DataFrame(rows)
    assert set(df.columns) - {c["cycle"]} == _SUMMARY_KEYS, \
        f"SimResult.summary() anahtarlari degismis: {list(df.columns)}"
    df = df.rename(columns={"menzil_km": c["range"]})
    df[c["range_full"]] = p.e_nom_kwh * 1000.0 / df[c["cons"]]
    for key, km in (range_refs or {}).items():
        df[c[key]] = np.where(df[c["cycle"]] == WLTP_CYCLE, km, np.nan)
    return df


# ---------------------------------------------------------------------------
# Enerji akisi (cubuk grafik ve Sankey icin ortak kaynak)
# ---------------------------------------------------------------------------
FLOW_RTOL = 1e-9  # denge kontrolleri: goreli tolerans


def energy_flows(r, p: VehicleParams) -> dict:
    """Bir dongunun enerji akisi [Wh], SimResult.energy_wh kalemlerinden.

    Cekis adimlari (P_w >= 0, model.py ile ayni):
      batarya_brut = tekerlek_cekis / (eta_t eta_m) + E_aux
      tekerlek_cekis = aero_c + yuvarlanma_c + ivme_c (+ egim_c)
      aktarma_cekis = tekerlek_cekis (1/eta_t - 1) ; motor_kaybi = kayip_motor_cekis
    Frenleme adimlari: cekiste tekerlege verilen ivmelenme enerjisi (kinetik enerji)
      ivme_c = geri_kazanilan + rejen_kaybi + aktarma_fren + surtunmeli_fren
               + aero_fren + yuvarlanma_fren (+ egim_fren) + kinetik_net
      aero_fren / yuvarlanma_fren: frenleme anindaki direnc kinetik enerjiden karsilanir
      kinetik_net = E_inertia (tum dongu; dongu durarak basladigi ve bittigi icin ~0)
    Bakiye: batarya_brut - geri_kazanilan = E_bat. Tum dengeler assert ile denetlenir.
    """
    e = r.energy_wh
    wheel_c = e["E_tekerlek_cekis"]
    aero_c, roll_c, acc_c = e["E_aero_cekis"], e["E_roll_cekis"], e["E_ivme_cekis"]
    grade_c = wheel_c - (aero_c + roll_c + acc_c)
    trans_c = wheel_c * (1.0 / p.eta_t - 1.0)
    f = {
        "aero_cekis": aero_c, "yuvarlanma_cekis": roll_c, "ivme_cekis": acc_c,
        "egim_cekis": grade_c, "tekerlek_cekis": wheel_c,
        "aktarma_cekis": trans_c, "motor_kaybi": e["kayip_motor_cekis"],
        "aktarma_fren": e["kayip_aktarma"] - trans_c, "rejen_kaybi": e["kayip_rejen"],
        "surtunmeli_fren": e["kayip_surtunmeli_fren"], "geri_kazanilan": _regen_wh(r),
        "aero_fren": e["E_aero"] - aero_c, "yuvarlanma_fren": e["E_roll"] - roll_c,
        "egim_fren": e["E_grade"] - grade_c, "kinetik_net": e["E_inertia"],
        "yardimci": e["E_aux"], "E_bat": e["E_bat"], "mesafe_km": r.distance_km,
    }
    f["motor_girisi"] = wheel_c + trans_c + f["motor_kaybi"]
    f["batarya_brut"] = f["motor_girisi"] + f["yardimci"]
    check_energy_flows(f)
    return f


def _close(a: float, b: float, scale: float) -> bool:
    return abs(a - b) <= FLOW_RTOL * max(abs(scale), 1.0)


def check_energy_flows(f: dict) -> None:
    """Dugum giris = cikis dengeleri ve bakiye (goreli FLOW_RTOL)."""
    s = f["batarya_brut"]
    assert _close(f["batarya_brut"] - f["geri_kazanilan"], f["E_bat"], s), \
        "pozitif yigin - geri kazanilan != E_bat"
    assert _close(f["motor_girisi"], f["motor_kaybi"] + f["aktarma_cekis"] + f["tekerlek_cekis"], s), \
        "motor/reduktor dengesi tutmuyor"
    assert _close(f["tekerlek_cekis"], f["aero_cekis"] + f["yuvarlanma_cekis"] + f["ivme_cekis"]
                  + f["egim_cekis"], s), "tekerlek dengesi tutmuyor"
    out_kin = sum(f[k] for k in ("geri_kazanilan", "rejen_kaybi", "aktarma_fren", "surtunmeli_fren",
                                 "aero_fren", "yuvarlanma_fren", "egim_fren", "kinetik_net"))
    assert _close(f["ivme_cekis"], out_kin, s), "kinetik enerji dengesi tutmuyor"


FLOW_TABLE_COLS = {  # sutun -> energy_flows() kalemleri (Wh/km); yuzde = brut cekilene gore
    "dongu": None,
    "aero_cekis_Wh_km": ["aero_cekis"],
    "yuvarlanma_cekis_Wh_km": ["yuvarlanma_cekis"],
    "ivmelenme_cekis_Wh_km": ["ivme_cekis"],
    "egim_cekis_Wh_km": ["egim_cekis"],
    "guc_aktarim_kayiplari_cekis_Wh_km": ["aktarma_cekis", "motor_kaybi"],
    "yardimci_Wh_km": ["yardimci"],
    "brut_cekilen_Wh_km": ["batarya_brut"],
    "geri_kazanilan_Wh_km": ["geri_kazanilan"],
    "net_E_bat_Wh_km": ["E_bat"],
}
FLOW_PCT_SUFFIX = "_pct_brut"


def energy_flow_table(flows: dict) -> pd.DataFrame:
    """Enerji dagilimi grafigiyle ayni kaynak: kalemler Wh/km ve brut cekilene gore %."""
    rows = []
    for name, f in flows.items():
        row = {"dongu": name}
        for col, keys in FLOW_TABLE_COLS.items():
            if keys:
                row[col] = sum(f[k] for k in keys) / f["mesafe_km"]
        for col, keys in FLOW_TABLE_COLS.items():
            if keys and keys[0] not in ("batarya_brut",):
                row[col.replace("_Wh_km", FLOW_PCT_SUFFIX)] = (
                    sum(f[k] for k in keys) / f["batarya_brut"] * 100)
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Soru 1 ve Soru 2
# ---------------------------------------------------------------------------
def q1_wheel_shares(results: dict) -> pd.DataFrame:
    """Cekis adimlarindaki tekerlek enerjisinin aero / yuvarlanma / ivmelenme paylari.

    Paylar bu uc bilesenin toplamina gore (egim 0). Ayrica geri kazanilan enerji (batarya
    tarafi), surtunmeli frene giden enerji (tekerlek tarafi) ve
    ivme_enerjisinin_geri_kazanilan_pct = geri kazanilan (batarya) / cekisteki ivmelenme
    enerjisi (tekerlek) * 100.
    """
    c = Q1_COLS
    rows = []
    for name, r in results.items():
        e, s = r.energy_wh, r.distance_km
        aero, roll, acc = e["E_aero_cekis"], e["E_roll_cekis"], e["E_ivme_cekis"]
        total = aero + roll + acc
        regen = _regen_wh(r)
        rows.append({
            c["cycle"]: name,
            c["aero"]: aero / s, c["roll"]: roll / s, c["acc"]: acc / s,
            c["aero_pct"]: aero / total * 100, c["roll_pct"]: roll / total * 100,
            c["acc_pct"]: acc / total * 100,
            c["regen"]: regen / s,
            c["friction"]: e["kayip_surtunmeli_fren"] / s,
            c["acc_recovered"]: regen / acc * 100 if acc > 0 else np.nan,
        })
    return pd.DataFrame(rows)


def q2_peak_power(results: dict, p: VehicleParams) -> pd.DataFrame:
    """Tepe cekis gucu (P_bat), tepe rejenerasyon gucu (-P_trac, batarya tarafi), P_reg,max'a pay."""
    c = Q2_COLS
    p_reg_kw = p.p_reg_max_w / 1e3
    rows = []
    for name, r in results.items():
        peak_regen = float(max(-r.p_trac_w.min(), 0.0)) / 1e3
        rows.append({c["cycle"]: name, c["p_bat_max"]: float(r.p_bat_w.max()) / 1e3,
                     c["regen_peak"]: peak_regen, c["p_reg_max"]: p_reg_kw,
                     c["margin"]: p_reg_kw - peak_regen, c["limit_steps"]: r.n_reg_limited})
    return pd.DataFrame(rows)


def q2_phase_peaks(results: dict, p: VehicleParams, phases: dict) -> pd.DataFrame:
    """Faz bazinda tepe rejenerasyon gucu. phases: {dongu: faz etiketleri (load_phases)}."""
    c = Q2_COLS
    p_reg_kw = p.p_reg_max_w / 1e3
    rows = []
    for name, labels in phases.items():
        if labels is None or name not in results:
            continue
        r = results[name]
        for ph in dict.fromkeys(labels):  # Excel sirasi
            m = labels == ph
            peak = float(max(-r.p_trac_w[m].min(), 0.0)) / 1e3
            rows.append({c["cycle"]: name, c["phase"]: ph, c["regen_peak"]: peak,
                         c["margin"]: p_reg_kw - peak})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# WLTP karsilastirma zinciri
# ---------------------------------------------------------------------------
def wltp_chain(e_terminal_wh_km: float, eta_charge: float = ETA_CHARGE,
               batt_loss: float = BATT_LOSS_SHARE, wltp: float = WLTP_OFFICIAL) -> dict:
    """a) model batarya uc tarafi -> b) a/(1 - batarya kayip payi) -> c) b/eta_sarj -> d) resmi."""
    b = e_terminal_wh_km / (1.0 - batt_loss)
    grid = b / eta_charge
    return {"a": e_terminal_wh_km, "b": b, "c": grid, "d": wltp,
            "diff": grid - wltp, "diff_pct": (grid - wltp) / wltp * 100}


def wltp_chain_table(e_terminal_wh_km: float, eta_charge: float = ETA_CHARGE,
                     batt_loss: float = BATT_LOSS_SHARE, wltp: float = WLTP_OFFICIAL) -> pd.DataFrame:
    """Zincirin adim adim tablosu (Wh/km); son satir fark."""
    k = wltp_chain(e_terminal_wh_km, eta_charge, batt_loss, wltp)
    c = CHAIN_COLS
    rows = [  # tanim metinleri arayuzde gorunur
        ("a", f"Model batarya uç tarafı ({WLTP_CYCLE})", k["a"], np.nan),
        ("b", f"+ batarya iç kayıpları: a / (1 − {batt_loss}) [R24 Şekil 8, s. 16]", k["b"], np.nan),
        ("c", f"÷ η_şarj ({eta_charge}) [ADAC26] → model şebeke tarafı", k["c"], np.nan),
        ("d", "Resmi WLTP [EEA] (şebeke tarafı)", k["d"], np.nan),
        ("fark", "c − d", k["diff"], k["diff_pct"]),
    ]
    return pd.DataFrame(rows, columns=[c["step"], c["desc"], c["whkm"], c["pct"]])


def wltp_band_table(e_terminal_wh_km: float, etas=None, batt_loss: float = BATT_LOSS_SHARE,
                    wltp: float = WLTP_OFFICIAL) -> pd.DataFrame:
    """eta_sarj belirsizlik bandi: [ADAC26] araligi alt, Model Y degeri, aralik ust."""
    etas = (ETA_CHARGE_RANGE[0], ETA_CHARGE, ETA_CHARGE_RANGE[1]) if etas is None else etas
    c = BAND_COLS
    rows = []
    for eta in etas:
        k = wltp_chain(e_terminal_wh_km, eta, batt_loss, wltp)
        rows.append({c["eta"]: eta, c["grid"]: k["c"], c["wltp"]: wltp, c["diff"]: k["diff"],
                     c["diff_pct"]: k["diff_pct"]})
    return pd.DataFrame(rows)


def wltp_sensitivity(p: VehicleParams, cycles: dict, eta_charge: float = ETA_CHARGE,
                     wltp: float = WLTP_OFFICIAL, eta_table: pd.DataFrame | None = None) -> pd.DataFrame:
    """Kalan fark icin duyarlilik (WLTC_3b, sebeke tarafi Wh/km).

    eta_m, eta_reg: donguler arasi min-max (analysis/p2_efficiency.efficiency_table);
    P_aux +-SENS_P_AUX_STEP_W; eta_t SENS_ETA_T_VALUES; v_min SENS_V_MIN_KMH;
    batarya kayip payi +-SENS_BATT_LOSS_STEP (yuzde puan).
    """
    from analysis import p2_efficiency as p2e

    if eta_table is None:
        eta_table = p2e.efficiency_table(p2e.working_params(p), cycles)
    ec, cyc = p2e.EFF_COLS, p2e.EFF_COLS["cycle"]
    t, v = cycles[WLTP_CYCLE]

    def grid(params: VehicleParams, batt_loss: float = BATT_LOSS_SHARE) -> float:
        return wltp_chain(simulate(t, v, params).consumption_wh_km, eta_charge, batt_loss, wltp)["c"]

    base = grid(p)
    cases = [(SENS_REFERENCE, np.nan, "params.py değerleri", base)]  # aciklamalar ekranda gorunur
    for field, col in (("eta_m", ec["eta_m"]), ("eta_reg", ec["eta_reg"])):
        for fn, label in ((pd.Series.idxmin, "min"), (pd.Series.idxmax, "max")):
            row = eta_table.loc[fn(eta_table[col])]
            cases.append((field, row[col], f"döngüler arası {label} ({row[cyc]})",
                          grid(p.with_(**{field: row[col]}))))
    for sign in (-1, +1):
        val = p.p_aux_w + sign * SENS_P_AUX_STEP_W
        cases.append(("p_aux_w", val, f"{sign * SENS_P_AUX_STEP_W:+.0f} W", grid(p.with_(p_aux_w=val))))
    for val in SENS_ETA_T_VALUES:
        cases.append(("eta_t", val, "", grid(p.with_(eta_t=val))))
    for kmh in SENS_V_MIN_KMH:
        cases.append(("v_min_kmh", kmh, "", grid(p.with_(v_min_ms=kmh * KMH))))
    for sign in (-1, +1):
        val = BATT_LOSS_SHARE + sign * SENS_BATT_LOSS_STEP
        cases.append(("batarya_kayip_payi", val, f"{sign * SENS_BATT_LOSS_STEP * 100:+.0f} puan",
                      grid(p, val)))
    c = SENS_COLS
    return pd.DataFrame([{c["param"]: f, c["value"]: val, c["note"]: note, c["grid"]: g,
                          c["change"]: g - base, c["diff_pct"]: (g - wltp) / wltp * 100}
                         for f, val, note, g in cases])


def main(p: VehicleParams = TESLA_M3_SRP) -> dict | None:
    """3A tablolarini hesaplar, results/tables altina CSV yazar ve dondurur."""
    try:
        p.check_complete()
    except ValueError as err:
        print(f"  ATLANDI 3A: {err}")
        print("          (params.py'deki None degerler kaynakli doldurulunca tablolar uretilir)")
        return None

    cycles = load_all_cycles()
    results = {name: simulate(t, v, p) for name, (t, v) in cycles.items()}
    phases = {name: load_phases(name) for name in PHASE_CYCLES}
    e_term = results[WLTP_CYCLE].consumption_wh_km
    tables = {
        "a3_dongu_tablosu": cycle_table(results, p, RANGE_REFS),
        "a3_enerji_akisi": energy_flow_table({n: energy_flows(r, p) for n, r in results.items()}),
        "a3_soru1_tekerlek_paylari": q1_wheel_shares(results),
        "a3_soru2_tepe_guc": q2_peak_power(results, p),
        "a3_soru2_faz_tepe_rejen": q2_phase_peaks(results, p, phases),
        "a3_wltp_zincir": wltp_chain_table(e_term),
        "a3_wltp_bant": wltp_band_table(e_term),
        "a3_wltp_duyarlilik": wltp_sensitivity(p, cycles),
    }
    TABLES.mkdir(parents=True, exist_ok=True)
    (TABLES / "a3_wltp_karsilastirma.csv").unlink(missing_ok=True)  # eski tek adimli (0.90) tablo
    for name, df in tables.items():
        df.to_csv(TABLES / f"{name}.csv", index=False)
        print(f"\n{name} ({p.name}):\n" + df.round(3).to_string(index=False))
    return tables


if __name__ == "__main__":
    main()
