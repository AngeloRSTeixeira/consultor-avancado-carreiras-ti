"""Carregamento e validação da Base de Conhecimento (arquivo JSON externo).

Nenhuma regra, peso ou pergunta fica fixa no código: tudo vem de
``data/regras_carreiras.json``.
"""
import json
from functools import lru_cache
from pathlib import Path

CAMINHO_PADRAO = Path(__file__).resolve().parent / "data" / "regras_carreiras.json"
OPERADORES = {">=", "<=", ">", "<", "==", "!="}


class ErroBaseConhecimento(ValueError):
    """Erro de estrutura ou de consistência no JSON."""


def carregar_base(caminho: str | Path = CAMINHO_PADRAO) -> dict:
    """Lê o JSON, valida e devolve a base pronta para o motor."""
    with open(caminho, encoding="utf-8") as arquivo:
        base = json.load(arquivo)
    validar_base(base)
    return base


@lru_cache(maxsize=1)
def base_padrao() -> dict:
    """Base padrão carregada uma única vez (cache)."""
    return carregar_base()


def perguntas_por_id(base: dict) -> dict:
    return {p["id"]: p for p in base["perguntas"]}


def validar_base(base: dict) -> None:
    """Confere se o JSON é coerente antes de o motor usá-lo."""
    for chave in ("escala", "perguntas", "trilhas", "regras"):
        if chave not in base:
            raise ErroBaseConhecimento(f"Chave obrigatória ausente: {chave}")

    perguntas = perguntas_por_id(base)
    if len(perguntas) != len(base["perguntas"]):
        raise ErroBaseConhecimento("Há perguntas com id repetido.")

    def caracteristica_existe(chave: str) -> bool:
        if "=" in chave:
            pid, opcao = chave.split("=", 1)
            p = perguntas.get(pid)
            return p is not None and p["tipo"] == "escolha" and opcao in p["opcoes"]
        p = perguntas.get(chave)
        return p is not None and p["tipo"] == "likert"

    for tid, trilha in base["trilhas"].items():
        for chave, peso in trilha["pesos"].items():
            if not caracteristica_existe(chave):
                raise ErroBaseConhecimento(f"Trilha {tid}: peso para característica inexistente '{chave}'.")
            if peso <= 0:
                raise ErroBaseConhecimento(f"Trilha {tid}: pesos devem ser positivos ('{chave}').")

    ids_regras = set()
    for regra in base["regras"]:
        if regra["id"] in ids_regras:
            raise ErroBaseConhecimento(f"Regra repetida: {regra['id']}")
        ids_regras.add(regra["id"])
        if regra["trilha"] not in base["trilhas"]:
            raise ErroBaseConhecimento(f"Regra {regra['id']}: trilha inexistente '{regra['trilha']}'.")
        if regra["tipo"] == "bonus" and regra["efeito"] <= 0:
            raise ErroBaseConhecimento(f"Regra {regra['id']}: bônus precisa de efeito positivo.")
        if regra["tipo"] == "penalidade" and regra["efeito"] >= 0:
            raise ErroBaseConhecimento(f"Regra {regra['id']}: penalidade precisa de efeito negativo.")
        for cond in regra["se"]:
            if cond["pergunta"] not in perguntas:
                raise ErroBaseConhecimento(f"Regra {regra['id']}: pergunta inexistente '{cond['pergunta']}'.")
            if cond["op"] not in OPERADORES:
                raise ErroBaseConhecimento(f"Regra {regra['id']}: operador inválido '{cond['op']}'.")
