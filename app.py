"""
Interaktif web arayuzu (Streamlit + Plotly).

Calistirma (proje kokunden):  streamlit run app.py

Bu dosya HESAP YAPMAZ ve ACIKLAMA METNI TASIMAZ. Yalnizca su kaynaklari kullanir:
  evmodel  : simulate(), load_all_cycles(), load_phases(), VehicleParams.with_(), t_max_nm()
  analysis : 3A ve 3B tablo fonksiyonlari + sutun adi sabitleri (run_all.py ile ayni sayilar)
  tests    : run_t1(), run_t2() (dogrulama rozeti)
  app_texts: tum aciklama metinleri, bilgi kutulari, parametre yardimlari

Streamlit mantigi: kullanici her widget'a dokundugunda bu script BASTAN SONA
yeniden calisir. Degerler st.session_state'te saklanir; pahali isler
(@st.cache_data) onbellekten gelir. Onbellek anahtarina kod damgasi (STAMP)
eklenir: evmodel/analysis/tests dosyalari degisince eski sonuc kullanilmaz.

Bolumler: 0 ayarlar | 1 onbellekli veri | 2 yardimcilar | 3 parametre durumu |
          4 kenar cubugu | 5 simulasyon | 6 dogrulama rozeti | 7 ozet kartlari | 8 sekmeler
"""

import dataclasses
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app_texts as T  # noqa: E402
from analysis import a3_cycles as a3  # noqa: E402
from analysis import b3_sensitivity as b3  # noqa: E402
from analysis import c3_bonus as c3  # noqa: E402
from analysis import yorum  # noqa: E402
from evmodel.envelope import base_speed_rpm  # noqa: E402
from analysis import p2_efficiency as p2e  # noqa: E402
from analysis import p2_road_load as p2  # noqa: E402
from evmodel.efficiency_map import eta_grid, load_eta_map  # noqa: E402
from evmodel.envelope import t_max_nm  # noqa: E402
from evmodel import interactive as ia  # noqa: E402
from analysis import ogrenci_yukleme as ogr  # noqa: E402
from evmodel.cycles import (CYCLE_NAMES, EXCEL_PATH, REFERENCE_DISTANCES_KM,  # noqa: E402
                            cycle_distance_km, load_all_cycles, load_phases)
from evmodel.model import simulate  # noqa: E402
from evmodel.params import (BASE_VEHICLE, TESLA_M3_SRP, TESLA_SOURCED,  # noqa: E402
                            VehicleParams)

# ===========================================================================
# 0. Sayfa ayarlari ve arayuz sabitleri
# ===========================================================================
st.set_page_config(page_title="Elektrikli Araç Modeli · MKTS 5081", page_icon="⚡", layout="wide")

# Gorunum: baslik bandi, bilgi cipleri ve ozet kartlari (yalnizca stil)
CSS = """
<style>
.ev-hero {background: linear-gradient(120deg, #0d366b 0%, #2a78d6 55%, #1baf7a 100%);
  border-radius: 14px; padding: 18px 24px 14px 24px; margin-bottom: 10px; color: white;}
.ev-hero h1 {color: white; font-size: 1.9rem; margin: 0 0 2px 0; padding: 0;}
.ev-hero p {color: rgba(255,255,255,0.88); margin: 0 0 10px 0; font-size: 0.95rem;}
.ev-chip {display: inline-block; background: rgba(255,255,255,0.16);
  border: 1px solid rgba(255,255,255,0.30); border-radius: 999px; padding: 2px 11px;
  margin: 0 6px 6px 0; font-size: 0.82rem; color: white;}
div[data-testid="stMetric"] {background: rgba(42,120,214,0.06);
  border: 1px solid rgba(42,120,214,0.18); border-radius: 12px; padding: 10px 14px;}
.ev-nav-title {font-size: 0.8rem; font-weight: 600; letter-spacing: .06em;
  text-transform: uppercase; color: #5f6673; margin: 8px 0 4px 2px;}
.ev-nav-group {font-weight: 700; color: #2a78d6; margin-bottom: 4px;}
.ev-page-title {font-size: 1.45rem; font-weight: 700; color: #2a78d6; margin: 14px 0 6px 0;
  padding-bottom: 6px; border-bottom: 1px solid rgba(42,120,214,0.25);}
div[class*="st-key-nav_"] button {justify-content: flex-start; text-align: left;
  border-radius: 10px; transition: transform .08s ease, box-shadow .08s ease;}
div[class*="st-key-nav_"] button > div, div[class*="st-key-nav_"] button p {
  justify-content: flex-start; text-align: left; width: 100%;}
div[class*="st-key-nav_"] button:hover {transform: translateX(3px);
  box-shadow: 0 2px 8px rgba(42,120,214,0.25);}
div[class*="st-key-nav_"] button[kind="primary"],
div[class*="st-key-nav_"] button[data-testid="stBaseButton-primary"] {
  background: linear-gradient(120deg, #0d366b 0%, #2a78d6 100%); border-color: #2a78d6;
  color: white; font-weight: 600;}
div[data-testid="stMetricValue"], div[data-testid="stMetricValue"] div {
  font-size: 1.35rem !important; overflow: visible !important; white-space: nowrap;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

VEHICLES = {"Temel Araç": BASE_VEHICLE, "Tesla Model 3 SR+ (LFP)": TESLA_M3_SRP}
BASE_LABEL = "Temel Araç"
VALIDATION_TOL_PCT = 0.5     # rozet esigi (testlerdeki TOL ile ayni: %0,5)
FIRST_WINDOW_S = 200.0       # "Ilk 200 s" penceresi (odev 3A)
WINDOW_OPTIONS = ["İlk 200 s", "Tüm döngü", "Özel aralık"]
SCEN_A, SCEN_B = "Baseline", "S4"   # 3B Soru 5 karsilastirmasi
PLOTLY_CONFIG = {"displayModeBar": True, "displaylogo": False,
                 "toImageButtonOptions": {"format": "png", "scale": 3}}
HIGHLIGHT_DIFF = "background-color: rgba(235,104,52,0.25)"     # sifirdan farkli fark
HIGHLIGHT_NEGATIVE = "background-color: rgba(227,73,72,0.25)"  # negatif esik payi
ENVELOPE_LOW_FRAC = 0.5      # bilgi kutusu: zarfin bu kesrinin altindaki cekis noktalari (gosterim)
ROAD_ERR_HIGHLIGHT_PCT = 5.0  # yol yuku tablosunda |hata| bunun ustundeyse vurgula (gorsel)

# Arayuzde gosterilen parametreler: alan -> (etiket, birim, olcek, adim, bicim, min, max)
# olcek: gosterilen = SI * olcek  (orn. W -> kW icin 1e-3, m/s -> km/h icin 3.6)
PARAM_SPECS = {
    "m_kg":        ("m", "kg", 1.0, 10.0, "%.0f", 500.0, 4000.0),
    "cd":          ("C_d", "-", 1.0, 0.001, "%.3f", 0.10, 0.60),
    "af_m2":       ("A_f", "m²", 1.0, 0.01, "%.2f", 1.0, 4.0),
    "fr":          ("f_r", "-", 1.0, 0.0005, "%.4f", 0.003, 0.030),
    "delta":       ("δ", "-", 1.0, 0.01, "%.2f", 1.0, 1.3),
    "eta_t":       ("η_t", "-", 1.0, 0.005, "%.3f", 0.50, 1.0),
    "eta_m":       ("η_m", "-", 1.0, 0.005, "%.3f", 0.50, 1.0),
    "eta_reg":     ("η_reg", "-", 1.0, 0.005, "%.3f", 0.0, 1.0),
    "p_reg_max_w": ("P_reg,max", "kW", 1e-3, 1.0, "%.1f", 0.0, 300.0),
    "v_min_ms":    ("v_min", "km/h", 3.6, 0.5, "%.1f", 0.0, 30.0),
    "p_aux_w":     ("P_aux", "W", 1.0, 50.0, "%.0f", 0.0, 5000.0),
    "e_nom_kwh":   ("E_nom", "kWh", 1.0, 0.5, "%.1f", 10.0, 150.0),
    "soc0_pct":    ("SoC_0", "%", 1.0, 1.0, "%.0f", 0.0, 100.0),
    "soc_min_pct": ("SoC_min", "%", 1.0, 1.0, "%.0f", 0.0, 100.0),
    "grade_pct":   ("Eğim", "%", 1.0, 0.5, "%.1f", -15.0, 15.0),
}

# Tesla icin params.py'de None olan alanlarin GECICI baslangic degerleri
# (gosterim birimiyle). VARSAYIM - kaynaksiz, rapora GIRMEZ; params.py'ye yazilmaz.
# Asama 2 bitti: tum Tesla parametreleri params.py'de, bu sozluk BOS kalmali.
TESLA_PLACEHOLDERS = {}

# params.py'de deger olan ama kaynagi VARSAYIM olan alanlar: alan -> app_texts.UI etiket anahtari
ASSUMED_FIELDS = {
    "Tesla Model 3 SR+ (LFP)": {"eta_t": "param_assumed_lit", "v_min_ms": "param_assumed"},
}

# Dogrulama tablosu (bu dosyada uretilir) sutun adlari
VAL_COLS = {"test": "test", "qty": "büyüklük", "exp": "beklenen", "model": "model",
            "dev": "sapma [%]"}

# Gosterim etiketleri: anahtarlar uretici modulun sabitlerinden gelir
CYC = a3.CYCLE_COLS


def cycle_labels(soc0: float, soc_min: float) -> dict:
    """Dongu tablosu basliklari; menzil sutunlarinda SoC tanimi acikca yazilir."""
    return {
        CYC["cycle"]: "Döngü", CYC["distance"]: "Mesafe [km]",
        CYC["avg_speed"]: "Ort. hız [km/h]", CYC["e_bat"]: "E_bat [Wh]",
        CYC["cons"]: "Tüketim [Wh/km]", CYC["regen_share"]: "Rejen. payı [%]",
        CYC["limit_steps"]: "P_reg sınır adımı", CYC["envelope"]: "Zarf dışı adım",
        CYC["range"]: f"Menzil [km] (SoC {soc0:.0f}→{soc_min:.0f})",
        CYC["range_full"]: "Tam batarya menzili [km] (SoC 100→0)",
        CYC["ref_coc"]: "Ref. CoC WLTP menzili [km]",
        CYC["ref_r24"]: "Ref. R24 dinamometre menzili [km]",
    }


Q1 = a3.Q1_COLS
Q1_LABELS = {
    Q1["cycle"]: "Döngü", Q1["aero"]: "Aero [Wh/km]", Q1["roll"]: "Yuvarlanma [Wh/km]",
    Q1["acc"]: "İvmelenme [Wh/km]", Q1["aero_pct"]: "Aero [%]",
    Q1["roll_pct"]: "Yuvarlanma [%]", Q1["acc_pct"]: "İvmelenme [%]",
    Q1["regen"]: "Geri kazanılan [Wh/km]", Q1["friction"]: "Sürtünmeli fren [Wh/km]",
    Q1["acc_recovered"]: "İvme enerjisinin geri kazanılan payı [%]",
}
_FLOW_NAMES = {  # energy_flow_table sutun kokleri -> ekran adi
    "aero_cekis": "Aero (çekiş)", "yuvarlanma_cekis": "Yuvarlanma (çekiş)",
    "ivmelenme_cekis": "İvmelenme (çekiş)", "egim_cekis": "Eğim (çekiş)",
    "guc_aktarim_kayiplari_cekis": "Güç aktarım kayıpları (çekiş)", "yardimci": "Yardımcı yük",
    "brut_cekilen": "Brüt çekilen", "geri_kazanilan": "Geri kazanılan",
    "net_E_bat": "Net E_bat",
}


def flow_labels(columns) -> dict:
    """energy_flow_table() sutun adlari -> Turkce, birimli basliklar."""
    out = {"dongu": "Döngü"}
    for col in columns:
        for root, label in _FLOW_NAMES.items():
            if col == f"{root}_Wh_km":
                out[col] = f"{label} [Wh/km]"
            elif col == f"{root}{a3.FLOW_PCT_SUFFIX}":
                out[col] = f"{label} [% brüt]"
    return out


Q2 = a3.Q2_COLS
Q2_LABELS = {
    Q2["cycle"]: "Döngü", Q2["phase"]: "Faz", Q2["p_bat_max"]: "Tepe çekiş P_bat,max [kW]",
    Q2["regen_peak"]: "Tepe rejenerasyon [kW]", Q2["p_reg_max"]: "P_reg,max [kW]",
    Q2["margin"]: "Sınıra pay [kW]", Q2["limit_steps"]: "P_reg sınır adımı",
}
CH, BD, SE = a3.CHAIN_COLS, a3.BAND_COLS, a3.SENS_COLS
CHAIN_LABELS = {CH["step"]: "Adım", CH["desc"]: "Tanım", CH["whkm"]: "Wh/km",
                CH["pct"]: "Fark [%]"}
BAND_LABELS = {BD["eta"]: "η_şarj [-]", BD["grid"]: "Model şebeke tarafı [Wh/km]",
               BD["wltp"]: "Resmi WLTP [Wh/km]", BD["diff"]: "Fark [Wh/km]",
               BD["diff_pct"]: "Fark [%]"}
SENS_LABELS = {SE["param"]: "Parametre", SE["value"]: "Değer", SE["note"]: "Açıklama",
               SE["grid"]: "Şebeke tarafı [Wh/km]", SE["change"]: "Değişim [Wh/km]",
               SE["diff_pct"]: "Resmi değere fark [%]"}
SC = b3.SCENARIO_COLS
BC = b3.brake_table_columns(SCEN_A, SCEN_B)


def code_stamp() -> float:
    """Hesap kodunun ve verinin en son degisme zamani (onbellek anahtari icin)."""
    files = [*ROOT.glob("evmodel/*.py"), *ROOT.glob("analysis/*.py"),
             *ROOT.glob("tests/*.py"), *ROOT.glob("data/*.csv"), EXCEL_PATH]
    return max(f.stat().st_mtime for f in files)


STAMP = code_stamp()


# ===========================================================================
# 1. Onbellekli veri. Her fonksiyon 'stamp' alir: kod degisince anahtar degisir,
#    eski bicimli sonuc (orn. sutunu eksik tablo) geri donmez.
# ===========================================================================
_HASH = {VehicleParams: dataclasses.astuple}  # dondurulmus dataclass -> tuple ile anahtar


@st.cache_data(show_spinner="Sürüş döngüleri okunuyor...")
def get_cycles(stamp: float) -> dict:
    return load_all_cycles()


@st.cache_data
def get_phases(name: str, stamp: float):
    return load_phases(name)


@st.cache_data(hash_funcs=_HASH)
def run_sim(cycle_name: str, p: VehicleParams, stamp: float):
    t, v = get_cycles(stamp)[cycle_name]
    return simulate(t, v, p)


@st.cache_data(hash_funcs=_HASH, show_spinner="G taraması yapılıyor (haritalı model)...")
def get_g_scan(cycle_name: str, p: VehicleParams, stamp: float) -> pd.DataFrame:
    t, v = get_cycles(stamp)[cycle_name]
    return c3.g_scan(t, v, p)


@st.cache_data(hash_funcs=_HASH)
def run_sim_map(cycle_name: str, p: VehicleParams, mode: str, stamp: float) -> float:
    """Haritali model tuketimi [Wh/km] (3C)."""
    t, v = get_cycles(stamp)[cycle_name]
    return c3.simulate_map(t, v, p, mode)["consumption_wh_km"]


@st.cache_data(hash_funcs=_HASH)
def get_constant_vs_map(p: VehicleParams, stamp: float) -> pd.DataFrame:
    return c3.constant_vs_map(get_cycles(stamp), p)


@st.cache_data(show_spinner="20 Kasım kontrol belgesi çalıştırılıyor...")
def get_kontrol(stamp: float) -> dict:
    from analysis.kontrol_20kasim import run_all_checks
    return run_all_checks()


@st.cache_data(hash_funcs=_HASH, show_spinner="Animasyon kareleri hazırlanıyor...")
def get_drive_figure(cycle_name: str, p: VehicleParams, step_s: int, speed: float,
                     stamp: float):
    return ia.fig_drive_animation(run_sim(cycle_name, p, stamp), cycle_name, p.p_reg_max_w,
                                  step_s, speed)


@st.cache_data(hash_funcs=_HASH)
def get_scenario_table(cycle_name: str, base: VehicleParams, stamp: float) -> pd.DataFrame:
    """3B senaryolari: base.with_(...) - Temel Arac seciliyken kullanicinin degerleri dahil."""
    t, v = get_cycles(stamp)[cycle_name]
    return b3.scenario_table(t, v, base)


@st.cache_data(hash_funcs=_HASH)
def get_phase_table(cycle_name: str, base: VehicleParams, stamp: float) -> pd.DataFrame:
    t, v = get_cycles(stamp)[cycle_name]
    return b3.phase_comparison(t, v, get_phases(cycle_name, stamp), SCEN_A, SCEN_B, base)


@st.cache_data
def get_t2(stamp: float) -> dict:
    """T2 (0->50 km/h, 10 s): yamuk ve sag uc toplam enerji, son ornek gucu."""
    from tests.test_t1_t2 import run_t2
    r2 = run_t2()
    dt_s = float(r2.t_s[1] - r2.t_s[0])
    return {"trap": float(np.trapezoid(r2.p_bat_w, r2.t_s) / 3600.0), "rect": r2.e_bat_wh,
            "half": float(r2.p_bat_w[-1] * dt_s / 2 / 3600.0)}


@st.cache_data(hash_funcs=_HASH, show_spinner="Yorum soruları hesaplanıyor...")
def get_q3a(cycle_names: tuple, p: VehicleParams, real: bool, stamp: float) -> list:
    res = {n: run_sim(n, p, stamp) for n in cycle_names}
    return yorum.questions_3a(res, p, get_cycles(stamp), real)


@st.cache_data(hash_funcs=_HASH, show_spinner="3B senaryoları hesaplanıyor...")
def get_q3b(base: VehicleParams, stamp: float) -> list:
    return yorum.questions_3b(base, get_cycles(stamp), get_phases(yorum.WLTP_CYCLE, stamp))


@st.cache_data(hash_funcs=_HASH)
def get_wltp_sensitivity(p: VehicleParams, wltp: float, eta_charge: float,
                         stamp: float) -> pd.DataFrame:
    return a3.wltp_sensitivity(p, get_cycles(stamp), eta_charge, wltp)


@st.cache_data
def get_road_load(stamp: float) -> tuple:
    """Asama 2 yol yuku: (karsilastirma tablosu, v_kmh, egriler)."""
    cycles = get_cycles(stamp)
    v, curves = p2.road_load_curves(cycles)
    return p2.compare(cycles), v, curves


@st.cache_data
def get_cycle_overview(stamp: float) -> pd.DataFrame:
    """Donguleri taniyin tablosu (sure, mesafe, hiz, rolanti) - veriden."""
    return a3.cycle_overview(get_cycles(stamp))


@st.cache_data
def get_eta_grid(stamp: float) -> tuple:
    """Verim haritasi izgarasi + okunan noktalar: (n, T, eta[ny, nx], (n_pts, T_pts))."""
    n, t, eta = eta_grid()
    pts, _ = load_eta_map()
    return n, t, eta, (pts[:, 0], pts[:, 1])


@st.cache_data
def validation_table(stamp: float) -> pd.DataFrame:
    """T1, T1b, T2, T4: tests/ icindeki ayni fonksiyonlarla, Temel Arac uzerinde."""
    from tests.test_t1_t2 import run_t1, run_t2

    r1, r1b, r2 = run_t1(0.0), run_t1(400.0), run_t2()
    rows = [
        ("T1", "tüketim [Wh/km]", 143.5, r1.consumption_wh_km),
        ("T1b", "tüketim [Wh/km]", 147.9, r1b.consumption_wh_km),
        ("T2", "E_bat yamuk [Wh]", 63.1, np.trapezoid(r2.p_bat_w, r2.t_s) / 3600.0),
        ("T2", "P_bat(10 s) [kW]", 46.1, r2.p_bat_w[-1] / 1e3),
    ]
    for name, (_, v) in get_cycles(stamp).items():
        rows.append(("T4", f"{name} mesafe [km]", REFERENCE_DISTANCES_KM[name],
                     cycle_distance_km(v)))
    c = VAL_COLS
    df = pd.DataFrame(rows, columns=[c["test"], c["qty"], c["exp"], c["model"]])
    df[c["dev"]] = (df[c["model"]] - df[c["exp"]]) / df[c["exp"]] * 100
    return df


# ===========================================================================
# 2. Yardimcilar: grafik, guvenli stil, bilgi kutusu
# ===========================================================================
def show(fig) -> None:
    """Plotly grafigini mod cubugu acik (kamera ikonuyla PNG) olarak ciz."""
    st.plotly_chart(fig, config=PLOTLY_CONFIG, theme="streamlit")


def has_cols(df: pd.DataFrame, cols) -> bool:
    return all(c in df.columns for c in cols)


def style_cells(styler, func, cols):
    """Yalnizca tabloda gercekten bulunan sutunlara stil uygular; hic yoksa atlar."""
    present = [c for c in cols if c in styler.data.columns]
    return styler.map(func, subset=present) if present else styler


def fmt_tr(x: float, nd: int = 1) -> str:
    """Ondalik virgullu sayi (aciklama metinleri icin)."""
    return f"{x:.{nd}f}".replace(".", ",")


def placeholder_values() -> dict:
    """app_texts.PLACEHOLDERS icin o anki sonuclar (WLTC_3b Baseline faz tepesi)."""
    ph = get_phase_table("WLTC_3b", SCEN_BASE, STAMP)
    phases = ph[ph[BC["phase"]] != b3.WHOLE_CYCLE] if has_cols(ph, [BC["phase"]]) else ph
    if phases.empty or not has_cols(phases, [BC["peak_a"]]):
        return {p: "—" for p in T.PLACEHOLDERS}
    top = phases.loc[phases[BC["peak_a"]].idxmax()]
    return {"{WLTC tepe faz}": str(top[BC["phase"]]),
            "{WLTC tepe kW}": fmt_tr(top[BC["peak_a"]])}


def abbreviations_in(*texts: str) -> list:
    """Metinlerde gecen kisaltmalar (app_texts.ABBREVIATIONS sirasiyla).

    Harf komsulugu yoksa eslesir: 'SoC_0' ve 'SoC(t)' icinde SoC bulunur, 'SoCx' icinde bulunmaz.
    """
    joined = " ".join(t for t in texts if t)
    return [a for a in T.ABBREVIATIONS
            if re.search(rf"(?<![A-Za-z]){re.escape(a)}(?![A-Za-z])", joined)]


def abbrev_help(*texts: str, base: str | None = None, extra: tuple = ()) -> str | None:
    """help= metni: base + metinlerde gecen (ve extra) kisaltmalarin sozluk aciklamalari."""
    abbrs = list(dict.fromkeys([*abbreviations_in(*texts, base or ""), *extra]))
    notes = [f"**{a}**: {T.GLOSSARY[T.ABBREVIATIONS[a]]}" for a in abbrs]
    parts = ([base] if base else []) + notes
    return "\n\n".join(parts) if parts else None


def info_box(key: str, values: dict | None = None, extra_abbr: tuple = ()) -> None:
    """app_texts.TEXTS[key] icin kapali bilgi kutusu (dort baslik + denklem + kisaltmalar).

    extra_abbr: kutunun metninde gecmeyen ama ayni sekmede (orn. alt yazida) kullanilan
    kisaltmalar; onlar da kutunun altinda aciklanir.
    """
    item = T.TEXTS[key]
    merged = {**globals().get("DYN", {}), **(values or {})}  # canli degerler (DYN) + sayfaya ozel
    with st.expander(T.EXPANDER_LABELS[item["tur"]], expanded=False):
        st.caption(item["baslik"])
        texts = []
        for field, heading in T.HEADINGS:
            text = item[field]
            for ph, val in merged.items():
                text = text.replace(ph if ph.startswith("{") else "{" + ph + "}", str(val))
            texts.append(text)
            st.markdown(f"**{heading}**  \n{text}")
        for eq in item.get("denklem", []):
            st.latex(eq)
        abbrs = list(dict.fromkeys([*abbreviations_in(item["baslik"], *texts), *extra_abbr]))
        if abbrs:
            st.caption(f"{T.ABBREV_CAPTION}: " + " · ".join(
                f"**{a}** – {T.GLOSSARY[T.ABBREVIATIONS[a]]}" for a in abbrs))


# ===========================================================================
# 3. Parametre durumu (st.session_state) ve geri cagirma (callback) fonksiyonlari
# ===========================================================================
def missing_fields(p: VehicleParams) -> list:
    """params.py'de None olan arayuz parametreleri."""
    return [f for f in PARAM_SPECS if getattr(p, f) is None]


def default_values(vehicle_label: str) -> dict:
    """Secili aracin varsayilanlari (gosterim birimi); None -> gecici varsayim."""
    p = VEHICLES[vehicle_label]
    out = {}
    for f, (_, _, scale, *_rest) in PARAM_SPECS.items():
        val = getattr(p, f)
        if val is None:
            if f not in TESLA_PLACEHOLDERS:
                raise ValueError(f"{p.name}: '{f}' params.py'de None ve gecici deger yok")
            out[f] = float(TESLA_PLACEHOLDERS[f])
        elif scale == 1.0:
            out[f] = float(val)  # birim donusumu yok: params.py degeri birebir
        else:
            out[f] = round(float(val) * scale, 9)  # orn. 7/3.6*3.6 kayan nokta artigini temizle
    return out


def reset_params() -> None:
    """Tum parametre kutularini secili aracin varsayilanina dondurur."""
    for f, val in default_values(st.session_state.vehicle).items():
        st.session_state[f"par_{f}"] = val
    st.session_state.scenario = SCEN_A


def apply_scenario() -> None:
    """3B senaryosu: once varsayilana don, sonra senaryonun degisikliklerini uygula."""
    name = st.session_state.scenario
    for f, val in default_values(st.session_state.vehicle).items():
        st.session_state[f"par_{f}"] = val
    for f, si_val in b3.SCENARIOS[name][1].items():
        st.session_state[f"par_{f}"] = round(si_val * PARAM_SPECS[f][2], 9)


def param_input(f: str, defaults: dict) -> None:
    """Tek parametre kutusu (yardim metniyle); varsayilandan farkliysa altinda turuncu not."""
    label, unit, _, step, fmt, lo, hi = PARAM_SPECS[f]
    st.number_input(f"{label} [{unit}]", min_value=lo, max_value=hi, step=step,
                    format=fmt, key=f"par_{f}",
                    help=abbrev_help(label, base=T.PARAM_HELP.get(f)))
    assumed = ASSUMED_FIELDS.get(st.session_state.vehicle, {}).get(f)
    if assumed:
        st.caption(T.UI[assumed])
    if not np.isclose(st.session_state[f"par_{f}"], defaults[f]):
        st.caption(T.UI["param_changed"].format(default=fmt % defaults[f]))


def changed_params(defaults: dict) -> list:
    """[(etiket, yeni, varsayilan, birim)] - varsayilandan farkli olanlar."""
    out = []
    for f, (label, unit, _, _, fmt, *_r) in PARAM_SPECS.items():
        cur = st.session_state[f"par_{f}"]
        if not np.isclose(cur, defaults[f]):
            out.append((label, fmt % cur, fmt % defaults[f], unit))
    return out


# ===========================================================================
# 4. Kenar cubugu
# ===========================================================================
with st.sidebar:
    st.header("Araç ve döngü")
    st.selectbox("Araç", list(VEHICLES), key="vehicle", on_change=reset_params)
    if "par_m_kg" not in st.session_state:  # ilk calistirma
        reset_params()
    vehicle_label = st.session_state.vehicle
    base_params = VEHICLES[vehicle_label]
    defaults = default_values(vehicle_label)
    missing = missing_fields(base_params)

    # 4.1 Tesla: params.py'de eksik olanlar
    if missing:
        st.error(T.UI["tesla_missing"].format(
            fields=", ".join(PARAM_SPECS[f][0] for f in missing)))
        with st.container(border=True):
            st.warning(T.UI["tesla_placeholder"])
            for f in missing:
                param_input(f, defaults)

    # 4.2 Dongu secimi
    cycle_help = T.CYCLE_SELECT_HELP_TITLE + "\n\n" + "\n".join(
        f"- **{c}**: {T.CYCLE_INFO[c]['kisa']}" for c in CYCLE_NAMES if c in T.CYCLE_INFO)
    selected = st.multiselect("Sürüş döngüleri", CYCLE_NAMES, default=CYCLE_NAMES,
                              help=cycle_help)

    # 4.3 3B senaryo kisayollari (yalnizca Temel Arac)
    if vehicle_label == BASE_LABEL:
        st.radio("3B senaryosu", list(b3.SCENARIOS), key="scenario", on_change=apply_scenario,
                 format_func=lambda s: f"{s} · {b3.SCENARIOS[s][0]}")

    # 4.4 Parametre ayarlari
    with st.expander("Parametre ayarları", expanded=False):
        for f in PARAM_SPECS:
            if f not in missing:
                param_input(f, defaults)
    st.button("Varsayılana dön", on_click=reset_params, width="stretch")

    # 4.5 Grafik zaman penceresi
    st.header("Grafik zaman penceresi")
    window_mode = st.radio("Pencere", WINDOW_OPTIONS, key="window_mode",
                           label_visibility="collapsed")
    cycles_all = get_cycles(STAMP)
    if window_mode == WINDOW_OPTIONS[0]:
        t_window = (0.0, FIRST_WINDOW_S)
    elif window_mode == WINDOW_OPTIONS[1] or not selected:
        t_window = None
    else:
        t_end_max = max(cycles_all[c][0][-1] for c in selected)
        t_window = st.slider("Aralık [s]", 0.0, float(t_end_max),
                             (0.0, min(FIRST_WINDOW_S, float(t_end_max))), step=1.0)

    # 4.6 Terimler sozlugu (en altta, varsayilan kapali)
    with st.expander(T.GLOSSARY_LABEL, expanded=False):
        for term, text in T.GLOSSARY.items():
            st.markdown(f"**{term}**  \n{text}")

if not selected:
    st.warning(T.UI["no_cycle"])
    st.stop()

# ===========================================================================
# 5. Simulasyon: kutulardaki degerler .with_() ile uygulanir
# ===========================================================================
changes = {f: st.session_state[f"par_{f}"] / PARAM_SPECS[f][2] for f in PARAM_SPECS}
params = base_params.with_(**changes)
results = {name: run_sim(name, params, STAMP) for name in selected}
# 3B senaryolarinin tabani: Temel Arac seciliyse kullanicinin degistirdigi degerler dahil
SCEN_BASE = params if vehicle_label == BASE_LABEL else BASE_VEHICLE
envelope_ok = params.t_peak_nm is not None and params.p_peak_w is not None


def compute_dyn() -> dict:
    """Bilgi kutularindaki {yer tutucu}lar icin CANLI degerler (o anki parametre ve donguler)."""
    cons = {n: r.consumption_wh_km for n, r in results.items()}
    regen = {n: r.regen_share * 100 for n, r in results.items()}
    q1 = a3.q1_wheel_shares(results).set_index(a3.Q1_COLS["cycle"])
    drops = [params.soc0_pct - r.soc_pct[-1] for r in results.values()]
    t2 = get_t2(STAMP)
    val_tbl = validation_table(STAMP)
    t4_dev = val_tbl[val_tbl[VAL_COLS["test"]] == "T4"][VAL_COLS["dev"]].abs().max()
    d = {
        "tol": fmt_tr(VALIDATION_TOL_PCT), "t2_trap": fmt_tr(t2["trap"]),
        "t2_rect": fmt_tr(t2["rect"]), "t2_half": fmt_tr(t2["half"]),
        "max_cons_cycle": max(cons, key=cons.get), "max_cons": fmt_tr(max(cons.values())),
        "min_cons_cycle": min(cons, key=cons.get), "min_cons": fmt_tr(min(cons.values())),
        "max_regen_cycle": max(regen, key=regen.get), "max_regen": fmt_tr(max(regen.values())),
        "t4_dev": fmt_tr(t4_dev, 4), "v_min": fmt_tr(params.v_min_ms * 3.6),
        "soc_drop_min": fmt_tr(min(drops), 2), "soc_drop_max": fmt_tr(max(drops), 2),
        "max_aero_cycle": q1[a3.Q1_COLS["aero_pct"]].idxmax(),
        "max_aero_pct": fmt_tr(q1[a3.Q1_COLS["aero_pct"]].max()),
        "max_acc_cycle": q1[a3.Q1_COLS["acc_pct"]].idxmax(),
        "max_acc_pct": fmt_tr(q1[a3.Q1_COLS["acc_pct"]].max()),
        "p_cont": fmt_tr(TESLA_SOURCED["p_30min_w"] / 1e3, 0),
    }
    if envelope_ok:
        low, total = 0, 0
        for r in results.values():
            k = r.p_w_w > 0
            lim = t_max_nm(r.n_m_rpm[k], params.t_peak_nm, params.p_peak_w, params.n_max_rpm)
            low += int(np.sum(r.t_m_nm[k] < ENVELOPE_LOW_FRAC * lim))
            total += int(k.sum())
        d.update(env_viol=sum(r.n_envelope_violations for r in results.values()),
                 env_low_share=fmt_tr(low / max(total, 1) * 100),
                 n_base=fmt_tr(base_speed_rpm(params.t_peak_nm, params.p_peak_w), 0))
    else:
        d.update(env_viol="— (motor zarfı tanımsız)", env_low_share="—", n_base="—")
    return d


DYN = compute_dyn()

# ===========================================================================
# 6. Baslik ve dogrulama rozeti
# ===========================================================================
chips = [f"🚗 {params.name}", f"m = {params.m_kg:.0f} kg", f"E_nom = {params.e_nom_kwh:g} kWh",
         f"G = {params.gear_ratio:g}", f"P_aux = {params.p_aux_w:.0f} W"]
if params.p_peak_w is not None:
    chips.append(f"P_tepe = {params.p_peak_w / 1e3:.0f} kW · T_tepe = {params.t_peak_nm:.0f} Nm")
chips.append(f"Döngüler: {', '.join(selected)}")
st.markdown(f"<div class='ev-hero'><h1>⚡ {T.UI['hero_title']}</h1><p>{T.UI['hero_sub']}</p>"
            + "".join(f"<span class='ev-chip'>{c}</span>" for c in chips) + "</div>",
            unsafe_allow_html=True)

info_box("dogrulama_rozeti")
val = validation_table(STAMP)
V = VAL_COLS
if (val[V["dev"]].abs() < VALIDATION_TOL_PCT).all():
    st.success(T.UI["validation_ok"].format(tol=VALIDATION_TOL_PCT))
else:
    st.error(T.UI["validation_fail"].format(tol=VALIDATION_TOL_PCT))
for col, test in zip(st.columns(4), ["T1", "T1b", "T2", "T4"]):
    sub = val[val[V["test"]] == test]
    lines = [f"{r[V['qty']]}: **{r[V['model']]:.2f}** / {r[V['exp']]}"
             for _, r in sub.iterrows()] if test != "T4" else \
        [T.UI["t4_summary"].format(dev=sub[V["dev"]].abs().max())]
    col.markdown(f"**{test}** (model / beklenen)  \n" + "  \n".join(lines))
with st.expander("Doğrulama ayrıntısı"):
    st.dataframe(val.round(4), hide_index=True)

if missing:
    st.warning(T.UI["tesla_results"])
diff = changed_params(defaults)
if diff:
    st.markdown(T.UI["changed_params"] + " · ".join(
        f":orange[{lab} = {cur} {u}] (varsayılan {d})" for lab, cur, d, u in diff))

# ===========================================================================
# 7. Ozet kartlari
# ===========================================================================
info_box("ozet_kartlari")
card_cycle = st.selectbox("Özet kartları için döngü", selected)
rc = results[card_cycle]
envelope_ok = params.t_peak_nm is not None and params.p_peak_w is not None
rd = run_sim(card_cycle, base_params, STAMP) if diff and not missing else None


def _delta(cur: float, ref_attr: str, scale: float = 1.0, nd: int = 1, unit: str = ""):
    """Varsayilana gore fark metni (parametre degistirildiyse)."""
    if rd is None:
        return None
    d = (cur - getattr(rd, ref_attr)) * scale
    return None if abs(d) < 10 ** -(nd + 1) else f"{d:+.{nd}f}{unit}"


k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Tüketim", f"{rc.consumption_wh_km:.1f} Wh/km",
          _delta(rc.consumption_wh_km, "consumption_wh_km", unit=" Wh/km"), delta_color="inverse")
k2.metric("Menzil", f"{rc.range_km:.0f} km", _delta(rc.range_km, "range_km", nd=0, unit=" km"))
k3.metric("Son SoC", f"{rc.soc_pct[-1]:.2f} %",
          None if rd is None else f"{rc.soc_pct[-1] - rd.soc_pct[-1]:+.2f} puan")
k4.metric("Rejenerasyon payı", f"{rc.regen_share * 100:.1f} %",
          _delta(rc.regen_share, "regen_share", scale=100, unit=" puan"))
k5.metric("P_reg,max sınır adımı", f"{rc.n_reg_limited}")
k6.metric("Zarf dışı adım", f"{rc.n_envelope_violations}" if envelope_ok else "—",
          help=None if envelope_ok else T.UI["envelope_missing"])
if rd is not None:
    st.caption(T.UI["kpi_delta_note"])

# ===========================================================================
# 8. Sekmeler
# ===========================================================================
# Gezinme: yatay sekmeler yerine gruplu buton menusu (hepsi gorunur, yalnizca secili
# bolum hesaplanir). NAV_GROUPS ve sayfa anahtarlari app_texts.NAV'dan gelir.
if "page" not in st.session_state:
    st.session_state.page = T.NAV_DEFAULT


def _go(key: str) -> None:
    st.session_state.page = key


st.markdown(f"<div class='ev-nav-title'>{T.UI['nav_title']}</div>", unsafe_allow_html=True)
for col, (group, items) in zip(st.columns(len(T.NAV)), T.NAV.items()):
    with col.container(border=True):
        st.markdown(f"<div class='ev-nav-group'>{group}</div>", unsafe_allow_html=True)
        for key, label in items:
            st.button(label, key=f"nav_{key}", on_click=_go, args=(key,), width="stretch",
                      type="primary" if st.session_state.page == key else "secondary")
page = st.session_state.page
page_label = next(lbl for items in T.NAV.values() for k, lbl in items if k == page)
st.markdown(f"<div class='ev-page-title'>{page_label}</div>", unsafe_allow_html=True)


def eff_map_figure(p: VehicleParams, cycle_name: str, title: str):
    """Verim haritasi + dongunun cekis/geri kazanim noktalari (zarf ustu cizilmez)."""
    n_g, t_g, eta_g, map_pts = get_eta_grid(STAMP)
    env = None
    if p.t_peak_nm is not None and p.p_peak_w is not None:
        eta_g = np.where(t_g[:, None] > t_max_nm(n_g, p.t_peak_nm, p.p_peak_w,
                                                p.n_max_rpm)[None, :], np.nan, eta_g)
        n_env = np.linspace(0, p.n_max_rpm or n_g[-1], 300)
        env = (n_env, t_max_nm(n_env, p.t_peak_nm, p.p_peak_w, p.n_max_rpm))
    r = run_sim(cycle_name, p, STAMP)
    trac = r.p_w_w > 0
    reg = (r.p_w_w < 0) & (r.v_ms >= p.v_min_ms)
    ops = {"Çekiş": (r.n_m_rpm[trac], r.t_m_nm[trac]),
           "Geri kazanım": (r.n_m_rpm[reg], np.abs(r.t_m_nm[reg]))}
    return ia.fig_efficiency_map(n_g, t_g, eta_g, map_pts, ops, env, title=title), r


# ✅ 20 Kasim "Kendi Modelini Kontrol Et" belgesi (Temel Arac, kenar cubugundan bagimsiz)
def _color_status(val) -> str:
    s = str(val).lower()
    if s.startswith("tutuyor"):
        return "background-color: rgba(27,175,122,0.22)"
    if s.startswith("tutmuyor"):
        return "background-color: rgba(227,73,72,0.30)"
    return ""


if page == "chk":
    st.markdown(T.UI["chk_intro"])
    if st.button("🔁 Testi şimdi yeniden çalıştır", key="chk_rerun"):
        get_kontrol.clear()
    chk = get_kontrol(STAMP)
    n_rows = sum(len(df) for df in chk.values())
    n_bad = sum(int(df["durum"].astype(str).str.lower().str.startswith("tutmuyor").sum())
                for df in chk.values())
    if n_bad == 0:
        st.success(T.UI["chk_ok"].format(n=n_rows))
    else:
        st.error(T.UI["chk_fail"].format(n=n_rows, bad=n_bad))
    for key, title in T.UI["chk_sections"].items():
        df = chk[key]
        ok = not df["durum"].astype(str).str.lower().str.startswith("tutmuyor").any()
        with st.expander(f"{'✅' if ok else '❌'} {title} · {len(df)} satır", expanded=key in (
                "kontrol_tablosu", "ogrenci_kontrol")):
            st.dataframe(df.style.format(precision=4).map(_color_status, subset=["durum"]),
                         hide_index=True)
    st.caption(T.UI["chk_caption"])

    # Kendi modelinin ciktisini yukle (baska ogrenciler icin)
    st.subheader(T.UI["up_title"])
    st.markdown(T.UI["up_intro"])
    u1, u2 = st.columns([1, 2])
    up_cycle = u1.selectbox("Döngü", CYCLE_NAMES, index=CYCLE_NAMES.index("WLTC_3b"),
                            key="up_cycle")
    u1.download_button(T.UI["up_example"], ogr.example_csv(up_cycle),
                       file_name=f"ornek_{up_cycle}_temel_arac.csv", mime="text/csv")
    up_file = u2.file_uploader(T.UI["up_label"], type=["csv", "xlsx"], key="up_file")
    if up_file is not None:
        try:
            t_u, p_u = ogr.parse_series(ogr.read_upload(up_file.name, up_file.getvalue()))
            up_tab, up_info = ogr.compare(t_u, p_u, up_cycle)
        except Exception as exc:  # okunamayan dosya: mesaj goster, uygulama durmasin
            st.error(T.UI["up_error"].format(err=exc))
        else:
            n_bad_up = int((up_tab["durum"] == "tutmuyor").sum())
            (st.success if n_bad_up == 0 else st.warning)(T.UI["up_result"].format(
                n=len(up_tab), bad=n_bad_up, pts=up_info["n_points"], tot=up_info["n_cycle"],
                dmax=up_info["max_abs_diff_kw"], tmax=up_info["t_max_diff_s"]))
            st.dataframe(up_tab.style.format(precision=3).map(_color_status, subset=["durum"]),
                         hide_index=True)
            st.plotly_chart(ia.fig_upload_compare(up_info, up_cycle), config=PLOTLY_CONFIG,
                            theme="streamlit")

# 🎬 Surus simulatoru
if page == "sim":
    st.markdown(T.UI["sim_intro"])
    s1, s2, s3 = st.columns([3, 1, 1])
    sim_cycle = s1.selectbox("Döngü", selected, key="sim_cycle")
    sim_step = s2.select_slider("Kare adımı [s]", options=[1, 2, 5, 10], value=5,
                                key="sim_step", help=T.UI["sim_step_help"])
    sim_speed = s3.select_slider("Oynatma hızı", options=[0.25, 0.5, 1.0, 2.0], value=0.5,
                                 format_func=lambda x: f"{x:g}×".replace(".", ","),
                                 key="sim_speed", help=T.UI["sim_speed_help"])
    st.plotly_chart(get_drive_figure(sim_cycle, params, sim_step, sim_speed, STAMP),
                    config={**PLOTLY_CONFIG, "displayModeBar": False}, theme="streamlit")

# 🆚 Parametre etkisi (varsayilan - guncel)
if page == "cmp":
    if not diff:
        st.info(T.UI["cmp_none"])
    else:
        st.markdown(T.UI["cmp_intro"])
        st.markdown(T.UI["changed_params"] + " · ".join(
            f":orange[{lab} = {cur} {u}] (varsayılan {d})" for lab, cur, d, u in diff))
        base_res = {n: run_sim(n, base_params, STAMP) for n in selected}
        cmp = pd.DataFrame({
            "Döngü": selected,
            "Tüketim varsayılan [Wh/km]": [base_res[n].consumption_wh_km for n in selected],
            "Tüketim güncel [Wh/km]": [results[n].consumption_wh_km for n in selected],
            "Menzil varsayılan [km]": [base_res[n].range_km for n in selected],
            "Menzil güncel [km]": [results[n].range_km for n in selected],
            "Rejen. payı varsayılan [%]": [base_res[n].regen_share * 100 for n in selected],
            "Rejen. payı güncel [%]": [results[n].regen_share * 100 for n in selected],
        })
        cmp.insert(3, "Tüketim değişimi [%]",
                   (cmp["Tüketim güncel [Wh/km]"] / cmp["Tüketim varsayılan [Wh/km]"] - 1) * 100)
        cmp.insert(6, "Menzil değişimi [%]",
                   (cmp["Menzil güncel [km]"] / cmp["Menzil varsayılan [km]"] - 1) * 100)
        st.dataframe(cmp.round(2), hide_index=True)
        g1, g2 = st.columns(2)
        with g1:
            show(ia.fig_compare_default(selected, list(cmp["Tüketim varsayılan [Wh/km]"]),
                                        list(cmp["Tüketim güncel [Wh/km]"]), "Tüketim", "Wh/km"))
        with g2:
            show(ia.fig_compare_default(selected, list(cmp["Menzil varsayılan [km]"]),
                                        list(cmp["Menzil güncel [km]"]), "Menzil", "km"))

# ⚙️ 3C bonus: motor haritasi + G taramasi
if page == "c3":
    if not envelope_ok or vehicle_label == BASE_LABEL:
        st.info(T.UI["c3_vehicle_only"])
    else:
        st.markdown(T.UI["c3_intro"].format(v_top=c3.V_TOP_KMH))
        labels = T.UI["c3_mode_labels"]
        a1, a2 = st.columns([1, 2])
        c3_cycle = a1.selectbox("Döngü", CYCLE_NAMES, index=CYCLE_NAMES.index(c3.SCAN_CYCLE),
                                key="c3_cycle")
        g_sel = a2.slider("Redüktör oranı G", c3.G_MIN, c3.G_MAX, float(params.gear_ratio),
                          step=c3.G_STEP, key="c3_g")
        scan = get_g_scan(c3_cycle, params, STAMP)
        SCN = c3.SCAN_COLS
        curves = {labels[m]: (df[SCN["G"]].to_numpy(), df[SCN["cons"]].to_numpy())
                  for m, df in scan.groupby(SCN["mode"], sort=False)}
        p_sel = params.with_(gear_ratio=float(g_sel))
        sel_vals = {labels[m]: run_sim_map(c3_cycle, p_sel, m, STAMP) for m in c3.LOW_T_MODES}
        ref_vals = {labels[m]: run_sim_map(c3_cycle, params, m, STAMP) for m in c3.LOW_T_MODES}
        lim = c3.design_limits(p_sel)
        g_up = c3.g_upper_for_top_speed(params)
        m1, m2, m3, m4 = st.columns(4)
        for col, m in zip((m1, m2), c3.LOW_T_MODES):
            lab = labels[m]
            chg = (sel_vals[lab] / ref_vals[lab] - 1) * 100
            col.metric(lab.split(" (")[0], f"{sel_vals[lab]:.2f} Wh/km",
                       None if abs(chg) < 0.005 else
                       f"{chg:+.2f} % (araç G = {params.gear_ratio:g})", delta_color="inverse")
        m3.metric("Azami hız (n_max)", f"{lim['v_max_kmh']:.0f} km/h",
                  "kısıt sağlanıyor" if g_sel <= g_up else f"< {c3.V_TOP_KMH:.0f} km/h!",
                  delta_color="normal" if g_sel <= g_up else "inverse")
        m4.metric("Kalkış tekerlek kuvveti", f"{lim['f0_kn']:.1f} kN")
        show(ia.fig_g_scan(curves, params.gear_ratio, g_up, float(g_sel), sel_vals, c3_cycle))
        fig_map, _ = eff_map_figure(p_sel, c3_cycle,
                                    T.UI["c3_map_title"].format(cycle=c3_cycle, g=g_sel))
        show(fig_map)
        st.markdown(T.UI["c3_table_title"])
        st.dataframe(get_constant_vs_map(params, STAMP).round(2), hide_index=True)

# ❓ Yorum sorulari (odev 3A ve 3B): soru sabit, bulgular CANLI (analysis/yorum.py)
def render_questions(title: str, caption: str, items: list) -> None:
    st.subheader(title)
    st.caption(caption)
    for q in items:
        with st.container(border=True):
            st.markdown(f"**Soru {q['no']}.** *{q['soru']}*")
            st.markdown(T.UI["q_live_label"])
            st.markdown("\n".join(f"- {b}" for b in q["bulgular"]))
            if q["tablo"] is not None:
                with st.expander(T.UI["q_table_label"]):
                    st.dataframe(q["tablo"], width="stretch")


if page == "yorum":
    st.markdown(T.UI["q_intro"])
    real = vehicle_label != BASE_LABEL
    render_questions(T.UI["q3a_title"], T.UI["q3a_caption"].format(vehicle=params.name,
                                                                    cycles=", ".join(selected)),
                     get_q3a(tuple(selected), params, real, STAMP))
    render_questions(T.UI["q3b_title"], T.UI["q3b_caption"].format(base=SCEN_BASE.name),
                     get_q3b(SCEN_BASE, STAMP))

# a) Dongu tablosu (3A)
if page == "dongu":
    info_box("dongu_tablosu")
    refs = a3.RANGE_REFS if vehicle_label != BASE_LABEL else None  # referanslar Tesla'ya ait
    df = a3.cycle_table(results, params, refs)
    st.dataframe(df.rename(columns=cycle_labels(params.soc0_pct, params.soc_min_pct)).round(2),
                 hide_index=True)
    st.caption(T.UI["range_caption"])
    if not envelope_ok:
        st.caption(T.UI["envelope_missing_table"])
    st.download_button("CSV indir", df.to_csv(index=False).encode("utf-8"),
                       file_name="dongu_tablosu.csv", mime="text/csv")

# b) Hiz - zaman
if page == "hiz":
    with st.expander(T.CYCLES_BOX_LABEL, expanded=False):
        ov = get_cycle_overview(STAMP)
        OV = a3.OVERVIEW_COLS
        if has_cols(ov, OV.values()):
            names = ov[OV["cycle"]]
            ov.insert(1, "Bölge", names.map(lambda c: T.CYCLE_INFO.get(c, {}).get("bolge", "—")))
            ov["Karakter"] = names.map(lambda c: T.CYCLE_INFO.get(c, {}).get("kisa", "—"))
            st.dataframe(ov.rename(columns={
                OV["cycle"]: "Döngü", OV["duration"]: "Süre [s]", OV["distance"]: "Mesafe [km]",
                OV["avg_speed"]: "Ort. hız [km/h]", OV["max_speed"]: "Maks. hız [km/h]",
                OV["idle"]: "Rölanti [%]"}).round(2), hide_index=True)
        st.caption(T.CYCLES_BOX_CAPTION)
    info_box("hiz_zaman")
    show(ia.fig_speed_profiles({c: cycles_all[c] for c in selected}, t_window))

# c) Batarya gucu - zaman
if page == "guc":
    info_box("batarya_gucu")
    show(ia.fig_power_profiles(results, params.p_reg_max_w, t_window))
    st.markdown(T.UI["q2_title"])
    st.dataframe(a3.q2_peak_power(results, params).rename(columns=Q2_LABELS).round(2),
                 hide_index=True)
    phase_sel = {c: get_phases(c, STAMP) for c in a3.PHASE_CYCLES if c in results}
    if phase_sel:
        st.markdown(T.UI["q2_phase_title"])
        st.dataframe(a3.q2_phase_peaks(results, params, phase_sel).rename(columns=Q2_LABELS)
                     .round(2), hide_index=True)
    st.caption(T.UI["q2_caption"])

# d) SoC - zaman
if page == "soc":
    info_box("soc_zaman")
    show(ia.fig_soc(results, t_window))

# e) Enerji dagilimi (3A Soru 1)
if page == "enerji":
    info_box("enerji_dagilimi")
    per_km = st.radio("Birim", ["Wh/km", "Wh"], horizontal=True, key="energy_unit") == "Wh/km"
    flows = {n: a3.energy_flows(r, params) for n, r in results.items()}
    show(ia.fig_energy_breakdown(flows, per_km))
    st.caption(T.UI["energy_chart_caption"])
    flow_tbl = a3.energy_flow_table(flows)
    st.markdown(T.UI["energy_pct_title"])
    st.dataframe(flow_tbl.rename(columns=flow_labels(flow_tbl.columns)).round(2), hide_index=True)
    st.download_button("CSV indir", flow_tbl.to_csv(index=False).encode("utf-8"),
                       file_name="enerji_akisi.csv", mime="text/csv")

    st.subheader(T.UI["sankey_title"])
    sankey_cycle = st.selectbox("Döngü (enerji akışı)", list(flows), key="sankey_cycle")
    info_box("enerji_akisi")
    show(ia.fig_energy_sankey(flows[sankey_cycle], sankey_cycle, per_km))
    st.markdown(T.UI["q1_title"])
    q1 = a3.q1_wheel_shares(results)
    st.dataframe(q1.rename(columns=Q1_LABELS).round(2), hide_index=True)
    st.caption(T.UI["q1_caption"])
    st.download_button("CSV indir", q1.to_csv(index=False).encode("utf-8"),
                       file_name="soru1_tekerlek_paylari.csv", mime="text/csv", key="dl_q1")

# f) Motor calisma noktalari
if page == "motor":
    info_box("motor_noktalari")
    if envelope_ok:
        show(ia.fig_motor_points(results, params))
        st.caption(T.UI["motor_caption"])
    else:
        st.info(T.UI["motor_missing"])

# g) Senaryo karsilastirma (3B, her zaman Temel Arac)
if page == "senaryo":
    st.caption(T.UI["scenario_caption"].format(base=SCEN_BASE.name))
    sc_cycle = st.selectbox("Döngü", b3.CYCLES_3B, key="sc_cycle")
    sc = get_scenario_table(sc_cycle, SCEN_BASE, STAMP)
    _sv = sc.set_index(SC["scenario"])
    info_box("senaryo_karsilastirma", {
        "sc_cycle": sc_cycle,
        "sc_s1": f"{_sv.loc['S1', SC['cons_change']]:+.1f} %".replace(".", ","),
        "sc_s2": f"{_sv.loc['S2', SC['cons_change']]:+.1f} %".replace(".", ","),
        "sc_s3r": f"{_sv.loc['S3', SC['range_change']]:+.1f} %".replace(".", ","),
        "sc_s3c": f"{_sv.loc['S3', SC['cons_change']]:+.1f} %".replace(".", ","),
        "sc_s4": f"{_sv.loc['S4', SC['cons_change']]:+.2f} %".replace(".", ",")})
    st.dataframe(sc.round(3), hide_index=True)
    if has_cols(sc, [SC["scenario"], SC["cons"], SC["cons_change"]]):
        show(ia.fig_scenario_comparison(list(sc[SC["scenario"]]), list(sc[SC["cons"]]),
                                        list(sc[SC["cons_change"]]), sc_cycle))

    st.subheader(T.UI["brake_title"].format(cycle=sc_cycle, a=SCEN_A, b=SCEN_B))
    info_box("faz_tablosu", placeholder_values())
    ph = get_phase_table(sc_cycle, SCEN_BASE, STAMP)
    if get_phases(sc_cycle, STAMP) is None:
        st.caption(T.UI["no_phases"])
    styler = ph.style.format(precision=2)
    styler = style_cells(styler, lambda x: HIGHLIGHT_DIFF if abs(x) > 1e-9 else "", BC["diffs"])
    styler = style_cells(styler, lambda x: HIGHLIGHT_NEGATIVE if x < 0 else "", [BC["margin"]])
    st.dataframe(styler, hide_index=True)
    st.caption(T.UI["margin_caption"].format(a=SCEN_A, b=SCEN_B))

    needed = [BC["phase"], BC["peak_a"], BC["limit_b"], BC["margin"], BC["steps_b"],
              BC["regen_diff"], BC["friction_diff"], BC["cons_diff"]]
    whole_rows = ph[ph[BC["phase"]] == b3.WHOLE_CYCLE] if has_cols(ph, needed) else ph.iloc[0:0]
    if not whole_rows.empty:
        w = whole_rows.iloc[0]
        if w[BC["steps_b"]] == 0:
            st.info(T.UI["s4_no_effect"].format(
                cycle=sc_cycle, a=SCEN_A, b=SCEN_B, peak=w[BC["peak_a"]],
                limit=w[BC["limit_b"]], margin=w[BC["margin"]]))
        else:
            st.warning(T.UI["s4_effect"].format(
                cycle=sc_cycle, b=SCEN_B, steps=int(w[BC["steps_b"]]),
                regen=-w[BC["regen_diff"]], friction=w[BC["friction_diff"]],
                cons=w[BC["cons_diff"]]))

# h) WLTP karsilastirma (3A)
if page == "wltp":
    info_box("wltp_karsilastirma", extra_abbr=tuple(abbreviations_in(T.UI["wltp_source"])))
    if vehicle_label == BASE_LABEL:
        st.info(T.UI["wltp_base_only"])
    else:
        if missing:
            st.warning(T.UI["wltp_tesla_assumed"])
        c_a, c_b = st.columns(2)
        wltp_label = "Resmi WLTP tüketimi [Wh/km] (şebeke tarafı)"
        wltp = c_a.number_input(wltp_label,
                                value=float(TESLA_SOURCED["wltp_consumption_wh_km"]),
                                step=1.0, format="%.1f", key="wltp_value",
                                help=abbrev_help(wltp_label, T.UI["wltp_source"]))
        c_a.caption(T.UI["wltp_source"])
        eta_charge = c_b.number_input("AC şarj verimi η_şarj [-]", min_value=0.5,
                                      max_value=1.0, value=float(a3.ETA_CHARGE),
                                      step=0.001, format="%.3f", key="eta_charge",
                                      help=f"**{T.GRID_VS_BATTERY}**: "
                                           f"{T.GLOSSARY[T.GRID_VS_BATTERY]}")
        c_b.caption(T.UI["eta_charge_source"].format(
            lo=a3.ETA_CHARGE_RANGE[0], hi=a3.ETA_CHARGE_RANGE[1], eta=a3.ETA_CHARGE,
            loss=fmt_tr((1 - a3.ETA_CHARGE) * 100)))

        e_term = run_sim(a3.WLTP_CYCLE, params, STAMP).consumption_wh_km
        st.markdown(T.UI["chain_title"])
        chain = a3.wltp_chain_table(e_term, eta_charge, wltp=wltp)
        st.dataframe(chain.rename(columns=CHAIN_LABELS).round(3), hide_index=True)
        st.markdown(T.UI["band_title"])
        band = a3.wltp_band_table(e_term, wltp=wltp)
        st.dataframe(band.rename(columns=BAND_LABELS).round(3), hide_index=True)

        st.subheader(T.UI["sens_title"])
        sens = get_wltp_sensitivity(params, wltp, eta_charge, STAMP)
        st.dataframe(sens.rename(columns=SENS_LABELS).round(3), hide_index=True)
        st.caption(T.UI["sens_caption"].format(
            aux=fmt_tr(a3.SENS_P_AUX_STEP_W, 0),
            eta_t="/".join(fmt_tr(x, 2) for x in a3.SENS_ETA_T_VALUES),
            vmin="/".join(fmt_tr(x, 0) for x in a3.SENS_V_MIN_KMH),
            batt=fmt_tr(a3.SENS_BATT_LOSS_STEP * 100, 0)))
        if has_cols(sens, [SE["param"]]):
            for name in dict.fromkeys(sens[SE["param"]]):
                if name == a3.SENS_REFERENCE:
                    continue
                st.text_area(T.UI["sens_note_label"].format(param=name), key=f"note_{name}",
                             height=80, placeholder=T.UI["sens_note_placeholder"])

# i) Parametre turetme (Tesla, Asama 2): CoC yol yuku -> f_r, C_d*A_f
if page == "turetme":
    road, v_road, curves = get_road_load(STAMP)
    err_cols = [c for c in road.columns if c.endswith(p2.ERR_SUFFIX)]
    _rng = [f"{r[err_cols].min():+.1f} … {r[err_cols].max():+.1f} %".replace(".", ",")
            for _, r in road.iterrows()]
    info_box("parametre_turetme", {
        "road_a": _rng[0], "road_b": _rng[1], "road_c": _rng[2],
        "cd_info": fmt_tr(p2.CD_TESLA, 2), "af_eq": fmt_tr(TESLA_M3_SRP.af_m2, 2)},
        extra_abbr=tuple(abbreviations_in(T.UI["road_inputs"])))
    st.caption(T.UI["road_inputs"].format(f0=p2.F0, f1=p2.F1, f2=p2.F2, m=p2.MASS_KG,
                                          rho=p2.RHO, g=p2.G))
    styler = road.style.format(precision=4)
    styler = style_cells(styler, lambda x: HIGHLIGHT_NEGATIVE
                         if abs(x) > ROAD_ERR_HIGHLIGHT_PCT else "", err_cols)
    st.dataframe(styler, hide_index=True)
    st.caption(T.UI["road_err_caption"])
    st.caption(T.UI["road_cd_todo"].format(
        cd=p2.CD_TESLA, cda_eq=fmt_tr(TESLA_SOURCED["cda_equivalent_m2"], 3),
        cda_phys=fmt_tr(TESLA_SOURCED["cda_physical_m2"], 3)))
    st.caption(T.UI["road_mass_note"])
    st.download_button("CSV indir", road.to_csv(index=False).encode("utf-8"),
                       file_name="p2_yol_yuku_yontemleri.csv", mime="text/csv")
    show(ia.fig_road_load(v_road, curves))

# j) Verim haritasi ([R24] Sekil 5a) + WLTC calisma noktalari
if page == "verim":
    if vehicle_label == BASE_LABEL:
        info_box("verim_haritasi", {"eta_m_eq": "—", "eta_reg_eq": "—", "low_t_share": "—",
                                    "eta_m_par": fmt_tr(params.eta_m, 3),
                                    "eta_reg_par": fmt_tr(params.eta_reg, 3)})
        st.info(T.UI["eta_map_vehicle_only"])
    else:
        fig_map, r_w = eff_map_figure(params, p2e.REF_CYCLE,
                                      f"Verim haritası + {p2e.REF_CYCLE} çalışma noktaları")
        eff = p2e.equivalent_efficiencies(r_w, params)
        info_box("verim_haritasi", {"eta_m_eq": fmt_tr(eff["eta_m"], 3),
                                    "eta_reg_eq": fmt_tr(eff["eta_reg"], 3),
                                    "low_t_share": fmt_tr(eff["low_t"]),
                                    "eta_m_par": fmt_tr(params.eta_m, 3),
                                    "eta_reg_par": fmt_tr(params.eta_reg, 3)})
        show(fig_map)
        st.caption(T.UI["eta_map_caption"].format(low=eff["low_t"], cycle=p2e.REF_CYCLE))
