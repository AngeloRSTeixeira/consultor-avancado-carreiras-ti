"""Fase 5 — Testes de robustez e casos limite.  Rode com:  python -m pytest -q"""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from base_conhecimento import (CAMINHO_PADRAO, ErroBaseConhecimento,  # noqa: E402
                               base_padrao, carregar_base, validar_base)
from gaps_roadmap import analisar_gaps, gerar_roadmap  # noqa: E402
from motor_inferencia import MotorInferencia, diagnosticar  # noqa: E402
from personas import CASOS_LIMITE, PERSONAS, perfil  # noqa: E402

CASO = {c["nome"]: c["respostas"] for c in CASOS_LIMITE}


# ------------------------------------------------------------ base de conhecimento
def test_json_externo_carrega_e_e_valido():
    base = carregar_base(CAMINHO_PADRAO)
    assert len(base["trilhas"]) == 10
    assert len(base["regras"]) >= 20


def test_json_com_erro_e_rejeitado():
    base = copy.deepcopy(base_padrao())
    base["trilhas"]["backend"]["pesos"]["pergunta_que_nao_existe"] = 2
    with pytest.raises(ErroBaseConhecimento):
        validar_base(base)


def test_conhecimento_desacoplado_do_codigo(tmp_path):
    """Mudar só o JSON muda o resultado, sem tocar no Python."""
    respostas = perfil(mobile=5, interfaces=5, logica=5, obj_produto=5, ambiente="web")
    assert MotorInferencia().diagnosticar(respostas).vencedora.id == "frontend"

    # Um único peso novo no JSON: "quem prefere web também conta para Mobile"
    base = copy.deepcopy(base_padrao())
    base["trilhas"]["mobile"]["pesos"]["ambiente=web"] = 3
    arquivo = tmp_path / "regras.json"
    arquivo.write_text(json.dumps(base, ensure_ascii=False), encoding="utf-8")

    motor = MotorInferencia(carregar_base(arquivo))
    assert motor.diagnosticar(respostas).vencedora.id == "mobile"


# ------------------------------------------------------------ motor de inferência
@pytest.mark.parametrize("persona", PERSONAS, ids=[p["nome"] for p in PERSONAS])
def test_persona_recebe_trilha_esperada(persona):
    d = diagnosticar(persona["respostas"])
    assert d.vencedora.id == persona["esperado"]
    assert d.vencedora.principais_motivos(), "precisa haver justificativa"


def test_todas_as_trilhas_sao_alcancaveis():
    assert {p["esperado"] for p in PERSONAS} == set(base_padrao()["trilhas"])


def test_top3_ordenado_com_percentuais_validos():
    d = diagnosticar(PERSONAS[0]["respostas"])
    valores = [r.compatibilidade for r in d.top3]
    assert len(d.top3) == 3
    assert valores == sorted(valores, reverse=True)
    assert all(0 <= r.compatibilidade <= 100 for r in d.ranking)


def test_resposta_maior_aumenta_compatibilidade():
    """Monotonicidade: aumentar a afinidade central de uma trilha nunca a prejudica."""
    anterior = -1
    for nota in range(1, 6):
        d = diagnosticar(perfil(padrao=3, seguranca=nota))
        atual = next(r.compatibilidade for r in d.ranking if r.id == "seguranca")
        assert atual >= anterior
        anterior = atual


def test_penalidade_separa_cientista_de_engenheiro_de_dados():
    base = dict(dados=5, logica=4, infraestrutura=4, automacao=4, obj_insights=5)
    assert diagnosticar(perfil(matematica=5, **base)).vencedora.id == "ciencia_dados"
    d = diagnosticar(perfil(matematica=1, **base))
    assert d.vencedora.id == "engenharia_dados"
    cientista = next(r for r in d.ranking if r.id == "ciencia_dados")
    assert "P01" in {rg.id for rg in cientista.regras}


def test_ambiente_separa_devops_de_cloud():
    respostas = CASO["DevOps ou Cloud?"]
    assert diagnosticar(respostas).vencedora.id == "devops"
    assert diagnosticar({**respostas, "ambiente": "nuvem"}).vencedora.id == "cloud"


def test_ambiente_separa_frontend_de_mobile():
    respostas = perfil(interfaces=5, criatividade=5, obj_produto=5, logica=3, mobile=4)
    assert diagnosticar({**respostas, "ambiente": "web"}).vencedora.id == "frontend"
    assert diagnosticar({**respostas, "ambiente": "mobile"}).vencedora.id == "mobile"


def test_resposta_invalida_gera_erro():
    with pytest.raises(ValueError):
        diagnosticar({**perfil(), "matematica": 7})
    with pytest.raises(ValueError):
        diagnosticar({**perfil(), "ambiente": "desktop"})
    respostas = perfil()
    del respostas["logica"]
    with pytest.raises(ValueError):
        diagnosticar(respostas)


# ------------------------------------------------------------ casos limite
def test_perfil_ambiguo_dados_e_web_e_marcado_como_hibrido():
    d = diagnosticar(CASO["Dados e web na mesma medida"])
    assert d.hibrido
    assert {d.ranking[0].id, d.ranking[1].id} == {"frontend", "ciencia_dados"}
    # As duas trilhas empatadas trazem justificativas coerentes
    assert any("dados" in c.caracteristica for c in next(r for r in d.top3 if r.id == "ciencia_dados").contribuicoes)
    assert any("interfaces" in c.caracteristica for c in next(r for r in d.top3 if r.id == "frontend").contribuicoes)


def test_respostas_neutras_geram_baixa_confianca():
    d = diagnosticar(CASO["Tudo neutro (3)"])
    assert d.baixa_confianca
    assert any("parecidas" in a for a in d.alertas)


def test_sem_afinidade_nenhuma_avisa_e_nao_chama_de_hibrido():
    d = diagnosticar(CASO["Tudo mínimo (1)"])
    assert d.baixa_confianca and not d.hibrido
    assert d.vencedora.compatibilidade < 50


def test_gosta_de_tudo_avisa_empate_multiplo():
    d = diagnosticar(CASO["Tudo máximo (5)"])
    assert d.baixa_confianca
    assert any("empatadas" in a for a in d.alertas)


def test_desempate_e_deterministico():
    respostas = CASO["Tudo máximo (5)"]
    primeira = [r.id for r in diagnosticar(respostas).ranking]
    for _ in range(5):
        assert [r.id for r in diagnosticar(respostas).ranking] == primeira


# ------------------------------------------------------------ gaps e roadmap
def test_iniciante_tem_todas_as_lacunas():
    a = analisar_gaps("devops", {})
    assert a.prontidao == 0
    assert a.nivel_atual == "Iniciante"
    assert len(a.lacunas) == len(a.itens)
    assert [g.prioridade for g in a.lacunas] == sorted(g.prioridade for g in a.lacunas)


def test_usuario_completo_nao_tem_lacunas():
    tudo_avancado = {c: 3 for c in base_padrao()["competencias"]}
    a = analisar_gaps("backend", tudo_avancado, experiencia="mais3")
    assert a.prontidao == 100 and not a.lacunas
    assert "Pleno" in a.nivel_atual
    roadmap = gerar_roadmap(a)
    assert roadmap.horas_totais == 0 and roadmap.semanas == 0


def test_roadmap_estima_horas_e_pula_o_que_ja_sabe():
    base = base_padrao()
    a = analisar_gaps("devops", {"linux": 1, "docker": 0, "git": 2})
    roadmap = gerar_roadmap(a, horas_semana=15)
    assert roadmap.horas_totais == sum(g.falta for g in a.lacunas) * base["horas_por_nivel"]
    assert roadmap.semanas == -(-roadmap.horas_totais // 15)
    linux = next(i for e in roadmap.etapas for i in e.itens if i.nome == "Linux")
    assert linux.topicos[0] != base["competencias"]["linux"]["estudar"][0]
    assert roadmap.certificacoes and roadmap.projetos


@pytest.mark.parametrize("objetivo", ["primeiro_emprego", "transicao", "crescer"])
def test_roadmap_para_todas_as_trilhas_e_objetivos(objetivo):
    for trilha in base_padrao()["trilhas"]:
        roadmap = gerar_roadmap(analisar_gaps(trilha, {"programacao": 1}), 8, objetivo)
        assert roadmap.etapas[-1].extras, f"{trilha}: faltam projetos/certificação"
        assert roadmap.dica_objetivo
