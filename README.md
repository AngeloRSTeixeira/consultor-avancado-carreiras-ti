# 🧭 Consultor Avançado de Carreiras em TI

Sistema Especialista baseado em regras com **tratamento de incerteza** e **pontuação ponderada**, em Python. Ele analisa o perfil do usuário a partir de respostas graduais (escala de 1 a 5) e entrega:

- um **ranking de compatibilidade (%)** com as 10 trilhas de TI e o **Top 3**;
- a **justificativa** de cada recomendação (respostas que mais pesaram e regras disparadas);
- a **análise de lacunas** (*skill gaps*) até o nível Júnior;
- um **roadmap personalizado**, com o que estudar primeiro, tempo estimado, certificações e projetos de portfólio.

> Trabalho da disciplina de Inteligência Artificial — Ciência da Computação, UNIPAC Barbacena.
>
> **Aluno:** Angelo Ricardo de Souza Teixeira · **Professor:** Felipe Roncalli de Paula Carneiro

## Trilhas avaliadas

Back-end · Front-end/UX · Ciência de Dados · Engenharia de Dados · Cibersegurança · DevOps/SRE · Cloud Architecture · Mobile · QA · Product Management

## Arquitetura

```
 data/regras_carreiras.json  ─►  base_conhecimento.py  ─►  motor_inferencia.py  ─►  gaps_roadmap.py
   (conhecimento: perguntas,       (carrega e valida        (pontuação ponderada,    (lacunas até o Júnior,
    pesos, regras, roadmap)         o JSON)                  regras, Top 3)           roadmap e portfólio)
                                                                     │
                                                                     ▼
                                                                  app.py  (interface Streamlit em etapas)
```

**A base de conhecimento não fica no código.** Perguntas, pesos, as 27 regras de bônus e penalidade, competências, requisitos do nível Júnior, certificações e projetos ficam todos em [`data/regras_carreiras.json`](data/regras_carreiras.json). Para mudar o comportamento do sistema, basta editar esse arquivo. Um dos testes automatizados prova isso.

### Motor de inferência (pontuação ponderada + regras)

1. Cada resposta vira uma **intensidade** entre 0 e 1 (1 → 0,0 · 3 → 0,5 · 5 → 1,0).
2. Para cada trilha: `pontos = Σ peso × intensidade`, e `base% = 100 × pontos ÷ máximo possível`.
3. **Regras SE-ENTÃO** lidas do JSON somam ou subtraem pontos percentuais:
   - **10 regras de bônus** (sinergias). Ex.: `matemática ≥ 4 E dados ≥ 4 → Ciência de Dados +8`.
   - **17 regras de penalidade** (perfis conflitantes). Ex.: `matemática ≤ 2 → Ciência de Dados −20`.
4. `compatibilidade = base% + ajustes`, limitada entre 0 e 100. As trilhas são ordenadas e o Top 3 é exibido.
5. **Tratamento de incerteza:** o sistema avisa quando o perfil é **híbrido** (1º e 2º lugar a menos de 5 pontos), quando **várias trilhas empatam** no topo, quando **nenhuma passa de 50%** e quando as respostas são **uniformes demais**.

O detalhamento completo, com a matriz de pesos, fica em [`docs/modelagem_conhecimento.md`](docs/modelagem_conhecimento.md).

### Análise de gaps e roadmap

O usuário informa o nível atual em 24 competências (Nenhum, Básico, Intermediário ou Avançado). Para a trilha escolhida, o sistema:

- compara o nível atual com o exigido para Júnior e lista as **lacunas por prioridade**;
- calcula a **prontidão** (% do caminho já percorrido) e estima o **nível atual** (Iniciante → Em formação → Pronto para Júnior → Júnior → Rumo ao Pleno);
- monta o **roadmap em etapas**: fundamentos essenciais, competências complementares, e portfólio + certificação. Ele mostra os tópicos de estudo (pulando o que a pessoa já sabe), as horas estimadas e as semanas, de acordo com as horas semanais disponíveis.

## Estrutura do repositório

```
consultor-avancado-carreiras-ti/
├── app.py                        # Interface web em etapas (Streamlit)
├── base_conhecimento.py          # Carrega e valida o JSON
├── motor_inferencia.py           # Pontuação ponderada, regras e Top 3
├── gaps_roadmap.py               # Lacunas, nível estimado e roadmap
├── personas.py                   # Personas e casos limite (relatório no terminal)
├── data/
│   └── regras_carreiras.json     # Base de conhecimento
├── docs/
│   └── modelagem_conhecimento.md # Fase 1: modelagem e matriz de pesos
├── tests/
│   └── test_sistema.py           # 31 testes automatizados (pytest)
└── requirements.txt
```

## Instalação

Requer **Python 3.10 ou superior**.

```bash
git clone https://github.com/AngeloRSTeixeira/consultor-avancado-carreiras-ti.git
cd consultor-avancado-carreiras-ti

# (opcional) ambiente virtual
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate

pip install -r requirements.txt
```

## Execução

Interface web:

```bash
streamlit run app.py
```

O navegador abre em `http://localhost:8501`. O fluxo tem três passos (**Perfil pessoal → Afinidades técnicas → Objetivos de carreira**) e depois a tela de resultado, com quatro abas: gráficos de radar e barras, justificativas, lacunas e roadmap.

Relatório das personas e casos limite no terminal:

```bash
python personas.py
```

Testes automatizados:

```bash
python -m pytest -q
```

Também dá para rodar cada módulo sozinho (`python motor_inferencia.py`, `python gaps_roadmap.py`) para ver um exemplo.

## Testes de robustez (Fase 5)

**Personas:** 10 perfis, um para cada trilha. Resultado: **10/10 acertos**.

| Persona | Trilha recomendada | Compatibilidade |
|---|---|---|
| Ana — analítica | Ciência de Dados | 100% |
| Bruno — infra/segurança | Cibersegurança | 99% |
| Carla — visual/front-end | Front-end & UI/UX | 100% |
| Diego — negócios/produto | Product Management | 95% |
| Eduardo — construtor de APIs | Back-end | 76% |
| Fernanda — pipelines de dados | Engenharia de Dados | 77% |
| Gustavo — automação de deploys | DevOps & SRE | 97% |
| Helena — arquiteta de nuvem | Cloud Architecture | 87% |
| Igor — apps | Mobile | 93% |
| Júlia — caçadora de bugs | QA | 93% |

**Casos limite:**

| Caso | Comportamento do sistema |
|---|---|
| Gosta igualmente de dados e de web | Front-end 94% × Ciência de Dados 92%: **avisa que o perfil é híbrido** e mostra a justificativa de cada uma. |
| Automação + nuvem, ambiente indiferente | DevOps vence. Ao trocar o ambiente para "nuvem", Cloud passa a vencer (regras B03/B04). |
| Respondeu 3 em tudo | Avisa que as respostas estão **uniformes demais**. |
| Respondeu 1 em tudo | Avisa que **nenhuma trilha passou de 50%** e não chama o resultado de "híbrido". |
| Respondeu 5 em tudo | Avisa que **7 trilhas empataram no topo** e pede respostas mais diferenciadas. |

Os testes também conferem que o desempate é determinístico, que aumentar uma afinidade nunca reduz a compatibilidade da trilha, que respostas inválidas e JSON inconsistente são rejeitados, e que o roadmap funciona para todas as trilhas e objetivos.

> **Observação:** as certificações sugeridas no JSON refletem o mercado no momento em que o trabalho foi feito. Confira no site de cada emissor se continuam disponíveis.

## Tecnologias

- Python 3.10+
- Pandas (tabelas do ranking e dos gaps)
- Streamlit (interface web em etapas)
- Plotly (gráficos de radar e barras)
- pytest (testes)
