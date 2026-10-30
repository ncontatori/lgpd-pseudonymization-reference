import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pseudonymize import (  # noqa: E402
    external_id,
    is_valid_cnpj,
    is_valid_cpf,
    normalize,
    pseudonymize,
)

KEY = b"test-key"
CPF = "529.982.247-25"          # fictício, válido
CNPJ = "11.222.333/0001-81"     # fictício, válido


def test_normalize():
    assert normalize(CPF) == "52998224725"


def test_validation():
    assert is_valid_cpf(CPF)
    assert not is_valid_cpf("111.111.111-11")
    assert not is_valid_cpf("529.982.247-24")
    assert is_valid_cnpj(CNPJ)
    assert not is_valid_cnpj("11.222.333/0001-80")


def test_deterministic_and_format_insensitive():
    assert pseudonymize(CPF, "crm", KEY) == pseudonymize("52998224725", "crm", KEY)
    assert len(pseudonymize(CPF, "crm", KEY)) == 64


def test_context_and_key_separation():
    assert pseudonymize(CPF, "crm", KEY) != pseudonymize(CPF, "datalake", KEY)
    assert pseudonymize(CPF, "crm", KEY) != pseudonymize(CPF, "crm", b"outra-chave")


def test_external_id_is_uuid():
    eid = external_id(CNPJ, "erp", KEY)
    assert len(eid) == 36 and eid[14] == "4"


def test_invalid_document_raises():
    with pytest.raises(ValueError):
        pseudonymize("123", "crm", KEY)


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("PSEUDONYM_KEY", raising=False)
    with pytest.raises(RuntimeError):
        pseudonymize(CPF)
