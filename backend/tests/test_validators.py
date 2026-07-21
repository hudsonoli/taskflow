from app.domain.validators import validar_cnpj


def test_validar_cnpj_accepts_formatted_valid_cnpj():
    assert validar_cnpj("15.519.472/0001-22") is True


def test_validar_cnpj_accepts_unformatted_valid_cnpj():
    assert validar_cnpj("15519472000122") is True


def test_validar_cnpj_rejects_wrong_check_digits():
    assert validar_cnpj("15.519.472/0001-23") is False


def test_validar_cnpj_rejects_wrong_length():
    assert validar_cnpj("155194720001") is False
    assert validar_cnpj("1551947200012299") is False


def test_validar_cnpj_rejects_repeated_digit_sequences():
    assert validar_cnpj("00000000000000") is False
    assert validar_cnpj("11111111111111") is False


def test_validar_cnpj_rejects_none_or_empty():
    assert validar_cnpj(None) is False
    assert validar_cnpj("") is False
    assert validar_cnpj("   ") is False


def test_validar_cnpj_rejects_non_numeric_garbage():
    assert validar_cnpj("abcd.efg/hijk-lm") is False
