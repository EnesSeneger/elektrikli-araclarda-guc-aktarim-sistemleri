# MKTS 5081 · EV Güç Aktarım Sistemi Modeli

Geriye dönük (backward-facing) elektrikli araç enerji ve SoC modeli. Gerçek araç: **Tesla Model 3 Standard Range Plus RWD, LFP (11/2020–12/2021)**.

## Kurulum (Windows PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Çalıştırma (tek komut)

```powershell
python run_all.py
```

Sıra: T4 veri kontrolü → T1–T4 doğrulama testleri → PNG grafikleri → analizler (3A, 3B, 3C bonus: motor haritası + G taraması). Tablolar `results/tables/`, grafikler `results/figures/` altına yazılır. Grafikleri atlamak için: `python run_all.py --no-figures`. Yalnızca testler için: `pytest tests/ -v`

> PowerShell `Activate.ps1` için "running scripts is disabled" hatası verirse bir kez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` çalıştırın ya da etkinleştirmeden `.venv\Scripts\python.exe run_all.py` kullanın.

## Web'de yayınlama (GitHub + Streamlit Community Cloud)

Uygulama kurulum gerektirmeden bir web linkinden açılır. GitHub'a yalnızca kod gider: kaynak PDF'leri, rapor, sunum ve exe `.gitignore` ile dışarıda kalır.

1. **Temiz kod klasörünü üret** (proje kökünden):
   ```powershell
   powershell -ExecutionPolicy Bypass -File github_kopyasi.ps1
   ```
   Çıktı: bir üst klasörde `elektrikli-araclarda-guc-aktarim-sistemleri` (yalnızca kod + `data/`).
2. **GitHub'a yükle (GitHub Desktop):** *File → Add local repository* → `elektrikli-araclarda-guc-aktarim-sistemleri` klasörü → "create a repository" (.gitignore ve lisans: None) → *Commit to main* → *Publish repository*. Betik `.git` klasörüne dokunmaz, depo geçmişi korunur.
3. **Streamlit Cloud'a bağla:** share.streamlit.io → GitHub ile giriş → *Create app* → depo `elektrikli-araclarda-guc-aktarim-sistemleri`, dal `main`, ana dosya `app.py` → *Advanced settings*'te Python **3.12** veya üstü → *Deploy*. Birkaç dakika sonra `https://<ad>.streamlit.app` linki hazır olur.
4. Kod değişince: kodu **bu proje klasöründe** düzenle, 1. adımı tekrarla, GitHub Desktop'ta *Commit* + *Push origin*. Streamlit Cloud uygulamayı kendiliğinden günceller.

Bağımlılıklar: `requirements.txt` (uygulama, bulut bunu kurar) · `requirements-dev.txt` (pytest, kaleido, PyInstaller; yalnızca yerel geliştirme).

## Rapor

`rapor/rapor.tex` → `rapor/rapor.pdf` (XeLaTeX, MiKTeX). Sayılar `run_all.py` tablolarından alınmıştır; kod değişirse rapordaki sayılar elle güncellenmelidir.

```powershell
cd rapor; xelatex rapor.tex; xelatex rapor.tex
```

Test edilen sürümler: Python 3.14.0, NumPy 2.5.4, pandas 3.1.0, Matplotlib 3.11.2, SciPy 1.18.1, openpyxl 3.1.5.

## Masaüstü uygulaması: Elektrikli Araç Modeli (ElektrikliArac.exe)

`dist\ElektrikliArac\ElektrikliArac.exe` ya da masaüstündeki **"Elektrikli Araç Modeli"** kısayolu ile açılır. Python kurulu olması gerekmez. Arayüz kendi penceresinde açılır (Edge uygulama modu, adres çubuğu yok); pencere kapatılınca arka plandaki sunucu da kapanır. Edge yoksa varsayılan tarayıcı açılır, yanında küçük bir "Uygulamayı kapat" penceresi çıkar. Sunucu günlüğü: `%TEMP%\ElektrikliArac_sunucu.log`.

- Giriş noktası: `ev_uygulama.py` (paketlemeden `python ev_uygulama.py` ile de çalışır)
- Yeniden üretmek için: `powershell -ExecutionPolicy Bypass -File build_exe.ps1` (PyInstaller, ~2 dk, ~320 MB klasör). `dist\ElektrikliArac\` klasörü bütün olarak taşınmalıdır, exe tek başına çalışmaz.
- Kod değiştiyse exe'yi yeniden üretin; exe, üretildiği andaki kodu içerir.

## Web arayüzü

**Tek tıkla (Python ile):** proje klasöründeki `Baslat.bat` dosyasına çift tıklayın. İlk seferde `.venv` kurulur ve kütüphaneler yüklenir. Sonra tarayıcıda arayüz açılır. Kapatmak için siyah pencereyi kapatın.

Öne çıkan sekmeler:
- **🎬 Sürüş simülatörü:** Döngü saniye saniye oynatılır (▶ Oynat / kaydırıcı). Hız, batarya gücü ve SoC göstergeleri canlı değişir.
- **🆚 Parametre etkisi:** Kenar çubuğunda değiştirilen her parametrenin etkisi döngü döngü gösterilir (tüketim, menzil, rejenerasyon payı; varsayılana göre %). Özet kartlarında da değişim okları görünür.
- **⚙️ 3C · Motor haritası ve G:** G kaydırıcısıyla haritalı model canlı çalışır. Ekranda tarama eğrileri, azami hız kısıtı, kalkış kuvveti ve verim haritası üzerindeki çalışma noktaları yer alır.

`tests/test_app_smoke.py` arayüzü iki araçla, senaryo seçimiyle ve parametre değişikliğiyle otomatik çalıştırır (`run_all.py` içinde).

Elle başlatmak için (yalnızca yerel, `localhost`):

```powershell
pip install -r requirements.txt   # streamlit ve plotly dahil
streamlit run app.py
```

Tarayıcıda `http://localhost:8501` açılır. Kenar çubuğundan araç (Temel Araç / Tesla), döngüler, parametreler, 3B senaryoları ve grafik zaman penceresi seçilir. Sekmeler: döngü tablosu (CSV), hız, batarya gücü, SoC, enerji dağılımı, motor çalışma noktaları, senaryo karşılaştırma (faz tablosu dahil) ve WLTP karşılaştırma. Grafikler kamera ikonuyla PNG olarak indirilebilir.

Arayüz hesap yapmaz: `simulate()` ve `analysis/` içindeki tablo fonksiyonlarını çağırır, yani gösterdiği 3A/3B sayıları `run_all.py` çıktısıyla aynıdır. Tesla parametrelerinin tamamı `params.py`'de kaynaklıdır. Teslim için geçerli olan çıktı `python run_all.py`'dir.

## Klasörler

| Klasör / dosya | İçerik |
|---|---|
| `data/` | `surus_donguleri.xlsx` (kullanılan sayfalar: WLTC_3b, NEDC, UDDS, HWFET, US06; yalnızca A:B sütunları) |
| `evmodel/params.py` | Temel Araç ve Tesla parametreleri (kaynaklı) |
| `evmodel/cycles.py` | Excel okuyucu, mesafe hesabı (`python -m evmodel.cycles`) |
| `evmodel/model.py` | `simulate()`: ödev Bölüm 1 denklemleri, enerji kalemleri |
| `evmodel/envelope.py` | Motor tepe tork–hız zarfı |
| `evmodel/plotting.py` | Rapor için matplotlib PNG grafikleri |
| `evmodel/interactive.py` | Web arayüzü için Plotly grafikleri |
| `app.py` | Streamlit web arayüzü |
| `app_texts.py` | Arayüzün tüm açıklama metinleri (bilgi kutuları, parametre yardımları, mesajlar) |
| `tests/` | 18 test: T1, T1b, T2, T3, T4 doğrulama; 20 Kasım kontrol belgesi (65 satır); parametre ve kaynak tutarlılığı; 3C; arayüz duman testi |
| `analysis/` | 3A, 3B, 3C analiz scriptleri |
| `docs/kaynaklar.md` | Parametre kaynak defteri |

## Kaynaklar

Parametrelerin kaynakları, sayfa numaraları ve güven düzeyleri: [`docs/kaynaklar.md`](docs/kaynaklar.md) (sonunda IEEE stilinde numaralı kaynakça). Kaynakların yerel kopyaları `docs/kaynaklar/` altında arşivlidir:

| Kısaltma | Kaynak | Arşiv dosyası |
|---|---|---|
| [R24] | Rosenberger vd. 2024, *World Electric Vehicle Journal* 15:268 (Tesla Model 3 analizi) | `R24_Rosenberger_2024.pdf` |
| [EEA] | AB Çevre Ajansı CO2 izleme veri tabanı, Va = E6CR sorgusu | `EEA_E6CR_sorgu_2021.json` |
| [ADAC26] | ADAC şarj kaybı testi, 06.08.2026 | `ADAC26_Ladeverluste_2026-08-06.pdf` |
| [L23] | Lacock vd. 2023, *World Electric Vehicle Journal* 14:342 (aktarma verimi) | `L23_Lacock_2023.pdf` |
| [EVDB] | EV Database, Tesla Model 3 SR+ (CATL) | `EVDB_Tesla_Model3_SRplus_CATL.pdf` |

`tests/test_sources.py`, EEA arşivindeki WLTP tüketimi ve test kütlesinin `evmodel/params.py` ile aynı olduğunu denetler.

## Doğrulama notu (T2)

Beklenen 63,1 Wh, P_bat'ın 0–10 s arasındaki yamuk (trapez) integraline karşılık gelir. Ödevdeki dikdörtgen toplam bu kısa profilde 69,5 Wh verir; fark tam olarak son örneğin yarısıdır (P_bat(10 s)·Δt/2 ≈ 6,4 Wh). Uçlarında hızı sıfır olan sürüş döngülerinde iki yöntem pratikte aynı sonucu verir.
