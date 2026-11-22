"""
Asama 2 - Tesla parametre calismasi, parca 1: CoC yol yuku katsayilarindan
model parametrelerine (f_r, C_d*A_f) gecis.

CoC (WLTP) yol yuku [R24 Tablo A1]:  F_CoC(v) = f0 + f1*v + f2*v^2   (v km/h, F N)
Model (odev 3.2) yalnizca iki terim icerir:  F = f_r*m*g + 1/2*rho*C_d*A_f*v^2
Hizla dogrusal artan f1 teriminin modelde karsiligi yok. Model DEGISMEZ; uc yontemle
CoC egrisi F = A + B*v^2 (v km/h) bicimine indirgenir:

  a) dogrudan : A = f0, B = f2                              (f1 ihmal)
  b) EKK      : [1, v^2] tabaniyla 0..v_max(WLTC_3b) araliginda N_FIT noktada lstsq
  c) f1->f_r  : B = f2 (fiziksel aero korunur); f1*v teriminin WLTC_3b'deki isi
                sabit kuvvete esitlenir: A = f0 + f1 * sum(v^2)/sum(v)  (v > 0 adimlari)

Donusum:  f_r = A / (m*g)        C_d*A_f = 2*B*3.6^2 / rho
          (3.6^2: N/(km/h)^2 -> N/(m/s)^2)

ONEMLI: f_r turetiminde kullanilan kutle (m) ve rho, modelde de AYNEN kullanilmalidir.
Aksi halde modeldeki f_r*m*g ve 1/2*rho*C_d*A_f carpimlari CoC degerlerini (A, B)
vermez; turetilen f_r ve C_d*A_f yalnizca bu m ve rho ile birlikte anlamlidir.

Bu dosya params.py'ye DEGER YAZMAZ; yontem secimi kullanicinin karari.
Calistirma:  python -m analysis.p2_road_load
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evmodel.cycles import CYCLE_NAMES, load_all_cycles  # noqa: E402
from evmodel.params import BASE_VEHICLE, TESLA_SOURCED  # noqa: E402

TABLES = ROOT / "results" / "tables"
FIT_CYCLE = "WLTC_3b"       # EKK araliginin ust siniri ve c) yonteminin agirlik dongusu
N_FIT = 500                 # EKK nokta sayisi
KMH_TO_MS = 3.6             # N/(km/h)^2 -> N/(m/s)^2 icin 3.6^2

# Kullanilmiyor (yalnizca bilgi): model yalnizca C_d*A_f kullanir. Yalnizca A_f'yi C_d*A_f'den ayirmak icin
# gecici sabit; f_r ve C_d*A_f sonuclarini etkilemez.
CD_TESLA = 0.23

# Girdiler: kaynakli degerler TESLA_SOURCED'dan, fiziksel sabitler BASE_VEHICLE'dan
F0 = TESLA_SOURCED["f0_N"]
F1 = TESLA_SOURCED["f1_N_per_kmh"]
F2 = TESLA_SOURCED["f2_N_per_kmh2"]
MASS_KG = TESLA_SOURCED["mass_wltp_test_kg"]  # [EEA] Mt: CoC yol yuku bu kutleyle belirlenir
RHO = BASE_VEHICLE.rho_kgm3
G = BASE_VEHICLE.g_ms2

METHODS = {  # etiketler tabloda ve grafik lejantinda gorunur
    "a": "a) doğrudan",
    "b": "b) EKK",
    "c": "c) f1→f_r",
}

# Tablo sutun adlari (app.py ayni sabitleri kullanir)
ROAD_COLS = {
    "method": "yontem",
    "A": "A_N",
    "B": "B_N_per_kmh2",
    "fr": "f_r",
    "cda": "CdA_m2",
    "af": "A_f_m2",
}
ERR_SUFFIX = "_%"  # dongu basina direnc enerjisi hatasi sutunu: "<dongu>_%"


def f_coc(v_kmh: np.ndarray) -> np.ndarray:
    """CoC yol yuku egrisi F(v) [N], v km/h."""
    return F0 + F1 * v_kmh + F2 * v_kmh ** 2


def fit_direct() -> tuple[float, float]:
    """a) f1 ihmal."""
    return F0, F2


def fit_lstsq(v_max_kmh: float, n: int = N_FIT) -> tuple[float, float]:
    """b) [1, v^2] tabaniyla en kucuk kareler (0..v_max, n nokta)."""
    v = np.linspace(0.0, v_max_kmh, n)
    basis = np.column_stack([np.ones_like(v), v ** 2])
    (a, b), *_ = np.linalg.lstsq(basis, f_coc(v), rcond=None)
    return float(a), float(b)


def fit_f1_to_fr(v_cycle_kmh: np.ndarray) -> tuple[float, float]:
    """c) f1*v isini (v > 0 adimlarinda) sabit kuvvete esitle; B = f2."""
    v = v_cycle_kmh[v_cycle_kmh > 0]
    return F0 + F1 * float(np.sum(v ** 2) / np.sum(v)), F2


def to_model_params(a_n: float, b_n_kmh2: float) -> dict:
    """(A, B) -> f_r, C_d*A_f [m^2], A_f [m^2] (C_d = CD_TESLA ile)."""
    cda = 2.0 * b_n_kmh2 * KMH_TO_MS ** 2 / RHO
    return {"fr": a_n / (MASS_KG * G), "cda": cda, "af": cda / CD_TESLA}


def resistance_energy_error_pct(a_n: float, b_n_kmh2: float, v_kmh: np.ndarray) -> float:
    """(sum (A + B v^2) v / sum F_CoC(v) v - 1) * 100, yalnizca v > 0 adimlari."""
    v = v_kmh[v_kmh > 0]
    return (np.sum((a_n + b_n_kmh2 * v ** 2) * v) / np.sum(f_coc(v) * v) - 1.0) * 100.0


def method_least_squares(cycles: dict | None = None) -> dict:
    """Secilen yontem b) EKK: {"A", "B", "fr", "cda", "af"} (params.py degerlerinin kaynagi).

    tests/test_p2_params.py, params.TESLA_M3_SRP degerlerini bununla karsilastirir.
    """
    cycles = load_all_cycles() if cycles is None else cycles
    a_n, b_n = fit_lstsq(float(cycles[FIT_CYCLE][1].max()))
    return {"A": a_n, "B": b_n, **to_model_params(a_n, b_n)}


def fits(cycles: dict | None = None) -> dict:
    """{yontem etiketi: (A, B)}."""
    cycles = load_all_cycles() if cycles is None else cycles
    v_fit = cycles[FIT_CYCLE][1]
    return {
        METHODS["a"]: fit_direct(),
        METHODS["b"]: fit_lstsq(float(v_fit.max())),
        METHODS["c"]: fit_f1_to_fr(v_fit),
    }


def compare(cycles: dict | None = None) -> pd.DataFrame:
    """Uc yontemin karsilastirma tablosu: A, B, f_r, C_d*A_f, A_f ve dongu basina % hata."""
    cycles = load_all_cycles() if cycles is None else cycles
    c = ROAD_COLS
    rows = []
    for label, (a_n, b_n) in fits(cycles).items():
        mp = to_model_params(a_n, b_n)
        row = {c["method"]: label, c["A"]: a_n, c["B"]: b_n,
               c["fr"]: mp["fr"], c["cda"]: mp["cda"], c["af"]: mp["af"]}
        for name in CYCLE_NAMES:
            row[name + ERR_SUFFIX] = resistance_energy_error_pct(a_n, b_n, cycles[name][1])
        rows.append(row)
    return pd.DataFrame(rows)


def road_load_curves(cycles: dict | None = None, n: int = N_FIT) -> tuple[np.ndarray, dict]:
    """Grafik icin 0..v_max(WLTC_3b) araliginda F(v) egrileri: (v_kmh, {ad: F_N})."""
    cycles = load_all_cycles() if cycles is None else cycles
    v = np.linspace(0.0, float(cycles[FIT_CYCLE][1].max()), n)
    curves = {"CoC (f0 + f1 v + f2 v²)": f_coc(v)}
    curves.update({label: a_n + b_n * v ** 2 for label, (a_n, b_n) in fits(cycles).items()})
    return v, curves


def plot_png(cycles: dict | None = None) -> Path:
    """run_all.py icin matplotlib PNG: results/figures/p2_yol_yuku_egrileri.png."""
    from evmodel.plotting import C_LIMIT, plt, save_fig, setup_style

    setup_style()
    v, curves = road_load_curves(cycles)
    colors = [C_LIMIT, "#2a78d6", "#eb6834", "#1baf7a"]  # CoC gri, sonra kategorik sira
    styles = ["-", "--", "-", "-."]
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    for (name, f), color, ls in zip(curves.items(), colors, styles):
        ax.plot(v, f, color=color, linestyle=ls, linewidth=2.0 if name.startswith("CoC") else 1.4,
                label=name)
    ax.set_xlabel("v [km/h]")
    ax.set_ylabel("F [N]")
    ax.set_title("Yol yükü: CoC eğrisi ve iki terimli model yaklaşımları", loc="left", fontsize=9)
    ax.set_xlim(0, v[-1])
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    return save_fig(fig, "p2_yol_yuku_egrileri")


def main(figures: bool = True) -> pd.DataFrame:
    """Tabloyu yazdirir, CSV olarak kaydeder; istenirse PNG grafigini uretir."""
    cycles = load_all_cycles()
    df = compare(cycles)
    TABLES.mkdir(parents=True, exist_ok=True)
    df.to_csv(TABLES / "p2_yol_yuku_yontemleri.csv", index=False)
    print(f"\np2_yol_yuku_yontemleri (m = {MASS_KG:.0f} kg, rho = {RHO}, g = {G}, "
          f"C_d = {CD_TESLA} [yalnizca bilgi]):")
    print(df.round(4).to_string(index=False))
    if figures:
        print("  ", plot_png(cycles))
    return df


if __name__ == "__main__":
    main()
