"""
Ortak grafik fonksiyonlari. Tum grafikler results/figures altina PNG (300 dpi) kaydedilir.
"""

from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")  # ekran acmadan dosyaya cizer (terminalden calisirken)
import matplotlib.pyplot as plt  # noqa: E402

FIG_DIR = Path(__file__).resolve().parent.parent / "results" / "figures"

# Renkler: cekis ve rejenerasyon her grafikte ayni anlami tasir
C_LINE = "#2a78d6"    # hiz / cekis (mavi)
C_REGEN = "#eb6834"   # rejenerasyon (turuncu)
C_LIMIT = "#52514e"   # sinir cizgileri (gri)


def setup_style() -> None:
    """Tum grafiklerde ayni sade gorunum."""
    plt.rcParams.update({
        "figure.dpi": 100,
        "savefig.dpi": 300,
        "font.size": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linewidth": 0.5,
        "lines.linewidth": 1.0,
    })


def save_fig(fig, name: str) -> Path:
    """Grafigi results/figures/<name>.png olarak kaydeder ve kapatir."""
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = FIG_DIR / f"{name}.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


PLOTLY_PNG_WIDTH_PX = 1400
PLOTLY_PNG_SCALE = 2


def save_plotly_png(fig, name: str, width: int = PLOTLY_PNG_WIDTH_PX,
                    scale: int = PLOTLY_PNG_SCALE) -> Path | None:
    """Plotly grafigini results/figures/<name>.png olarak kaydeder (kaleido gerekir).

    kaleido 1.x yerel bir Chrome/Edge kullanir. Paket ya da tarayici yoksa run_all.py
    cokmesin diye uyari yazar ve None dondurur (rapor icin diger PNG'ler etkilenmez).
    """
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = FIG_DIR / f"{name}.png"
    try:
        fig.write_image(path, width=width, scale=scale)
    except Exception as err:  # kaleido/Chrome yok: atla
        print(f"  ATLANDI {name}.png (Plotly PNG disa aktarimi basarisiz: {type(err).__name__}: "
              f"{str(err)[:120]})")
        return None
    return path


def _fmt_tr(x: float, nd: int = 1) -> str:
    """Ondalik virgullu, tipografik eksili sayi (etiket metinleri icin)."""
    return f"{x:.{nd}f}".replace(".", ",").replace("-", "−")


def plot_speed_profiles(cycles: dict) -> Path:
    """Tum donguler icin hiz-zaman grafigi (alt alta, ayni eksen olcegi).

    cycles: {ad: (t_s, v_kmh)}  -> load_all_cycles() ciktisi
    """
    setup_style()
    n = len(cycles)
    fig, axes = plt.subplots(n, 1, figsize=(7, 1.6 * n), sharex=True, sharey=True)
    for ax, (name, (t, v)) in zip(axes, cycles.items()):
        ax.plot(t, v, color=C_LINE)
        ax.set_title(name, loc="left", fontsize=9, fontweight="bold")
        ax.set_ylabel("v [km/h]")
    axes[-1].set_xlabel("Zaman [s]")
    axes[0].set_ylim(0, 140)
    fig.tight_layout()
    return save_fig(fig, "hiz_zaman_donguler")


def plot_power_profiles(results: dict, p_reg_max_w: float, t_end_s: float | None,
                        name: str) -> Path:
    """Batarya gucu-zaman grafikleri: yan yana, AYNI eksen olcegi (odev 3A).

    results : {dongu_adi: SimResult}
    t_end_s : ilk kac saniye cizilsin (None -> tum dongu)
    Lejant altta (panel basliklariyla cakismaz); -P_reg,max koyu gri, 1.5 pt, son panelde
    degeriyle etiketli; y ekseni degerleri tum panellerde.
    """
    setup_style()
    n = len(results)
    p_lim_kw = -p_reg_max_w / 1e3
    fig, axes = plt.subplots(1, n, figsize=(2.7 * n, 3.3), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, (cyc, r) in zip(axes, results.items()):
        mask = r.t_s <= t_end_s if t_end_s is not None else slice(None)
        t, p_kw = r.t_s[mask], r.p_bat_w[mask] / 1e3
        ax.fill_between(t, p_kw, 0, where=p_kw >= 0, interpolate=True, color=C_LINE,
                        alpha=0.8, linewidth=0, label="Çekiş (P_bat > 0)")
        ax.fill_between(t, p_kw, 0, where=p_kw < 0, interpolate=True, color=C_REGEN,
                        alpha=0.8, linewidth=0, label="Rejenerasyon (P_bat < 0)")
        ax.axhline(p_lim_kw, color=C_LIMIT, linestyle="--", linewidth=1.5, label="−P_reg,max")
        ax.axhline(0, color="black", linewidth=0.5)
        ax.set_title(cyc, loc="left", fontsize=9, fontweight="bold")
        ax.set_xlabel("Zaman [s]")
        ax.tick_params(labelleft=True)  # sharey olsa da her panelde y degerleri
        ax.grid(True, alpha=0.25, linewidth=0.5)
        if t_end_s is not None:
            ax.set_xlim(0, t_end_s)
    last = axes[-1]
    last.annotate(f"−P_reg,max = {_fmt_tr(p_lim_kw)} kW", xy=(1.0, p_lim_kw),
                  xycoords=("axes fraction", "data"), xytext=(0, 3), textcoords="offset points",
                  ha="right", va="bottom", fontsize=7.5, color=C_LIMIT)
    axes[0].set_ylabel("P_bat [kW]")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False,
               bbox_to_anchor=(0.5, 0.0))
    return save_fig(fig, name)


WLTC_PHASE_ENDS_S = (589, 1022, 1477, 1800)  # WLTC 3b faz sonlari (Low/Medium/High/Extra High)


def plot_wltc_check(r, name: str) -> Path:
    """20 Kasim kontrol belgesindeki grafigin karsiligi: v, P_bat ve kumulatif E_bat,
    faz sonlarinda Sigma E etiketli; tepe cekis ve tepe geri kazanim isaretli."""
    setup_style()
    e_cum = np.cumsum(r.e_step_wh)
    fig, axes = plt.subplots(3, 1, figsize=(8, 6.2), sharex=True)
    axes[0].plot(r.t_s, r.v_ms * 3.6, color="#13786f")
    axes[0].set_ylabel("v [km/h]")
    axes[0].set_title(f"WLTC 3b · Temel Araç · {_fmt_tr(r.consumption_wh_km)} Wh/km",
                      fontweight="bold")
    axes[1].plot(r.t_s, r.p_bat_w / 1e3, color="#c0392b")
    i_max, i_reg = int(np.argmax(r.p_bat_w)), int(np.argmin(r.p_bat_w))
    for i in (i_max, i_reg):
        axes[1].plot(r.t_s[i], r.p_bat_w[i] / 1e3, "o", mfc="none", mec="black", ms=7)
    axes[1].set_ylabel("P_bat [kW]")
    axes[2].plot(r.t_s, e_cum, color="#333333")
    for t_end in WLTC_PHASE_ENDS_S:
        k = int(np.where(r.t_s == t_end)[0][0])
        axes[2].plot(t_end, e_cum[k], "o", color="#eb6834", mec="#13786f", ms=6)
        axes[2].annotate(f"{_fmt_tr(e_cum[k])} Wh", (t_end, e_cum[k]), xytext=(5, -12),
                         textcoords="offset points", fontsize=8)
        for ax in axes:
            ax.axvline(t_end, color="grey", lw=0.6, ls=":")
    axes[2].set_ylabel("Σ E_bat [Wh]")
    axes[2].set_xlabel("t [s]")
    axes[2].set_xlim(0, r.t_s[-1])
    fig.tight_layout()
    return save_fig(fig, name)


C_NAVY = "#0d366b"
C_TEAL = "#1baf7a"
C_AMBER = "#eda100"


def plot_validation_scorecard(rows: list, tol_pct: float, name: str) -> Path:
    """Dogrulama karnesi: her kontrolun |sapma| %'si (log olcek) ve kabul siniri.
    rows: [(etiket, sapma_pct)]; sapma 0 ise olcekte en alt degere cizilir."""
    setup_style()
    labels = [r[0] for r in rows][::-1]
    dev = np.array([abs(r[1]) for r in rows][::-1])
    floor = 1e-4
    fig, ax = plt.subplots(figsize=(7.6, 0.24 * len(rows) + 0.9))
    ax.barh(labels, np.maximum(dev, floor), color=[C_TEAL if d <= tol_pct else C_REGEN for d in dev],
            height=0.6)
    ax.axvline(tol_pct, color=C_LIMIT, ls="--", lw=1.2)
    ax.text(tol_pct, len(rows) - 0.4, f" kabul sınırı %{_fmt_tr(tol_pct, 0)}", fontsize=8,
            color=C_LIMIT, va="bottom")
    for i, d in enumerate(dev):
        ax.text(max(d, floor) * 1.15, i, f"%{_fmt_tr(d, 3)}", va="center", fontsize=7.5)
    ax.set_xscale("log")
    ax.set_xlim(floor, tol_pct * 30)
    ax.set_xlabel("|model / beklenen − 1| [%] (logaritmik eksen)")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    return save_fig(fig, name)


def plot_a3_summary(table, name: str, range_col: str, cons_col: str, cycle_col: str,
                    ref_range_km: float | None = None) -> Path:
    """3A ozeti: dongu basina tuketim [Wh/km] ve menzil [km] yan yana; en yuksek tuketim turuncu."""
    setup_style()
    df = table.sort_values(cons_col)
    names = list(df[cycle_col])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.2))
    cols = [C_REGEN if v == df[cons_col].max() else (C_TEAL if v == df[cons_col].min() else C_NAVY)
            for v in df[cons_col]]
    a1.bar(names, df[cons_col], color=cols, width=0.6)
    for i, v in enumerate(df[cons_col]):
        a1.text(i, v, _fmt_tr(v), ha="center", va="bottom", fontsize=8)
    a1.set_ylabel("Tüketim [Wh/km]")
    a1.set_title("Tüketim (batarya uç tarafı)", loc="left", fontsize=9)
    a2.bar(names, df[range_col], color=cols, width=0.6)
    for i, v in enumerate(df[range_col]):
        a2.text(i, v, _fmt_tr(v, 0), ha="center", va="bottom", fontsize=8)
    if ref_range_km is not None:
        a2.axhline(ref_range_km * 0.8, color=C_LIMIT, ls="--", lw=1)
        a2.text(len(names) - 0.5, ref_range_km * 0.8, f"WLTP menzili × 0,8 = {_fmt_tr(ref_range_km * 0.8, 0)}",
                ha="right", va="bottom", fontsize=7.5, color=C_LIMIT)
    a2.set_ylabel("Menzil [km] (SoC 90→10)")
    a2.set_title("Tahmini menzil", loc="left", fontsize=9)
    for a in (a1, a2):
        a.grid(axis="x", visible=False)
        a.tick_params(axis="x", labelsize=8)
    fig.tight_layout()
    return save_fig(fig, name)


def plot_wltp_waterfall(chain: dict, name: str) -> Path:
    """WLTP karsilastirma selalesi: model batarya ucu -> +batarya ic kaybi -> +sarj kaybi
    -> model priz tarafi; yaninda resmi WLTP. chain: analysis.a3_cycles.wltp_chain() ciktisi."""
    setup_style()
    a, b, c, d = chain["a"], chain["b"], chain["c"], chain["d"]
    labels = ["Model\n(batarya ucu)", "+ batarya\niç kaybı", "+ şarj\nkaybı", "Model\n(priz tarafı)",
              "Resmi WLTP\n(priz tarafı)"]
    bottoms = [0, a, b, 0, 0]
    heights = [a, b - a, c - b, c, d]
    colors = [C_NAVY, C_AMBER, C_AMBER, C_LINE, C_TEAL]
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    ax.bar(labels, heights, bottom=bottoms, color=colors, width=0.6)
    for i, (bt, h) in enumerate(zip(bottoms, heights)):
        txt = _fmt_tr(bt + h) if i in (0, 3, 4) else "+" + _fmt_tr(h)
        ax.text(i, bt + h + 1, txt, ha="center", va="bottom", fontsize=8.5)
    for i in range(3):
        ax.plot([i + 0.3, i + 0.7], [bottoms[i] + heights[i]] * 2, color=C_LIMIT, lw=0.8)
    ax.set_ylim(min(a, d) * 0.85, max(c, d) * 1.08)
    ax.set_ylabel("Tüketim [Wh/km]")
    ax.set_title(f"WLTC 3b: model priz tarafı − resmi WLTP = {_fmt_tr(c - d)} Wh/km "
                 f"(%{_fmt_tr((c / d - 1) * 100)})", loc="left", fontsize=9)
    ax.grid(axis="x", visible=False)
    ax.tick_params(axis="x", labelsize=8)
    fig.tight_layout()
    return save_fig(fig, name)


def plot_b3_scenarios(tables: dict, name: str, scn_col: str, chg_col: str) -> Path:
    """3B: senaryo basina tuketim degisimi [%], donguler yan yana gruplu cubuk."""
    setup_style()
    cycles = list(tables)
    scen = [s for s in tables[cycles[0]][scn_col] if s != "Baseline"]
    x = np.arange(len(scen))
    w = 0.8 / len(cycles)
    colors = [C_NAVY, C_TEAL, C_AMBER, C_REGEN]
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    for i, cyc in enumerate(cycles):
        df = tables[cyc].set_index(scn_col)
        vals = [df.loc[s, chg_col] for s in scen]
        ax.bar(x + (i - (len(cycles) - 1) / 2) * w, vals, w, label=cyc, color=colors[i % 4])
        for xi, v in zip(x, vals):
            ax.text(xi + (i - (len(cycles) - 1) / 2) * w, v, _fmt_tr(v), ha="center",
                    va="bottom", fontsize=7)
    ax.set_xticks(x, ["S1 kütle +%20", "S2 C_d +%20", "S3 batarya +%20\n(+100 kg)",
                      "S4 P_reg,max\n30 kW"][:len(scen)])
    ax.set_ylabel("Tüketim değişimi [%]")
    ax.axhline(0, color="black", lw=0.6)
    ax.legend(frameon=False, fontsize=8, ncol=len(cycles), loc="upper right")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    return save_fig(fig, name)


# Enerji akisi kategorileri (interactive.py ile ayni renkler ve etiketler)
_FLOW_STACK = [
    ("Aerodinamik (çekiş)", "#256abf", ["aero_cekis"]),
    ("Yuvarlanma (çekiş)", "#86b6ef", ["yuvarlanma_cekis"]),
    ("İvmelenme (çekiş)", "#eb6834", ["ivme_cekis"]),
    ("Eğim (çekiş)", "#6250d6", ["egim_cekis"]),
    ("Güç aktarım kayıpları (çekiş)", "#898781", ["aktarma_cekis", "motor_kaybi"]),
    ("Yardımcı yük", "#008300", ["yardimci"]),
]
_LABEL_MIN_PCT = 5.0
_LABEL_MIN_HEIGHT = 0.06   # dilim yuksekligi en buyuk cubugun bu payindan kucukse yazi sigmaz
_DIAMOND_DX = 0.36         # elmas cubugun sag kenarinda (cubuk genisligi 0.6)


def plot_energy_breakdown(flows: dict, name: str, title: str, per_km: bool = True) -> Path:
    """Enerji dagilimi PNG: brut cekilen (pozitif yigin), geri kazanilan (negatif, tarali),
    net E_bat (elmas + deger). flows: {dongu: analysis.a3_cycles.energy_flows(r, p)}.
    Pozitif yigin - geri kazanilan = E_bat assert ile denetlenir.
    """
    setup_style()
    names = list(flows)
    unit = "Wh/km" if per_km else "Wh"
    k = {n: (1.0 / flows[n]["mesafe_km"] if per_km else 1.0) for n in names}
    stack = [s for s in _FLOW_STACK
             if s[2] != ["egim_cekis"] or any(abs(flows[n]["egim_cekis"]) > 1e-9 for n in names)]
    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(1.5 * len(names) + 2.5, 4.4))
    bottom = np.zeros(len(names))
    totals = np.array([sum(flows[n][key] for _, _, keys in stack for key in keys) * k[n]
                       for n in names])
    for label, color, keys in stack:
        y = np.array([sum(flows[n][key] for key in keys) * k[n] for n in names])
        ax.bar(x, y, 0.6, bottom=bottom, color=color, edgecolor="white", linewidth=0.8,
               label=label)
        for i, (v, b) in enumerate(zip(y, bottom)):
            pct = v / totals[i] * 100
            if pct > _LABEL_MIN_PCT and v >= _LABEL_MIN_HEIGHT * totals.max():
                ax.text(x[i], b + v / 2, f"%{_fmt_tr(pct, 0)}", ha="center", va="center",
                        fontsize=7, color="black" if color == "#86b6ef" else "white")
        bottom += y
    rec = np.array([flows[n]["geri_kazanilan"] * k[n] for n in names])
    ax.bar(x, -rec, 0.6, color="#f4b393", edgecolor="#eb6834", hatch="///", linewidth=0.5,
           label="Rejenerasyonla geri kazanılan")
    nets = np.array([flows[n]["E_bat"] * k[n] for n in names])
    assert np.allclose(totals - rec, nets, rtol=1e-9, atol=0.0), "pozitif yığın − geri kazanılan ≠ E_bat"
    for i in range(len(names)):
        pct = rec[i] / totals[i] * 100
        if pct > _LABEL_MIN_PCT and rec[i] >= _LABEL_MIN_HEIGHT * totals.max():
            ax.text(x[i], -rec[i] / 2, f"−%{_fmt_tr(pct, 0)}", ha="center", va="center",
                    fontsize=7, color="black")
        ax.text(x[i], totals[i], f"E_bat = {_fmt_tr(nets[i])}", ha="center", va="bottom",
                fontsize=7.5)
    ax.scatter(x + _DIAMOND_DX, nets, marker="D", s=40, color="#0b0b0b", edgecolor="white",
               zorder=5, clip_on=False, label="Net E_bat (batarya uç tarafı)")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x, names)
    ax.set_xlabel("Döngü")
    ax.set_ylabel(f"Enerji [{unit}]")
    ax.set_title(title, loc="left", fontsize=9)
    ax.set_ylim(top=totals.max() * 1.1)
    fig.tight_layout(rect=(0, 0.16, 1, 1))
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, fontsize=7.5,
               bbox_to_anchor=(0.5, 0.0))
    return save_fig(fig, name)
