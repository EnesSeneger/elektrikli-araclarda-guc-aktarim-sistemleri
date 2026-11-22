"""
Surus dongusu okuyucu (data/surus_donguleri.xlsx).

Excel yapisi: her donguye bir sayfa; TUM sayfalarda A = t_s (s), B = v_kmh (km/h),
1. satir baslik, dt = 1 s, t = 0'dan baslar. C ve sonraki sutunlar sayfaya gore
degisir (faz etiketi / mph / aciklama) ve OKUNMAZ.

Calistirma (proje kokunden):  python -m evmodel.cycles
"""

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXCEL_PATH = PROJECT_ROOT / "data" / "surus_donguleri.xlsx"

CYCLE_NAMES = ["WLTC_3b", "NEDC", "UDDS", "HWFET", "US06"]

# T4 referans mesafeleri [km] (odev Bolum 2 / Excel OZET sayfasi)
REFERENCE_DISTANCES_KM = {
    "WLTC_3b": 23.266,
    "NEDC": 11.013,
    "UDDS": 11.990,
    "HWFET": 16.507,
    "US06": 12.888,
}


def load_cycle(name: str, path: Path = EXCEL_PATH) -> tuple[np.ndarray, np.ndarray]:
    """Bir dongunun (t_s, v_kmh) dizilerini dondurur ve veriyi kontrol eder."""
    if name not in CYCLE_NAMES:
        raise ValueError(f"Bilinmeyen dongu: {name}. Gecerli: {CYCLE_NAMES}")
    df = pd.read_excel(path, sheet_name=name, usecols="A:B")
    df.columns = ["t_s", "v_kmh"]
    t = df["t_s"].to_numpy(dtype=float)
    v = df["v_kmh"].to_numpy(dtype=float)

    # Veri kontrolleri: bos hucre yok, t=0'dan baslar, adim her yerde 1 s
    assert not np.isnan(t).any() and not np.isnan(v).any(), f"{name}: bos hucre var"
    assert t[0] == 0, f"{name}: t=0'dan baslamiyor"
    assert np.allclose(np.diff(t), 1.0), f"{name}: zaman adimi 1 s degil"
    assert (v >= 0).all(), f"{name}: negatif hiz var"
    return t, v


def load_all_cycles(path: Path = EXCEL_PATH) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Tum donguleri {ad: (t_s, v_kmh)} sozlugu olarak dondurur."""
    return {name: load_cycle(name, path) for name in CYCLE_NAMES}


PHASE_COLUMN = "faz"  # C sutunu basligi faz etiketi tasiyan sayfalarda (WLTC_3b, NEDC)


def load_phases(name: str, path: Path = EXCEL_PATH) -> np.ndarray | None:
    """Dongunun faz etiketlerini (t_s ile ayni sirada, ornek basina bir etiket) dondurur.

    Yalnizca C sutunu basligi 'faz' olan sayfalarda (WLTC_3b, NEDC) etiket vardir;
    EPA dongulerinde C sutunu mph oldugundan None doner. load_cycle() ile ayni
    satirlari okudugu, t_s karsilastirmasiyla kontrol edilir.
    """
    if name not in CYCLE_NAMES:
        raise ValueError(f"Bilinmeyen dongu: {name}. Gecerli: {CYCLE_NAMES}")
    df = pd.read_excel(path, sheet_name=name, usecols="A,C")
    if df.columns[1] != PHASE_COLUMN:
        return None
    t_phase = df.iloc[:, 0].to_numpy(dtype=float)
    labels = df.iloc[:, 1].to_numpy(dtype=object)
    t, _ = load_cycle(name, path)
    assert np.array_equal(t_phase, t), f"{name}: faz sutunu t_s ile hizali degil"
    assert not pd.isna(labels).any(), f"{name}: bos faz etiketi var"
    return labels.astype(str)


def cycle_distance_km(v_kmh: np.ndarray, dt_s: float = 1.0) -> float:
    """Mesafe = sum(v_kmh) * dt / 3600 [km]."""
    return float(np.sum(v_kmh) * dt_s / 3600.0)


def cycle_summary() -> pd.DataFrame:
    """T4 tablosu: nokta, sure, mesafe, referans, sapma, ortalama/azami hiz."""
    rows = []
    for name, (t, v) in load_all_cycles().items():
        s = cycle_distance_km(v)
        ref = REFERENCE_DISTANCES_KM[name]
        rows.append({
            "dongu": name,
            "nokta": len(t),
            "sure_s": t[-1],
            "mesafe_km": round(s, 4),
            "referans_km": ref,
            "sapma_pct": round((s - ref) / ref * 100, 4),
            "ort_hiz_kmh": round(s / (t[-1] / 3600), 2),
            "maks_hiz_kmh": v.max(),
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print(cycle_summary().to_string(index=False))
