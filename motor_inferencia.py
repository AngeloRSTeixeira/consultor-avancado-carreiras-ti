"""Motor de Inferência próprio com pontuação ponderada e regras de bônus/penalidade.

Passo a passo do raciocínio:

1. **Fatos:** as respostas do usuário viram intensidades de 0 a 1
   (Likert 1→0,0 · 3→0,5 · 5→1,0; escolhas viram características 0/1).
2. **Pontuação ponderada:** para cada trilha, soma ``peso × intensidade`` e
   divide pelo máximo possível, gerando um percentual-base.
3. **Regras SE-ENTÃO:** regras de bônus (sinergias) e de penalidade (perfis
   conflitantes), lidas do JSON, ajustam o percentual.
4. **Decisão:** ordena as trilhas, devolve o Top 3 e marca casos de incerteza
   (perfil híbrido, baixa confiança, respostas uniformes).
"""
from __future__ import annotations

import operator
import statistics
from dataclasses import dataclass, field

import pandas as pd

from base_conhecimento import base_padrao, perguntas_por_id

OPS = {">=": operator.ge, "<=": operator.le, ">": operator.gt, "<": operator.lt,
       "==": operator.eq, "!=": operator.ne}

LIMIAR_EMPATE = 5.0       # diferença (em pontos %) abaixo da qual o perfil é híbrido
LIMIAR_CONFIANCA = 50.0   # abaixo disso, nenhuma trilha tem aderência forte
LIMIAR_UNIFORME = 6.0     # desvio-padrão mínimo esperado entre as trilhas


@dataclass
class Contribuicao:
    caracteristica: str
    rotulo: str
    resposta: str
    pontos: float          # quanto essa característica somou ao percentual-base


@dataclass
class RegraDisparada:
    id: str
    tipo: str
    efeito: float
    motivo: str


@dataclass
class ResultadoTrilha:
    id: str
    nome: str
    descricao: str
    base: float
    ajuste: float
    compatibilidade: float
    contribuicoes: list[Contribuicao] = field(default_factory=list)
    regras: list[RegraDisparada] = field(default_factory=list)

    def principais_motivos(self, n: int = 3) -> list[Contribuicao]:
        return sorted(self.contribuicoes, key=lambda c: -c.pontos)[:n]


@dataclass
class Diagnostico:
    ranking: list[ResultadoTrilha]
    alertas: list[str]
    hibrido: bool
    baixa_confianca: bool

    @property
    def top3(self) -> list[ResultadoTrilha]:
        return self.ranking[:3]

    @property
    def vencedora(self) -> ResultadoTrilha:
        return self.ranking[0]

    def tabela(self) -> pd.DataFrame:
        """Ranking completo como DataFrame (usado na interface e nos testes)."""
        return pd.DataFrame([
            {"Posição": i, "Trilha": r.nome, "id": r.id, "Base (%)": r.base,
             "Ajustes": r.ajuste, "Compatibilidade (%)": r.compatibilidade}
            for i, r in enumerate(self.ranking, start=1)
        ])


class MotorInferencia:
    def __init__(self, base: dict | None = None):
        self.base = base or base_padrao()
        self.perguntas = perguntas_por_id(self.base)
        self.escala_min = self.base["escala"]["min"]
        self.escala_max = self.base["escala"]["max"]

    # ------------------------------------------------------------------ fatos
    def validar_respostas(self, respostas: dict) -> None:
        for pid, p in self.perguntas.items():
            if p["tipo"] == "numero":
                continue
            if pid not in respostas:
                raise ValueError(f"Resposta ausente: {pid}")
            valor = respostas[pid]
            if p["tipo"] == "likert" and not (self.escala_min <= valor <= self.escala_max):
                raise ValueError(f"'{pid}' deve estar entre {self.escala_min} e {self.escala_max}.")
            if p["tipo"] == "escolha" and valor not in p["opcoes"]:
                raise ValueError(f"Opção inválida para '{pid}': {valor!r}")

    def intensidade(self, chave: str, respostas: dict) -> float:
        """Converte a resposta em força da evidência, de 0 a 1."""
        if "=" in chave:
            pid, opcao = chave.split("=", 1)
            return 1.0 if respostas[pid] == opcao else 0.0
        return (respostas[chave] - self.escala_min) / (self.escala_max - self.escala_min)

    def maximo_trilha(self, pesos: dict) -> float:
        """Maior pontuação possível: Likert somam; escolhas contam só a maior opção."""
        total, por_escolha = 0.0, {}
        for chave, peso in pesos.items():
            if "=" in chave:
                pid = chave.split("=", 1)[0]
                por_escolha[pid] = max(por_escolha.get(pid, 0.0), peso)
            else:
                total += peso
        return total + sum(por_escolha.values())

    def rotulo(self, chave: str, respostas: dict) -> tuple[str, str]:
        if "=" in chave:
            pid, opcao = chave.split("=", 1)
            p = self.perguntas[pid]
            return f"{p['texto']} → {p['opcoes'][opcao]}", p["opcoes"][opcao]
        p = self.perguntas[chave]
        return p["texto"], f"{respostas[chave]}/{self.escala_max}"

    # ----------------------------------------------------------------- regras
    def condicao_ok(self, cond: dict, respostas: dict) -> bool:
        return OPS[cond["op"]](respostas[cond["pergunta"]], cond["valor"])

    def regras_disparadas(self, trilha_id: str, respostas: dict) -> list[RegraDisparada]:
        return [
            RegraDisparada(r["id"], r["tipo"], r["efeito"], r["motivo"])
            for r in self.base["regras"]
            if r["trilha"] == trilha_id and all(self.condicao_ok(c, respostas) for c in r["se"])
        ]

    # --------------------------------------------------------------- cálculo
    def avaliar_trilha(self, trilha_id: str, respostas: dict) -> ResultadoTrilha:
        trilha = self.base["trilhas"][trilha_id]
        maximo = self.maximo_trilha(trilha["pesos"])

        contribuicoes = []
        pontos = 0.0
        for chave, peso in trilha["pesos"].items():
            valor = peso * self.intensidade(chave, respostas)
            pontos += valor
            if valor > 0:
                rotulo, resposta = self.rotulo(chave, respostas)
                contribuicoes.append(Contribuicao(chave, rotulo, resposta, round(100 * valor / maximo, 1)))

        base_pct = 100 * pontos / maximo
        regras = self.regras_disparadas(trilha_id, respostas)
        ajuste = sum(r.efeito for r in regras)
        final = min(100.0, max(0.0, base_pct + ajuste))

        return ResultadoTrilha(
            id=trilha_id, nome=trilha["nome"], descricao=trilha["descricao"],
            base=round(base_pct, 1), ajuste=round(ajuste, 1), compatibilidade=round(final, 1),
            contribuicoes=contribuicoes, regras=regras,
        )

    def diagnosticar(self, respostas: dict) -> Diagnostico:
        self.validar_respostas(respostas)
        ordem = list(self.base["trilhas"])
        resultados = [self.avaliar_trilha(t, respostas) for t in ordem]

        # Desempate: compatibilidade → percentual-base → ordem do JSON
        ranking = sorted(resultados, key=lambda r: (-r.compatibilidade, -r.base, ordem.index(r.id)))

        alertas = []
        primeiro, segundo = ranking[0], ranking[1]
        aderencia_forte = primeiro.compatibilidade >= LIMIAR_CONFIANCA
        # Trilhas "empatadas" com a primeira (diferença menor que o limiar)
        empatadas = [r for r in ranking if primeiro.compatibilidade - r.compatibilidade < LIMIAR_EMPATE]

        hibrido = aderencia_forte and len(empatadas) >= 2
        baixa_confianca = False
        if hibrido and len(empatadas) == 2:
            diferenca = primeiro.compatibilidade - segundo.compatibilidade
            alertas.append(
                f"Perfil híbrido: {primeiro.nome} e {segundo.nome} ficaram a apenas "
                f"{diferenca:.1f} ponto(s) de distância. As duas trilhas são boas opções; "
                "veja os motivos de cada uma para decidir."
            )
        elif hibrido:
            baixa_confianca = True
            alertas.append(
                f"{len(empatadas)} trilhas ficaram praticamente empatadas no topo "
                f"({', '.join(r.nome for r in empatadas[:4])}{'...' if len(empatadas) > 4 else ''}). "
                "Seu perfil é muito amplo; tente diferenciar mais as respostas para uma "
                "recomendação mais precisa."
            )

        if not aderencia_forte:
            baixa_confianca = True
            alertas.append(
                "Nenhuma trilha passou de 50% de aderência. Suas respostas indicam pouca afinidade "
                "com as áreas avaliadas; o resultado deve ser visto com cautela."
            )
        desvio = statistics.pstdev(r.compatibilidade for r in ranking)
        if desvio < LIMIAR_UNIFORME and not (hibrido and len(empatadas) > 2):
            baixa_confianca = True
            alertas.append(
                "Suas respostas ficaram muito parecidas entre si, então as trilhas obtiveram "
                "pontuações próximas. Tente diferenciar mais o que você gosta do que não gosta."
            )

        return Diagnostico(ranking=ranking, alertas=alertas, hibrido=hibrido, baixa_confianca=baixa_confianca)


def diagnosticar(respostas: dict) -> Diagnostico:
    """Atalho: roda o motor com a base padrão."""
    return MotorInferencia().diagnosticar(respostas)


if __name__ == "__main__":
    exemplo = {
        "comunicacao": 3, "lideranca": 2, "atencao_detalhes": 3, "criatividade": 2,
        "experiencia": "nenhuma", "horas_semana": 10,
        "matematica": 3, "logica": 4, "interfaces": 2, "infraestrutura": 5, "dados": 3,
        "seguranca": 3, "automacao": 5, "nuvem": 4, "mobile": 1, "testes": 2,
        "obj_produto": 2, "obj_infra": 5, "obj_insights": 2, "obj_protecao": 3,
        "obj_qualidade": 3, "obj_negocio": 1, "ambiente": "indiferente", "objetivo": "primeiro_emprego",
    }
    d = diagnosticar(exemplo)
    print(d.tabela().drop(columns="id").to_string(index=False))
    print()
    for i, r in enumerate(d.top3, 1):
        print(f"{i}º {r.nome} — {r.compatibilidade}%")
        for c in r.principais_motivos():
            print(f"    +{c.pontos:>4} {c.rotulo} ({c.resposta})")
        for rg in r.regras:
            print(f"    [{rg.id}] {rg.efeito:+} {rg.motivo}")
    for a in d.alertas:
        print("ALERTA:", a)
