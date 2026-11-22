"""
Parametre setleri.

Iki set var:
  BASE_VEHICLE  -> Odevdeki "Temel Arac" (dogrulama T1-T4 ve 3B icin, tek ve baglayici set)
  TESLA_M3_SRP  -> Secilen gercek arac (3A ve WLTP karsilastirmasi icin)

Birimler: SI (kg, m, s, W, Wh). Odevde km/h ve kW verilen degerler burada
cevrilmis olarak tutulur; degisken adindaki son ek birimi gosterir.

Kaynak kisaltmalari (ayrintisi docs/kaynaklar.md):
  [ODEV] MKTS 5081 ara donem odevi, Bolum 2 (Temel Arac tablosu)
  [R24]  Rosenberger vd., "Comprehensive Analysis of the Tesla Model 3 on the
         Vehicle Level", World Electr. Veh. J. 2024, 15, 268.
         doi:10.3390/wevj15060268  (Tablo A1: degerler aracin CoC belgesinden)
  [EVDB] EV Database, Tesla Model 3 Standard Range Plus (CATL 6C), ikincil kaynak
  [EEA]  European Environment Agency, CO2 izleme veri tabani (Reg. (EU) 2019/631), Va=E6CR
  [ADAC26] ADAC, "Ladeverluste beim Elektroauto", W. Rudschies, 06.08.2026
  [L23]  Lacock, du Plessis, Booysen, "Electric Vehicle Drivetrain Efficiency and the
         Multi-Speed Transmission Question", World Electr. Veh. J. 2023, 14, 342.
         doi:10.3390/wevj14120342
"""

from dataclasses import dataclass, replace, fields


@dataclass(frozen=True)
class VehicleParams:
    """Modelin ihtiyac duydugu tum parametreler (SI birimleri)."""

    name: str
    m_kg: float            # test kutlesi
    delta: float           # donen kutle faktoru
    cd: float              # aerodinamik surtunme katsayisi
    af_m2: float           # on kesit alani
    fr: float              # yuvarlanma direnci katsayisi
    rw_m: float            # tekerlek dinamik yaricapi
    gear_ratio: float      # reduktor orani G
    eta_t: float           # aktarma organi verimi
    eta_m: float           # motor+invertor verimi (cekis)
    eta_reg: float         # motor+invertor verimi (geri kazanim)
    p_reg_max_w: float     # maksimum rejenerasyon gucu (batarya tarafi)
    v_min_ms: float        # rejenerasyon kesme hizi
    p_aux_w: float         # sabit yardimci yuk
    e_nom_kwh: float       # batarya enerjisi (modelde kullanilan)
    soc0_pct: float        # baslangic SoC
    soc_min_pct: float     # menzil hesabi icin alt SoC siniri
    rho_kgm3: float = 1.225
    g_ms2: float = 9.81
    grade_pct: float = 0.0  # yol egimi (%), aksi belirtilmedikce 0

    # Motor zarfi (yalnizca zarf kontrolu icin; None ise kontrol yapilmaz)
    t_peak_nm: float | None = None
    p_peak_w: float | None = None
    n_max_rpm: float | None = None

    def with_(self, **changes) -> "VehicleParams":
        """Tek parametre degistirerek yeni set uretir (3B senaryolari icin)."""
        return replace(self, **changes)

    def check_complete(self) -> None:
        """Model calistirilmadan once None kalan zorunlu parametre var mi bakar."""
        optional = {"t_peak_nm", "p_peak_w", "n_max_rpm"}
        missing = [f.name for f in fields(self)
                   if f.name not in optional and getattr(self, f.name) is None]
        if missing:
            raise ValueError(f"{self.name}: eksik parametre(ler): {missing}")


KMH = 1 / 3.6  # km/h -> m/s carpani

# ---------------------------------------------------------------------------
# Temel Arac [ODEV] - DEGISTIRME. 3B senaryolari .with_() ile turetilir.
# ---------------------------------------------------------------------------
BASE_VEHICLE = VehicleParams(
    name="Temel Arac",
    m_kg=1800.0,
    delta=1.05,
    cd=0.28,
    af_m2=2.4,
    fr=0.011,
    rw_m=0.33,
    gear_ratio=9.0,
    eta_t=0.95,
    eta_m=0.92,
    eta_reg=0.80,
    p_reg_max_w=60e3,
    v_min_ms=7 * KMH,
    p_aux_w=400.0,
    e_nom_kwh=60.0,
    soc0_pct=90.0,
    soc_min_pct=10.0,
)

# ---------------------------------------------------------------------------
# Tesla Model 3 Standard Range Plus RWD, LFP (CATL), uretim 11/2020-12/2021
# Kaynagi belli degerler girildi; None olanlar Asama 2'de (parametre
# calismasi) kaynakli olarak veya "VARSAYIM" etiketiyle doldurulacak.
# f_r ve C_d*A_f CoC yol yukunden turetildi (tests/test_p2_params.py tutarliligi denetler).
# ---------------------------------------------------------------------------
TESLA_SOURCED = {
    "mass_running_order_kg": 1825.0,   # [R24] Tablo A1, CoC
    "mass_actual_kg": 1861.0,          # [R24] Tablo A1, CoC
    "mass_measured_empty_kg": 1755.0,  # [R24] Bolum 2.1, tartim
    "tyre": "235/45R18 98Y",           # [R24] Tablo A1, CoC
    "rw_m": 0.3468,                    # [R24] Tablo A1, olcum
    "f0_N": 149.92,                    # [R24] Tablo A1, CoC yol yuku katsayilari
    "f1_N_per_kmh": 0.6299,            # [R24]
    "f2_N_per_kmh2": 0.02482,          # [R24]
    "p_peak_w": 239e3,                 # [R24] Tablo A1, CoC
    "p_30min_w": 100e3,                # [R24] Tablo A1, CoC
    "n_max_rpm": 16000.0,              # [R24] Tablo A1 (medya kaynakli)
    "t_peak_nm": 420.0,                # [R24] Tablo A1, ruhsat
    "gear_ratio": 9.04,                # [R24] Tablo A1, CoC
    "p_reg_measured_max_w": 66.9e3,    # [R24] Bolum 3.3.1, 130->100 km/h olcumu
    "e_pack_kwh": 58.0,                # [R24] Tablo A1, ruhsat
    "e_usable_kwh": 52.5,              # [EVDB] ikincil kaynak
    "v_top_kmh": 225.0,                # [EVDB] s. 4, Performance (azami hiz); 3C G kisiti
    "acc_0_100_s": 5.6,                # [EVDB] s. 4, Performance (bilgi)
    "wltp_range_km": 440.0,            # [R24] CoC
    "wltp_consumption_wh_km": 142.0,   # [EEA] Va=E6CR, alan Z (Wh/km), sebeke tarafi; [EVDB] ile ayni
    "eea_variant": "E6CR",             # [EEA] Va (TAN e4*2007/46*1293*17, *18, *19)
    "mass_wltp_test_kg": 1905.0,       # [EEA] alan Mt (WLTP test kutlesi)
    "wltp_dyno_range_km": 430.0,       # [R24] dinamometre olcumu
    # Turetilmis, bilgi amacli (analysis/p2_road_load.py; rho = 1.225 kg/m3):
    "cda_physical_m2": 0.5251709387755101,    # 2*f2*3.6^2/rho - fiziksel aero (f1 haric)
    "cda_equivalent_m2": 0.6203121369622925,  # yontem b) EKK - modelde kullanilan esdeger
    # [ADAC26] AC sarj verimi, 11 kW wallbox, sebeke enerjisine gore: Tesla Model Y kaybi %6,1.
    # Model Y olcumu (ayni platform); Model 3 icin olcum yok.
    "eta_charge_ac11": 0.939,
    "eta_charge_ac11_range": (0.930, 0.949),  # [ADAC26] bes aracin 11 kW araligi (kayip %7,0-%5,1)
    # [R24] Bolum 2.2.2, s. 6 ve Ek B: dinamometre coast-down katsayilari (bilgi; CoC'den farkli)
    "r24_coastdown_a0_N": 177.2,
    "r24_coastdown_a1_N_per_ms": 5.743,
    "r24_coastdown_a2_N_per_ms2": 0.2538,
    # [R24] WLTP dinamometre enerji akisi (bilgi, dogrulama icin; analysis/p2_efficiency.py):
    "r24_wltp_battery_wh_km": 136.0,   # [R24] dinamometre, batarya ic kayiplari dahil
    "r24_fig8_wltp_shares": {          # [R24] Sekil 8 (piksel olcumu; Urban sutunu yazili
        "tekerlek_yol": 0.836,         # etiketlerle %0,5 icinde dogrulandi)
        "invertor_tekerlek": 0.068,
        "yardimci": 0.0556,
        "batarya": 0.041,
    },
}
# [R24] WLTP, batarya uc tarafi = batarya tarafi * (1 - batarya ic kaybi payi)
TESLA_SOURCED["r24_wltp_terminal_wh_km"] = (
    TESLA_SOURCED["r24_wltp_battery_wh_km"] * (1 - TESLA_SOURCED["r24_fig8_wltp_shares"]["batarya"]))

TESLA_M3_SRP = VehicleParams(
    name="Tesla Model 3 SR+ (LFP)",
    # [EEA] WLTP test kutlesi Mt; CoC yol yuku katsayilari bu kutleyle belirlenir.
    # Kutle degisirse f_r = A/(m*g) ile yeniden turetilir (A = f_r*m*g sabit kalir).
    m_kg=1905.0,
    # [R24] Bolum 3.3.2: yazarlarin enerji hesabinda kullandigi donen kutle faktoru.
    delta=1.06,
    # Kullanilmiyor (yalnizca bilgi): model yalnizca C_d*A_f kullanir; raporda C_d*A_f
    # (esdeger 0,620 m^2, fiziksel 0,525 m^2) raporlanir.
    cd=0.23,
    # ESDEGER deger, fiziksel on alan degil; f1 terimi EKK ile v^2 terimine dagitildi.
    # af_m2 = C_d*A_f(esdeger) / 0.23. Fiziksel C_d*A_f = 2*f2*3.6^2/rho = 0.5252 m^2.
    # turetildi: analysis/p2_road_load.py, yontem b) EKK, [R24] f0/f1/f2
    af_m2=2.697009291140402,
    # turetildi: analysis/p2_road_load.py, yontem b) EKK, [R24] f0/f1/f2 (f_r = A/(m*g), m = 1905 kg)
    fr=0.008850999059998445,
    rw_m=TESLA_SOURCED["rw_m"],
    gear_ratio=TESLA_SOURCED["gear_ratio"],
    # LITERATURE DAYALI VARSAYIM: [L23] tek kademeli reduktor tipik verimi ~0,97.
    # Not: Tesla'nin reduktoru iki kademeli paralel milli oldugundan deger destekleyici
    # literaturdur, araca ozgu olcum degildir.
    eta_t=0.97,
    # [R24] Sekil 5a, WLTC enerji agirlikli, analysis/p2_efficiency.py
    eta_m=0.9325798992668461,
    # ayni harita, geri kazanim simetri VARSAYIMI (analysis/p2_efficiency.py)
    eta_reg=0.9173398234852924,
    p_reg_max_w=TESLA_SOURCED["p_reg_measured_max_w"],
    # VARSAYIM: odev Temel Arac degeri; [R24] surus modunun yalnizca 20 km/h altini etkiledigini belirtir
    v_min_ms=7 * KMH,
    # [R24] Sekil 8: WLTP'de yardimci yuk payi %5,56 x 136 Wh/km x 23,27 km / 0,5 h (HVAC kapali)
    # = 352 W. Hesap: analysis/p2_efficiency.py (aux_power_from_r24).
    p_aux_w=352.0,
    # [R24] Sekil 4: yeni arac C/57 sarj enerjisi (BMS sinirlari arasi)
    e_nom_kwh=57.0,
    soc0_pct=90.0,
    soc_min_pct=10.0,
    t_peak_nm=TESLA_SOURCED["t_peak_nm"],
    p_peak_w=TESLA_SOURCED["p_peak_w"],
    n_max_rpm=TESLA_SOURCED["n_max_rpm"],
)
