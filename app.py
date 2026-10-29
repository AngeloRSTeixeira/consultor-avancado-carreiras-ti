"""Fase 4 — Interface web em etapas (wizard) com Streamlit.

Execute com:  streamlit run app.py
"""
import plotly.graph_objects as go
import streamlit as st

from base_conhecimento import base_padrao
from gaps_roadmap import analisar_gaps, gerar_roadmap
from motor_inferencia import MotorInferencia

st.set_page_config(page_title="Consultor Avançado de Carreiras em TI", page_icon="🧭", layout="wide")

BASE = base_padrao()
MOTOR = MotorInferencia(BASE)
ESCALA = BASE["escala"]
NIVEIS = BASE["niveis_conhecimento"]
PASSOS = ["Perfil pessoal", "Afinidades técnicas", "Objetivos de carreira", "Resultado"]
LIKERT = list(range(ESCALA["min"], ESCALA["max"] + 1))

# ------------------------------------------------------------------ estado
if "passo" not in st.session_state:
    st.session_state.passo = 0
    st.session_state.respostas = {}
    st.session_state.conhecimentos = {}


def campo(chave: str, padrao, destino: str = "respostas"):
    """Mantém o valor do widget mesmo quando o usuário troca de etapa."""
    k = f"w_{destino}_{chave}"
    if k not in st.session_state:
        st.session_state[k] = st.session_state[destino].get(chave, padrao)
    return k


def guardar(chave: str, valor, destino: str = "respostas"):
    st.session_state[destino][chave] = valor


def ir_para(passo: int):
    """Salva os valores dos widgets da etapa atual antes de trocar de etapa."""
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and k.startswith("w_"):
            _, destino, chave = k.split("_", 2)
            st.session_state[destino][chave] = st.session_state[k]
    st.session_state.passo = passo


def pergunta_widget(p: dict):
    if p["tipo"] == "likert":
        k = campo(p["id"], 3)
        valor = st.select_slider(p["texto"], options=LIKERT, key=k,
                                 format_func=lambda v: f"{v} · {ESCALA['rotulos'][str(v)]}")
    elif p["tipo"] == "escolha":
        opcoes = p["opcoes"]
        k = campo(p["id"], next(iter(opcoes)))
        valor = st.radio(p["texto"], list(opcoes), format_func=opcoes.get, key=k, horizontal=True)
    else:
        k = campo(p["id"], p["padrao"])
        valor = st.slider(p["texto"], p["min"], p["max"], key=k, format="%d h")
    guardar(p["id"], valor)


def perguntas_da_etapa(etapa: int):
    return [p for p in BASE["perguntas"] if p["etapa"] == etapa]


def quebrar(texto: str, largura: int = 16) -> str:
    """Quebra nomes longos em linhas para caberem no gráfico de radar."""
    linhas, atual = [], ""
    for palavra in texto.split():
        if atual and len(atual) + len(palavra) + 1 > largura:
            linhas.append(atual)
            atual = palavra
        else:
            atual = f"{atual} {palavra}".strip()
    return "<br>".join(linhas + [atual])


def navegacao(anterior: int | None, proximo: int, rotulo_proximo: str = "Avançar →"):
    c1, _, c2 = st.columns([1, 3, 1])
    if anterior is not None:
        c1.button("← Voltar", on_click=ir_para, args=(anterior,), width="stretch")
    c2.button(rotulo_proximo, on_click=ir_para, args=(proximo,), type="primary", width="stretch")


# ------------------------------------------------------------------ cabeçalho
st.title("🧭 Consultor Avançado de Carreiras em TI")
st.caption("Sistema especialista com pontuação ponderada e tratamento de incerteza. "
           "Responda em uma escala de 1 a 5. Não existem respostas certas.")

passo = st.session_state.passo
st.progress((passo + 1) / len(PASSOS), text=f"Passo {passo + 1} de {len(PASSOS)}: {PASSOS[passo]}")

# ------------------------------------------------------------------ passos
if passo == 0:
    st.subheader("Passo 1 · Perfil pessoal")
    for p in perguntas_da_etapa(1):
        pergunta_widget(p)
    navegacao(None, 1)

elif passo == 1:
    st.subheader("Passo 2 · Afinidades técnicas")
    st.write("Quanto você gosta de cada assunto?")
    col_a, col_b = st.columns(2)
    for i, p in enumerate(perguntas_da_etapa(2)):
        with (col_a if i % 2 == 0 else col_b):
            pergunta_widget(p)

    st.subheader("Seus conhecimentos atuais")
    st.write("Informe seu nível hoje. Isso é usado para calcular o que falta até o nível Júnior.")
    niveis = [int(n) for n in NIVEIS]
    col_a, col_b, col_c = st.columns(3)
    for i, (sid, comp) in enumerate(BASE["competencias"].items()):
        with (col_a, col_b, col_c)[i % 3]:
            k = campo(sid, 0, "conhecimentos")
            valor = st.select_slider(comp["nome"], options=niveis, key=k,
                                     format_func=lambda v: NIVEIS[str(v)])
            guardar(sid, valor, "conhecimentos")
    navegacao(0, 2)

elif passo == 2:
    st.subheader("Passo 3 · Objetivos de carreira")
    for p in perguntas_da_etapa(3):
        pergunta_widget(p)
    navegacao(1, 3, "Ver meu resultado ✓")

# ------------------------------------------------------------------ resultado
else:
    respostas = st.session_state.respostas
    try:
        diag = MOTOR.diagnosticar(respostas)
    except ValueError as erro:
        st.error(f"Faltam respostas: {erro}. Volte às etapas anteriores.")
        st.button("← Voltar ao início", on_click=ir_para, args=(0,))
        st.stop()

    for alerta in diag.alertas:
        st.warning(alerta, icon="⚠️")

    st.subheader("Top 3 trilhas compatíveis")
    medalhas = ["🥇", "🥈", "🥉"]
    for col, medalha, r in zip(st.columns(3), medalhas, diag.top3):
        with col.container(border=True):
            st.markdown(f"#### {medalha} {r.nome}")
            st.metric("Compatibilidade", f"{r.compatibilidade:.0f}%",
                      delta=f"{r.ajuste:+.0f} pts de regras" if r.ajuste else None)
            st.caption(r.descricao)

    aba_graf, aba_motivos, aba_gaps, aba_roadmap = st.tabs(
        ["📊 Compatibilidade", "🧠 Por que essas trilhas?", "🧩 Lacunas (gaps)", "🗺️ Roadmap"])

    with aba_graf:
        tabela = diag.tabela()
        c1, c2 = st.columns(2)
        with c1:
            nomes = [quebrar(n) for n in tabela["Trilha"]]
            nomes.append(nomes[0])
            valores = list(tabela["Compatibilidade (%)"]) + [tabela["Compatibilidade (%)"].iloc[0]]
            radar = go.Figure(go.Scatterpolar(r=valores, theta=nomes, fill="toself", name="Compatibilidade"))
            radar.update_layout(polar=dict(radialaxis=dict(range=[0, 100]),
                                           angularaxis=dict(tickfont=dict(size=11))),
                                showlegend=False, margin=dict(l=90, r=90, t=40, b=40), height=440)
            st.plotly_chart(radar, width="stretch")
        with c2:
            ordenada = tabela.sort_values("Posição", ascending=False)  # mantém a ordem do ranking
            cores = ["#2e7d32" if p <= 3 else "#90a4ae" for p in ordenada["Posição"]]
            barras = go.Figure(go.Bar(x=ordenada["Compatibilidade (%)"], y=ordenada["Trilha"],
                                      orientation="h", marker_color=cores,
                                      text=[f"{v:.0f}%" for v in ordenada["Compatibilidade (%)"]]))
            barras.update_layout(xaxis=dict(range=[0, 100], title="%"), height=420,
                                 margin=dict(l=10, r=10, t=30, b=30))
            st.plotly_chart(barras, width="stretch")
        st.dataframe(tabela.drop(columns="id"), hide_index=True, width="stretch")
        st.caption("Base = soma ponderada das respostas. Ajustes = regras de bônus e penalidade. "
                   "Compatibilidade = base + ajustes, limitada entre 0 e 100.")

    with aba_motivos:
        for medalha, r in zip(medalhas, diag.top3):
            with st.expander(f"{medalha} {r.nome}: {r.compatibilidade:.0f}%", expanded=r is diag.vencedora):
                st.markdown("**Respostas que mais contribuíram:**")
                for c in r.principais_motivos():
                    st.markdown(f"- {c.rotulo} — resposta **{c.resposta}** → +{c.pontos:.1f} pts")
                if r.regras:
                    st.markdown("**Regras disparadas:**")
                    for rg in r.regras:
                        icone = "🟢" if rg.tipo == "bonus" else "🔴"
                        st.markdown(f"- {icone} **{rg.id}** ({rg.efeito:+.0f}) — {rg.motivo}")
                else:
                    st.caption("Nenhuma regra de bônus ou penalidade disparou para esta trilha.")

    trilhas = {r.id: r.nome for r in diag.ranking}
    with aba_gaps:
        escolhida = st.selectbox("Analisar lacunas para a trilha:", list(trilhas),
                                 format_func=trilhas.get, key="trilha_escolhida")
        analise = analisar_gaps(escolhida, st.session_state.conhecimentos, respostas["experiencia"], BASE)
        c1, c2 = st.columns(2)
        c1.metric("Prontidão para o nível Júnior", f"{analise.prontidao:.0f}%")
        c2.metric("Nível estimado nesta trilha", analise.nivel_atual)
        st.progress(analise.prontidao / 100)
        st.dataframe(analise.tabela(NIVEIS), hide_index=True, width="stretch")

    with aba_roadmap:
        escolhida = st.session_state.trilha_escolhida
        analise = analisar_gaps(escolhida, st.session_state.conhecimentos, respostas["experiencia"], BASE)
        roadmap = gerar_roadmap(analise, respostas["horas_semana"], respostas["objetivo"], BASE)
        st.markdown(f"### Plano de ação: {trilhas[escolhida]}")
        st.caption("Para ver o roadmap de outra trilha, troque a escolha na aba **Lacunas (gaps)**.")
        if roadmap.horas_totais:
            st.info(f"Estimativa: **{roadmap.horas_totais} horas** de estudo, cerca de "
                    f"**{roadmap.semanas} semanas** com {respostas['horas_semana']} h por semana.")
        else:
            st.success("Você já atende a todas as competências do nível Júnior nesta trilha! "
                       "Foque no portfólio e nas certificações.")
        for etapa in roadmap.etapas:
            titulo = etapa.titulo + (f" · {etapa.horas} h" if etapa.horas else "")
            with st.expander(titulo, expanded=True):
                st.caption(etapa.descricao)
                for item in etapa.itens:
                    st.markdown(f"**{item.nome}** ({item.de} → {item.para}, ~{item.horas} h)")
                    st.markdown("\n".join(f"  - {t}" for t in item.topicos))
                for extra in etapa.extras:
                    st.markdown(f"- {extra}")
        st.markdown("#### Certificações sugeridas")
        for c in roadmap.certificacoes:
            st.markdown(f"- **{c['momento']}:** {c['nome']}")
        st.markdown("#### Dica para o seu objetivo")
        st.write(roadmap.dica_objetivo)

    st.divider()
    c1, c2 = st.columns(2)
    c1.button("← Revisar respostas", on_click=ir_para, args=(0,), width="stretch")
    if c2.button("Recomeçar do zero", width="stretch"):
        st.session_state.clear()
        st.rerun()
