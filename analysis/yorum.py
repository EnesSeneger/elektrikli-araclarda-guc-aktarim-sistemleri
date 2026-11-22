"""
Odev yorum sorulari (3A Soru 1-4, 3B Soru 1-5) icin CANLI bulgular.

Soru metinleri odevden aynen alinir (sabit). Bulgular SABIT CEVAP DEGILDIR: her cagrida o anki
parametrelerle calistirilan simulasyonlardan hesaplanir ve sayilarla cumleye dokulur.
Parametre degisince bulgular da degisir (orn. kutle artinca S1 ile S2'nin sirasi degisebilir).

Her fonksiyon [{"no", "soru", "bulgular": [str], "tablo": DataFrame | None}] dondurur.
Kullanim: app.py "Yorum sorulari" bolumu. Hesaplar yalnizca evmodel/analysis fonksiyonlariyla.
"""

import numpy as np
import pandas as pd

from analysis import a3_cycles as a3
from analysis import b3_sensitivity as b3
from evmodel.model import simulate
from evmodel.params import TESLA_SOURCED, VehicleParams

# Odev metni (docs/odev.pdf, Bolum 5) - sorular aynen
Q3A = {
    1: "Hangi döngü en çok enerji tüketti? Aerodinamik, yuvarlanma ve ivmelenme enerjisi "
       "paylarını hesaplayarak açıklayın.",
    2: "Güç grafiklerindeki ani çekiş tepelerini ve rejenerasyon tepelerini karşılaştırın. "
       "P_reg,max sınırına hangi döngüde, ne sıklıkta ulaşıldı?",
    3: "Hangi döngü neden gerçek dışı ve \"iyimser\" bir menzil veriyor? Kendi sonuçlarınızla "
       "gösterin.",
    4: "Resmi WLTP değeri ile farkı kalem kalem açıklayın: şarj verimi, yardımcı yükler, test "
       "kütlesi, lastik, sabit verim varsayımı.",
}
Q3B = {
    1: "Kütledeki %20 artış tüketimi ne kadar değiştirdi? Rejenerasyon bu etkiyi nasıl "
       "yumuşattı?",
    2: "C_d'deki %20 artış tüketimi ne kadar değiştirdi?",
    3: "WLTC 3b gibi karma bir döngüde menzil için kütle mi daha kritik, aerodinamik mi? Aynı "
       "analizi HWFET ile tekrarlarsanız sonuç değişir mi?",
    4: "S3'te batarya %20 büyüdü; menzil tam %20 arttı mı? Farkı ek kütlenin tüketime etkisiyle "
       "nicel olarak açıklayın.",
    5: "S4'te rejenerasyon sınırının etkisi hangi fazda (düşük/orta/yüksek/çok yüksek) en "
       "belirgin?",
}
WLTP_CYCLE = a3.WLTP_CYCLE
HWFET = "HWFET"
SCENARIO_STEP_PCT = 20.0   # odev 3B: her senaryoda +%20 (S3 batarya)
MASS_SCN, CD_SCN, BATT_SCN, REG_SCN = "S1", "S2", "S3", "S4"
SENS_MASS_KG = 100.0       # Soru 4 test kutlesi duyarliligi (WLTP zinciri, a3 ile ayni amac)
SENS_FR_FACTOR = 0.10      # Soru 4 lastik: f_r +-%10
SENS_AUX_W = a3.SENS_P_AUX_STEP_W


def _f(x: float, nd: int = 1) -> str:
    """Ondalik virgullu sayi."""
    return f"{x:.{nd}f}".replace(".", ",").replace("-", "−")


def _signed(x: float, nd: int = 1) -> str:
    return ("+" if x >= 0 else "") + _f(x, nd)


def _pcts(x: float, nd: int = 1) -> str:
    """Isaretli yuzde, Turkce bicim: +%10,6 / −%1,2."""
    return ("+" if x >= 0 else "−") + "%" + _f(abs(x), nd)


# ---------------------------------------------------------------------------
# 3A
# ---------------------------------------------------------------------------
def questions_3a(results: dict, p: VehicleParams, cycles: dict, is_real_vehicle: bool) -> list:
    """results: {dongu: SimResult} (secili donguler, secili parametreler)."""
    out = []
    names = list(results)
    cons = {n: r.consumption_wh_km for n, r in results.items()}

    # Soru 1
    q1 = a3.q1_wheel_shares(results).set_index(a3.Q1_COLS["cycle"])
    c = a3.Q1_COLS
    hi, lo = max(cons, key=cons.get), min(cons, key=cons.get)
    b = [f"En çok tüketen döngü **{hi}**: {_f(cons[hi])} Wh/km. En az tüketen **{lo}**: "
         f"{_f(cons[lo])} Wh/km (fark %{_f((cons[hi] / cons[lo] - 1) * 100, 0)})."]
    row = q1.loc[hi]
    b.append(f"{hi} çekiş enerjisi payları: aerodinamik %{_f(row[c['aero_pct']])}, yuvarlanma "
             f"%{_f(row[c['roll_pct']])}, ivmelenme %{_f(row[c['acc_pct']])}.")
    top_aero = q1[c["aero"]].idxmax()
    top_acc = q1[c["acc"]].idxmax()
    b.append(f"Aerodinamik enerji en çok **{top_aero}** döngüsünde ({_f(q1.loc[top_aero, c['aero']])}"
             f" Wh/km), ivmelenme enerjisi en çok **{top_acc}** döngüsünde "
             f"({_f(q1.loc[top_acc, c['acc']])} Wh/km); rejenerasyonla geri dönen pay "
             f"%{_f(q1.loc[top_acc, c['acc_recovered']], 0)}.")
    tbl = q1[[c["aero"], c["roll"], c["acc"], c["aero_pct"], c["roll_pct"], c["acc_pct"]]].copy()
    tbl.insert(0, "tuketim_Wh_km", pd.Series(cons))
    out.append({"no": 1, "soru": Q3A[1], "bulgular": b, "tablo": tbl.round(1)})

    # Soru 2
    q2 = a3.q2_peak_power(results, p).set_index(a3.Q2_COLS["cycle"])
    c2 = a3.Q2_COLS
    pk = q2[c2["p_bat_max"]].idxmax()
    rg = q2[c2["regen_peak"]].idxmax()
    ratio = q2[c2["p_bat_max"]] / q2[c2["regen_peak"]].replace(0, np.nan)
    b = [f"En yüksek çekiş tepesi **{pk}**: {_f(q2.loc[pk, c2['p_bat_max']])} kW; en yüksek "
         f"rejenerasyon tepesi **{rg}**: {_f(q2.loc[rg, c2['regen_peak']])} kW.",
         f"Çekiş tepesi rejenerasyon tepesinin {_f(ratio.min())}–{_f(ratio.max())} katı "
         f"(döngüye göre)."]
    hit = q2[q2[c2["limit_steps"]] > 0]
    if hit.empty:
        b.append(f"P_reg,max = {_f(p.p_reg_max_w / 1e3)} kW sınırına **hiçbir seçili döngüde "
                 f"ulaşılmadı**; sınıra en yakın döngü **{rg}** (kalan pay "
                 f"{_f(q2.loc[rg, c2['margin']])} kW).")
    else:
        for n, r in hit.iterrows():
            n_brake = int(np.sum(results[n].p_w_w < 0))
            b.append(f"**{n}**: {int(r[c2['limit_steps']])} adımda sınıra ulaşıldı (frenleme "
                     f"adımlarının %{_f(r[c2['limit_steps']] / max(n_brake, 1) * 100)} kadarı).")
    out.append({"no": 2, "soru": Q3A[2], "bulgular": b,
                "tablo": q2[[c2["p_bat_max"], c2["regen_peak"], c2["margin"],
                             c2["limit_steps"]]].round(2)})

    # Soru 3
    tab = a3.cycle_table(results, p).set_index(a3.CYCLE_COLS["cycle"])
    cc = a3.CYCLE_COLS
    best = tab[cc["range"]].idxmax()
    worst = tab[cc["range"]].idxmin()
    b = [f"En uzun menzili **{best}** veriyor: {_f(tab.loc[best, cc['range']], 0)} km "
         f"(SoC {_f(p.soc0_pct, 0)}→{_f(p.soc_min_pct, 0)}), tam bataryada "
         f"{_f(tab.loc[best, cc['range_full']], 0)} km. En kısa **{worst}**: "
         f"{_f(tab.loc[worst, cc['range']], 0)} km.",
         f"{best}: ortalama hız {_f(tab.loc[best, cc['avg_speed']])} km/h, rejenerasyon payı "
         f"%{_f(tab.loc[best, cc['regen_share']])}, aerodinamik payı "
         f"%{_f(q1.loc[best, c['aero_pct']])} → düşük hız ve yüksek geri kazanım menzili "
         f"büyütüyor; HVAC yükü (P_aux = {_f(p.p_aux_w, 0)} W) gerçek kullanımdan düşük."]
    if is_real_vehicle:
        ref = TESLA_SOURCED["wltp_range_km"]
        over = tab[tab[cc["range_full"]] > ref].index.tolist()
        if over:
            b.append(f"Tam batarya menzili resmi WLTP menzilini ({_f(ref, 0)} km) aşan döngüler: "
                     f"**{', '.join(over)}**.")
    out.append({"no": 3, "soru": Q3A[3], "bulgular": b,
                "tablo": tab[[cc["avg_speed"], cc["cons"], cc["regen_share"], cc["range"],
                              cc["range_full"]]].round(1)})

    # Soru 4
    if not is_real_vehicle or WLTP_CYCLE not in cycles:
        b = ["Resmi WLTP değeri yalnızca gerçek araç için vardır; bu soruyu görmek için kenar "
             "çubuğundan Tesla'yı seçin."]
        out.append({"no": 4, "soru": Q3A[4], "bulgular": b, "tablo": None})
        return out
    t, v = cycles[WLTP_CYCLE]
    e_term = simulate(t, v, p).consumption_wh_km
    k = a3.wltp_chain(e_term)
    b = [f"Model batarya uç tarafı {_f(k['a'])} → batarya iç kaybıyla {_f(k['b'])} → şarj "
         f"verimiyle (η = {_f(a3.ETA_CHARGE, 3)}) priz tarafı **{_f(k['c'])} Wh/km**; resmi "
         f"WLTP {_f(k['d'])} Wh/km → fark {_signed(k['diff'])} Wh/km ({_pcts(k['diff_pct'])})."]

    def grid(pp):
        return a3.wltp_chain(simulate(t, v, pp).consumption_wh_km)["c"]

    base = k["c"]
    A = p.fr * p.m_kg * p.g_ms2  # yol yuku sabit terimi korunarak kutle degisimi
    items = [
        ("Şarj verimi", f"η_şarj {a3.ETA_CHARGE_RANGE[0]}–{a3.ETA_CHARGE_RANGE[1]}",
         a3.wltp_chain(e_term, a3.ETA_CHARGE_RANGE[1])["c"] - base,
         a3.wltp_chain(e_term, a3.ETA_CHARGE_RANGE[0])["c"] - base),
        ("Yardımcı yükler", f"P_aux ±{_f(SENS_AUX_W, 0)} W",
         grid(p.with_(p_aux_w=p.p_aux_w - SENS_AUX_W)) - base,
         grid(p.with_(p_aux_w=p.p_aux_w + SENS_AUX_W)) - base),
        ("Test kütlesi", f"m ±{_f(SENS_MASS_KG, 0)} kg (yol yükü sabit)",
         grid(p.with_(m_kg=p.m_kg - SENS_MASS_KG,
                      fr=A / ((p.m_kg - SENS_MASS_KG) * p.g_ms2))) - base,
         grid(p.with_(m_kg=p.m_kg + SENS_MASS_KG,
                      fr=A / ((p.m_kg + SENS_MASS_KG) * p.g_ms2))) - base),
        ("Lastik", f"f_r ±%{_f(SENS_FR_FACTOR * 100, 0)}",
         grid(p.with_(fr=p.fr * (1 - SENS_FR_FACTOR))) - base,
         grid(p.with_(fr=p.fr * (1 + SENS_FR_FACTOR))) - base),
        ("Sabit verim", f"η_t {a3.SENS_ETA_T_VALUES[1]}/{a3.SENS_ETA_T_VALUES[0]}",
         grid(p.with_(eta_t=a3.SENS_ETA_T_VALUES[1])) - base,
         grid(p.with_(eta_t=a3.SENS_ETA_T_VALUES[0])) - base),
    ]
    df = pd.DataFrame([{"kalem": n, "değişim": d, "alt_Wh_km": lo_, "ust_Wh_km": hi_,
                        "aralik_pct": (hi_ - lo_) / k["d"] * 100} for n, d, lo_, hi_ in items])
    biggest = df.loc[df["aralik_pct"].idxmax()]
    covered = df[df["aralik_pct"] / 2 >= abs(k["diff_pct"])]["kalem"].tolist()
    b.append(f"En duyarlı kalem **{biggest['kalem']}** ({biggest['değişim']}: "
             f"{_signed(biggest['alt_Wh_km'])} / {_signed(biggest['ust_Wh_km'])} Wh/km).")
    b.append("Tek başına kalan farkı karşılayabilen kalemler: "
             + (", ".join(covered) if covered else "hiçbiri") + ".")
    out.append({"no": 4, "soru": Q3A[4], "bulgular": b, "tablo": df.round(2)})
    return out


# ---------------------------------------------------------------------------
# 3B
# ---------------------------------------------------------------------------
def _scn(df: pd.DataFrame, name: str, col: str) -> float:
    c = b3.SCENARIO_COLS
    return float(df.loc[df[c["scenario"]] == name, c[col]].iloc[0])


def questions_3b(base: VehicleParams, cycles: dict, phases_wltc) -> list:
    """base: senaryolarin turetildigi parametre seti (Temel Arac ya da kullanicinin degistirdigi)."""
    out = []
    tw, vw = cycles[WLTP_CYCLE]
    th, vh = cycles[HWFET]
    sw = b3.scenario_table(tw, vw, base)
    sh = b3.scenario_table(th, vh, base)

    # Soru 1
    d1 = _scn(sw, MASS_SCN, "cons_change")
    no_reg = base.with_(eta_reg=0.0)
    s0 = b3.scenario_table(tw, vw, no_reg)
    d1_noreg = _scn(s0, MASS_SCN, "cons_change")
    b = [f"S1 ({b3.SCENARIOS[MASS_SCN][0]}): WLTC 3b tüketimi **{_pcts(d1)}** "
         f"({_f(_scn(sw, 'Baseline', 'cons'))} → {_f(_scn(sw, MASS_SCN, 'cons'))} Wh/km).",
         f"Rejenerasyon kapatılırsa (η_reg = 0) aynı kütle artışı {_pcts(d1_noreg)} olurdu → "
         f"rejenerasyon etkiyi {_f(d1_noreg - d1)} puan yumuşatıyor. Rejenerasyon payı "
         f"%{_f(_scn(sw, 'Baseline', 'regen_share'))} → %{_f(_scn(sw, MASS_SCN, 'regen_share'))}."]
    out.append({"no": 1, "soru": Q3B[1], "bulgular": b, "tablo": None})

    # Soru 2
    d2 = _scn(sw, CD_SCN, "cons_change")
    b = [f"S2 ({b3.SCENARIOS[CD_SCN][0]}): WLTC 3b tüketimi **{_pcts(d2)}** "
         f"({_f(_scn(sw, 'Baseline', 'cons'))} → {_f(_scn(sw, CD_SCN, 'cons'))} Wh/km); HWFET'te "
         f"{_pcts(_scn(sh, CD_SCN, 'cons_change'))}."]
    out.append({"no": 2, "soru": Q3B[2], "bulgular": b, "tablo": None})

    # Soru 3
    rows = []
    for cyc, df in ((WLTP_CYCLE, sw), (HWFET, sh)):
        m, a = _scn(df, MASS_SCN, "cons_change"), _scn(df, CD_SCN, "cons_change")
        rows.append({"döngü": cyc, "S1 kütle [%]": m, "S2 C_d [%]": a,
                     "daha kritik": "kütle" if m > a else "aerodinamik"})
    t3 = pd.DataFrame(rows).set_index("döngü")
    w_, h_ = t3.loc[WLTP_CYCLE, "daha kritik"], t3.loc[HWFET, "daha kritik"]
    gap_w = abs(t3.loc[WLTP_CYCLE, "S1 kütle [%]"] - t3.loc[WLTP_CYCLE, "S2 C_d [%]"])
    gap_h = abs(t3.loc[HWFET, "S1 kütle [%]"] - t3.loc[HWFET, "S2 C_d [%]"])
    b = [f"WLTC 3b'de **{w_}** daha kritik (S1 {_pcts(t3.loc[WLTP_CYCLE, 'S1 kütle [%]'])}, "
         f"S2 {_pcts(t3.loc[WLTP_CYCLE, 'S2 C_d [%]'])}).",
         f"HWFET'te **{h_}** daha kritik (S1 {_pcts(t3.loc[HWFET, 'S1 kütle [%]'])}, "
         f"S2 {_pcts(t3.loc[HWFET, 'S2 C_d [%]'])}) → sonuç "
         + ("**değişiyor**." if w_ != h_ else
            f"aynı kalıyor, ama iki senaryo arasındaki fark {_f(gap_w)} puandan {_f(gap_h)} "
            f"puana {'iniyor (aerodinamik ağırlık kazanıyor)' if gap_h < gap_w else 'çıkıyor'}.")]
    out.append({"no": 3, "soru": Q3B[3], "bulgular": b, "tablo": t3.round(2)})

    # Soru 4
    r_gain = _scn(sw, BATT_SCN, "range_change")
    c_gain = _scn(sw, BATT_SCN, "cons_change")
    e_only = b3.scenario_params(BATT_SCN, base).with_(m_kg=base.m_kg)
    r_eonly = simulate(tw, vw, e_only).range_km
    r_base = _scn(sw, "Baseline", "range")
    r_s3 = _scn(sw, BATT_SCN, "range")
    b = [f"S3'te menzil **{_pcts(r_gain)}** arttı ({_f(r_base, 0)} → {_f(r_s3, 0)} km), "
         f"%{_f(SCENARIO_STEP_PCT, 0)} değil.",
         f"Ek kütle tüketimi {_pcts(c_gain, 2)} artırıyor: menzil oranı "
         f"{_f(1 + SCENARIO_STEP_PCT / 100, 2)} / {_f(1 + c_gain / 100, 4)} = "
         f"{_f((1 + SCENARIO_STEP_PCT / 100) / (1 + c_gain / 100), 4)}.",
         f"Kütle değişmeseydi menzil {_f(r_eonly, 1)} km olurdu; ek kütle {_f(r_eonly - r_s3, 1)} "
         f"km götürüyor: eklenen menzilin %{_f((r_eonly - r_s3) / (r_eonly - r_base) * 100, 0)} "
         f"kadarı ek kütleyi taşımaya gidiyor."]
    out.append({"no": 4, "soru": Q3B[4], "bulgular": b, "tablo": None})

    # Soru 5
    bc = b3.brake_table_columns()
    ph = b3.phase_comparison(tw, vw, phases_wltc, base=base)
    phases = ph[ph[bc["phase"]] != b3.WHOLE_CYCLE].set_index(bc["phase"])
    whole = ph[ph[bc["phase"]] == b3.WHOLE_CYCLE].iloc[0]
    limit_kw = b3.scenario_params(REG_SCN, base).p_reg_max_w / 1e3
    b = []
    if whole[bc["steps_b"]] > 0:
        top = phases[bc["cons_diff"]].idxmax()
        b.append(f"S4 ({_f(limit_kw, 0)} kW) WLTC'de {int(whole[bc['steps_b']])} adımda sınıra "
                 f"takılıyor; etki en çok **{top}** fazında (tüketim "
                 f"{_signed(phases.loc[top, bc['cons_diff']], 2)} Wh/km, "
                 f"{int(phases.loc[top, bc['steps_b']])} adım).")
    else:
        near = phases[bc["margin"]].idxmin()
        b.append(f"S4 ({_f(limit_kw, 0)} kW) WLTC 3b'de **hiçbir fazda etkili değil**: en büyük "
                 f"geri kazanım {_f(whole[bc['peak_a']])} kW < {_f(limit_kw, 0)} kW.")
        b.append(f"Sınıra en yakın faz **{near}** (pay {_f(phases.loc[near, bc['margin']])} kW); "
                 f"sınır biraz düşük olsaydı ilk bu faz etkilenirdi.")
    tab = phases[[bc["peak_a"], bc["margin"], bc["steps_b"], bc["cons_diff"]]].round(2)
    out.append({"no": 5, "soru": Q3B[5], "bulgular": b, "tablo": tab})
    return out
