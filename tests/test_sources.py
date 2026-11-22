"""
Kaynak arsivi tutarliligi: [EEA] sorgu sonucu (docs/kaynaklar/EEA_E6CR_sorgu_2021.json)
ile params.TESLA_SOURCED ayni degerleri tasimali.

  - null olmayan tum Z (Wh/km) degerleri == TESLA_SOURCED["wltp_consumption_wh_km"]
  - null olmayan tum Mt degerleri       == TESLA_SOURCED["mass_wltp_test_kg"]
JSON yoksa test atlanir (pytest.skip / run_all.py'de ATLANDI).
"""

import json
from pathlib import Path

from evmodel.params import TESLA_SOURCED

EEA_JSON = Path(__file__).resolve().parent.parent / "docs" / "kaynaklar" / "EEA_E6CR_sorgu_2021.json"
Z_FIELD, MT_FIELD, COUNT_FIELD = "Z (Wh/km)", "Mt", "n"


class SkipTest(Exception):
    """JSON yoksa: pytest altinda pytest.skip, run_all.py'de ATLANDI olarak gorunur."""


def _skip(msg: str):
    try:
        import pytest
    except ImportError:
        raise SkipTest(msg)
    pytest.skip(msg)


def load_eea_rows() -> list:
    if not EEA_JSON.exists():
        _skip(f"EEA arsiv dosyasi yok: {EEA_JSON}")
    data = json.loads(EEA_JSON.read_text(encoding="utf-8"))
    return data["results"] if isinstance(data, dict) else data


def test_eea_matches_tesla_sourced():
    rows = load_eea_rows()
    z = {r[Z_FIELD] for r in rows if r.get(Z_FIELD) is not None}
    mt = {r[MT_FIELD] for r in rows if r.get(MT_FIELD) is not None}
    assert z == {TESLA_SOURCED["wltp_consumption_wh_km"]}, f"EEA Z degerleri: {sorted(z)}"
    assert mt == {TESLA_SOURCED["mass_wltp_test_kg"]}, f"EEA Mt degerleri: {sorted(mt)}"

    top = max(rows, key=lambda r: r[COUNT_FIELD])
    print(f"  EEA: {len(rows)} grup; en buyuk grup n = {top[COUNT_FIELD]} kayit "
          f"(Ve={top.get('Ve')}, TAN={top.get('TAN')}, Z={top.get(Z_FIELD)}, Mt={top.get(MT_FIELD)})")
