"""
Web arayuzu (app.py) aciklama metinleri. Metinler YALNIZCA burada; app.py metin gommez.

Her ogede ayni dort baslik kullanilir (HEADINGS). Alanlar:
  baslik  : bilgi kutusunun ust satiri
  tur     : "grafik" | "tablo" | "bolum"  -> kutu etiketi (EXPANDER_LABELS)
  ne, neden, nasil, dikkat : markdown metni
  denklem : (istege bagli) LaTeX satirlari, st.latex ile gosterilir

Yer tutucular: {...} icindeki ifadeler app.py'de o anki simulasyon sonucuyla
doldurulur (PLACEHOLDERS listesi). Yeni yer tutucu eklerseniz app.py'de de
karsiligini tanimlamaniz gerekir.
"""

HEADINGS = [
    ("ne", "Ne gösteriyor"),
    ("neden", "Neden önemli (ödevde nereye karşılık geliyor)"),
    ("nasil", "Nasıl okunur"),
    ("dikkat", "Dikkat"),
]

EXPANDER_LABELS = {
    "grafik": "ℹ️ Bu grafik ne anlatıyor?",
    "tablo": "ℹ️ Bu tablo ne anlatıyor?",
    "bolum": "ℹ️ Bu bölüm ne anlatıyor?",
}

# app.py bu yer tutucularin her birini doldurur
PLACEHOLDERS = ["{WLTC tepe faz}", "{WLTC tepe kW}"]

TEXTS = {
    "dogrulama_rozeti": {
        "baslik": "Doğrulama rozeti",
        "tur": "bolum",
        "ne": "Ödev Bölüm 2'deki doğrulama testlerinin (T1, T1b, T2, T4) modelin o anki "
              "koduyla yeniden hesaplanmış sonuçları ve beklenen değerler.",
        "neden": "Ödev \"dört test geçilmeden analiz sonuçları değerlendirmeye alınmaz\" diyor. "
                 "Rozet yeşilse model denklemleri doğru kodlanmış demektir. Testler her zaman "
                 "Temel Araç ile yapılır; seçili araçtan bağımsızdır.",
        "nasil": "Her satırda beklenen, hesaplanan ve sapma %. Hepsi %{tol} içindeyse yeşil.",
        "dikkat": "T2'de model yamuk (trapez) integrasyonla {t2_trap} Wh, ödevdeki adım "
                  "toplamıyla (E_adım = P_bat·Δt/3600) {t2_rect} Wh veriyor; fark son örneğin "
                  "yarısıdır (P_bat(10 s)·Δt/2 = {t2_half} Wh). Uçlarında hızı sıfır olan "
                  "döngülerde iki yöntem aynı sonucu verir.",
    },
    "ozet_kartlari": {
        "baslik": "Özet kartları",
        "tur": "bolum",
        "ne": "Seçili döngü için tüketim (Wh/km), menzil (km), rejenerasyon payı (%), "
              "P_reg,max sınırına takılan adım sayısı ve motor zarfı dışına çıkılan adım sayısı.",
        "neden": "Ödev Bölüm 1'in istediği temel çıktılar.",
        "nasil": "Tüketim = Σ E_adım / mesafe. Menzil = E_nom·(SoC_0 − SoC_min)/100 / tüketim. "
                 "Rejenerasyon payı = geri kazanılan enerji / çekişte harcanan enerji.",
        "dikkat": "Menzil, döngünün sürekli tekrarlandığı varsayımıyla hesaplanır; batarya "
                  "gerilimi, sıcaklık ve SoC'ye bağlı verim değişimi modelde yoktur. Şu an "
                  "seçili döngülerde zarf dışı adım toplamı: {env_viol}. Sıfırdan büyükse araç "
                  "döngüyü gerçekte izleyemez ve sonuç iyimserdir.",
    },
    "dongu_tablosu": {
        "baslik": "Döngü tablosu",
        "tur": "tablo",
        "ne": "Seçili her döngü için mesafe, ortalama hız, tüketim, rejenerasyon payı, "
              "P_reg,max sınırına takılan adım, zarf dışı adım ve menzil.",
        "neden": "Ödev 3A'nın istediği tablonun birebir karşılığı.",
        "nasil": "Şu anki parametrelerle en yüksek tüketim {max_cons_cycle} ({max_cons} Wh/km), "
                 "en düşük {min_cons_cycle} ({min_cons} Wh/km); en yüksek rejenerasyon payı "
                 "{max_regen_cycle} (%{max_regen}). Ortalama hız arttıkça aerodinamik, dur-kalk "
                 "arttıkça ivmelenme ve geri kazanım öne çıkar.",
        "dikkat": "Mesafeler T4 kontrolüyle doğrulanmıştır (en büyük sapma %{t4_dev}).",
    },
    "hiz_zaman": {
        "baslik": "Hız–zaman",
        "tur": "grafik",
        "ne": "Her sürüş döngüsünün zaman–hız profili (Excel'den okunan ham veri, Δt = 1 s).",
        "neden": "Modelin tek girdisi bu profildir; tüm güç ve enerji sonuçları buradan "
                 "türetilir. Döngülerin karakterini (dur-kalk, sabit hız, sert ivmelenme) "
                 "tanımak 3A yorumlarının temelidir.",
        "nasil": "Eğimin dikliği ivmeyi, yataylık sabit hızı, sıfırdaki düz bölgeler rölantiyi "
                 "gösterir. NEDC'nin düz çizgili, yapay profili ile WLTC ve US06'nın gerçek "
                 "sürüşe benzeyen dalgalı profili karşılaştırılabilir. Eksenler ortaktır; döngü "
                 "süreleri doğrudan kıyaslanabilir.",
        "dikkat": "Döngüler laboratuvar test profilleridir; trafik, eğim, rüzgâr ve sürücü "
                  "davranışı içermez.",
    },
    "batarya_gucu": {
        "baslik": "Batarya gücü–zaman",
        "tur": "grafik",
        "ne": "Bataryadan çekilen (mavi, pozitif) ve bataryaya geri verilen (turuncu, negatif) "
              "güç; kesikli gri çizgi −P_reg,max sınırıdır.",
        "neden": "Ödev 3A grafiği: \"aynı eksen ölçeğinde yan yana, en az ilk 200 s\". 3A Soru 2 "
                 "(çekiş ve rejenerasyon tepeleri, P_reg,max sınırına ulaşılması) doğrudan bu "
                 "grafikten cevaplanır.",
        "nasil": "Mavi tepeler sert ivmelenmeleri, turuncu tepeler frenlemeleri gösterir. Turuncu "
                 "alan kesikli çizgiye değiyorsa rejenerasyon sınıra takılmış, fazlası sürtünmeli "
                 "frende ısıya dönüşmüştür. Bütün paneller aynı y ölçeğindedir; döngülerin güç "
                 "talebi doğrudan karşılaştırılabilir.",
        "dikkat": "P_bat yardımcı yükü (P_aux) içerir; araç dururken bile küçük bir pozitif değer "
                  "görünür. {v_min} km/h altındaki frenlemelerde rejenerasyon kesilir (P_trac = 0).",
        "denklem": [
            r"P_{trac} = \begin{cases} \dfrac{P_w}{\eta_t\,\eta_m} & P_w \ge 0 \\[6pt]"
            r" \max\left(P_w\,\eta_t\,\eta_{reg},\ -P_{reg,max}\right) & P_w < 0 \end{cases}",
            r"P_{bat} = P_{trac} + P_{aux}",
        ],
    },
    "soc_zaman": {
        "baslik": "SoC–zaman",
        "tur": "grafik",
        "ne": "Her döngü boyunca batarya şarj durumunun (SoC) değişimi.",
        "neden": "Ödev Bölüm 1'in istediği SoC(t) çıktısı.",
        "nasil": "Eğim ne kadar dikse enerji o kadar hızlı tükeniyor. Yükselen kısa bölümler "
                 "rejenerasyonla geri kazanımı gösterir. Döngü sonundaki düşüş toplam net enerji "
                 "tüketimidir.",
        "dikkat": "Tek döngüdeki SoC düşüşü küçüktür (şu an {soc_drop_min}–{soc_drop_max} puan); "
                  "menzil bu düşüşün döngü tekrarlanarak SoC_min'e ulaşana kadar uzatılmasıyla "
                  "hesaplanır.",
        "denklem": [
            r"SoC(t) = SoC(t-1) - \frac{E_{\text{adım}}}{E_{nom}\cdot 1000}\cdot 100",
        ],
    },
    "enerji_dagilimi": {
        "baslik": "Enerji dağılımı",
        "tur": "grafik",
        "ne": "Bataryadan çekilen enerjinin nereye gittiği. Sıfırın üstü: çekiş sırasında "
              "tekerlekteki direnç bileşenleri (aerodinamik, yuvarlanma, ivmelenme), çekiş tarafı "
              "güç aktarım kayıpları (redüktör + motor/invertör) ve yardımcı yük. Sıfırın altı: "
              "rejenerasyonla bataryaya geri dönen enerji. Elmas işareti net batarya enerjisini "
              "(E_bat) gösterir: üst yığın − geri kazanılan.",
        "neden": "Ödev 3A Soru 1 (aerodinamik, yuvarlanma ve ivmelenme enerjisi payları) ve "
                 "rejenerasyonun rolü.",
        "nasil": "Şu an aerodinamik payı en büyük döngü {max_aero_cycle} (%{max_aero_pct}), "
                 "ivmelenme payı en büyük döngü {max_acc_cycle} (%{max_acc_pct}). İvmelenme "
                 "enerjisinin bir kısmı frenlemede geri kazanılır; net maliyet, ivmelenme dilimi "
                 "ile negatif çubuk arasındaki farktır.",
        "dikkat": "Frenleme kayıpları (rejenerasyon kaybı, frenlemede redüktör kaybı, sürtünmeli "
                  "fren, frenleme anındaki aerodinamik ve yuvarlanma direnci) ayrı dilim değildir; "
                  "çekişte verilen ivmelenme enerjisinin geri kazanılamayan kısmıdır ve İvmelenme "
                  "diliminin üzerine gelince ayrıntılı görünür. Ayrı gösterilseydi aynı enerji iki "
                  "kez sayılırdı.",
    },
    "enerji_akisi": {
        "baslik": "Enerji akış (Sankey) diyagramı",
        "tur": "grafik",
        "ne": "Seçilen döngüde bataryadan brüt çekilen enerjinin yolculuğu: yardımcı yük, motor/"
              "invertör ve redüktör kayıpları, tekerlekte aerodinamik ve yuvarlanma direnci ile "
              "araca kinetik enerji olarak verilen ivmelenme enerjisi; kinetik enerjinin "
              "frenlemede sürtünmeli frene, rejenerasyon kayıplarına ve bataryaya geri dönen "
              "kısma ayrılması.",
        "neden": "3A Soru 1'deki aerodinamik / yuvarlanma / ivmelenme paylarını ve "
                 "rejenerasyonun rolünü tek resimde gösterir: ivmelenme enerjisinin büyük kısmı "
                 "kaybolmaz, bataryaya geri döner. Dur-kalklı döngülerde bu geri dönüş, net "
                 "tüketimi brüt çekilenden belirgin biçimde düşürür.",
        "nasil": "Okların kalınlığı taşıdıkları enerjiyle orantılıdır (birim, sekmedeki "
                 "Birim seçimine göre Wh/km veya Wh). Soldan sağa: Batarya → Motor/invertör → Redüktör → "
                 "Tekerlek → direnç bileşenleri ve kinetik enerji. Net E_bat = brüt çekilen − "
                 "bataryaya geri dönen; değerler başlıkta yazılıdır. Gri düğümler kayıptır.",
        "dikkat": "Seçilen yaklaşım: frenleme anındaki aerodinamik ve yuvarlanma direnci aracı "
                  "zaten yavaşlattığı için kinetik enerjiden karşılanır ve \"Kinetik enerji\" "
                  "düğümünün çıkışlarına dahil edilmiştir (Kinetik enerji → Aerodinamik / "
                  "Yuvarlanma okları). Bu nedenle Aerodinamik ve Yuvarlanma düğümleri iki girişlidir "
                  "ve toplamları tüm döngüdeki direnç enerjisine eşittir; çubuk grafikteki "
                  "\"(çekiş)\" dilimleri ise yalnızca tekerlekten gelen kısımdır. Aktarma kaybı "
                  "düğümü de çekiş ve frenleme katkılarını birlikte toplar. Döngü durarak başlayıp "
                  "bittiği için kinetik enerjinin net değişimi ~0'dır ve gösterilmez. Tüm düğüm "
                  "dengeleri kodda assert ile denetlenir.",
    },
    "motor_noktalari": {
        "baslik": "Motor çalışma noktaları",
        "tur": "grafik",
        "ne": "Her çekiş adımında motorun çalıştığı devir (n_m) ve tork (T_m) noktaları ile "
              "motorun tepe tork–hız zarfı.",
        "neden": "Ödev Bölüm 1, 3.7 kontrolü: \"T_m > T_max olan adımları sayın ve raporlayın.\"",
        "nasil": "Zarf iki bölgelidir: temel hıza ({n_base} d/dk) kadar tork sabit (tepe tork), "
                 "sonrasında güç sabit (T = P/ω). Şu an çekiş noktalarının %{env_low_share}'i "
                 "zarfın yarısının altında; zarf dışı adım {env_viol}. Kırmızı noktalar zarf "
                 "dışıdır.",
        "dikkat": "Zarf, tepe değerlerle (kısa süreli) çizilmiştir; sürekli güç sınırı (30 dk "
                  "{p_cont} kW) ve sıcaklık sınırlaması modelde yoktur. Temel Araç'ın motor "
                  "verisi tanımlı olmadığından bu grafik yalnızca gerçek araç için çizilir.",
        "denklem": [
            r"T_m = \frac{T_w}{G\,\eta_t}, \qquad n_m = \frac{v}{r_w}\cdot\frac{60}{2\pi}\cdot G",
            r"T_{max} = \min\left(T_{peak},\ \frac{P_{peak}}{\omega_m}\right)",
        ],
    },
    "senaryo_karsilastirma": {
        "baslik": "Senaryo karşılaştırma",
        "tur": "tablo",
        "ne": "Temel Araç'ta her seferinde tek bir parametrenin değiştirildiği 3B senaryoları: "
              "S1 kütle +%20, S2 C_d +%20, S3 batarya +%20 (ve +100 kg), S4 P_reg,max yarıya.",
        "neden": "Ödev 3B tablosu ve yorum soruları 1–5.",
        "nasil": "Seçili döngüde ({sc_cycle}) şu an: S1 kütle → tüketim {sc_s1}, S2 C_d → "
                 "{sc_s2}, S3 batarya → menzil {sc_s3r} (tüketim {sc_s3c}), S4 → {sc_s4}. "
                 "Kütle yuvarlanma ve ivmelenme direncini, C_d yalnızca aerodinamik direnci "
                 "büyütür.",
        "dikkat": "Senaryo sonuçları Temel Araç içindir; gerçek araca genellenirken parametre "
                  "değerleri farklıdır.",
    },
    "faz_tablosu": {
        "baslik": "Faz bazında frenleme tablosu",
        "tur": "tablo",
        "ne": "Baseline ve S4 için her WLTC fazında (Low, Medium, High, Extra High) tepe "
              "rejenerasyon gücü, sınıra takılan adım, geri kazanılan ve sürtünmeli frene giden "
              "enerji. HWFET ve US06'da faz yoktur, tek satır döngü genelidir.",
        "neden": "Ödev 3B Soru 5: \"S4'te rejenerasyon sınırının etkisi hangi fazda en belirgin?\"",
        "nasil": "\"Eşik payı\" = S4 sınırı − o fazdaki tepe rejenerasyon gücü. Pay pozitifse "
                 "sınır o fazda hiç devreye girmez ve fark sütunları sıfırdır. WLTC'de en yüksek "
                 "tepe {WLTC tepe faz} fazında {WLTC tepe kW} kW'tır.",
        "dikkat": "Kaybedilen rejenerasyon enerjisi, frene giden ek tekerlek enerjisinin "
                  "η_t·η_reg katıdır; bu oran tutarlılık kontrolü olarak kullanılabilir.",
    },
    "parametre_turetme": {
        "baslik": "Parametre türetme (Tesla): CoC yol yükü → f_r, C_d·A_f",
        "tur": "bolum",
        "ne": "CoC'deki üç terimli yol yükü eğrisinin, modelin iki terimli direnç yapısına üç "
              "farklı yöntemle dönüştürülmesi.",
        "neden": "Tesla'nın f_r ve C_d·A_f değerleri buradan gelir; parametre kaynakları kriteri "
                 "(10 puan) ve 3A'nın tüm sonuçları bu seçime bağlıdır.",
        "nasil": "Tablodaki döngü hatalarına göre: a) {road_a}; b) {road_b}; c) {road_c}. "
                 "b) f1'i v² terimine yedirdiği için C_d·A_f fiziksel değil eşdeğerdir "
                 "(C_d = {cd_info} ile A_f = {af_eq} m²).",
        "dikkat": "f1 terimi lastik kayıplarının hızla artan kısmını ve aktarma organı "
                  "sürüklenmesini temsil eder; modelde karşılığı olmadığı için hangi yöntem "
                  "seçilirse seçilsin raporda sınırlılık olarak belirtilmelidir.",
        "denklem": [
            r"F_{CoC}(v) = f_0 + f_1\,v + f_2\,v^2 \;\approx\; A + B\,v^2 \qquad (v\ \text{km/h})",
            r"f_r = \frac{A}{m\,g}, \qquad C_d A_f = \frac{2\,B\cdot 3.6^2}{\rho}",
        ],
    },
    "verim_haritasi": {
        "baslik": "Motor + invertör verim haritası ([R24] Şekil 5a) ve WLTC çalışma noktaları",
        "tur": "grafik",
        "ne": "Tesla Model 3 motor + invertör veriminin devir–tork düzlemindeki dağılımı (renk) ve "
              "seçili parametrelerle WLTC 3b'deki motor çalışma noktaları: çekiş (koyu) ve geri "
              "kazanım (turuncu, |T_m|). Beyaz çarpılar haritadan okunan noktalardır.",
        "neden": "Modeldeki sabit η_m ve η_reg bu haritadan WLTC enerji ağırlıklı ortalama olarak "
                 "türetildi (Aşama 2, parametre kaynakları kriteri). Ödev bonusundaki \"motor "
                 "haritası\" adımının da temelidir.",
        "nasil": "Noktaların yoğunlaştığı bölgenin rengi, eşdeğer verimi belirler. Şu anki "
                 "parametrelerle haritadan WLTC eşdeğer verimi η_m = {eta_m_eq}, η_reg = "
                 "{eta_reg_eq} (modelde kullanılan: η_m = {eta_m_par}, η_reg = {eta_reg_par}).",
        "dikkat": "Harita, şekildeki eş-verim eğrilerinden elle okunmuş seyrek noktalardan "
                  "doğrusal enterpolasyonla üretilmiştir (±0,01). [R24] 15 Nm altını ölçmemiştir; "
                  "bu bölgedeki noktalar 20 Nm satırının verimiyle temsil edilir ve sonuç "
                  "iyimser olabilir (WLTC'de çekiş enerjisinin %{low_t_share}'i bu bölgede). "
                  "Geri kazanımda haritanın simetrik olduğu varsayılmıştır.",
        "denklem": [
            r"\eta_{m,es} = \frac{\sum P_m}{\sum P_m / \eta(n_m, T_m)}, \qquad "
            r"P_m = \frac{P_w}{\eta_t}\quad (P_w > 0)",
            r"\eta_{reg,es} = \frac{\sum P_{m,reg}\,\eta(n_m, |T_m|)}{\sum P_{m,reg}}, \qquad "
            r"P_{m,reg} = |P_w|\,\eta_t\quad (P_w < 0,\ v \ge v_{min})",
        ],
    },
    "wltp_karsilastirma": {
        "baslik": "WLTP karşılaştırma",
        "tur": "tablo",
        "ne": "Modelin WLTC 3b tüketimi (batarya tarafı ve şarj verimiyle şebeke tarafına "
              "çevrilmiş hali) ile resmi WLTP tüketimi.",
        "neden": "Ödev 3A: \"Resmi WLTP tüketimi ile model sonucunun karşılaştırması "
                 "(şebeke/batarya tarafı farkı açıkça ele alınarak)\" ve Soru 4 (farkın kalem "
                 "kalem açıklanması).",
        "nasil": "AB'deki resmi WLTP tüketimi prizden ölçülür ve şarj kayıplarını içerir; model "
                 "ise bataryadan çekilen enerjiyi hesaplar. Karşılaştırma için: "
                 "e_şebeke = e_batarya / η_şarj. Duyarlılık satırları, her kalemin farkı ne kadar "
                 "değiştirdiğini gösterir.",
        "dikkat": "Şarj verimi ve diğer duyarlılık adımları varsayımdır; raporda kaynak "
                  "gösterilmelidir. Resmi WLTP testi ayrıca sıcaklık (23 °C), test kütlesi ve "
                  "lastik koşullarını tanımlar; bunlar modeldeki değerlerle aynı olmayabilir.",
    },
}

# Gezinme menusu: grup -> [(sayfa anahtari, buton etiketi)]; anahtarlar app.py'de kullanilir
NAV = {
    "✅ Doğrulama": [("chk", "✅ Kendi modelini test et")],
    "🚗 Sürüş": [("sim", "🎬 Sürüş simülatörü"), ("hiz", "📈 Hız–zaman"),
                 ("guc", "⚡ Batarya gücü–zaman"), ("soc", "🔋 SoC–zaman")],
    "📊 Analiz (3A · 3B)": [("yorum", "❓ Yorum soruları"), ("dongu", "📋 Döngü tablosu"),
                           ("enerji", "🧮 Enerji dağılımı"),
                           ("wltp", "🏷️ WLTP karşılaştırma"), ("senaryo", "🧪 Senaryolar (3B)"),
                           ("cmp", "🆚 Parametre etkisi")],
    "⚙️ Motor ve parametreler": [("c3", "⚙️ 3C · Motor haritası ve G"),
                                 ("motor", "🎯 Motor çalışma noktaları"),
                                 ("verim", "🗺️ Verim haritası"),
                                 ("turetme", "🔧 Parametre türetme (Tesla)")],
}
NAV_DEFAULT = "chk"

# Arayuzdeki kisa mesajlar (uyari, bilgi, alt yazi). {ad} alanlari app.py'de
# str.format ile doldurulur; alan adlarini degistirmeyin.
UI = {
    "tesla_missing": "**params.py'de eksik (None) parametreler:**  \n{fields}",
    "tesla_placeholder": "Bu değerler kaynaksız **GEÇİCİ VARSAYIMDIR**, rapora girmez.",
    "param_changed": ":orange[▲ değişti · varsayılan {default}]",
    "param_assumed": ":red[**VARSAYIM** – ödev Temel Araç değeri (docs/kaynaklar.md)]",
    "param_assumed_lit": ":orange[**VARSAYIM (literatür destekli)** – [L23] tek kademeli "
                         "redüktör tipik verimi ~0,97; araca özgü ölçüm değil]",
    "eta_map_vehicle_only": "Verim haritası gerçek araca ([R24] Şekil 5a, Tesla Model 3) "
                            "aittir. Kenar çubuğundan Tesla'yı seçin.",
    "eta_map_caption": "Harita noktaları elle okunmuştur (±0,01). Boş bölge: tepe tork zarfının "
                       "üstü (motor oraya çıkamaz, çizilmedi). 20 Nm altındaki noktalar haritada 20 Nm satırının "
                       "verimiyle temsil edilir; bu bölgede çekiş enerjisinin payı: {low:.1f} % "
                       "({cycle}).",
    "no_cycle": "En az bir sürüş döngüsü seçin.",
    "validation_ok": "**Model doğrulandı** · T1, T1b, T2, T4 beklenen değerlerin %{tol} içinde "
                     "(Temel Araç)",
    "validation_fail": "**Doğrulama başarısız** · en az bir test %{tol} toleransın dışında",
    "t4_summary": "5 döngü, en büyük |sapma| **{dev:.4f} %**",
    "tesla_results": "Tesla sonuçları **geçici varsayımlar** içerir (kenar çubuğundaki kırmızı "
                     "kutu). Bu sayılar rapora girmez.",
    "changed_params": "**Varsayılandan farklı parametreler:** ",
    "envelope_missing": "Bu araçta motor zarfı parametreleri tanımlı değil",
    "envelope_missing_table": "Zarf dışı adım: bu araçta motor zarfı tanımlı değil, 0 gösterilir.",
    "energy_pct_title": "**Enerji akışı tablosu** (grafikle aynı kaynak; yüzdeler bataryadan "
                        "brüt çekilen enerjiye göre)",
    "energy_chart_caption": "Pozitif yığın = bataryadan brüt çekilen enerji (çekiş adımlarında "
                            "tekerleğe verilen + çekiş tarafı kayıplar + yardımcı yük); sıfırın "
                            "altı = rejenerasyonla bataryaya geri dönen; elmas = net E_bat. "
                            "Frenleme kayıpları (rejenerasyon kaybı, sürtünmeli fren, frenlemede "
                            "aktarma kaybı) ivmelenme enerjisinin geri kazanılamayan kısmıdır; ayrı "
                            "dilim olarak eklenirse iki kez sayılır. Ayrıntı: İvmelenme dilimi "
                            "üzerine gelin veya aşağıdaki enerji akışı diyagramına bakın.",
    "sankey_title": "Enerji akışı (Sankey) – tek döngü",
    "motor_caption": "Yalnızca çekiş adımları (P_w ≥ 0). Zarf dışı: T_m > T_max(n_m).",
    "motor_missing": "Bu araçta motor zarfı parametreleri (T_peak, P_peak) tanımlı değil; "
                     "çalışma noktası / zarf kontrolü yalnızca Tesla için yapılır.",
    "scenario_caption": "Senaryolar {base} parametrelerinden .with_(...) ile türetilir (ödev "
                        "3B). Temel Araç seçiliyken kenar çubuğunda değiştirdiğiniz değerler "
                        "taban olur; gerçek araç seçiliyken ödevdeki Temel Araç kullanılır.",
    "brake_title": "Frenleme enerjisi · {cycle}, {a} - {b} (3B Soru 5)",
    "no_phases": "Bu döngüde faz etiketi yok; yalnızca tüm döngü satırı gösterilir.",
    "margin_caption": "Eşik payı = P_reg,max({b}) − {a} tepe rejenerasyon gücü. Pozitifse "
                      "{b} sınırı o fazda hiç devreye girmez; negatifse girer.",
    "s4_no_effect": "{cycle}: {a} tepe rejenerasyon gücü {peak:.1f} kW < {limit:.0f} kW "
                    "({b} sınırı) → {b} etkisiz (pay {margin:.1f} kW).",
    "s4_effect": "{cycle}: {b}'te {steps} adım sınıra takılıyor; {regen:.1f} Wh daha az geri "
                 "kazanım, sürtünmeli frene {friction:.1f} Wh ek enerji, tüketim "
                 "{cons:+.2f} Wh/km.",
    "wltp_base_only": "Resmi WLTP değeri yalnızca gerçek araç (Tesla) için var. "
                      "Kenar çubuğundan Tesla'yı seçin.",
    "wltp_tesla_assumed": "Tesla parametrelerinin bir kısmı geçici varsayım; bu tablo rapora "
                          "girmez.",
    "wltp_source": "Kaynak: [EEA] CO2 izleme veri tabanı, Va = E6CR, alan Z (şebeke tarafı); "
                   "[EVDB] ile doğrulandı",
    "eta_charge_source": ":orange[**Bağımsız test (benzer araç: Model Y)** – [ADAC26] Model Y "
                         "ölçümü (aynı platform); Model 3 için ölçüm yok.] 11 kW wallbox, kayıp "
                         "%{loss} → η = {eta}; beş aracın aralığı η {lo}–{hi}.",
    "chain_title": "**Karşılaştırma zinciri** (batarya uç tarafı → batarya iç kayıpları → "
                   "şarj verimi → şebeke tarafı)",
    "band_title": "**η_şarj belirsizlik bandı** ([ADAC26] aralığı)",
    "range_caption": "Menzil iki tanımla: SoC_0→SoC_min (ödev 3.6) ve tam batarya E_nom/e "
                     "(SoC 100→0, resmi menzil tanımına yakın). Referanslar yalnızca Tesla ve "
                     "WLTC satırında: CoC WLTP menzili ve [R24] dinamometre menzili.",
    "q1_title": "**Soru 1: çekiş adımlarında tekerlek enerjisi payları, geri kazanım ve "
                "sürtünmeli fren**",
    "q1_caption": "Paylar aero + yuvarlanma + ivmelenme toplamına göre (yalnızca çekiş "
                  "adımları). Geri kazanılan: batarya tarafı; sürtünmeli fren: tekerlek tarafı. "
                  "İvme enerjisinin geri kazanılan payı = geri kazanılan / çekişteki ivmelenme "
                  "enerjisi.",
    "q2_title": "**Soru 2: tepe çekiş ve rejenerasyon güçleri**",
    "q2_phase_title": "**Soru 2: faz bazında tepe rejenerasyon gücü** (WLTC 3b, NEDC)",
    "q2_caption": "Tepe rejenerasyon gücü batarya tarafında (−P_trac); sınıra pay = "
                  "P_reg,max − tepe rejenerasyon gücü.",
    "sens_note_label": "Açıklama (rapor notu): {param}",
    "road_inputs": "Girdiler: f0 = {f0} N, f1 = {f1} N/(km/h), f2 = {f2} N/(km/h)² [R24 Tablo A1] · "
                   "m = {m:.0f} kg ([EEA] WLTP test kütlesi Mt) · ρ = {rho} kg/m³, "
                   "g = {g} m/s² (BASE_VEHICLE)",
    "road_cd_todo": ":gray[A_f sütunu C_d = {cd} ile hesaplandı: **yalnızca bilgi** – model "
                    "yalnızca C_d·A_f kullanır; raporda C_d·A_f (eşdeğer {cda_eq} m², fiziksel "
                    "{cda_phys} m²) raporlanır.] f_r ve C_d·A_f bu değerden etkilenmez.",
    "road_mass_note": "Türetilen f_r ve C_d·A_f yalnızca yukarıdaki m ve ρ ile birlikte "
                      "anlamlıdır; modelde de aynı değerler kullanılmalıdır.",
    "road_err_caption": "Hata % = (Σ(A + B·v²)·v / Σ F_CoC(v)·v − 1)·100, yalnızca v > 0 "
                        "adımları. Seçilen: **b) EKK** (params.py'de; c) duyarlılık, a) f1'i "
                        "yok saymanın etkisi örneği).",
    "nav_title": "Bölümler",
    # --- yorum sorulari (odev 3A, 3B) ---
    "q_intro": "Ödevdeki yorum soruları aşağıda **aynen** yer alıyor. Altlarındaki bulgular sabit "
               "bir cevap değildir: o an seçili araç, döngüler ve parametrelerle **yeniden "
               "hesaplanır**. Kenar çubuğunda bir değeri değiştirin; bulgular da değişir.",
    "q_live_label": "📡 **Canlı bulgular** (şu anki parametrelerle hesaplandı)",
    "q_table_label": "Bulguların dayandığı tablo",
    "q3a_title": "3A · Sürüş döngüsü analizi",
    "q3a_caption": "Araç: {vehicle} · döngüler: {cycles}",
    "q3b_title": "3B · Parametre duyarlılığı",
    "q3b_caption": "Senaryolar {base} parametrelerinden türetilir (her senaryoda tek parametre "
                   "değişir); WLTC 3b, karşılaştırma için HWFET.",
    # --- 20 Kasim kontrol belgesi ---
    "chk_intro": "Dersin **\"MKTS5081 · 20 Kasım — Kendi Modelini Kontrol Et\"** belgesindeki her "
                 "satır, **Temel Araç + WLTC 3b** için modelle otomatik karşılaştırılır. Kabul "
                 "ölçütü belgedeki gibidir: |model / referans − 1| ≤ %1 (T3 artığı ≤ %0,1). Bu "
                 "sekme kenar çubuğundaki ayarlardan etkilenmez.",
    "chk_ok": "**Model kabul edildi** · belgedeki {n} kontrol satırının hepsi tutuyor "
              "(T4 → T1/T1b → T2 → WLTC 3b → faz sonu → 6 kontrol saniyesi → T3 → sert fren).",
    "chk_fail": "**{bad} / {n} satır tutmuyor** – teşhis sırasını belgedeki gibi ilk tutmayan "
                "satırdan başlatın.",
    "chk_sections": {"kontrol_tablosu": "Kontrol tablosu (T4, T1, T1b, T2, WLTC 3b)",
                     "faz_sonu": "Faz sonu kümülatifleri",
                     "kontrol_saniyeleri": "Altı kontrol saniyesi (karar bloğunun her dalı)",
                     "t3_kalemleri": "T3 enerji dengesi kalemleri",
                     "sert_fren": "Sert fren testi (100 → 0 km/h, 4 s)",
                     "ogrenci_kontrol": "ogrenci_kontrol.py çıktısı (belgedeki betik)"},
    "chk_caption": "Sayısal ayarlar: ivme merkezi fark (np.gradient), Δt = 1 s, toplama sağ uç "
                   "(T2 için yamuk 63,1 Wh ve sağ uç 69,5 Wh ikisi de verilir); ρ_reg P_tr ile "
                   "(ödev §3.5), P_bat ile değeri bilgi amaçlı. Kod: analysis/kontrol_20kasim.py · "
                   "test: tests/test_kontrol_20kasim.py.",
    "up_title": "📤 Kendi modelinizin çıktısını yükleyin",
    "up_intro": "Kendi kodunuzu **Temel Araç** parametreleriyle çalıştırın ve saniyelik batarya "
                "gücünü CSV ya da Excel olarak kaydedin. İki sütun yeterli: **t_s** (zaman, s) ve "
                "**p_bat_kw** (kW; W ise sütunu **p_bat_w** adlandırın). Dosya bu modelin aynı "
                "döngüdeki sonucuyla karşılaştırılır; kabul ölçütü %1'dir. Biçim için örnek "
                "dosyayı indirebilirsiniz. Yüklenen dosya hiçbir yere kaydedilmez.",
    "up_steps": (
        "**Nasıl kullanılır? (4 adım)**\n\n"
        "1. Kendi modelinizi **Temel Araç** parametreleriyle çalıştırın (m = 1800 kg, "
        "C_d = 0,28, A_f = 2,4 m², f_r = 0,011, η_t = 0,95, η_m = 0,92, η_reg = 0,80, "
        "P_reg,max = 60 kW, P_aux = 400 W …). Kendi gerçek aracınızın parametreleriyle "
        "karşılaştırma anlamlı olmaz.\n"
        "2. Saniyelik batarya gücünü **iki sütunlu** bir dosyaya kaydedin:\n"
        "    - `t_s`: zaman [s] → 0, 1, 2, …\n"
        "    - `p_bat_kw`: batarya gücü [kW] → **çekişte artı, rejenerasyonda eksi** "
        "(W ise sütun adı `p_bat_w`)\n"
        "3. Aşağıdan dosyanızdaki **döngünün aynısını** seçin (ör. WLTC_3b) ve dosyayı yükleyin.\n"
        "4. Sonuç tablosuna bakın: toplam enerji, tüketim, en büyük çekiş ve en büyük geri "
        "kazanım %1 içindeyse **tutuyor** yazar. Tutmuyorsa alttaki grafikte farkın hangi "
        "saniyede başladığına bakın; o saniyedeki hız ve ivmeyi kendi kodunuzda kontrol edin."
    ),
    "up_howto_title": "📄 Dosyayı nasıl hazırlarım? (Python · MATLAB · Excel örnekleri)",
    "up_howto": (
        "**Python** (kodunuzun sonuna ekleyin; `t` saniye, `P_bat` watt cinsinden diziler):\n"
        "```python\n"
        "import pandas as pd\n"
        "pd.DataFrame({\"t_s\": t, \"p_bat_kw\": P_bat / 1000}).to_csv(\"benim_modelim.csv\", "
        "index=False)\n"
        "```\n"
        "**MATLAB:**\n"
        "```matlab\n"
        "T = table(t(:), P_bat(:)/1000, 'VariableNames', {'t_s','p_bat_kw'});\n"
        "writetable(T, 'benim_modelim.csv');\n"
        "```\n"
        "**Excel:** A1 hücresine `t_s`, B1 hücresine `p_bat_kw` yazın, değerleri altlarına "
        "yapıştırın ve `.xlsx` olarak kaydedin. Ondalık virgül ve `;` ayırıcı sorun değildir.\n\n"
        "**Sık yapılan hatalar**\n"
        "- Uygulamada seçilen döngü dosyadaki döngüden farklı → her şey *tutmuyor* çıkar.\n"
        "- Rejenerasyon artı işaretle yazılmış → *en büyük geri kazanım* satırı tutmaz.\n"
        "- Güç W olduğu hâlde sütun adı `p_bat_kw` → değerler 1000 kat büyük çıkar.\n"
        "- Zaman 1'den başlıyor ya da adım 1 s değil → karşılaştırılan nokta sayısı eksik kalır.\n\n"
        "Emin değilseniz önce **⬇ Örnek dosya**'yı indirip açın; biçim tam olarak budur. "
        "Örnek dosyayı olduğu gibi geri yüklerseniz dört satırın hepsi *tutuyor* çıkar."
    ),
    "up_cycle_mismatch": "Dosyanızın süresi ({t_up:.0f} s) seçili döngünün süresiyle ({t_cyc:.0f} s) "
                         "uyuşmuyor. Döngü seçimini kontrol edin; dosyanız başka bir döngüye ait "
                         "olabilir.",
    "up_example": "⬇ Örnek dosya (CSV)",
    "up_label": "CSV veya XLSX dosyası",
    "up_error": "Dosya okunamadı: {err}",
    "up_result": "**{n} büyüklüğün {bad} tanesi %1 dışında.** Karşılaştırılan nokta: {pts} / "
                 "{tot} s. Saniyelik en büyük fark {dmax:.2f} kW (t = {tmax:.0f} s); farkın "
                 "nereden başladığını aşağıdaki grafikte görebilirsiniz.",
    # --- baslik bandi ve yeni sekmeler ---
    "hero_title": "Elektrikli Araç Modeli · geriye dönük enerji ve menzil hesabı",
    "hero_sub": "Saniye saniye güç, enerji ve SoC · ödev Bölüm 1 denklemleri · T1–T4 doğrulamalı",
    "kpi_delta_note": "Kartlardaki küçük oklar, kenar çubuğunda değiştirdiğiniz parametrelerin "
                      "varsayılana göre etkisidir.",
    "sim_intro": "Döngüyü saniye saniye oynatın: **▶ Oynat** ile başlatın, kaydırıcıyla istediğiniz "
                 "ana atlayın. Sağdaki göstergeler o anki hızı, batarya gücünü (turuncu bölge = "
                 "rejenerasyon) ve SoC'yi gösterir. Kenar çubuğundaki parametreler buraya da uygulanır.",
    "sim_step_help": "Her karede kaç saniye ilerlenir. Küçük adım daha akıcı ama daha yavaş yüklenir.",
    "sim_speed_help": "Animasyonun hızı. 0,5× yarı hız, 0,25× çeyrek hızdır. Kare adımı 5 s iken "
                      "1× hızda döngünün 1800 saniyesi yaklaşık 15 saniyede, 0,5× hızda yaklaşık "
                      "30 saniyede oynar.",
    "cmp_none": "Henüz parametre değiştirmediniz. Kenar çubuğunda **Parametre ayarları**ndan bir "
                "değeri (örn. kütle, C_d, P_aux) değiştirin; etkisi burada döngü döngü görünür.",
    "cmp_intro": "Seçili araç **varsayılan** parametreleriyle ve **sizin değiştirdiğiniz** "
                 "parametrelerle aynı döngülerde çalıştırıldı.",
    "c3_vehicle_only": "Verim haritası gerçek araca ([R24] Şekil 5a, Tesla Model 3) aittir. "
                       "Kenar çubuğundan Tesla'yı seçin.",
    "c3_intro": "Sabit verimli modelde tüketim G'den **bağımsızdır** (P_w G'ye bağlı değil). G "
                "yalnızca motor çalışma noktasını kaydırır; etkisi ancak verim haritasıyla görünür. "
                "20 Nm altı ölçülmediğinden iki sınır çizilir: **iyimser** (verim sabit) ve "
                "**kötümser** (kayıp sabit); gerçek değer aradadır. Gri bölge: 16 000 rpm'de "
                "azami hız {v_top:.0f} km/h'nin altına düşer ([EVDB]).",
    "c3_mode_labels": {"eta_sabit": "İyimser sınır (T<20 Nm'de η sabit)",
                       "kayip_sabit": "Kötümser sınır (T<20 Nm'de kayıp sabit)"},
    "c3_table_title": "**Sabit verim mi, harita mı?** (araç G'sinde, tüm döngüler) – sabit "
                      "verim varsayımının döngüye göre hatası",
    "c3_map_title": "Verim haritası + {cycle} çalışma noktaları (G = {g:.2f})",
    "sens_title": "Kalan fark için duyarlılık (WLTC 3b, şebeke tarafı)",
    "sens_note_placeholder": "Bu kalem farkı nasıl etkiliyor? Kaynak / gerekçe...",
    "sens_caption": "η_m, η_reg: döngüler arası min–max (p2_verimler); P_aux ±{aux} W; η_t "
                    "{eta_t}; v_min {vmin} km/h; batarya kayıp payı ±{batt} puan. Adımlar "
                    "analysis/a3_cycles.py içinde tanımlı (analiz tanımı, fiziksel değer değil). "
                    "Açıklamalar yalnızca bu oturumda tutulur.",
}

# ---------------------------------------------------------------------------
# Terimler sozlugu (kenar cubugu, "📖 Terimler sozlugu"); sira = gosterim sirasi
# ---------------------------------------------------------------------------
GLOSSARY_LABEL = "📖 Terimler sözlüğü"
GLOSSARY = {
    "WLTP": "Worldwide harmonised Light vehicles Test Procedure. AB'de 2017–2018'den beri zorunlu "
            "tip onayı test prosedürü: döngünün yanında sıcaklık (23 °C), test kütlesi, şarj ve "
            "ölçüm kurallarını tanımlar. Resmi tüketim prizden (şebeke tarafı) ölçülür, şarj "
            "kayıplarını içerir.",
    "WLTC 3b": "WLTP'nin test döngüsü (güç/kütle oranı 34 W/kg üstü araçlar için Class 3b). "
               "4 faz: Low, Medium, High, Extra High. 1800 s, 23,3 km, en yüksek hız 131 km/h.",
    "NEDC": "New European Driving Cycle. WLTP'den önceki Avrupa döngüsü: 4 × ECE-15 şehir + EUDC "
            "şehirlerarası. Sabit hız ve sabit ivmeli yapay profil; gerçek tüketimi olduğundan "
            "düşük gösterdiği için WLTP ile değiştirildi.",
    "UDDS": "Urban Dynamometer Driving Schedule. ABD EPA şehir içi döngüsü; sık dur-kalk, düşük "
            "ortalama hız.",
    "HWFET": "Highway Fuel Economy Test. ABD EPA şehirlerarası döngüsü; neredeyse durmasız, "
             "orta-yüksek sabit hızlar.",
    "US06": "ABD EPA'nın agresif sürüş döngüsü; sert ivmelenme ve frenleme, yüksek hızlar.",
    "CLTC-P": "China Light-duty Vehicle Test Cycle (Passenger). Çin döngüsü; standart ücretli "
              "olduğu için bu projede kullanılmadı.",
    "SoC": "State of Charge, bataryanın şarj durumu (%). Modelde SoC_0'dan başlar; menzil "
           "SoC_min'e kadar hesaplanır.",
    "EPA": "ABD Çevre Koruma Ajansı (Environmental Protection Agency); UDDS, HWFET ve US06 "
           "döngülerinin sahibi.",
    "CoC": "Certificate of Conformity (uygunluk belgesi). AB'de satılan aracın resmi teknik "
           "kimliği; kütle, güç ve WLTP yol yükü katsayıları (f0, f1, f2) burada yer alır.",
    "EEA": "European Environment Agency (AB Çevre Ajansı). Tip onayı verilerini yayımlar; "
           "Tesla'nın resmi WLTP tüketimi (142 Wh/km) ve test kütlesi (1905 kg) buradan alındı.",
    "Yol yükü katsayıları (f0, f1, f2)": "Coast-down testinden elde edilen toplam direnç eğrisi "
                                         "F = f0 + f1·v + f2·v². Yaklaşık olarak f0 yuvarlanma, "
                                         "f2 aerodinamik direnci temsil eder.",
    "Rejenerasyon": "Frenlemede motorun jeneratör olarak çalışıp enerjiyi bataryaya geri "
                    "vermesi; P_reg,max ile sınırlıdır ve v_min altında kesilir.",
    "Tork–hız zarfı": "Motorun her devirde verebileceği en yüksek tork: temel hıza kadar sabit "
                      "tork, sonrasında sabit güç.",
    "Geriye dönük model (backward-facing)": "Hız profili verilir, gereken kuvvet ve güç geriye "
                                            "doğru (tekerlekten bataryaya) hesaplanır; sürücü ve "
                                            "kontrol dinamiği modellenmez.",
    "Batarya tarafı / şebeke tarafı": "Model bataryadan çekilen enerjiyi hesaplar (batarya "
                                      "tarafı). Resmi WLTP prizden ölçülür (şebeke tarafı) ve "
                                      "şarj kayıplarını da içerir; karşılaştırmada şarj verimi "
                                      "hesaba katılmalıdır.",
}
GRID_VS_BATTERY = "Batarya tarafı / şebeke tarafı"  # eta_sarj kutusunun yardim metni

# Ilk kullanimda aciklanan kisaltmalar: kisaltma -> GLOSSARY anahtari. app.py bunlari
# bilgi kutusu metinlerinde ve ilgili kutularin help= metinlerinde arar.
ABBREVIATIONS = {"WLTP": "WLTP", "SoC": "SoC", "CoC": "CoC", "EEA": "EEA"}

# Dongu kisa aciklamalari (dongu secicinin help= metni) ve "Donguleri taniyin" tablosu
# (sure, mesafe, hiz, rolanti VERIDEN hesaplanir; burada yalnizca metinler).
CYCLE_INFO = {
    "WLTC_3b": {"bolge": "Avrupa (AB) · WLTP", "kisa": "Avrupa resmi döngüsü, 4 fazlı, gerçek "
                                                      "sürüşe en yakın"},
    "NEDC": {"bolge": "Avrupa (AB) · eski", "kisa": "Eski Avrupa döngüsü, yapay ve iyimser"},
    "UDDS": {"bolge": "ABD (EPA)", "kisa": "ABD şehir içi, dur-kalk"},
    "HWFET": {"bolge": "ABD (EPA)", "kisa": "ABD şehirlerarası, durmasız"},
    "US06": {"bolge": "ABD (EPA)", "kisa": "ABD agresif sürüş, en zorlu"},
}
CYCLES_BOX_LABEL = "ℹ️ Döngüleri tanıyın"
CYCLES_BOX_CAPTION = ("Süre, mesafe, hız ve rölanti oranı Excel verisinden hesaplanır "
                      "(cycle_summary()); rölanti = v = 0 olan örneklerin payı.")
CYCLE_SELECT_HELP_TITLE = "Döngüler (ayrıntı: Hız–zaman sekmesi → Döngüleri tanıyın):"
ABBREV_CAPTION = "Kısaltmalar"

# Kenar cubugu parametre kutulari icin kisa yardim (help=); anahtar = VehicleParams alani
_SOC_HELP = "Başlangıç ve menzil hesabındaki alt şarj sınırı."
PARAM_HELP = {
    "m_kg": "Test kütlesi. Yuvarlanma ve ivmelenme direncini doğrudan belirler.",
    "delta": "Dönen kütle faktörü. Tekerlek, motor ve aktarma organının dönme ataletini "
             "eşdeğer kütle olarak ekler.",
    "cd": "Aerodinamik sürüklenme katsayısı. A_f ile çarpımı aerodinamik direnci belirler "
          "(F ∝ C_d·A_f·v²).",
    "af_m2": "Ön kesit alanı (m²).",
    "fr": "Yuvarlanma direnci katsayısı. Lastik ve yola bağlıdır; F_roll = f_r·m·g.",
    "eta_t": "Aktarma organı (redüktör, diferansiyel) verimi.",
    "eta_m": "Motor + invertör verimi, çekişte.",
    "eta_reg": "Motor + invertör verimi, geri kazanımda.",
    "p_reg_max_w": "Bataryaya verilebilecek en yüksek rejenerasyon gücü; fazlası sürtünmeli "
                   "frende ısıya dönüşür.",
    "v_min_ms": "Bu hızın altında rejenerasyon kesilir, araç sürtünmeli frenle durur.",
    "p_aux_w": "Sabit yardımcı yük (klima, aydınlatma, elektronik).",
    "e_nom_kwh": "Batarya enerjisi; menzil hesabının temeli.",
    "soc0_pct": _SOC_HELP,
    "soc_min_pct": _SOC_HELP,
    "grade_pct": "Yol eğimi (%); F_grade = m·g·sin θ.",
}
