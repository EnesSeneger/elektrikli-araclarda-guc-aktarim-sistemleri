"""
Ogrenci modeli yukleme: baska bir ogrencinin kendi modelinden aldigi saniyelik P_bat ciktisini
(CSV/XLSX) bu modelin ayni dongu + Temel Arac sonucuyla karsilastirir.

Beklenen dosya: iki sutun yeterli
  - zaman: 't_s' (veya 't', 'zaman')         [s]
  - batarya gucu: 'p_bat_kw' [kW] ya da 'p_bat_w' [W] (adlarda buyuk/kucuk harf onemsiz)
Kabul olcutu 20 Kasim belgesiyle ayni: |ogrenci / referans - 1| <= %1.
"""

from __future__ import annotations

import io

import numpy as np
import pandas as pd

from evmodel.cycles import load_cycle
from evmodel.model import simulate
from evmodel.params import BASE_VEHICLE

TOL_PCT = 1.0                       # 20 Kasim belgesi kabul olcutu [%]
T_COLS = ("t_s", "t", "zaman", "time", "zaman_s")
P_KW_COLS = ("p_bat_kw", "pbat_kw", "p_bat [kw]", "p_bat_kW")
P_W_COLS = ("p_bat_w", "pbat_w", "p_bat [w]", "p_bat")


def read_upload(name: str, data: bytes) -> pd.DataFrame:
    """Yuklenen CSV/XLSX'i okur; CSV'de ayirici (',' ';' tab) ve ondalik virgul otomatik."""
    if name.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(data))
    text = data.decode("utf-8-sig", errors="replace")
    # ayirici yalnizca baslik satirindan: veri satirlarindaki ondalik virguller sayilmasin
    header = text.splitlines()[0] if text else ""
    sep = ";" if ";" in header else ("\t" if "\t" in header else ",")
    decimal = "," if sep == ";" else "."
    return pd.read_csv(io.StringIO(text), sep=sep, decimal=decimal)


def _pick(df: pd.DataFrame, names: tuple) -> str | None:
    low = {c.strip().lower(): c for c in df.columns}
    for n in names:
        if n.lower() in low:
            return low[n.lower()]
    return None


def parse_series(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """(t_s, p_bat_w) dondurur; uygun sutun yoksa ValueError (mesaj arayuzde gosterilir)."""
    t_col = _pick(df, T_COLS)
    kw_col, w_col = _pick(df, P_KW_COLS), _pick(df, P_W_COLS)
    if t_col is None or (kw_col is None and w_col is None):
        raise ValueError(f"Sütunlar bulunamadı. Gerekli: zaman ({', '.join(T_COLS[:2])}) ve "
                         f"batarya gücü (p_bat_kw veya p_bat_w). Dosyadaki sütunlar: "
                         f"{', '.join(map(str, df.columns))}")
    t_s = pd.to_numeric(df[t_col], errors="coerce").to_numpy(float)
    p = pd.to_numeric(df[kw_col if kw_col else w_col], errors="coerce").to_numpy(float)
    p_w = p * 1e3 if kw_col else p
    ok = np.isfinite(t_s) & np.isfinite(p_w)
    if ok.sum() < 2:
        raise ValueError("Dosyada sayısal veri bulunamadı (ayırıcı ve ondalık işaretini kontrol edin).")
    return t_s[ok], p_w[ok]


def compare(t_s: np.ndarray, p_bat_w: np.ndarray, cycle_name: str) -> tuple[pd.DataFrame, dict]:
    """Ogrenci serisini ayni dongudeki Temel Arac referansiyla karsilastirir.

    Doner: ozet tablo (buyukluk, referans, ogrenci, sapma %, durum) ve grafik icin seriler.
    Enerji, referansla ayni sekilde sag uc toplamla (P * dt / 3600) hesaplanir.
    """
    t_ref, v_kmh = load_cycle(cycle_name)
    r = simulate(t_ref, v_kmh, BASE_VEHICLE)
    # ogrenci serisini referans zaman eksenine oturt (ortak aralik)
    common = (t_ref >= t_s.min()) & (t_ref <= t_s.max())
    p_stu = np.interp(t_ref[common], t_s, p_bat_w)
    p_ref = r.p_bat_w[common]
    dt_s = float(t_ref[1] - t_ref[0])
    e_stu_wh = float(np.sum(p_stu) * dt_s / 3600.0)
    e_ref_wh = float(np.sum(p_ref) * dt_s / 3600.0)
    s_km = float(np.sum(r.v_ms[common]) * dt_s / 1000.0)

    rows = [
        ("Batarya enerjisi ΣE_bat [Wh]", e_ref_wh, e_stu_wh),
        ("Tüketim [Wh/km]", e_ref_wh / s_km if s_km else np.nan,
         e_stu_wh / s_km if s_km else np.nan),
        ("En büyük çekiş P_bat [kW]", p_ref.max() / 1e3, p_stu.max() / 1e3),
        ("En büyük geri kazanım P_bat [kW]", p_ref.min() / 1e3, p_stu.min() / 1e3),
    ]
    out = pd.DataFrame(rows, columns=["büyüklük", "referans", "sizin modeliniz"])
    out["sapma [%]"] = (out["sizin modeliniz"] / out["referans"] - 1.0) * 100.0
    out["durum"] = np.where(out["sapma [%]"].abs() <= TOL_PCT, "tutuyor", "tutmuyor")
    diff_kw = (p_stu - p_ref) / 1e3
    info = {"t_s": t_ref[common], "p_ref_kw": p_ref / 1e3, "p_stu_kw": p_stu / 1e3,
            "max_abs_diff_kw": float(np.max(np.abs(diff_kw))),
            "t_max_diff_s": float(t_ref[common][np.argmax(np.abs(diff_kw))]),
            "n_points": int(common.sum()), "n_cycle": len(t_ref)}
    return out, info


def example_csv(cycle_name: str = "WLTC_3b") -> bytes:
    """Ornek dosya: bu modelin Temel Arac ciktisi (sablon olarak indirilir)."""
    t_ref, v_kmh = load_cycle(cycle_name)
    r = simulate(t_ref, v_kmh, BASE_VEHICLE)
    df = pd.DataFrame({"t_s": t_ref, "p_bat_kw": np.round(r.p_bat_w / 1e3, 4)})
    return df.to_csv(index=False).encode("utf-8")
