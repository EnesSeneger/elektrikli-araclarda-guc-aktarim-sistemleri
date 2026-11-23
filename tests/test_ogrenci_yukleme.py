"""
Ogrenci modeli yukleme: ornek dosya geri yuklenince tum satirlar tutmali; Turkce Excel
CSV'si (';' ayirici, ondalik virgul, W birimi) da okunmali; bozuk P_bat tutmamali.
"""

from analysis import ogrenci_yukleme as ogr


def test_example_roundtrip_passes():
    data = ogr.example_csv("WLTC_3b")
    t, p = ogr.parse_series(ogr.read_upload("ornek.csv", data))
    tab, info = ogr.compare(t, p, "WLTC_3b")
    assert (tab["durum"] == "tutuyor").all(), tab
    assert info["n_points"] == info["n_cycle"]


def test_semicolon_decimal_comma_watts():
    df = ogr.read_upload("ornek.csv", ogr.example_csv("UDDS"))
    df["p_bat_w"] = df.pop("p_bat_kw") * 1e3
    text = df.to_csv(index=False, sep=";", decimal=",").encode("utf-8")
    t, p = ogr.parse_series(ogr.read_upload("tr.csv", text))
    tab, _ = ogr.compare(t, p, "UDDS")
    assert (tab["durum"] == "tutuyor").all(), tab


def test_wrong_cycle_is_flagged():
    t, p = ogr.parse_series(ogr.read_upload("ornek.csv", ogr.example_csv("WLTC_3b")))
    assert not ogr.compare(t, p, "WLTC_3b")[1]["sure_uyumsuz"]
    assert ogr.compare(t, p, "NEDC")[1]["sure_uyumsuz"]      # WLTC dosyasi, NEDC secili


def test_wrong_model_fails():
    t, p = ogr.parse_series(ogr.read_upload("ornek.csv", ogr.example_csv("WLTC_3b")))
    tab, _ = ogr.compare(t, p * 1.05, "WLTC_3b")       # %5 hatali model
    assert (tab["durum"] == "tutmuyor").any()
