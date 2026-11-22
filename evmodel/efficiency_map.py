"""
Motor + invertor verim haritasi eta(n_m, T_m) - Tesla Model 3 SR+ [R24] Sekil 5a.

Veri: data/r24_fig5a_eta_map.csv (n_rpm, T_nm, eta; '#' satirlari yorum).
Haritadan elle okunmus seyrek noktalar; araliklar dogrusal enterpolasyonla doldurulur.

  eta_at(n, T):
    1) n ve T, olculen araliga kirpilir (veri min/max: T 20-400 Nm, n 500-16000 rpm).
       [R24] 15 Nm altini OLCMEMISTIR; 20 Nm altindaki noktalar 20 Nm'deki verimle
       temsil edilir (dusuk tork bolgesindeki gercek verim muhtemelen daha dusuktur).
    2) scipy.interpolate.griddata, dogrusal (Delaunay ucgenleri), ham (n, T) uzayinda
       (varsayilan rescale=False). Not: rescale=True ile WLTC esdeger verimleri ~0,002-0,003
       yukari kayar; harita okuma belirsizligi (+-0,01) icinde kalir.
    3) Dogrusal enterpolasyonun tanimsiz kaldigi (dis bukey zarf disi, NaN) noktalar
       en yakin komsu ile doldurulur.

Bu modul model.py tarafindan KULLANILMAZ; model sabit verimle calisir. Harita,
esdeger sabit verimlerin turetilmesi (analysis/p2_efficiency.py) ve ileride
"motor haritasi" bonusu icindir.
"""

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import griddata

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ETA_MAP_PATH = PROJECT_ROOT / "data" / "r24_fig5a_eta_map.csv"


@lru_cache(maxsize=4)
def load_eta_map(path: Path = ETA_MAP_PATH) -> tuple[np.ndarray, np.ndarray]:
    """Harita noktalari: (points[N, 2] = (n_rpm, T_nm), eta[N])."""
    df = pd.read_csv(path, comment="#")
    assert list(df.columns) == ["n_rpm", "T_nm", "eta"], f"beklenmeyen sutunlar: {list(df.columns)}"
    assert df["eta"].between(0, 1).all(), "verim 0-1 araliginda olmali"
    return df[["n_rpm", "T_nm"]].to_numpy(dtype=float), df["eta"].to_numpy(dtype=float)


def map_bounds(path: Path = ETA_MAP_PATH) -> dict:
    """Olculen aralik: {"n": (min, max), "T": (min, max)}."""
    pts, _ = load_eta_map(path)
    return {"n": (pts[:, 0].min(), pts[:, 0].max()), "T": (pts[:, 1].min(), pts[:, 1].max())}


def eta_at(n_rpm, t_nm, path: Path = ETA_MAP_PATH) -> np.ndarray:
    """Verilen (n_m, T_m) noktalarinda verim. T_m pozitif buyukluk olarak verilmelidir."""
    pts, eta = load_eta_map(path)
    b = map_bounds(path)
    n = np.clip(np.asarray(n_rpm, dtype=float), *b["n"])
    t = np.clip(np.asarray(t_nm, dtype=float), *b["T"])  # 15 Nm alti olculmedi (yukariya bakin)
    q = np.column_stack([n.ravel(), t.ravel()])
    out = griddata(pts, eta, q, method="linear")
    nan = np.isnan(out)
    if nan.any():
        out[nan] = griddata(pts, eta, q[nan], method="nearest")
    return out.reshape(n.shape)


def eta_grid(n_points: int = 120, path: Path = ETA_MAP_PATH):
    """Gorsellestirme icin duzenli izgara: (n_rpm[nx], T_nm[ny], eta[ny, nx])."""
    b = map_bounds(path)
    n = np.linspace(*b["n"], n_points)
    t = np.linspace(*b["T"], n_points)
    nn, tt = np.meshgrid(n, t)
    return n, t, eta_at(nn, tt, path)
