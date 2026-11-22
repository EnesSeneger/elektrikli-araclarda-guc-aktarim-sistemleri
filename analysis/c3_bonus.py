"""
3C - Bonus: MOTOR HARITASI + reduktor orani (G) taramasi (gercek arac: Tesla Model 3 SR+).

Odev: "Sabit eta_m yerine tork-devir kayip haritasi; G oranini 8-11 arasinda tarayip
WLTC 3b tuketimini minimize eden orani bulun."

Neden harita gerekir: sabit verimli modelde P_bat yalnizca P_w'ye baglidir; P_w ise G'den
bagimsizdir (F_trac, v). Yani sabit eta_m ile tuketim G'ye DUYARSIZDIR. G yalnizca motorun
calisma noktasini (n_m = n_w G, T_m = T_w / (G eta_t)) kaydirir; tuketimi ancak verimin bu
noktaya bagli oldugu bir harita degistirir.

Harita: [R24] Sekil 5a (evmodel/efficiency_map.py, eta_at). Her adimda:
  cekis (P_w >= 0)  : P_m = P_w / eta_t ;  P_trac = P_m + P_kayip(n_m, T_m)
  frenleme (P_w < 0): P_m,reg = |P_w| eta_t ; P_trac = max(-(P_m,reg - P_kayip), -P_reg,max)
  v < v_min ve P_w < 0: P_trac = 0 (odev 3.4 karar blogu aynen)
  P_bat = P_trac + P_aux
Geri kazanimda harita simetrisi VARSAYIMI (analysis/p2_efficiency.py ile ayni).

Dusuk tork belirsizligi: [R24] 15 Nm altini olcmedi; haritanin en dusuk satiri 20 Nm. Bu bolge
iki SINIR ile kapatilir (gercek deger arada):
  "eta_sabit" (iyimser) : T < 20 Nm'de verim eta(n, 20 Nm) kabul edilir -> kayip torkla
                          birlikte sifira gider (evmodel/efficiency_map.py davranisi).
  "kayip_sabit" (kotumser): T < 20 Nm'de kayip P_kayip(n, 20 Nm) kabul edilir -> bostaki
                          demir + anahtarlama kayiplari tork azalsa da azalmaz.
Iyimser sinir G = 9,04'te sabit verimli modelle (params.py, WLTC esdeger verim) ayni sonucu
vermelidir; tests/test_c3_bonus.py bunu denetler.

Ek tasarim kisitlari (her G icin): zarf disi adim (3.7), azami hiz v_max = n_max r_w / G
ve kalkis tekerlek kuvveti F_0 = T_peak G eta_t / r_w.

Calistirma:  python -m analysis.c3_bonus
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evmodel.cycles import CYCLE_NAMES, load_all_cycles  # noqa: E402
from evmodel.efficiency_map import eta_at, map_bounds  # noqa: E402
from evmodel.model import simulate  # noqa: E402
from evmodel.params import TESLA_M3_SRP, TESLA_SOURCED, VehicleParams  # noqa: E402

TABLES = ROOT / "results" / "tables"
V_TOP_KMH = TESLA_SOURCED["v_top_kmh"]   # [EVDB] azami hiz: G icin ust sinir kisiti
SCAN_CYCLE = "WLTC_3b"                # odev: WLTC 3b tuketimini minimize eden G
CHECK_CYCLES = ["WLTC_3b", "HWFET", "US06"]  # optimum G'nin diger donguleri nasil etkiledigi
G_MIN, G_MAX, G_STEP = 8.0, 11.0, 0.05     # odev: 8-11 arasi tarama
LOW_T_MODES = ("eta_sabit", "kayip_sabit")  # dusuk tork bolgesi icin iki sinir (yukariya bakin)

SCAN_COLS = {
    "G": "G",
    "mode": "dusuk_tork_siniri",
    "cons": "tuketim_Wh_km",
    "cons_change": "degisim_G_ref_pct",
    "eta_m": "eta_m_esdeger",
    "eta_reg": "eta_reg_esdeger",
    "envelope": "zarf_disi_adim",
    "v_max": "v_max_kmh",
    "f0": "kalkis_kuvveti_kN",
}


def _rad_s(n_rpm):
    return np.asarray(n_rpm) * 2.0 * np.pi / 60.0


def _loss(p_m_w, eta, motoring):
    """Mil gucu P_m ve verimden kayip: motor modunda P_m(1/eta - 1) (giris = P_m/eta),
    generator modunda P_m(1 - eta) (cikis = P_m eta; p2_efficiency ile ayni simetri)."""
    return np.where(motoring, p_m_w * (1.0 / eta - 1.0), p_m_w * (1.0 - eta))


def motor_loss_w(n_rpm: np.ndarray, t_nm: np.ndarray, motoring: np.ndarray,
                 mode: str) -> np.ndarray:
    """Motor + invertor kaybi [W]. motoring: True cekis, False geri kazanim.
    mode: LOW_T_MODES'tan biri (dusuk tork bolgesi siniri)."""
    if mode not in LOW_T_MODES:
        raise ValueError(f"bilinmeyen dusuk tork modu: {mode}")
    n = np.asarray(n_rpm, dtype=float)
    t_abs = np.abs(np.asarray(t_nm, dtype=float))
    omega = _rad_s(n)
    eta = eta_at(n, t_abs)              # T < T_min'de eta(n, T_min) (kirpma)
    loss = _loss(t_abs * omega, eta, motoring)
    if mode == "kayip_sabit":
        t_min = map_bounds()["T"][0]
        low = t_abs < t_min
        if low.any():
            eta_min = eta_at(n[low], np.full(low.sum(), t_min))
            loss[low] = _loss(t_min * omega[low], eta_min, np.asarray(motoring)[low])
    return np.where(omega > 0, loss, 0.0)


def simulate_map(t_s, v_kmh, p: VehicleParams, mode: str = "eta_sabit") -> dict:
    """simulate() calisma noktalariyla haritali batarya gucu. P_w, n_m, T_m simulate()'ten
    alinir (eta_m/eta_reg'e bagli degiller); yalnizca 3.4 karar blogu haritayla yeniden kurulur.
    """
    r = simulate(t_s, v_kmh, p)
    dt = float(r.t_s[1] - r.t_s[0])
    traction = r.p_w_w >= 0
    loss = motor_loss_w(r.n_m_rpm, r.t_m_nm, traction, mode)

    p_m = np.where(traction, r.p_w_w / p.eta_t, -r.p_w_w * p.eta_t)  # motor mili, pozitif
    p_regen_ideal = -(p_m - loss)
    p_regen = np.maximum(p_regen_ideal, -p.p_reg_max_w)
    low_speed = (r.v_ms < p.v_min_ms) & ~traction
    p_trac = np.where(traction, p_m + loss, p_regen)
    p_trac = np.where(low_speed, 0.0, p_trac)
    p_bat = p_trac + p.p_aux_w

    e_bat_wh = float(p_bat.sum() * dt / 3600.0)
    # esdeger verimler (bilgi): cekiste sum P_m / sum P_elek, geri kazanimda sum P_elek / sum P_m
    trac = traction & (r.p_w_w > 0)
    reg = (~traction) & (~low_speed)
    eta_m_eq = float(p_m[trac].sum() / (p_m[trac] + loss[trac]).sum())
    eta_reg_eq = (float((p_m[reg] - loss[reg]).sum() / p_m[reg].sum())
                  if p_m[reg].sum() > 0 else np.nan)
    return {"sim": r, "p_bat_w": p_bat, "p_trac_w": p_trac, "e_bat_wh": e_bat_wh,
            "consumption_wh_km": e_bat_wh / r.distance_km, "eta_m_eq": eta_m_eq,
            "eta_reg_eq": eta_reg_eq, "n_envelope_violations": r.n_envelope_violations}


def design_limits(p: VehicleParams) -> dict:
    """G'ye bagli tasarim kisitlari: azami hiz (n_max'tan) ve kalkis tekerlek kuvveti."""
    v_max_ms = _rad_s(p.n_max_rpm) * p.rw_m / p.gear_ratio
    f0_n = p.t_peak_nm * p.gear_ratio * p.eta_t / p.rw_m
    return {"v_max_kmh": v_max_ms * 3.6, "f0_kn": f0_n / 1e3}


def g_values() -> np.ndarray:
    n = int(round((G_MAX - G_MIN) / G_STEP)) + 1
    return np.round(np.linspace(G_MIN, G_MAX, n), 4)


def g_scan(t_s, v_kmh, p: VehicleParams = TESLA_M3_SRP, gs=None) -> pd.DataFrame:
    """Her G ve her dusuk tork siniri icin tuketim, esdeger verimler ve kisitlar."""
    c = SCAN_COLS
    gs = np.union1d(g_values(), [p.gear_ratio]) if gs is None else gs  # G_ref tam degeriyle
    rows = []
    for mode in LOW_T_MODES:
        ref = simulate_map(t_s, v_kmh, p, mode)["consumption_wh_km"]
        for g in gs:
            pg = p.with_(gear_ratio=float(g))
            m = simulate_map(t_s, v_kmh, pg, mode)
            lim = design_limits(pg)
            rows.append({c["G"]: g, c["mode"]: mode, c["cons"]: m["consumption_wh_km"],
                         c["cons_change"]: (m["consumption_wh_km"] / ref - 1) * 100,
                         c["eta_m"]: m["eta_m_eq"], c["eta_reg"]: m["eta_reg_eq"],
                         c["envelope"]: m["n_envelope_violations"],
                         c["v_max"]: lim["v_max_kmh"], c["f0"]: lim["f0_kn"]})
    return pd.DataFrame(rows)


def g_upper_for_top_speed(p: VehicleParams = TESLA_M3_SRP,
                          v_top_kmh: float = V_TOP_KMH) -> float:
    """Azami motor devrinde v_top'a ulasabilen en buyuk G: n_max r_w / v_top."""
    return float(_rad_s(p.n_max_rpm) * p.rw_m / (v_top_kmh / 3.6))


def optimum_table(scan: pd.DataFrame, p: VehicleParams = TESLA_M3_SRP) -> pd.DataFrame:
    """Her sinir icin optimum G (kisitsiz ve azami hiz kisitli), tuketim ve
    G_ref = p.gear_ratio'ya gore kazanc."""
    c = SCAN_COLS
    g_up = g_upper_for_top_speed(p)
    rows = []
    for mode, df in scan.groupby(c["mode"], sort=False):
        best = df.loc[df[c["cons"]].idxmin()]
        feas = df[df[c["G"]] <= g_up]
        best_c = feas.loc[feas[c["cons"]].idxmin()]
        ref = df.loc[(df[c["G"]] - p.gear_ratio).abs().idxmin()]
        rows.append({c["mode"]: mode, "G_ref_tarama": ref[c["G"]],
                     "tuketim_G_ref_Wh_km": ref[c["cons"]],
                     "G_opt": best[c["G"]], "tuketim_G_opt_Wh_km": best[c["cons"]],
                     "kazanc_pct": (1 - best[c["cons"]] / ref[c["cons"]]) * 100,
                     "v_max_G_opt_kmh": best[c["v_max"]],
                     "zarf_disi_G_opt": int(best[c["envelope"]]),
                     "G_ust_v_top": g_up,
                     "G_opt_kisitli": best_c[c["G"]],
                     "tuketim_G_opt_kisitli_Wh_km": best_c[c["cons"]],
                     "kazanc_kisitli_pct": (1 - best_c[c["cons"]] / ref[c["cons"]]) * 100})
    return pd.DataFrame(rows)


def constant_vs_map(cycles: dict, p: VehicleParams = TESLA_M3_SRP) -> pd.DataFrame:
    """G = p.gear_ratio'da sabit verimli model ile haritali model (iki sinir), tum donguler.
    3A Soru 4'teki "sabit verim varsayimi" kaleminin buyuklugu."""
    rows = []
    for name in CYCLE_NAMES:
        t, v = cycles[name]
        row = {"dongu": name, "sabit_verim_Wh_km": simulate(t, v, p).consumption_wh_km}
        for mode in LOW_T_MODES:
            m = simulate_map(t, v, p, mode)
            row[f"harita_{mode}_Wh_km"] = m["consumption_wh_km"]
            row[f"fark_{mode}_pct"] = (m["consumption_wh_km"] / row["sabit_verim_Wh_km"] - 1) * 100
        rows.append(row)
    return pd.DataFrame(rows)


def optimum_on_other_cycles(cycles: dict, opt: pd.DataFrame,
                            p: VehicleParams = TESLA_M3_SRP) -> pd.DataFrame:
    """WLTC optimum G'si diger dongulerde de kazanc saglar mi? (her sinir icin)."""
    rows = []
    for _, o in opt.iterrows():
        mode = o[SCAN_COLS["mode"]]
        for name in CHECK_CYCLES:
            t, v = cycles[name]
            ref = simulate_map(t, v, p, mode)["consumption_wh_km"]
            new = simulate_map(t, v, p.with_(gear_ratio=float(o["G_opt"])), mode)
            rows.append({SCAN_COLS["mode"]: mode, "dongu": name, "G_opt_WLTC": o["G_opt"],
                         "tuketim_G_ref_Wh_km": ref, "tuketim_G_opt_Wh_km": new["consumption_wh_km"],
                         "degisim_pct": (new["consumption_wh_km"] / ref - 1) * 100,
                         "zarf_disi_G_opt": new["n_envelope_violations"]})
    return pd.DataFrame(rows)


def make_figure(scan: pd.DataFrame, opt: pd.DataFrame, t_s, v_kmh,
                p: VehicleParams = TESLA_M3_SRP):
    """(a) tuketim-G egrileri, (b) WLTC calisma noktalari verim haritasi uzerinde."""
    from evmodel.efficiency_map import eta_grid
    from evmodel.envelope import t_max_nm
    from evmodel.plotting import C_LINE, C_REGEN, plt, save_fig, setup_style

    c = SCAN_COLS
    setup_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.8))
    colors = {"eta_sabit": C_LINE, "kayip_sabit": C_REGEN}
    labels = {"eta_sabit": "iyimser sınır: T<20 Nm'de η sabit",
              "kayip_sabit": "kötümser sınır: T<20 Nm'de kayıp sabit"}
    for mode, df in scan.groupby(c["mode"], sort=False):
        ax1.plot(df[c["G"]], df[c["cons"]], color=colors[mode], label=labels[mode])
        best = opt[opt[c["mode"]] == mode].iloc[0]
        ax1.plot(best["G_opt"], best["tuketim_G_opt_Wh_km"], "o", color=colors[mode], ms=5)
        ax1.annotate(f"G* = {best['G_opt']:.2f}".replace(".", ","),
                     (best["G_opt"], best["tuketim_G_opt_Wh_km"]), xytext=(-4, 6),
                     textcoords="offset points", ha="right", fontsize=7.5, color=colors[mode])
    g_up = g_upper_for_top_speed(p)
    ax1.axvline(p.gear_ratio, color="#52514e", ls="--", lw=1)
    ax1.text(p.gear_ratio, ax1.get_ylim()[1], f" Tesla G = {p.gear_ratio}".replace(".", ","),
             va="top", ha="right", fontsize=7.5, color="#52514e")
    ax1.axvspan(g_up, G_MAX, color="#52514e", alpha=0.12, lw=0)
    ax1.text(g_up, ax1.get_ylim()[1],
             f"  v_max < {V_TOP_KMH:.0f} km/h\n  (G > {g_up:.2f})".replace(".", ","),
             va="top", fontsize=7, color="#52514e")
    ax1.set_xlabel("Redüktör oranı G [–]")
    ax1.set_ylabel(f"{SCAN_CYCLE} tüketimi [Wh/km] (batarya)")
    ax1.set_title("(a) Haritalı model, G taraması", loc="left", fontsize=9)
    ax1.legend(fontsize=7, frameon=False, loc="lower left")

    n, tq, eta = eta_grid()
    cs = ax2.contourf(n, tq, eta, levels=np.arange(0.70, 0.985, 0.02), cmap="Greys")
    fig.colorbar(cs, ax=ax2, label="η (motor + invertör)")
    nn = np.linspace(0, p.n_max_rpm, 300)
    ax2.plot(nn, t_max_nm(nn, p.t_peak_nm, p.p_peak_w, p.n_max_rpm), color="black", lw=1.2,
             label="T_max(n) zarfı")
    g_opt = float(opt.iloc[0]["G_opt"])
    for g, col, lab in ((p.gear_ratio, C_LINE, f"G = {p.gear_ratio}"),
                        (g_opt, C_REGEN, f"G = {g_opt:.2f} (tarama ucu)")):
        r = simulate(t_s, v_kmh, p.with_(gear_ratio=g))
        k = r.p_w_w > 0
        ax2.scatter(r.n_m_rpm[k], r.t_m_nm[k], s=2, color=col, alpha=0.5,
                    label=lab.replace(".", ","))
    t_min = map_bounds()["T"][0]
    ax2.axhspan(0, t_min, facecolor="none", edgecolor="#9a9893", hatch="////", lw=0)
    ax2.text(p.n_max_rpm * 0.98, t_min / 2, f"T < {t_min:.0f} Nm: ölçülmedi [R24]",
             ha="right", va="center", fontsize=6.5, color="#52514e")
    ax2.set_xlim(0, p.n_max_rpm)
    ax2.set_ylim(0, p.t_peak_nm * 1.05)
    ax2.set_xlabel("Motor devri n_m [rpm]")
    ax2.set_ylabel("Motor torku T_m [Nm]")
    ax2.set_title(f"(b) {SCAN_CYCLE} çekiş noktaları, [R24] Şekil 5a haritası", loc="left",
                  fontsize=9)
    ax2.legend(fontsize=7, frameon=True, loc="upper right", markerscale=4)
    fig.tight_layout()
    return save_fig(fig, "c3_motor_haritasi_G_taramasi")


def main(figures: bool = True) -> dict:
    cycles = load_all_cycles()
    t, v = cycles[SCAN_CYCLE]
    scan = g_scan(t, v)
    opt = optimum_table(scan)
    tables = {
        "c3_G_taramasi": scan,
        "c3_G_optimum": opt,
        "c3_sabit_verim_harita": constant_vs_map(cycles),
        "c3_G_optimum_diger_donguler": optimum_on_other_cycles(cycles, opt),
    }
    TABLES.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(TABLES / f"{name}.csv", index=False)
        shown = df if name != "c3_G_taramasi" else df[df[SCAN_COLS["G"]].isin(
            np.round(np.arange(G_MIN, G_MAX + 1e-9, 0.5), 4))]
        print(f"\n{name}:\n" + shown.round(3).to_string(index=False))
    if figures:
        print("  ", make_figure(scan, opt, t, v))
    return tables


if __name__ == "__main__":
    main()
