"""
Interaktif (Plotly) grafik fonksiyonlari - web arayuzu (app.py) ve ileride
rapor/analiz defterleri icin. Her fig_* fonksiyonu go.Figure dondurur.

Bu modul HESAP YAPMAZ: yalnizca simulate() ciktisi olan SimResult alanlarini
ve envelope.t_max_nm() fonksiyonunu kullanir. Tek ek islem, guc egrisinin
sifir gecis noktalarinin dolgu icin dogrusal aradegerlenmesidir (yalnizca cizim).

Zaman penceresi: t_window = (t_bas_s, t_son_s) ya da None (tum dongu).
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from evmodel.cycles import CYCLE_NAMES
from evmodel.envelope import t_max_nm
from evmodel.params import VehicleParams

# Renkler: matplotlib grafikleriyle (plotting.py) ayni anlam
C_LINE = "#2a78d6"    # hiz / cekis (mavi)
C_REGEN = "#eb6834"   # rejenerasyon (turuncu)
C_LIMIT = "#52514e"   # sinir cizgileri (gri)
C_MUTED = "#898781"   # ikincil ogeler (baseline cubugu, egim payi)
C_ALERT = "#e34948"   # zarf disi noktalar (kirmizi)

# Kategorik renkler sabit sirada; renk donguye baglidir, siralamaya degil
_CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
                "#e87ba4", "#008300", "#6250d6", "#e34948"]
CYCLE_COLORS = {name: _CATEGORICAL[i] for i, name in enumerate(CYCLE_NAMES)}

PLOT_HEIGHT_PX = 420
PANEL_HEIGHT_PX = 170
LEGEND_Y = -0.22          # lejant cizim alaninin altinda (baslik/panel basliklariyla cakismaz)
GRID_COLOR = "rgba(0,0,0,0.08)"

# Enerji akisi kategorileri (cubuk grafik ve Sankey ayni renkler)
C_AERO = "#256abf"        # mavi (koyu)
C_ROLL = "#86b6ef"        # mavi (acik) - ayni tonun iki acikligi
C_ACC = "#eb6834"         # turuncu - ivmelenme (kinetik enerji)
C_RECOVERED = "#f4b393"   # acik turuncu - rejenerasyonla geri kazanilan (tarali)
C_LOSS = "#898781"        # gri - guc aktarim kayiplari
C_AUX = "#008300"         # yesil - yardimci yuk
C_GRADE = "#6250d6"       # mor - egim (yalnizca egim != 0)
C_INK = "#0b0b0b"
# (anahtar, etiket, renk, energy_flows() kalemleri) - pozitif yigin, alttan uste
FLOW_STACK = [
    ("aero", "Aerodinamik (çekiş)", C_AERO, ["aero_cekis"]),
    ("roll", "Yuvarlanma (çekiş)", C_ROLL, ["yuvarlanma_cekis"]),
    ("acc", "İvmelenme (çekiş)", C_ACC, ["ivme_cekis"]),
    ("grade", "Eğim (çekiş)", C_GRADE, ["egim_cekis"]),
    ("loss", "Güç aktarım kayıpları (çekiş)", C_LOSS, ["aktarma_cekis", "motor_kaybi"]),
    ("aux", "Yardımcı yük", C_AUX, ["yardimci"]),
]
RECOVERED_LABEL = "Rejenerasyonla geri kazanılan"
NET_LABEL = "Net E_bat (batarya uç tarafı)"
LABEL_MIN_PCT = 5.0       # bu yuzdeden buyuk dilimlerin icine etiket yazilir
LABEL_MIN_HEIGHT = 0.06   # ...ve dilim en buyuk cubugun bu payindan yuksekse (yazi sigsin)
BAR_WIDTH = 0.6
DIAMOND_DX = 0.36         # net E_bat elmasi cubugun sag kenarinda (yuzde etiketini ortmez)


def _window_mask(t_s: np.ndarray, t_window) -> np.ndarray:
    """Zaman penceresindeki ornekler icin boolean maske."""
    if t_window is None:
        return np.ones_like(t_s, dtype=bool)
    return (t_s >= t_window[0]) & (t_s <= t_window[1])


def _base_layout(fig: go.Figure, title: str, height: int) -> go.Figure:
    """Ortak gorunum: baslik, yukseklik, kenar boslugu, ALTTA lejant, ondalik virgul."""
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left"),
        height=height,
        margin=dict(l=60, r=20, t=70, b=120),
        legend=dict(orientation="h", yanchor="top", y=LEGEND_Y, x=0, xanchor="left"),
        hoverlabel=dict(namelength=-1),
        separators=",.",
    )
    fig.update_xaxes(gridcolor=GRID_COLOR)
    fig.update_yaxes(gridcolor=GRID_COLOR)
    return fig


def _fmt_tr(x: float, nd: int = 1) -> str:
    """Ondalik virgullu, tipografik eksili sayi (etiket metinleri icin)."""
    return f"{x:.{nd}f}".replace(".", ",").replace("-", "−")


def _with_zero_crossings(t: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Isaret degistiren her aralığa y=0 noktasini (dogrusal) ekler.

    Boylece pozitif ve negatif dolgular sifirda birlesir, aralarinda bosluk kalmaz.
    Yalnizca cizim icindir; model sonucunu degistirmez.
    """
    i = np.where(np.sign(y[:-1]) * np.sign(y[1:]) < 0)[0]
    t_zero = t[i] - y[i] * (t[i + 1] - t[i]) / (y[i + 1] - y[i])
    t_all = np.concatenate([t, t_zero])
    y_all = np.concatenate([y, np.zeros_like(t_zero)])
    order = np.argsort(t_all, kind="stable")
    return t_all[order], y_all[order]


# ---------------------------------------------------------------------------
# Hiz - zaman
# ---------------------------------------------------------------------------
def fig_speed_profiles(cycles: dict, t_window=None, v_max_kmh: float = 140.0) -> go.Figure:
    """Donguler alt alta, ortak x ve ayni y olcegi (0 - v_max_kmh).

    cycles: {ad: (t_s, v_kmh)}
    """
    n = len(cycles)
    fig = make_subplots(rows=n, cols=1, shared_xaxes=True, vertical_spacing=0.04,
                        subplot_titles=[f"<b>{name}</b>" for name in cycles])
    for row, (name, (t, v)) in enumerate(cycles.items(), start=1):
        m = _window_mask(t, t_window)
        fig.add_trace(go.Scatter(
            x=t[m], y=v[m], mode="lines", name=name, showlegend=False,
            line=dict(color=C_LINE, width=1.5),
            hovertemplate="t = %{x:.0f} s<br>v = %{y:.1f} km/h<extra>" + name + "</extra>",
        ), row=row, col=1)
        fig.update_yaxes(title_text="v [km/h]", range=[0, v_max_kmh], row=row, col=1)
    fig.update_xaxes(title_text="Zaman [s]", row=n, col=1)
    for ann in fig.layout.annotations:  # panel basliklari sola yasli
        ann.update(x=0, xanchor="left", font=dict(size=12))
    fig.update_layout(hovermode="x")
    return _base_layout(fig, "Hız–zaman", max(PLOT_HEIGHT_PX, PANEL_HEIGHT_PX * n + 100))


# ---------------------------------------------------------------------------
# Batarya gucu - zaman
# ---------------------------------------------------------------------------
def fig_power_profiles(results: dict, p_reg_max_w: float, t_window=None) -> go.Figure:
    """Donguler YAN YANA, tum panellerde AYNI y olcegi (odev 3A).

    results: {dongu_adi: SimResult}
    Mavi dolgu P_bat > 0 (cekis), turuncu dolgu P_bat < 0 (rejenerasyon),
    koyu gri kesikli -P_reg,max (son panelde degeriyle etiketli), ince siyah y = 0.
    Y ekseni degerleri her panelde gosterilir. Fare: t, v, P_bat, P_w.
    """
    n = len(results)
    fig = make_subplots(rows=1, cols=n, shared_yaxes=True, horizontal_spacing=0.035,
                        subplot_titles=[f"<b>{name}</b>" for name in results])
    p_lim_kw = -p_reg_max_w / 1e3
    for col, (name, r) in enumerate(results.items(), start=1):
        m = _window_mask(r.t_s, t_window)
        t, p_kw = r.t_s[m], r.p_bat_w[m] / 1e3
        t_f, p_f = _with_zero_crossings(t, p_kw)
        first = col == 1

        fig.add_trace(go.Scatter(
            x=t_f, y=np.maximum(p_f, 0), mode="lines", fill="tozeroy",
            line=dict(width=0, color=C_LINE), fillcolor=C_LINE, opacity=0.85,
            name="Çekiş (P_bat > 0)", legendgroup="cekis", showlegend=first,
            hoverinfo="skip"), row=1, col=col)
        fig.add_trace(go.Scatter(
            x=t_f, y=np.minimum(p_f, 0), mode="lines", fill="tozeroy",
            line=dict(width=0, color=C_REGEN), fillcolor=C_REGEN, opacity=0.85,
            name="Rejenerasyon (P_bat < 0)", legendgroup="rejen", showlegend=first,
            hoverinfo="skip"), row=1, col=col)
        fig.add_trace(go.Scatter(
            x=[t[0], t[-1]], y=[p_lim_kw, p_lim_kw], mode="lines",
            line=dict(color=C_LIMIT, width=1.5, dash="dash"),
            name="−P_reg,max", legendgroup="sinir", showlegend=first,
            hoverinfo="skip"), row=1, col=col)
        if col == n:  # sinir degeri etiketi son panelin sag ucunda
            fig.add_annotation(x=t[-1], y=p_lim_kw, text=f"−P_reg,max = {_fmt_tr(p_lim_kw)} kW",
                               xanchor="right", yanchor="bottom", showarrow=False,
                               font=dict(size=11, color=C_LIMIT), row=1, col=col)
        fig.add_hline(y=0, line=dict(color="black", width=0.6), row=1, col=col)

        # gorunmez cizgi: yalnizca fare ustu bilgi kutusu icin
        custom = np.column_stack([r.v_ms[m] * 3.6, r.p_w_w[m] / 1e3])
        fig.add_trace(go.Scatter(
            x=t, y=p_kw, mode="lines", line=dict(width=0, color="rgba(0,0,0,0)"),
            customdata=custom, showlegend=False, name=name,
            hovertemplate=("t = %{x:.0f} s<br>v = %{customdata[0]:.1f} km/h"
                           "<br>P_bat = %{y:.2f} kW<br>P_w = %{customdata[1]:.2f} kW"
                           "<extra>" + name + "</extra>")), row=1, col=col)
        fig.update_xaxes(title_text="Zaman [s]", row=1, col=col)
    fig.update_yaxes(title_text="P_bat [kW]", row=1, col=1)
    fig.update_yaxes(showticklabels=True, tickfont=dict(size=11))  # tum panellerde okunur
    for ann in fig.layout.annotations:
        if ann.text and ann.text.startswith("<b>"):  # panel basliklari
            ann.update(font=dict(size=12))
    fig.update_layout(hovermode="x")
    return _base_layout(fig, "Batarya gücü–zaman (tüm paneller aynı y ölçeği)",
                        PLOT_HEIGHT_PX + 40)


# ---------------------------------------------------------------------------
# SoC - zaman
# ---------------------------------------------------------------------------
def fig_soc(results: dict, t_window=None) -> go.Figure:
    """Secili donguler tek grafikte; her dongu kendi sabit renginde."""
    fig = go.Figure()
    for name, r in results.items():
        m = _window_mask(r.t_s, t_window)
        fig.add_trace(go.Scatter(
            x=r.t_s[m], y=r.soc_pct[m], mode="lines", name=name,
            line=dict(color=CYCLE_COLORS.get(name, C_LINE), width=2),
            hovertemplate="t = %{x:.0f} s<br>SoC = %{y:.3f} %<extra>" + name + "</extra>",
        ))
    fig.update_xaxes(title_text="Zaman [s]")
    fig.update_yaxes(title_text="SoC [%]")
    fig.update_layout(hovermode="x unified")
    return _base_layout(fig, "SoC–zaman", PLOT_HEIGHT_PX)


# ---------------------------------------------------------------------------
# Enerji dagilimi
# ---------------------------------------------------------------------------
def _scaled(f: dict, per_km: bool) -> dict:
    """energy_flows() sozlugu -> Wh veya Wh/km."""
    k = 1.0 / f["mesafe_km"] if per_km else 1.0
    return {key: (val * k if key != "mesafe_km" else val) for key, val in f.items()}


def fig_energy_breakdown(flows: dict, per_km: bool = True) -> go.Figure:
    """Yigilmis cubuk: bataryadan cekilen brut enerji (pozitif) ve geri kazanilan (negatif).

    flows: {dongu: analysis.a3_cycles.energy_flows(r, p)}. Pozitif yigin = aero + yuvarlanma +
    ivmelenme (+ egim) [cekis adimlari, tekerlek] + cekis tarafi guc aktarim kayiplari + yardimci;
    sifirin altinda geri kazanilan. Elmas: net E_bat = pozitif - geri kazanilan (assert).
    Frenleme kayiplari (rejen. kaybi, surtunmeli fren, aktarma-frenleme) ivmelenme enerjisinin
    geri kazanilamayan kismidir; ayri dilim degildir (cift sayim olurdu), hover'da gosterilir.
    """
    names = list(flows)
    unit = "Wh/km" if per_km else "Wh"
    sf = {n: _scaled(flows[n], per_km) for n in names}
    stack = [s for s in FLOW_STACK
             if s[0] != "grade" or any(abs(sf[n]["egim_cekis"]) > 1e-9 for n in names)]
    totals = {n: sum(sf[n][k] for _, _, _, keys in stack for k in keys) for n in names}
    for n in names:  # pozitif yigin - geri kazanilan = E_bat
        net = totals[n] - sf[n]["geri_kazanilan"]
        assert abs(net - sf[n]["E_bat"]) <= 1e-9 * max(abs(totals[n]), 1.0), \
            f"{n}: pozitif yigin - geri kazanilan != E_bat"

    xs = list(range(len(names)))  # sayisal x: elmas cubugun kenarina kaydirilabilsin
    h_min = LABEL_MIN_HEIGHT * max(totals.values())

    def label_text(vals, pcts, sign=""):
        return [f"{sign}%{_fmt_tr(p, 0)}" if p > LABEL_MIN_PCT and abs(v) >= h_min else ""
                for v, p in zip(vals, pcts)]

    fig = go.Figure()
    for key, label, color, keys in stack:
        y = [sum(sf[n][k] for k in keys) for n in names]
        pct = [v / totals[n] * 100 for v, n in zip(y, names)]
        if key == "loss":
            custom = [[sf[n]["aktarma_cekis"], sf[n]["motor_kaybi"], p] for n, p in zip(names, pct)]
            extra = ("<br>  aktarma (çekiş): %{customdata[0]:.1f}<br>  motor + invertör (çekiş): "
                     "%{customdata[1]:.1f}<br><i>frenleme kayıpları ivmelenme diliminde</i>")
        elif key == "acc":
            custom = [[sf[n]["geri_kazanilan"], sf[n]["rejen_kaybi"], sf[n]["aktarma_fren"],
                       sf[n]["surtunmeli_fren"], sf[n]["aero_fren"] + sf[n]["yuvarlanma_fren"], p]
                      for n, p in zip(names, pct)]
            extra = ("<br>kinetik enerjinin akıbeti:<br>  geri kazanılan: %{customdata[0]:.1f}"
                     "<br>  rejenerasyon kaybı: %{customdata[1]:.1f}"
                     "<br>  aktarma kaybı (frenleme): %{customdata[2]:.1f}"
                     "<br>  sürtünmeli fren: %{customdata[3]:.1f}"
                     "<br>  frenlemede aero + yuvarlanma: %{customdata[4]:.1f}")
        else:
            custom = [[p] for p in pct]
            extra = ""
        custom = [[*c, n] for c, n in zip(custom, names)]  # son eleman: dongu adi (hover)
        fig.add_trace(go.Bar(
            x=xs, y=y, width=BAR_WIDTH, name=label, customdata=custom,
            marker=dict(color=color, line=dict(width=1, color="white")),
            text=label_text(y, pct),
            textposition="inside", insidetextanchor="middle", textangle=0,
            textfont=dict(color="white" if key not in ("roll",) else C_INK, size=11),
            hovertemplate="%{customdata[" + str(len(custom[0]) - 1) + "]}<br><b>" + label
                          + "</b>: %{y:.1f} " + unit
                          + " (%{customdata[" + str(len(custom[0]) - 2) + "]:.1f} %)"
                          + extra + "<extra></extra>"))
    rec = [-sf[n]["geri_kazanilan"] for n in names]
    rec_pct = [-r / totals[n] * 100 for r, n in zip(rec, names)]
    fig.add_trace(go.Bar(
        x=xs, y=rec, width=BAR_WIDTH, name=RECOVERED_LABEL,
        customdata=[[p, n] for p, n in zip(rec_pct, names)],
        marker=dict(color=C_RECOVERED, line=dict(width=1, color="white"),
                    pattern=dict(shape="/", fgcolor=C_ACC, size=6, solidity=0.25)),
        text=label_text(rec, rec_pct, sign="−"),
        textposition="inside", insidetextanchor="middle", textangle=0,
        textfont=dict(color=C_INK, size=11),
        hovertemplate="%{customdata[1]}<br><b>" + RECOVERED_LABEL + "</b>: %{y:.1f} " + unit
                      + " (brütün %{customdata[0]:.1f} %'i)<extra></extra>"))
    nets = [sf[n]["E_bat"] for n in names]
    fig.add_trace(go.Scatter(
        x=[x + DIAMOND_DX for x in xs], y=nets, mode="markers", name=NET_LABEL,
        customdata=names, cliponaxis=False,
        marker=dict(symbol="diamond", size=13, color=C_INK, line=dict(width=1.5, color="white")),
        hovertemplate="%{customdata}<br><b>" + NET_LABEL + "</b>: %{y:.1f} " + unit
                      + "<extra></extra>"))
    for x, n, net in zip(xs, names, nets):  # net degeri cubugun ustunde
        fig.add_annotation(x=x, y=totals[n], text=f"E_bat = {_fmt_tr(net)}", showarrow=False,
                           yanchor="bottom", font=dict(size=11, color=C_INK))
    fig.add_hline(y=0, line=dict(color=C_INK, width=1))
    fig.update_layout(barmode="relative")
    fig.update_xaxes(title_text="Döngü", tickmode="array", tickvals=xs, ticktext=names,
                     range=[-0.6, len(names) - 0.4])
    fig.update_yaxes(title_text=f"Enerji [{unit}]")
    return _base_layout(fig, f"Enerji dağılımı [{unit}]: brüt çekilen, geri kazanılan ve net",
                        PLOT_HEIGHT_PX + 120)


# Sankey dugumleri: (anahtar, etiket, renk)
SANKEY_NODES = [
    ("bat", "Batarya (brüt çekilen)", C_INK),
    ("aux", "Yardımcı yük", C_AUX),
    ("motor", "Motor/invertör", C_LINE),
    ("motor_loss", "Motor kaybı", C_LOSS),
    ("red", "Redüktör", C_LINE),
    ("trans_loss", "Aktarma kaybı", C_LOSS),
    ("wheel", "Tekerlek", C_LINE),
    ("aero", "Aerodinamik", C_AERO),
    ("roll", "Yuvarlanma", C_ROLL),
    ("grade", "Eğim", C_GRADE),
    ("kin", "Kinetik enerji", C_ACC),
    ("friction", "Sürtünmeli fren", C_LOSS),
    ("regen_loss", "Rejenerasyon kayıpları", C_LOSS),
    ("recovered", "Bataryaya geri dönen", C_RECOVERED),
    ("kin_net", "Kinetik enerji değişimi (net)", C_ACC),
]
# Sankey akislari: (kaynak, hedef, energy_flows() kalemleri, renk)
SANKEY_LINKS = [
    ("bat", "aux", ["yardimci"], C_AUX),
    ("bat", "motor", ["motor_girisi"], C_LINE),
    ("motor", "motor_loss", ["motor_kaybi"], C_LOSS),
    ("motor", "red", ["aktarma_cekis", "tekerlek_cekis"], C_LINE),
    ("red", "trans_loss", ["aktarma_cekis"], C_LOSS),
    ("red", "wheel", ["tekerlek_cekis"], C_LINE),
    ("wheel", "aero", ["aero_cekis"], C_AERO),
    ("wheel", "roll", ["yuvarlanma_cekis"], C_ROLL),
    ("wheel", "grade", ["egim_cekis"], C_GRADE),
    ("wheel", "kin", ["ivme_cekis"], C_ACC),
    ("kin", "aero", ["aero_fren"], C_AERO),
    ("kin", "roll", ["yuvarlanma_fren"], C_ROLL),
    ("kin", "grade", ["egim_fren"], C_GRADE),
    ("kin", "friction", ["surtunmeli_fren"], C_LOSS),
    ("kin", "trans_loss", ["aktarma_fren"], C_LOSS),
    ("kin", "regen_loss", ["rejen_kaybi"], C_LOSS),
    ("kin", "recovered", ["geri_kazanilan"], C_RECOVERED),
    ("kin", "kin_net", ["kinetik_net"], C_ACC),
]
SANKEY_MIN_SHARE = 1e-4   # brut enerjinin bu payindan kucuk akislar cizilmez (orn. ~0 egim)


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})"


def fig_energy_sankey(flow: dict, cycle_name: str, per_km: bool = True) -> go.Figure:
    """Tek dongu icin enerji akis (Sankey) diyagrami; flow = energy_flows(r, p).

    Frenleme anindaki aero/yuvarlanma direnci kinetik enerjiden karsilanir: "Kinetik enerji"
    dugumunden Aerodinamik ve Yuvarlanma dugumlerine giden akislar olarak gosterilir.
    Ara dugumlerde giris = cikis assert ile denetlenir. Negatif akis (orn. inis egimi)
    cizilemez; varsa grafigin altinda not edilir.
    """
    unit = "Wh/km" if per_km else "Wh"
    sf = _scaled(flow, per_km)
    vals = [(s, t, sum(sf[k] for k in keys), c) for s, t, keys, c in SANKEY_LINKS]
    for node in ("motor", "red", "wheel", "kin"):  # ara dugum dengesi
        inn = sum(v for s, t, v, _ in vals if t == node)
        out = sum(v for s, t, v, _ in vals if s == node)
        assert abs(inn - out) <= 1e-9 * max(abs(sf["batarya_brut"]), 1.0), \
            f"{cycle_name}: '{node}' dugumunde giris != cikis"
    tol = SANKEY_MIN_SHARE * sf["batarya_brut"]
    negative = [(s, t, v) for s, t, v, _ in vals if v < -tol]
    shown = [(s, t, v, c) for s, t, v, c in vals if v > tol]
    used = {s for s, *_ in shown} | {t for _, t, *_ in shown}
    nodes = [n for n in SANKEY_NODES if n[0] in used]
    idx = {key: i for i, (key, _, _) in enumerate(nodes)}
    labels = {key: label for key, label, _ in SANKEY_NODES}
    fig = go.Figure(go.Sankey(
        arrangement="snap", valueformat=".1f", valuesuffix=f" {unit}",
        node=dict(label=[label for _, label, _ in nodes], color=[c for _, _, c in nodes],
                  pad=30, thickness=16, line=dict(width=0.5, color="white")),
        link=dict(source=[idx[s] for s, *_ in shown], target=[idx[t] for _, t, *_ in shown],
                  value=[v for _, _, v, _ in shown], color=[_rgba(c, 0.45) for *_, c in shown],
                  hovertemplate="%{source.label} → %{target.label}: %{value}<extra></extra>")))
    if negative:
        fig.add_annotation(text="Gösterilmeyen negatif akış: " + ", ".join(
            f"{labels[s]} → {labels[t]} ({_fmt_tr(v)} {unit})" for s, t, v in negative),
            x=0, y=-0.08, xref="paper", yref="paper", showarrow=False, xanchor="left",
            font=dict(size=11, color=C_LIMIT))
    fig = _base_layout(fig, f"Enerji akışı – {cycle_name} [{unit}]: brüt çekilen "
                            f"{_fmt_tr(sf['batarya_brut'])}, geri dönen "
                            f"{_fmt_tr(sf['geri_kazanilan'])}, net E_bat {_fmt_tr(sf['E_bat'])}",
                       PLOT_HEIGHT_PX + 220)
    fig.update_layout(margin=dict(l=40, r=40, t=70, b=50), title=dict(x=0.01))
    return fig


# ---------------------------------------------------------------------------
# Motor calisma noktalari
# ---------------------------------------------------------------------------
def fig_motor_points(results: dict, p: VehicleParams, n_points: int = 400) -> go.Figure:
    """n_m - T_m dagilimi (yalnizca cekis adimlari, P_w >= 0) + tepe tork zarfi.

    Zarf disi kosulu model.py 3.7 ile ayni: cekis ve T_m > T_max(n_m).
    Zarf parametreleri (t_peak_nm, p_peak_w) tanimli olmalidir.
    """
    fig = go.Figure()
    n_all, t_all, name_all, ts_all, v_all = [], [], [], [], []
    for name, r in results.items():
        trac = r.p_w_w >= 0
        n_all.append(r.n_m_rpm[trac])
        t_all.append(r.t_m_nm[trac])
        ts_all.append(r.t_s[trac])
        v_all.append(r.v_ms[trac] * 3.6)
        name_all.append(np.full(trac.sum(), name, dtype=object))
    n_m, t_m = np.concatenate(n_all), np.concatenate(t_all)
    custom = np.column_stack([np.concatenate(name_all), np.concatenate(ts_all),
                              np.concatenate(v_all)])
    outside = t_m > t_max_nm(n_m, p.t_peak_nm, p.p_peak_w, p.n_max_rpm)

    hover = ("%{customdata[0]}<br>t = %{customdata[1]:.0f} s, v = %{customdata[2]:.1f} km/h"
             "<br>n_m = %{x:.0f} rpm<br>T_m = %{y:.1f} Nm<extra></extra>")
    for mask, label, color, size in [(~outside, "Zarf içinde", C_LINE, 5),
                                     (outside, "Zarf dışı", C_ALERT, 8)]:
        fig.add_trace(go.Scattergl(
            x=n_m[mask], y=t_m[mask], mode="markers", name=f"{label} ({mask.sum()})",
            marker=dict(color=color, size=size, opacity=0.55,
                        line=dict(width=0.5, color="white")),
            customdata=custom[mask], hovertemplate=hover))

    n_end = p.n_max_rpm if p.n_max_rpm is not None else max(n_m.max(), 1.0) * 1.1
    n_grid = np.linspace(0, n_end, n_points)
    fig.add_trace(go.Scatter(
        x=n_grid, y=t_max_nm(n_grid, p.t_peak_nm, p.p_peak_w, p.n_max_rpm),
        mode="lines", name="Tepe tork zarfı T_max(n_m)",
        line=dict(color=C_LIMIT, width=2),
        hovertemplate="n_m = %{x:.0f} rpm<br>T_max = %{y:.1f} Nm<extra></extra>"))
    fig.update_xaxes(title_text="Motor devri n_m [rpm]")
    fig.update_yaxes(title_text="Motor torku T_m [Nm]", rangemode="tozero")
    return _base_layout(fig, "Motor çalışma noktaları (çekiş adımları)", PLOT_HEIGHT_PX + 60)


# ---------------------------------------------------------------------------
# Verim haritasi (Asama 2 - [R24] Sekil 5a)
# ---------------------------------------------------------------------------
# Sirali (tek ton) mavi rampa: dusuk verim acik, yuksek verim koyu
_SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


def fig_efficiency_map(n_rpm: np.ndarray, t_nm: np.ndarray, eta: np.ndarray,
                       map_points: tuple, op_points: dict, envelope: tuple | None = None,
                       title: str = "Motor + invertör verim haritası") -> go.Figure:
    """Verim haritasi (kontur) + calisma noktalari + okunan harita noktalari + zarf.

    n_rpm[nx], t_nm[ny], eta[ny, nx] : izgara (zarf ustu NaN olabilir; cizilmez)
    map_points : (n, T) haritadan okunan noktalar
    op_points  : {etiket: (n, T)}; "geri kazanim" iceren etiket turuncu, digerleri koyu
    envelope   : (n, T_max) tepe tork zarfi (istege bagli)
    Hesap yapilmaz; tum diziler cagiran tarafindan hazirlanir.
    """
    steps = np.linspace(0, 1, len(_SEQ_BLUE))
    fig = go.Figure(go.Contour(
        x=n_rpm, y=t_nm, z=eta, colorscale=[[s, c] for s, c in zip(steps, _SEQ_BLUE)],
        contours=dict(coloring="heatmap", showlabels=True, start=0.70, end=0.97, size=0.01,
                      labelfont=dict(size=9, color="white")),
        line=dict(width=0.5, color="rgba(255,255,255,0.5)"),
        colorbar=dict(title=dict(text="η [-]"), thickness=12),
        hovertemplate="n = %{x:.0f} rpm<br>T = %{y:.0f} Nm<br>η = %{z:.3f}<extra>harita</extra>",
        name="η(n, T)", showscale=True))
    for label, (n, t) in op_points.items():
        regen = "geri" in label.lower()
        fig.add_trace(go.Scattergl(
            x=n, y=t, mode="markers", name=f"{label} ({len(n)})",
            marker=dict(size=5, color=C_REGEN if regen else C_INK, opacity=0.6,
                        line=dict(width=0.5, color="white")),
            hovertemplate="n = %{x:.0f} rpm<br>|T| = %{y:.1f} Nm<extra>" + label + "</extra>"))
    fig.add_trace(go.Scatter(
        x=map_points[0], y=map_points[1], mode="markers", name="Haritadan okunan nokta",
        marker=dict(symbol="x-thin", size=7, color="white", line=dict(width=1.5, color="white")),
        hovertemplate="okunan: n = %{x:.0f} rpm, T = %{y:.0f} Nm<extra></extra>"))
    if envelope is not None:
        fig.add_trace(go.Scatter(
            x=envelope[0], y=envelope[1], mode="lines", name="Tepe tork zarfı",
            line=dict(color=C_LIMIT, width=2),
            hovertemplate="n = %{x:.0f} rpm<br>T_max = %{y:.0f} Nm<extra></extra>"))
    fig.update_xaxes(title_text="Motor devri n_m [rpm]")
    fig.update_yaxes(title_text="Motor torku |T_m| [Nm]", rangemode="tozero")
    return _base_layout(fig, title, PLOT_HEIGHT_PX + 120)


# ---------------------------------------------------------------------------
# Yol yuku egrileri (Asama 2 - Tesla parametre turetme)
# ---------------------------------------------------------------------------
def fig_road_load(v_kmh: np.ndarray, curves: dict) -> go.Figure:
    """CoC yol yuku egrisi ve yontem yaklasimlari ust uste.

    curves: {ad: F_N}; ilk eleman CoC referansi (kalin gri), digerleri kategorik sirada.
    Egriler analysis.p2_road_load.road_load_curves() ile hazirlanir; burada hesap yapilmaz.
    """
    fig = go.Figure()
    dashes = ["solid", "dash", "solid", "dashdot", "dot"]
    for i, (name, f_n) in enumerate(curves.items()):
        ref = i == 0
        fig.add_trace(go.Scatter(
            x=v_kmh, y=f_n, mode="lines", name=name,
            line=dict(color=C_LIMIT if ref else _CATEGORICAL[i - 1],
                      width=3 if ref else 2, dash=dashes[i % len(dashes)]),
            hovertemplate="v = %{x:.1f} km/h<br>F = %{y:.1f} N<extra>" + name + "</extra>"))
    fig.update_xaxes(title_text="v [km/h]")
    fig.update_yaxes(title_text="F [N]", rangemode="tozero")
    fig.update_layout(hovermode="x unified")
    return _base_layout(fig, "Yol yükü: CoC eğrisi ve iki terimli model yaklaşımları",
                        PLOT_HEIGHT_PX)


# ---------------------------------------------------------------------------
# Senaryo karsilastirma
# ---------------------------------------------------------------------------
def fig_scenario_comparison(names: list, wh_km: list, change_pct: list,
                            cycle_name: str) -> go.Figure:
    """Senaryo basina tuketim cubugu; ilk eleman baseline (gri), uzerinde % degisim."""
    colors = [C_MUTED] + [C_LINE] * (len(names) - 1)
    text = ["referans"] + [f"{_fmt_tr(c)} %" if c < 0 else f"+{_fmt_tr(c)} %"
                           for c in change_pct[1:]]
    fig = go.Figure(go.Bar(
        x=names, y=wh_km, marker=dict(color=colors), text=text, textposition="outside",
        hovertemplate="%{x}<br>%{y:.2f} Wh/km<extra></extra>", showlegend=False))
    fig.add_hline(y=wh_km[0], line=dict(color=C_LIMIT, width=1, dash="dash"))
    fig.update_xaxes(title_text="Senaryo")
    fig.update_yaxes(title_text="Tüketim [Wh/km]", rangemode="tozero")
    return _base_layout(fig, f"3B senaryoları – {cycle_name} tüketimi [Wh/km]", PLOT_HEIGHT_PX)


# ---------------------------------------------------------------------------
# Surus simulatoru (animasyon): hiz, P_bat, SoC + gostergeler
# ---------------------------------------------------------------------------
ANIM_FRAME_MS = 40        # 1x oynatma hizinda kare suresi; hiz carpanina bolunur
ANIM_CONTROLS_PX = 90       # grafik ustundeki oynat/kaydirici seridi
ANIM_HEIGHT_PX = 820


def _gauge(value: float, title: str, unit: str, lo: float, hi: float, color: str,
           steps: list | None = None) -> go.Indicator:
    return go.Indicator(
        mode="gauge+number", value=value,
        number=dict(suffix=f" {unit}", valueformat=".1f", font=dict(size=26)),
        title=dict(text=title, font=dict(size=13)),
        gauge=dict(axis=dict(range=[lo, hi], tickfont=dict(size=10)),
                   bar=dict(color=color, thickness=0.35), steps=steps or [],
                   borderwidth=0))


def fig_drive_animation(r, cycle_name: str, p_reg_max_w: float, step_s: int = 5,
                        speed: float = 1.0) -> go.Figure:
    """Dongunun saniye saniye oynatilmasi (Plotly kareleri, oynat/durdur + kaydirici).

    speed: oynatma hizi carpani (0,5 = yari hiz); kare suresi ANIM_FRAME_MS / speed.

    Sol: hiz, batarya gucu, SoC egrileri (tam dongu soluk) + o anki nokta ve dikey cizgi.
    Sag: hiz, P_bat ve SoC gostergeleri. Baslikta kat edilen mesafe ve bataryadan cekilen
    net enerji (SimResult alanlarinin kumulatif toplami; yalnizca gosterim).
    """
    t, v_kmh = r.t_s, r.v_ms * 3.6
    p_kw, soc = r.p_bat_w / 1e3, r.soc_pct
    dt_s = float(t[1] - t[0])
    s_km = np.cumsum(r.v_ms) * dt_s / 1000.0
    e_wh = np.cumsum(r.e_step_wh)
    p_lo = min(-p_reg_max_w / 1e3, float(p_kw.min())) * 1.1
    p_hi = max(float(p_kw.max()) * 1.1, 10.0)
    v_hi = max(140.0, float(v_kmh.max()) * 1.05)
    soc_lo, soc_hi = float(soc.min()), float(soc.max())
    pad = max((soc_hi - soc_lo) * 0.1, 0.05)

    fig = make_subplots(
        rows=3, cols=2, column_widths=[0.7, 0.3], shared_xaxes=True,
        vertical_spacing=0.12, horizontal_spacing=0.08,
        specs=[[{"type": "xy"}, {"type": "indicator"}],
               [{"type": "xy"}, {"type": "indicator"}],
               [{"type": "xy"}, {"type": "indicator"}]])
    series = [(v_kmh, C_LINE, "v [km/h]"), (p_kw, C_REGEN, "P_bat [kW]"),
              (soc, "#1baf7a", "SoC [%]")]
    for row, (y, color, label) in enumerate(series, start=1):
        fig.add_trace(go.Scatter(x=t, y=y, mode="lines", line=dict(color=color, width=1.2),
                                 opacity=0.35, showlegend=False, hoverinfo="skip"), row=row, col=1)
        fig.update_yaxes(title_text=label, row=row, col=1)
    fig.update_yaxes(range=[0, v_hi], row=1, col=1)
    fig.update_yaxes(range=[p_lo, p_hi], row=2, col=1)
    fig.update_yaxes(range=[soc_lo - pad, soc_hi + pad], row=3, col=1)
    fig.add_hline(y=-p_reg_max_w / 1e3, line=dict(color=C_LIMIT, width=1, dash="dash"),
                  row=2, col=1)
    fig.update_xaxes(title_text="Zaman [s]", row=3, col=1)

    # hareketli izler: 3 nokta + 3 gosterge (indeksleri kareler icin sakla)
    moving_start = len(fig.data)
    for row, (y, color, _) in enumerate(series, start=1):
        fig.add_trace(go.Scatter(x=[t[0]], y=[y[0]], mode="markers", showlegend=False,
                                 marker=dict(size=12, color=color, line=dict(width=2, color="white")),
                                 hoverinfo="skip"), row=row, col=1)
    fig.add_trace(_gauge(v_kmh[0], "Hız", "km/h", 0, v_hi, C_LINE), row=1, col=2)
    fig.add_trace(_gauge(p_kw[0], "Batarya gücü", "kW", p_lo, p_hi, "#eda100",
                         steps=[dict(range=[p_lo, 0], color="rgba(235,104,52,0.25)"),
                                dict(range=[0, p_hi], color="rgba(42,120,214,0.15)")]),
                  row=2, col=2)
    fig.add_trace(_gauge(soc[0], "SoC", "%", 0, 100, "#1baf7a"), row=3, col=2)
    moving = list(range(moving_start, len(fig.data)))

    def title_at(i: int) -> str:
        mode = "çekiş" if p_kw[i] > 0.5 else ("rejenerasyon" if p_kw[i] < 0 else "rölanti / sabit")
        return (f"<b>{cycle_name}</b> · t = {t[i]:.0f} s · s = {_fmt_tr(s_km[i], 2)} km · "
                f"E_bat = {_fmt_tr(e_wh[i], 0)} Wh · mod: {mode}")

    idx = list(range(0, len(t), step_s))
    if idx[-1] != len(t) - 1:
        idx.append(len(t) - 1)
    frames = []
    for i in idx:
        frames.append(go.Frame(
            name=f"{t[i]:.0f}", traces=moving,
            data=[go.Scatter(x=[t[i]], y=[v_kmh[i]]), go.Scatter(x=[t[i]], y=[p_kw[i]]),
                  go.Scatter(x=[t[i]], y=[soc[i]]), go.Indicator(value=v_kmh[i]),
                  go.Indicator(value=p_kw[i]), go.Indicator(value=soc[i])],
            layout=dict(title=dict(text=title_at(i)))))
    fig.frames = frames
    frame_ms = ANIM_FRAME_MS / speed
    play = dict(frame=dict(duration=frame_ms, redraw=False), fromcurrent=True,
                transition=dict(duration=0))
    # Kontroller USTTE: baslik en ustte, altinda Oynat/Durdur ve zaman kaydiricisi; kaydiricinin
    # tik etiketleri gizli (sik cizgi kalabaligi), o anki zaman "t = ... s" olarak yazilir.
    fig.update_layout(
        title=dict(text=title_at(0), x=0, xanchor="left", y=0.985, yanchor="top",
                   yref="container"),
        height=ANIM_HEIGHT_PX + ANIM_CONTROLS_PX,
        margin=dict(l=60, r=20, t=ANIM_CONTROLS_PX + 40, b=50), separators=",.",
        showlegend=False,
        updatemenus=[dict(type="buttons", direction="left", x=0, y=1.0, xanchor="left",
                          yanchor="bottom", pad=dict(r=10, t=0, b=34), showactive=False,
                          bgcolor="#2a78d6", bordercolor="#2a78d6", font=dict(color="white", size=13),
                          buttons=[
                              dict(label="▶  Oynat", method="animate", args=[None, play]),
                              dict(label="⏸  Durdur", method="animate",
                                   args=[[None], dict(frame=dict(duration=0, redraw=False),
                                                      mode="immediate")])])],
        sliders=[dict(active=0, x=0.2, y=1.0, len=0.8, xanchor="left", yanchor="bottom",
                      pad=dict(t=0, b=30), ticklen=0, minorticklen=0, tickcolor="rgba(0,0,0,0)",
                      font=dict(size=1, color="rgba(0,0,0,0)"),
                      bgcolor="#e8f0fa", activebgcolor="#2a78d6", bordercolor="#2a78d6",
                      currentvalue=dict(visible=True, prefix="t = ", suffix=" s", xanchor="right",
                                        font=dict(size=13, color="#2a78d6")),
                      steps=[dict(label=f.name, method="animate",
                                  args=[[f.name], dict(mode="immediate", frame=dict(
                                      duration=0, redraw=True), transition=dict(duration=0))])
                             for f in frames])])
    fig.update_xaxes(gridcolor=GRID_COLOR)
    fig.update_yaxes(gridcolor=GRID_COLOR)
    return fig


# ---------------------------------------------------------------------------
# Varsayilan ile karsilastirma (parametre degisikliginin etkisi)
# ---------------------------------------------------------------------------
def fig_compare_default(cycles: list, default_vals: list, current_vals: list,
                        quantity: str, unit: str) -> go.Figure:
    """Dongu basina varsayilan (gri) ve guncel (mavi) cubuk; uzerinde % degisim."""
    pct = [(c / d - 1) * 100 if d else 0.0 for d, c in zip(default_vals, current_vals)]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=cycles, y=default_vals, name="Varsayılan", marker_color=C_MUTED,
                         hovertemplate="%{x}<br>%{y:.2f} " + unit + "<extra>varsayılan</extra>"))
    fig.add_trace(go.Bar(x=cycles, y=current_vals, name="Güncel parametreler",
                         marker_color=C_LINE,
                         text=[f"{'+' if x >= 0 else ''}{_fmt_tr(x)} %" for x in pct],
                         textposition="outside",
                         hovertemplate="%{x}<br>%{y:.2f} " + unit + "<extra>güncel</extra>"))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title_text=f"{quantity} [{unit}]", rangemode="tozero")
    return _base_layout(fig, f"{quantity}: varsayılan ve güncel parametreler", PLOT_HEIGHT_PX)


# ---------------------------------------------------------------------------
# 3C bonus: G taramasi
# ---------------------------------------------------------------------------
def fig_g_scan(curves: dict, g_ref: float, g_upper: float, g_sel: float,
               sel_values: dict, cycle_name: str) -> go.Figure:
    """Tuketim-G egrileri (dusuk tork siniri basina), Tesla G'si, azami hiz kisiti bolgesi
    ve secili G. curves: {etiket: (G[], tuketim[])}, sel_values: {etiket: tuketim(G_sel)}.
    """
    colors = [C_LINE, C_REGEN, "#1baf7a", "#eda100"]
    fig = go.Figure()
    g_all = np.concatenate([g for g, _ in curves.values()])
    fig.add_vrect(x0=g_upper, x1=float(g_all.max()), fillcolor=C_LIMIT, opacity=0.10,
                  line_width=0, annotation_text="azami hız kısıtı ihlali",
                  annotation_position="top left", annotation_font_size=11)
    for i, (label, (g, e)) in enumerate(curves.items()):
        col = colors[i % len(colors)]
        fig.add_trace(go.Scatter(x=g, y=e, mode="lines", name=label, line=dict(color=col, width=2.5),
                                 hovertemplate="G = %{x:.2f}<br>%{y:.2f} Wh/km<extra>" + label
                                               + "</extra>"))
        if label in sel_values:
            fig.add_trace(go.Scatter(x=[g_sel], y=[sel_values[label]], mode="markers",
                                     marker=dict(size=13, color=col, symbol="diamond",
                                                 line=dict(width=2, color="white")),
                                     showlegend=False, hoverinfo="skip"))
    fig.add_vline(x=g_ref, line=dict(color=C_LIMIT, dash="dash", width=1.5),
                  annotation_text=f"araç G = {_fmt_tr(g_ref, 2)}", annotation_position="bottom right")
    fig.add_vline(x=g_sel, line=dict(color=C_INK, width=1))
    fig.update_xaxes(title_text="Redüktör oranı G [-]")
    fig.update_yaxes(title_text=f"{cycle_name} tüketimi [Wh/km]")
    fig.update_layout(hovermode="x unified")
    return _base_layout(fig, f"3C · Haritalı model ile G taraması ({cycle_name})", PLOT_HEIGHT_PX + 40)
