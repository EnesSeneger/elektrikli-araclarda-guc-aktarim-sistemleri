"""
Asama 2 - Tesla parametre calismasi, son parca: esdeger sabit verimler ve kalan parametreler.

Model (odev 3.4) sabit eta_m (cekis) ve eta_reg (geri kazanim) kullanir. [R24] Sekil 5a
verim haritasindan (evmodel/efficiency_map.py) dongu basina ESDEGER sabit verimler:

  Cekis adimlari (P_w > 0):
    P_m = P_w / eta_t                      (motor mili gucu)
    eta_m,es = sum(P_m) / sum(P_m / eta(n_m, T_m))
    -> enerji agirlikli harmonik ortalama: sabit eta_m ile toplam elektrik girisi korunur.
  Geri kazanim adimlari (P_w < 0 ve v >= v_min):
    P_m,reg = |P_w| * eta_t                (motor miline gelen guc)
    eta_reg,es = sum(P_m,reg * eta(n_m, |T_m|)) / sum(P_m,reg)
    -> enerji agirlikli aritmetik ortalama: sabit eta_reg ile toplam geri kazanim korunur.
    VARSAYIM: harita geri kazanimda simetrik (ayni |T|, n'de ayni verim). Gerekce: [R24]
    yalnizca motor modu haritasi verir; PMSM + invertorde bakir/demir/anahtarlama kayiplari
    torkun isaretinden buyuk olcude bagimsizdir, bu nedenle ayna simetri yaygin bir yaklasimdir.

T_m ve n_m yalnizca eta_t, G, r_w ve hiz profiline baglidir; eta_m/eta_reg'e bagli DEGILDIR.
Bu nedenle baslangic verimiyle (0.93) yapilan hesap ile bulunan degerlerle tekrarlanan hesap
ayni sonucu verir (yakinsama tek adimda; main() bunu gosterir).

Ayrica: P_aux'un [R24] Sekil 8'den turetilmesi, eta_m/eta_reg duyarliligi ve [R24] Sekil 8
ile WLTC enerji akisi karsilastirmasi (dogrulama tablosu).

Calistirma:  python -m analysis.p2_efficiency
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evmodel.cycles import CYCLE_NAMES, cycle_distance_km, load_all_cycles  # noqa: E402
from evmodel.efficiency_map import eta_at, map_bounds  # noqa: E402
from evmodel.model import simulate  # noqa: E402
from evmodel.params import TESLA_M3_SRP, TESLA_SOURCED, VehicleParams  # noqa: E402

TABLES = ROOT / "results" / "tables"
REF_CYCLE = "WLTC_3b"   # params.py'ye yazilan esdeger verimlerin dongusu
START_ETA = 0.93        # yinelemenin baslangic verimi (sonucu etkilemez, yukariya bakin)
SENS_STEP = 0.01        # duyarlilik: eta_m ve eta_reg +-0.01

# Tablo sutun adlari (app.py ve testler ayni sabitleri kullanir)
EFF_COLS = {
    "cycle": "dongu",
    "eta_m": "eta_m_esdeger",
    "eta_reg": "eta_reg_esdeger",
    "low_t": "T_m_20Nm_alti_cekis_payi_pct",
}
R24_NOTE = ("Toplamlar yakin ama kalemler farkli: R24 dinamometrede kendi coast-down "
            "katsayilarini (a0=177 N) kullandi, model CoC katsayilarini (f0=150 N); model guc "
            "aktarim kayiplarini sabit verim nedeniyle daha yuksek hesapliyor. Toplamdaki uyum "
            "kismen kalemler arasi dengelenmedir.")
# a0 / f0 orani TESLA_SOURCED'daki kaynakli degerlerden hesaplanir (s. 6 ve Tablo A1)
R24_A0_NOTE = ("R24'un dinamometre ayarinda kullandigi a0 = {a0} N (s. 6), CoC f0 = {f0} N "
               "degerinden yaklasik %{pct:.0f} yuksektir; tekerlek-yol kalemindeki farkin ana "
               "nedeni budur.")


# ---------------------------------------------------------------------------
# P_aux: [R24] Sekil 8'den
# ---------------------------------------------------------------------------
def aux_power_from_r24(t_s: np.ndarray, v_kmh: np.ndarray) -> dict:
    """P_aux = pay_yardimci * e_batarya [Wh/km] * mesafe [km] / sure [h].

    [R24] Sekil 8 WLTP: yardimci yuk payi %5,56, batarya tarafi 136 Wh/km (HVAC kapali);
    mesafe ve sure WLTC_3b verisinden (23,27 km, 1800 s = 0,5 h).
    """
    share = TESLA_SOURCED["r24_fig8_wltp_shares"]["yardimci"]
    e_wh_km = TESLA_SOURCED["r24_wltp_battery_wh_km"]
    dist_km = cycle_distance_km(v_kmh, float(t_s[1] - t_s[0]))
    dur_h = (t_s[-1] - t_s[0]) / 3600.0
    return {"pay": share, "e_bat_Wh_km": e_wh_km, "mesafe_km": dist_km, "sure_h": dur_h,
            "E_aux_Wh": share * e_wh_km * dist_km, "P_aux_W": share * e_wh_km * dist_km / dur_h}


# ---------------------------------------------------------------------------
# Esdeger verimler
# ---------------------------------------------------------------------------
def working_params(p: VehicleParams = TESLA_M3_SRP, eta_m: float | None = None,
                   eta_reg: float | None = None) -> VehicleParams:
    """Hesap icin tam parametre seti: verilmeyen/None verimler START_ETA ile doldurulur."""
    return p.with_(eta_m=eta_m if eta_m is not None else (p.eta_m or START_ETA),
                   eta_reg=eta_reg if eta_reg is not None else (p.eta_reg or START_ETA))


def equivalent_efficiencies(r, p: VehicleParams) -> dict:
    """Bir SimResult icin esdeger eta_m, eta_reg ve 20 Nm alti cekis enerjisi payi [%]."""
    trac = r.p_w_w > 0
    p_m = r.p_w_w[trac] / p.eta_t
    eta_trac = eta_at(r.n_m_rpm[trac], r.t_m_nm[trac])
    eta_m = float(p_m.sum() / (p_m / eta_trac).sum())

    reg = (r.p_w_w < 0) & (r.v_ms >= p.v_min_ms)
    p_m_reg = np.abs(r.p_w_w[reg]) * p.eta_t
    eta_reg_pts = eta_at(r.n_m_rpm[reg], np.abs(r.t_m_nm[reg]))  # simetri VARSAYIMI
    eta_reg = float((p_m_reg * eta_reg_pts).sum() / p_m_reg.sum()) if p_m_reg.sum() > 0 else np.nan

    t_min = map_bounds()["T"][0]  # olculen en dusuk tork satiri (20 Nm)
    low = r.t_m_nm[trac] < t_min
    low_share = float(p_m[low].sum() / p_m.sum() * 100)
    return {"eta_m": eta_m, "eta_reg": eta_reg, "low_t": low_share}


def efficiency_table(p: VehicleParams, cycles: dict) -> pd.DataFrame:
    """Dongu basina esdeger verimler."""
    c = EFF_COLS
    rows = []
    for name in CYCLE_NAMES:
        t, v = cycles[name]
        e = equivalent_efficiencies(simulate(t, v, p), p)
        rows.append({c["cycle"]: name, c["eta_m"]: e["eta_m"], c["eta_reg"]: e["eta_reg"],
                     c["low_t"]: e["low_t"]})
    return pd.DataFrame(rows)


def ref_cycle_efficiencies(p: VehicleParams = TESLA_M3_SRP,
                           cycles: dict | None = None) -> tuple[float, float]:
    """REF_CYCLE (WLTC_3b) esdeger (eta_m, eta_reg) - params.py degerlerinin kaynagi."""
    cycles = load_all_cycles() if cycles is None else cycles
    pw = working_params(p)
    t, v = cycles[REF_CYCLE]
    e = equivalent_efficiencies(simulate(t, v, pw), pw)
    return e["eta_m"], e["eta_reg"]


def convergence(p: VehicleParams, cycles: dict) -> pd.DataFrame:
    """1. gecis START_ETA ile, 2. gecis 1. gecisin WLTC degerleriyle; fark ~0 olmali."""
    c = EFF_COLS
    p1 = working_params(p, START_ETA, START_ETA)
    t1 = efficiency_table(p1, cycles)
    w = t1[t1[c["cycle"]] == REF_CYCLE].iloc[0]
    p2 = working_params(p, w[c["eta_m"]], w[c["eta_reg"]])
    t2 = efficiency_table(p2, cycles)
    out = t1[[c["cycle"]]].copy()
    for col in (c["eta_m"], c["eta_reg"]):
        out[f"{col} [1. gecis, {START_ETA}]"] = t1[col]
        out[f"{col} [2. gecis]"] = t2[col]
        out[f"{col} [fark]"] = t2[col] - t1[col]
    return out


def sensitivity(p: VehicleParams, cycles: dict) -> pd.DataFrame:
    """eta_m ve eta_reg +-SENS_STEP icin REF_CYCLE tuketim degisimi [Wh/km]."""
    t, v = cycles[REF_CYCLE]
    base = simulate(t, v, p).consumption_wh_km
    rows = []
    for field in ("eta_m", "eta_reg"):
        for step in (-SENS_STEP, +SENS_STEP):
            new = getattr(p, field) + step
            r = simulate(t, v, p.with_(**{field: new}))
            rows.append({"parametre": field, "deger": new, "tuketim_Wh_km": r.consumption_wh_km,
                         "degisim_Wh_km": r.consumption_wh_km - base,
                         "degisim_pct": (r.consumption_wh_km / base - 1) * 100})
    return pd.DataFrame(rows)


def validation_vs_r24(p: VehicleParams, cycles: dict) -> pd.DataFrame:
    """Tesla modeli (REF_CYCLE) ile [R24] Sekil 8 WLTP enerji akisi [Wh/km]."""
    t, v = cycles[REF_CYCLE]
    r = simulate(t, v, p)
    e, s = r.energy_wh, r.distance_km
    sh, e_r24 = TESLA_SOURCED["r24_fig8_wltp_shares"], TESLA_SOURCED["r24_wltp_battery_wh_km"]
    rows = [
        ("tekerlek-yol (aero + yuvarlanma)", (e["E_aero"] + e["E_roll"]) / s,
         sh["tekerlek_yol"] * e_r24),
        ("guc aktarim kayiplari (aktarma + motor + rejen + surtunmeli fren)",
         (e["kayip_aktarma"] + e["kayip_motor_cekis"] + e["kayip_rejen"]
          + e["kayip_surtunmeli_fren"]) / s, sh["invertor_tekerlek"] * e_r24),
        ("yardimci (E_aux)", e["E_aux"] / s, sh["yardimci"] * e_r24),
        ("toplam, batarya uc tarafi (E_bat)", r.consumption_wh_km,
         TESLA_SOURCED["r24_wltp_terminal_wh_km"]),
    ]
    df = pd.DataFrame(rows, columns=["kalem", "model_Wh_km", "R24_Wh_km"])
    df["fark_Wh_km"] = df["model_Wh_km"] - df["R24_Wh_km"]
    df["fark_pct"] = df["fark_Wh_km"] / df["R24_Wh_km"] * 100
    return df


def final_params(p: VehicleParams = TESLA_M3_SRP, cycles: dict | None = None) -> VehicleParams:
    """params.py'deki degerler varsa onlar; yoksa WLTC esdeger verimleriyle tamamlanmis set."""
    if p.eta_m is not None and p.eta_reg is not None:
        return p
    eta_m, eta_reg = ref_cycle_efficiencies(p, cycles)
    return p.with_(eta_m=eta_m, eta_reg=eta_reg)


def main() -> dict:
    cycles = load_all_cycles()
    p = final_params(TESLA_M3_SRP, cycles)
    aux = aux_power_from_r24(*cycles[REF_CYCLE])
    tables = {
        "p2_verimler": efficiency_table(working_params(TESLA_M3_SRP), cycles),
        "p2_verim_yakinsama": convergence(TESLA_M3_SRP, cycles),
        "p2_verim_duyarlilik": sensitivity(p, cycles),
        "p2_r24_sekil8_dogrulama": validation_vs_r24(p, cycles),
    }
    print(f"\nP_aux [R24 Sekil 8]: {aux['pay']} x {aux['e_bat_Wh_km']} Wh/km x "
          f"{aux['mesafe_km']:.2f} km / {aux['sure_h']:.2f} h = {aux['P_aux_W']:.1f} W "
          f"(params.py: {TESLA_M3_SRP.p_aux_w} W)")
    TABLES.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(TABLES / f"{name}.csv", index=False)
        print(f"\n{name}:\n" + df.round(4).to_string(index=False))
    print("Not: " + R24_NOTE)
    a0, f0 = TESLA_SOURCED["r24_coastdown_a0_N"], TESLA_SOURCED["f0_N"]
    print("Not: " + R24_A0_NOTE.format(a0=a0, f0=f0, pct=(a0 / f0 - 1) * 100))
    return tables


if __name__ == "__main__":
    main()
