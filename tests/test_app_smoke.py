"""
Arayuz duman testi (Streamlit AppTest): app.py iki aracla, parametre degisikligiyle ve
3B senaryosuyla hatasiz calisiyor mu? Tum sekmeler ayni calistirmada uretilir.
streamlit kurulu degilse atlanir.
"""

import re
from pathlib import Path

import pytest

APP_TIMEOUT_S = 300


def _app():
    testing = pytest.importorskip("streamlit.testing.v1")
    app_path = str(Path(__file__).resolve().parent.parent / "app.py")
    at = testing.AppTest.from_file(app_path, default_timeout=APP_TIMEOUT_S)
    return at.run()


def _no_errors(at):
    assert not at.exception, [e.value for e in at.exception]


def test_app_base_vehicle_and_scenario():
    at = _app()
    _no_errors(at)
    at.radio(key="scenario").set_value("S1").run()
    _no_errors(at)
    assert at.session_state["par_m_kg"] == 2160.0


def test_app_tesla_with_changed_param():
    at = _app()
    at.selectbox(key="vehicle").set_value("Tesla Model 3 SR+ (LFP)").run()
    _no_errors(at)
    at.number_input(key="par_p_aux_w").set_value(1352.0).run()
    _no_errors(at)
    at.button(key="nav_c3").click().run()   # 3C bolumune gec (gruplu buton menusu)
    _no_errors(at)
    at.slider(key="c3_g").set_value(10.0).run()
    _no_errors(at)


def test_app_questions_are_live():
    """Yorum sorulari bulgulari parametreye bagli: kutle degisince metin de degismeli."""
    at = _app()
    at.button(key="nav_yorum").click().run()
    _no_errors(at)
    before = "\n".join(m.value for m in at.markdown if m.value.startswith("- "))
    at.number_input(key="par_m_kg").set_value(2500.0).run()
    _no_errors(at)
    after = "\n".join(m.value for m in at.markdown if m.value.startswith("- "))
    assert before and after and before != after


def test_app_every_page_renders():
    """Menudeki her bolum iki aracla da hatasiz acilir."""
    import app_texts as T

    at = _app()
    for vehicle in ("Temel Araç", "Tesla Model 3 SR+ (LFP)"):
        at.selectbox(key="vehicle").set_value(vehicle).run()
        for items in T.NAV.values():
            for key, _ in items:
                at.button(key=f"nav_{key}").click().run()
                _no_errors(at)
                assert at.session_state["page"] == key
                # canli metin: doldurulmamis {yer_tutucu} kalmamali
                left = [m.value for m in at.markdown if re.search(r"\{[a-z_0-9]+\}", m.value)]
                assert not left, (vehicle, key, left[:2])
