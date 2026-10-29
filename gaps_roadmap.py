"""Fase 3 — Análise de lacunas (Skill Gap Analysis) e geração do roadmap.

Cruza a trilha escolhida com o nível atual do usuário em cada competência
(0 = nenhum, 1 = básico, 2 = intermediário, 3 = avançado) e com o que a base
de conhecimento exige para o nível Júnior. Depois monta um plano de estudos
em etapas, com tempo estimado, certificações e projetos de portfólio.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd

from base_conhecimento import base_padrao

ROTULO_PRIORIDADE = {1: "Alta", 2: "Média", 3: "Baixa"}


@dataclass
class Gap:
    competencia: str
    nome: str
    atual: int
    exigido: int
    prioridade: int

    @property
    def falta(self) -> int:
        return max(0, self.exigido - self.atual)


@dataclass
class AnaliseGaps:
    trilha: str
    nome_trilha: str
    itens: list[Gap]
    prontidao: float          # % do caminho até o Júnior já percorrido
    nivel_atual: str

    @property
    def lacunas(self) -> list[Gap]:
        """Só as competências que ainda faltam, da mais urgente para a menos."""
        return sorted((g for g in self.itens if g.falta > 0),
                      key=lambda g: (g.prioridade, -g.falta, g.nome))

    @property
    def pontos_fortes(self) -> list[Gap]:
        return [g for g in self.itens if g.falta == 0]

    def tabela(self, niveis: dict) -> pd.DataFrame:
        return pd.DataFrame([
            {"Competência": g.nome, "Seu nível": niveis[str(g.atual)],
             "Exigido (Júnior)": niveis[str(g.exigido)],
             "Situação": "✅ Atende" if g.falta == 0 else f"⚠️ Falta {g.falta} nível(is)",
             "Prioridade": ROTULO_PRIORIDADE[g.prioridade]}
            for g in sorted(self.itens, key=lambda g: (g.falta == 0, g.prioridade, -g.falta))
        ])


@dataclass
class ItemEstudo:
    nome: str
    de: str
    para: str
    topicos: list[str]
    horas: int


@dataclass
class EtapaRoadmap:
    titulo: str
    descricao: str
    itens: list[ItemEstudo] = field(default_factory=list)
    extras: list[str] = field(default_factory=list)

    @property
    def horas(self) -> int:
        return sum(i.horas for i in self.itens)


@dataclass
class Roadmap:
    etapas: list[EtapaRoadmap]
    horas_totais: int
    semanas: int
    certificacoes: list[dict]
    projetos: list[str]
    dica_objetivo: str


def estimar_nivel(prontidao: float, lacunas_criticas: int, sem_lacunas: bool,
                  experiencia: str, todos_avancados: bool) -> str:
    """Estima a senioridade atual do usuário na trilha."""
    if prontidao < 40:
        return "Iniciante"
    if lacunas_criticas > 0 or prontidao < 85:
        return "Em formação (pré-Júnior)"
    if sem_lacunas and todos_avancados and experiencia in ("1a3", "mais3"):
        return "Júnior consolidado — rumo ao Pleno"
    if experiencia in ("1a3", "mais3"):
        return "Júnior"
    return "Pronto para vagas Júnior"


def analisar_gaps(trilha_id: str, conhecimentos: dict, experiencia: str = "nenhuma",
                  base: dict | None = None) -> AnaliseGaps:
    base = base or base_padrao()
    plano = base["plano_carreira"][trilha_id]
    competencias = base["competencias"]
    nivel_max = max(int(n) for n in base["niveis_conhecimento"])

    itens = []
    for skill, (exigido, prioridade) in plano["junior"].items():
        atual = int(conhecimentos.get(skill, 0))
        if not 0 <= atual <= nivel_max:
            raise ValueError(f"Nível inválido para '{skill}': {atual}")
        itens.append(Gap(skill, competencias[skill]["nome"], atual, exigido, prioridade))

    exigido_total = sum(g.exigido for g in itens)
    atingido = sum(min(g.atual, g.exigido) for g in itens)
    prontidao = round(100 * atingido / exigido_total, 1)

    criticas = sum(1 for g in itens if g.falta > 0 and g.prioridade == 1)
    nivel = estimar_nivel(
        prontidao, criticas, all(g.falta == 0 for g in itens), experiencia,
        all(g.atual >= nivel_max for g in itens),
    )
    return AnaliseGaps(trilha_id, base["trilhas"][trilha_id]["nome"], itens, prontidao, nivel)


def gerar_roadmap(analise: AnaliseGaps, horas_semana: int = 10, objetivo: str = "primeiro_emprego",
                  base: dict | None = None) -> Roadmap:
    base = base or base_padrao()
    plano = base["plano_carreira"][analise.trilha]
    niveis = base["niveis_conhecimento"]
    horas_nivel = base["horas_por_nivel"]

    def item(g: Gap) -> ItemEstudo:
        topicos = base["competencias"][g.competencia]["estudar"]
        # Quem já tem algum nível pula os tópicos iniciais.
        inicio = min(g.atual, len(topicos) - 1)
        return ItemEstudo(g.nome, niveis[str(g.atual)], niveis[str(g.exigido)],
                          topicos[inicio:], g.falta * horas_nivel)

    criticas = [item(g) for g in analise.lacunas if g.prioridade == 1]
    complementares = [item(g) for g in analise.lacunas if g.prioridade > 1]

    etapas = []
    if criticas:
        etapas.append(EtapaRoadmap(
            "Etapa 1 — Fundamentos essenciais",
            "Competências de prioridade alta: sem elas é difícil passar numa entrevista Júnior.",
            criticas))
    if complementares:
        etapas.append(EtapaRoadmap(
            f"Etapa {len(etapas) + 1} — Competências complementares",
            "Diferenciais que completam o perfil Júnior.",
            complementares))
    certs = plano["certificacoes"]
    etapas.append(EtapaRoadmap(
        f"Etapa {len(etapas) + 1} — Portfólio e certificação",
        "Mostre na prática o que aprendeu: publique os projetos no GitHub com um bom README.",
        extras=[f"Projeto: {p}" for p in plano["projetos"]]
        + [f"Certificação ({c['momento']}): {c['nome']}" for c in certs if c["momento"] == "Para o Júnior"]))

    horas_totais = sum(e.horas for e in etapas)
    semanas = math.ceil(horas_totais / max(1, horas_semana)) if horas_totais else 0

    fortes = ", ".join(g.nome for g in analise.pontos_fortes) or "nenhuma competência ainda"
    dicas = {
        "primeiro_emprego": "Como seu foco é o primeiro emprego, priorize terminar a Etapa 1 e publicar "
                            "pelo menos dois projetos. Recrutadores de vagas Júnior e estágio olham muito o GitHub.",
        "transicao": f"Na transição de área, aproveite o que você já domina ({fortes}) e "
                     "destaque essas competências no currículo enquanto fecha as lacunas.",
        "crescer": "Para crescer na área, depois de fechar as lacunas mire na certificação de "
                   "'Próximo passo' e em projetos mais complexos, que mostram autonomia.",
    }
    return Roadmap(etapas, horas_totais, semanas, certs, plano["projetos"], dicas[objetivo])


if __name__ == "__main__":
    conhecimentos = {"linux": 1, "git": 2, "docker": 0, "programacao": 2, "redes": 1}
    analise = analisar_gaps("devops", conhecimentos, "nenhuma")
    print(f"{analise.nome_trilha}: prontidão {analise.prontidao}% — {analise.nivel_atual}\n")
    print(analise.tabela(base_padrao()["niveis_conhecimento"]).to_string(index=False))
    roadmap = gerar_roadmap(analise, horas_semana=10, objetivo="primeiro_emprego")
    print(f"\nTotal: {roadmap.horas_totais} h (~{roadmap.semanas} semanas a 10 h/semana)")
    for etapa in roadmap.etapas:
        print(f"\n{etapa.titulo} ({etapa.horas} h)")
        for i in etapa.itens:
            print(f"  - {i.nome}: {i.de} → {i.para} ({i.horas} h): {'; '.join(i.topicos)}")
        for x in etapa.extras:
            print(f"  - {x}")
    print("\nDica:", roadmap.dica_objetivo)
