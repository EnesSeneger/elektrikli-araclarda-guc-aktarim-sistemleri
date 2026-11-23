# GitHub'a yuklenecek temiz kod klasorunu uretir: yalnizca kod, veri ve ayarlar.
# Kaynak PDF'leri, rapor, sunum, exe ve sanal ortam DAHIL EDILMEZ (.gitignore ile ayni liste).
# Calistirma (proje kokunden):  powershell -ExecutionPolicy Bypass -File github_kopyasi.ps1
# Cikti: ..\elektrikli-araclarda-guc-aktarim-sistemleri  (GitHub Desktop'taki yerel depo)
# Her calistirmada icerik yenilenir; .git klasoru (depo gecmisi) KORUNUR.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$out = Join-Path (Split-Path $PSScriptRoot -Parent) "elektrikli-araclarda-guc-aktarim-sistemleri"

$files = "app.py", "app_texts.py", "run_all.py", "conftest.py", "Baslat.bat",
         "requirements.txt", "requirements-dev.txt", ".gitignore", "README.md",
         "github_kopyasi.ps1", ".streamlit\config.toml"
$dirs  = "evmodel", "analysis", "tests", "data"

New-Item -ItemType Directory -Force $out | Out-Null
# Eski icerigi temizle ama .git (depo gecmisi) ve .devcontainer'a (Streamlit Cloud'un ekledigi)
# dokunma; silinen dosyalar GitHub'da da silinmis gorunur
$keep = ".git", ".devcontainer"
Get-ChildItem $out -Force | Where-Object { $keep -notcontains $_.Name } | Remove-Item -Recurse -Force
foreach ($f in $files) {
    $dst = Join-Path $out $f
    New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
    Copy-Item $f $dst
}
foreach ($d in $dirs) {
    Copy-Item $d (Join-Path $out $d) -Recurse
}
# Uretilen cikti klasorleri bos ama var olsun (analizler buraya yazar)
foreach ($d in "results\tables", "results\figures") {
    New-Item -ItemType Directory -Force (Join-Path $out $d) | Out-Null
    New-Item -ItemType File -Force (Join-Path $out "$d\.gitkeep") | Out-Null
}
Get-ChildItem $out -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

$code = Get-ChildItem $out -Recurse -File -Force | Where-Object { $_.FullName -notlike "*\.git\*" }
$n = $code.Count
$mb = ($code | Measure-Object Length -Sum).Sum / 1MB
Write-Host ("Hazir: {0}  ({1} dosya, {2:N2} MB)" -f $out, $n, $mb)
