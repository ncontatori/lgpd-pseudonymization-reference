"""Pseudonimização de CPF/CNPJ para integrações entre plataformas (referência).

Ideia central
-------------
CPF e CNPJ são dados pessoais/identificadores fortes. Em vez de trafegá-los
entre CRM, ERP, ITSM e plataforma de dados, cada sistema recebe um
*identificador pseudônimo* estável, derivado com HMAC-SHA256 e uma chave
secreta mantida fora do código (cofre de segredos / KMS).

- Mesmo documento + mesma chave  -> mesmo pseudônimo (permite joins e deduplicação)
- Sem a chave                    -> impossível recalcular por força bruta
- Contextos diferentes           -> pseudônimos diferentes (evita correlação indevida)

Este módulo é uma referência educacional. Não é aconselhamento jurídico;
valide o desenho com o DPO e o jurídico da sua organização.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import uuid

__all__ = [
    "normalize",
    "is_valid_cpf",
    "is_valid_cnpj",
    "pseudonymize",
    "external_id",
]

_NON_DIGITS = re.compile(r"\D")


def normalize(document: str) -> str:
    """Remove pontuação e espaços: '123.456.789-09' -> '12345678909'."""
    return _NON_DIGITS.sub("", document or "")


def _check_digit(digits: str, weights: list[int]) -> int:
    total = sum(int(d) * w for d, w in zip(digits, weights))
    rest = total % 11
    return 0 if rest < 2 else 11 - rest


def is_valid_cpf(document: str) -> bool:
    cpf = normalize(document)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    d1 = _check_digit(cpf[:9], list(range(10, 1, -1)))
    d2 = _check_digit(cpf[:10], list(range(11, 1, -1)))
    return cpf[-2:] == f"{d1}{d2}"


def is_valid_cnpj(document: str) -> bool:
    cnpj = normalize(document)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    w2 = [6] + w1
    d1 = _check_digit(cnpj[:12], w1)
    d2 = _check_digit(cnpj[:13], w2)
    return cnpj[-2:] == f"{d1}{d2}"


def _key(key: bytes | None) -> bytes:
    if key:
        return key
    env = os.environ.get("PSEUDONYM_KEY")
    if not env:
        raise RuntimeError(
            "Defina PSEUDONYM_KEY (vinda do cofre de segredos) ou passe key=..."
        )
    return env.encode()


def pseudonymize(document: str, context: str = "default", key: bytes | None = None) -> str:
    """Retorna o pseudônimo hexadecimal (64 caracteres) do documento.

    `context` separa domínios (ex.: 'crm', 'datalake') para que o mesmo
    titular não seja correlacionável entre contextos sem autorização.
    """
    doc = normalize(document)
    if not (is_valid_cpf(doc) or is_valid_cnpj(doc)):
        raise ValueError("Documento inválido: informe um CPF ou CNPJ válido")
    message = f"{context}:{doc}".encode()
    return hmac.new(_key(key), message, hashlib.sha256).hexdigest()


def external_id(document: str, context: str = "default", key: bytes | None = None) -> str:
    """Pseudônimo no formato UUID — útil para campos External ID (Salesforce, SAP, etc.)."""
    digest = bytes.fromhex(pseudonymize(document, context, key))
    return str(uuid.UUID(bytes=digest[:16], version=4))


if __name__ == "__main__":  # demonstração com documento fictício
    demo_key = b"chave-de-demonstracao-nao-use-em-producao"
    cpf_ficticio = "529.982.247-25"  # CPF de exemplo amplamente usado em testes
    print("pseudônimo (crm):     ", pseudonymize(cpf_ficticio, "crm", demo_key))
    print("pseudônimo (datalake):", pseudonymize(cpf_ficticio, "datalake", demo_key))
    print("external id (crm):    ", external_id(cpf_ficticio, "crm", demo_key))
