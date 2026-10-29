"""Fase 5 — Personas e casos limite usados para testar a robustez do sistema.

Execute ``python personas.py`` para ver o relatório completo no terminal.
"""
from motor_inferencia import diagnosticar

LIKERT = ["comunicacao", "lideranca", "atencao_detalhes", "criatividade",
          "matematica", "logica", "interfaces", "infraestrutura", "dados", "seguranca",
          "automacao", "nuvem", "mobile", "testes",
          "obj_produto", "obj_infra", "obj_insights", "obj_protecao", "obj_qualidade", "obj_negocio"]


def perfil(padrao: int = 2, ambiente: str = "indiferente", experiencia: str = "nenhuma",
           objetivo: str = "primeiro_emprego", horas_semana: int = 10, **notas) -> dict:
    """Monta um conjunto de respostas: tudo com a nota ``padrao``, exceto o que for informado."""
    respostas = {p: padrao for p in LIKERT}
    respostas.update(notas)
    respostas.update(ambiente=ambiente, experiencia=experiencia, objetivo=objetivo, horas_semana=horas_semana)
    return respostas


# Personas com uma trilha claramente esperada (as 4 primeiras seguem o perfil do enunciado anterior)
PERSONAS = [
    {"nome": "Ana — analítica", "esperado": "ciencia_dados",
     "respostas": perfil(matematica=5, dados=5, logica=4, obj_insights=5, comunicacao=3)},
    {"nome": "Bruno — infra/segurança", "esperado": "seguranca",
     "respostas": perfil(seguranca=5, infraestrutura=4, atencao_detalhes=5, obj_protecao=5, logica=3)},
    {"nome": "Carla — visual/front-end", "esperado": "frontend",
     "respostas": perfil(interfaces=5, criatividade=5, obj_produto=5, logica=3, comunicacao=4, ambiente="web")},
    {"nome": "Diego — negócios/produto", "esperado": "produto",
     "respostas": perfil(comunicacao=5, lideranca=5, obj_negocio=5, criatividade=3, dados=3)},
    {"nome": "Eduardo — construtor de APIs", "esperado": "backend",
     "respostas": perfil(logica=5, matematica=3, dados=3, obj_produto=4, interfaces=1, ambiente="web")},
    {"nome": "Fernanda — pipelines de dados", "esperado": "engenharia_dados",
     "respostas": perfil(dados=5, infraestrutura=4, automacao=4, logica=4, matematica=2, obj_insights=3, obj_infra=3)},
    {"nome": "Gustavo — automação de deploys", "esperado": "devops",
     "respostas": perfil(automacao=5, infraestrutura=5, obj_infra=5, logica=3, nuvem=3)},
    {"nome": "Helena — arquiteta de nuvem", "esperado": "cloud",
     "respostas": perfil(nuvem=5, infraestrutura=4, obj_infra=4, comunicacao=4, lideranca=3, ambiente="nuvem")},
    {"nome": "Igor — apps", "esperado": "mobile",
     "respostas": perfil(mobile=5, interfaces=4, logica=4, obj_produto=4, ambiente="mobile")},
    {"nome": "Júlia — caçadora de bugs", "esperado": "qa",
     "respostas": perfil(testes=5, atencao_detalhes=5, obj_qualidade=5, automacao=3, logica=3)},
]

# Casos limite: perfis ambíguos, uniformes ou extremos
CASOS_LIMITE = [
    {"nome": "Dados e web na mesma medida",
     "descricao": "Gosta tanto de analisar dados quanto de construir interfaces web.",
     "respostas": perfil(matematica=4, dados=5, obj_insights=5, interfaces=5, criatividade=4,
                         obj_produto=5, logica=4, ambiente="web")},
    {"nome": "DevOps ou Cloud?",
     "descricao": "Automação e nuvem com a mesma intensidade, ambiente indiferente.",
     "respostas": perfil(automacao=5, infraestrutura=5, nuvem=5, obj_infra=5)},
    {"nome": "Tudo neutro (3)", "descricao": "Respondeu 3 em todas as perguntas.",
     "respostas": perfil(padrao=3)},
    {"nome": "Tudo mínimo (1)", "descricao": "Nenhuma afinidade com nada.",
     "respostas": perfil(padrao=1)},
    {"nome": "Tudo máximo (5)", "descricao": "Gosta de absolutamente tudo.",
     "respostas": perfil(padrao=5)},
]


def relatorio():
    acertos = 0
    print("=== PERSONAS ===")
    for p in PERSONAS:
        d = diagnosticar(p["respostas"])
        ok = d.vencedora.id == p["esperado"]
        acertos += ok
        top = " | ".join(f"{r.nome} {r.compatibilidade:.0f}%" for r in d.top3)
        print(f"[{'OK ' if ok else 'ERRO'}] {p['nome']:<32} {top}")
    print(f"\nAcurácia: {acertos}/{len(PERSONAS)}\n")

    print("=== CASOS LIMITE ===")
    for c in CASOS_LIMITE:
        d = diagnosticar(c["respostas"])
        top = " | ".join(f"{r.nome} {r.compatibilidade:.0f}%" for r in d.top3)
        print(f"- {c['nome']}: {top}")
        for a in d.alertas:
            print(f"    ⚠ {a}")
        if not d.alertas:
            print("    (sem alertas)")
    return acertos == len(PERSONAS)


if __name__ == "__main__":
    relatorio()
