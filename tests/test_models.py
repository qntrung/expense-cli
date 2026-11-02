import unicodedata

from expense.models import normalize_category


def test_normalize_category_strips_and_lowercases():
    assert normalize_category("  An-Uong ") == "an-uong"


def test_normalize_category_handles_vietnamese_uppercase():
    assert normalize_category("ĂN UỐNG") == "ăn uống"


def test_normalize_category_nfd_equals_nfc():
    nfd = unicodedata.normalize("NFD", "Ăn uống")
    assert nfd != "Ăn uống"
    assert normalize_category(nfd) == normalize_category("Ăn uống") == "ăn uống"
