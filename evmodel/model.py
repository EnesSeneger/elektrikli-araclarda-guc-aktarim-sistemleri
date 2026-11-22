"""
Geriye donuk (backward-facing) EV enerji modeli - odev Bolum 1.

Girdi : zaman-hiz tablosu (t_s, v_kmh) + VehicleParams
Cikti : SimResult (zaman serileri, toplam enerji, Wh/km, rejenerasyon payi,
        menzil, zarf/limit uyarilari, enerji kalemleri)

Denklemler (dt = 1 s):
  3.1  v = v_kmh/3.6 ; a: merkezi fark, uclarda tek yonlu fark (np.gradient)
  3.2  F_aero = 0.5 rho Cd Af v^2 ; F_roll = fr m g cos(theta) (v=0 ve a=0 ise 0)
       F_grade = m g sin(theta) ; F_inertia = delta m a ; F_trac = toplam
  3.3  P_w = F_trac v ; T_w = F_trac rw ; n_w = v/rw * 60/(2 pi)
       T_m = T_w/(G eta_t) (cekis), T_w*eta_t/G (frenleme) ; n_m = n_w G
  3.4  P_w >= 0 : P_trac = P_w/(eta_t eta_m)
       P_w <  0 : P_trac = max(P_w eta_t eta_reg, -P_reg_max)
       v < v_min ve P_w < 0 : P_trac = 0 (surtunmeli fren)
       P_bat = P_trac + P_aux
  3.5  E_adim = P_bat dt/3600 [Wh] ; SoC(t) = SoC(t-1) - E_adim/(E_nom*1000)*100
       s = sum(v dt)/1000 ; e = sum(E_adim)/s ; rho_reg = |sum E(P_trac<0)| / sum E(P_trac>0)
  3.6  Menzil = E_nom (SoC0 - SoCmin)/100 / e
  3.7  T_m > T_max(n_m) olan adimlar sayilir.
"""

from dataclasses import dataclass, field

import numpy as np

from evmodel.envelope import t_max_nm
from evmodel.params import VehicleParams


@dataclass
class SimResult:
    """simulate() ciktisi. Zaman serileri numpy dizisi, ozetler float/int."""

    # zaman serileri
    t_s: np.ndarray
    v_ms: np.ndarray
    a_ms2: np.ndarray
    f_aero_n: np.ndarray
    f_roll_n: np.ndarray
    f_grade_n: np.ndarray
    f_inertia_n: np.ndarray
    f_trac_n: np.ndarray
    p_w_w: np.ndarray
    t_m_nm: np.ndarray
    n_m_rpm: np.ndarray
    p_trac_w: np.ndarray
    p_bat_w: np.ndarray
    e_step_wh: np.ndarray
    soc_pct: np.ndarray
    # ozetler
    distance_km: float
    e_bat_wh: float
    consumption_wh_km: float
    regen_share: float
    range_km: float
    n_reg_limited: int          # P_reg,max sinirina takilan adim sayisi
    n_envelope_violations: int  # T_m > T_max adim sayisi (zarf tanimliysa)
    energy_wh: dict = field(default_factory=dict)  # enerji kalemleri (T3)

    def summary(self) -> dict:
        """Tablolar icin tek satirlik ozet."""
        return {
            "mesafe_km": self.distance_km,
            "ort_hiz_kmh": self.distance_km / (self.t_s[-1] - self.t_s[0]) * 3600
            if self.t_s[-1] > self.t_s[0] else 0.0,
            "E_bat_Wh": self.e_bat_wh,
            "tuketim_Wh_km": self.consumption_wh_km,
            "rejen_payi_pct": self.regen_share * 100,
            "P_reg_sinir_adim": self.n_reg_limited,
            "zarf_disi_adim": self.n_envelope_violations,
            "menzil_km": self.range_km,
        }


def simulate(t_s: np.ndarray, v_kmh: np.ndarray, p: VehicleParams) -> SimResult:
    """Zaman-hiz profilini verilen parametrelerle saniye saniye cozer."""
    p.check_complete()
    t_s = np.asarray(t_s, dtype=float)
    v_kmh = np.asarray(v_kmh, dtype=float)
    dt = float(t_s[1] - t_s[0])
    assert np.allclose(np.diff(t_s), dt), "zaman adimi sabit olmali"

    # 3.1 Hiz ve ivme
    v = v_kmh / 3.6
    a = np.gradient(v, dt)  # ic noktalarda merkezi, uclarda tek yonlu fark

    # 3.2 Direnc kuvvetleri
    theta = np.arctan(p.grade_pct / 100.0)
    f_aero = 0.5 * p.rho_kgm3 * p.cd * p.af_m2 * v**2
    standing = (v == 0) & (a == 0)
    f_roll = np.where(standing, 0.0, p.fr * p.m_kg * p.g_ms2 * np.cos(theta))
    f_grade = np.full_like(v, p.m_kg * p.g_ms2 * np.sin(theta))  # v=0'da P_w=0 olur
    f_inertia = p.delta * p.m_kg * a
    f_trac = f_aero + f_roll + f_grade + f_inertia

    # 3.3 Tekerlek ve motor calisma noktasi
    p_w = f_trac * v
    t_w = f_trac * p.rw_m
    n_w = v / p.rw_m * 60.0 / (2.0 * np.pi)
    n_m = n_w * p.gear_ratio
    t_m = np.where(t_w >= 0, t_w / (p.gear_ratio * p.eta_t),
                   t_w * p.eta_t / p.gear_ratio)

    # 3.4 Batarya gucu (karar blogu)
    traction = p_w >= 0
    p_regen_ideal = p_w * p.eta_t * p.eta_reg             # negatif
    p_regen = np.maximum(p_regen_ideal, -p.p_reg_max_w)   # sinirli
    low_speed = (v < p.v_min_ms) & ~traction
    p_trac = np.where(traction, p_w / (p.eta_t * p.eta_m), p_regen)
    p_trac = np.where(low_speed, 0.0, p_trac)
    p_bat = p_trac + p.p_aux_w

    reg_limited = (~traction) & (~low_speed) & (p_regen_ideal < -p.p_reg_max_w)

    # 3.5 Enerji, SoC, tuketim
    e_step = p_bat * dt / 3600.0                       # Wh
    soc = p.soc0_pct - np.cumsum(e_step) / (p.e_nom_kwh * 1000.0) * 100.0
    distance_km = float(np.sum(v * dt) / 1000.0)
    e_bat = float(e_step.sum())
    consumption = e_bat / distance_km if distance_km > 0 else np.nan
    e_trac_pos = float(np.sum(p_trac[p_trac > 0]) * dt / 3600.0)
    e_trac_neg = float(np.sum(p_trac[p_trac < 0]) * dt / 3600.0)
    regen_share = abs(e_trac_neg) / e_trac_pos if e_trac_pos > 0 else 0.0

    # 3.6 Menzil
    range_km = p.e_nom_kwh * 1000.0 * (p.soc0_pct - p.soc_min_pct) / 100.0 / consumption

    # 3.7 Zarf kontrolu (yalnizca cekis adimlari; zarf tanimli degilse atlanir)
    n_violations = 0
    if p.t_peak_nm is not None and p.p_peak_w is not None:
        t_lim = t_max_nm(n_m, p.t_peak_nm, p.p_peak_w, p.n_max_rpm)
        n_violations = int(np.sum(traction & (t_m > t_lim)))

    energy = _energy_breakdown(dt, v, f_aero, f_roll, f_grade, f_inertia, p_w,
                               p_trac, traction, low_speed, p_regen_ideal, p_regen, p)

    return SimResult(
        t_s=t_s, v_ms=v, a_ms2=a, f_aero_n=f_aero, f_roll_n=f_roll,
        f_grade_n=f_grade, f_inertia_n=f_inertia, f_trac_n=f_trac, p_w_w=p_w,
        t_m_nm=t_m, n_m_rpm=n_m, p_trac_w=p_trac, p_bat_w=p_bat,
        e_step_wh=e_step, soc_pct=soc, distance_km=distance_km, e_bat_wh=e_bat,
        consumption_wh_km=consumption, regen_share=regen_share, range_km=range_km,
        n_reg_limited=int(reg_limited.sum()), n_envelope_violations=n_violations,
        energy_wh=energy,
    )


def _energy_breakdown(dt, v, f_aero, f_roll, f_grade, f_inertia, p_w, p_trac,
                      traction, low_speed, p_regen_ideal, p_regen, p) -> dict:
    """Enerji kalemleri [Wh] - T3 enerji dengesi ve 3A paylari icin.

    Kayiplar dogrudan guc akisindan, birbirinden bagimsiz hesaplanir:
      cekis   : aktarma = P_w(1/eta_t - 1) ; motor = P_w/eta_t (1/eta_m - 1)
      frenleme: once surtunmeli fren tekerlekte alir (v<v_min veya P_reg siniri),
                kalan tekerlek gucu aktarma (1-eta_t) ve motor (1-eta_reg) kaybina ugrar.
    """
    wh = dt / 3600.0
    pw_pos = np.where(traction, p_w, 0.0)
    pw_neg = np.where(~traction, -p_w, 0.0)  # pozitif buyukluk

    # frenlemede tekerlekten geri kazanima giden kisim (surtunmeli fren haric)
    recovered_wheel = np.where(low_speed, 0.0,
                               pw_neg * (p_regen / np.where(p_regen_ideal < 0, p_regen_ideal, 1.0)))
    recovered_wheel = np.where(~traction, recovered_wheel, 0.0)
    friction = pw_neg - recovered_wheel

    loss_trans = (pw_pos * (1 / p.eta_t - 1) + recovered_wheel * (1 - p.eta_t)).sum() * wh
    loss_motor = (pw_pos / p.eta_t * (1 / p.eta_m - 1)).sum() * wh
    loss_regen = (recovered_wheel * p.eta_t * (1 - p.eta_reg)).sum() * wh
    loss_friction = friction.sum() * wh

    e_wheel = float(p_w.sum() * wh)
    e_aux = p.p_aux_w * len(v) * wh
    e_bat = float((p_trac.sum() + p.p_aux_w * len(v)) * wh)
    losses = loss_trans + loss_motor + loss_regen + loss_friction

    # Tekerlek enerjisinin direnc bilesenleri (yalnizca cekis adimlari: 3A paylari)
    e_aero_trac = float((f_aero * v)[traction].sum() * wh)
    e_roll_trac = float((f_roll * v)[traction].sum() * wh)
    e_inertia_trac = float((f_inertia * v)[traction].sum() * wh)

    return {
        "E_bat": e_bat,
        "E_tekerlek": e_wheel,
        "E_tekerlek_cekis": float(pw_pos.sum() * wh),
        "E_tekerlek_fren": float(-pw_neg.sum() * wh),
        "E_aux": e_aux,
        "kayip_aktarma": float(loss_trans),
        "kayip_motor_cekis": float(loss_motor),
        "kayip_rejen": float(loss_regen),
        "kayip_surtunmeli_fren": float(loss_friction),
        "kayip_toplam": float(losses),
        # direnc bilesenleri (tum dongu, isaretli)
        "E_aero": float((f_aero * v).sum() * wh),
        "E_roll": float((f_roll * v).sum() * wh),
        "E_grade": float((f_grade * v).sum() * wh),
        "E_inertia": float((f_inertia * v).sum() * wh),
        "dE_kin": 0.5 * p.delta * p.m_kg * (v[-1] ** 2 - v[0] ** 2) / 3600.0,
        # cekis adimlarinda tekerlekteki pay
        "E_aero_cekis": e_aero_trac,
        "E_roll_cekis": e_roll_trac,
        "E_ivme_cekis": e_inertia_trac,
    }
