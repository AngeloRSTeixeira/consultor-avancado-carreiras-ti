# Fase 1 — Engenharia do Conhecimento e Modelagem JSON

Toda a base de conhecimento fica em [`data/regras_carreiras.json`](../data/regras_carreiras.json). O código Python apenas lê esse arquivo, então dá para mudar pesos, perguntas e regras sem mexer no motor.

## 1. Estrutura do JSON

| Chave | Conteúdo |
|---|---|
| `escala` | Escala Likert de 1 a 5 com os rótulos exibidos ao usuário. |
| `etapas` | As 3 etapas do wizard: Perfil pessoal, Afinidades técnicas e Objetivos de carreira. |
| `perguntas` | Lista de perguntas com `id`, `etapa`, `tipo` (`likert`, `escolha` ou `numero`) e `texto`. |
| `trilhas` | As 10 trilhas. Cada uma tem `nome`, `descricao` e `pesos` (correlação pergunta → trilha, de 1 a 3). |
| `regras` | Regras SE-ENTÃO de **bônus** (sinergias) e **penalidade** (conflitos), com condições, efeito em pontos percentuais e motivo. |

Os campos `competencias`, `requisitos_junior` e `roadmap` são acrescentados na Fase 3.

### Tipos de pergunta

- **likert**: resposta de 1 a 5. Entra no cálculo com intensidade `(resposta − 1) / 4`, ou seja, 1 → 0,0; 3 → 0,5; 5 → 1,0.
- **escolha**: alternativa única. No cálculo, cada opção vira uma característica binária, escrita como `pergunta=opcao` (ex.: `ambiente=web` vale 1 se o usuário escolheu Web).
- **numero**: valor numérico (horas de estudo por semana), usado só no roadmap.

## 2. Matriz de pesos (pergunta × trilha)

Peso 3 = característica central da trilha · 2 = importante · 1 = ajuda.

| Pergunta | Back | Front | C. Dados | Eng. Dados | Segur. | DevOps | Cloud | Mobile | QA | Produto |
|---|---|---|---|---|---|---|---|---|---|---|
| comunicacao | | 1 | 1 | | | | 1 | | 1 | **3** |
| lideranca | | | | | | | 1 | | | **3** |
| atencao_detalhes | | | | | 2 | | | | **3** | |
| criatividade | | **3** | | | | | | 1 | | 1 |
| matematica | 1 | | **3** | 1 | | | | | | |
| logica | **3** | 1 | 1 | 2 | 1 | 1 | | 2 | 1 | |
| interfaces | | **3** | | | | | | 2 | | |
| infraestrutura | 1 | | | 2 | 2 | **3** | 2 | | | |
| dados | 1 | | **3** | **3** | | | | | | 1 |
| seguranca | | | | | **3** | | | | | |
| automacao | 1 | | | 2 | | **3** | 1 | | 1 | |
| nuvem | | | | 1 | | 1 | **3** | | | |
| mobile | | | | | | | | **3** | | |
| testes | | | | | | | | | **3** | |
| obj_produto | 2 | **3** | | | | | | 2 | | 1 |
| obj_infra | | | | 1 | | **3** | 2 | | | |
| obj_insights | | | **3** | 1 | | | | | | |
| obj_protecao | | | | | **3** | | | | | |
| obj_qualidade | | | | | | | | | **3** | |
| obj_negocio | | | | | | | | | | **3** |
| ambiente=web | 1 | 2 | | | | | | | | |
| ambiente=mobile | | | | | | | | **3** | | |
| ambiente=nuvem | | | | | | | 2 | | | |
| ambiente=indiferente | 1 | | | | | | | | | |

## 3. Cálculo da compatibilidade

Para cada trilha *t*:

```
pontos(t)   = Σ peso(t, p) × intensidade(p)
maximo(t)   = Σ pesos de perguntas Likert + maior peso de cada pergunta de escolha
base(t)     = 100 × pontos(t) / maximo(t)
ajustes(t)  = Σ efeito das regras de bônus e penalidade disparadas para t
final(t)    = limitar(base(t) + ajustes(t), 0, 100)
```

Para perguntas de escolha, o máximo conta só a **maior** opção, porque o usuário escolhe uma alternativa só. Assim, o percentual de 100% continua alcançável.

## 4. Regras de bônus e penalidade

As regras tratam as interações que uma soma simples não captura.

**Bônus (sinergias):** B01–B10. Exemplo: `matematica ≥ 4 E dados ≥ 4 → Ciência de Dados +8`.

**Penalidades (perfis conflitantes):** P01–P17. Exemplo: `matematica ≤ 2 → Ciência de Dados −20`.

### Como as regras evitam ambiguidades

| Par confundível | O que separa |
|---|---|
| Ciência × Engenharia de Dados | Matemática alta dá bônus a Ciência (B01) e matemática baixa a penaliza (P01). Dados + infraestrutura dá bônus a Engenharia (B02). |
| DevOps × Cloud | Ambiente "nuvem" ativa B04 (Cloud). Automação + infraestrutura fora da nuvem ativa B03 (DevOps). |
| Front-end × Mobile | Ambiente "mobile" ativa B06 (Mobile) e P14 (penaliza Front-end). |
| Back-end × Front-end | Lógica alta com pouco interesse visual ativa B10 (Back-end). Pouco gosto visual ativa P05 (Front-end). |
| Segurança × DevOps | O peso de `obj_protecao` e a regra B08 puxam para Segurança. `obj_infra` e B03 puxam para DevOps. |

## 5. Tratamento de incerteza

- As respostas são graduais, então a "força" de cada evidência varia de 0 a 1 em vez de ser só verdadeira ou falsa.
- O resultado não é uma única trilha: é um **ranking com percentual de aderência**, e o sistema mostra o Top 3.
- Quando a diferença entre o 1º e o 2º lugar é pequena (menos de 5 pontos), o sistema avisa que o perfil é **híbrido**.
- Quando nenhuma trilha passa de 50%, ou todas ficam muito parecidas, o sistema avisa que a recomendação tem **baixa confiança**.

## 6. Fase 3 — Gaps e roadmap (campos adicionais do JSON)

| Chave | Conteúdo |
|---|---|
| `niveis_conhecimento` | 0 Nenhum · 1 Básico · 2 Intermediário · 3 Avançado. |
| `horas_por_nivel` | Horas de estudo estimadas para subir um nível (30 h). |
| `competencias` | 24 competências técnicas, cada uma com os tópicos de estudo em ordem. |
| `plano_carreira` | Para cada trilha: `junior` (competência → [nível exigido, prioridade 1–3]), `certificacoes` e `projetos` de portfólio. |

**Como a análise funciona:**

1. O usuário informa o nível atual em cada competência.
2. Para a trilha escolhida, o sistema compara o nível atual com o exigido para Júnior. Cada diferença positiva é uma **lacuna** (gap).
3. A **prontidão** é `Σ min(atual, exigido) / Σ exigido`. Ela mostra quanto do caminho até o Júnior já foi percorrido.
4. O **nível atual** é estimado com a prontidão, as lacunas críticas (prioridade alta) e a experiência informada: Iniciante → Em formação → Pronto para Júnior → Júnior → Rumo ao Pleno.
5. O **roadmap** ordena as lacunas por prioridade e tamanho. Ele pula os tópicos que o usuário já domina, estima as horas (`falta × 30 h`) e as semanas (pelas horas semanais informadas), e termina com projetos de portfólio e certificações.
