import streamlit as st
from motor_rag import (
    init_db_rag,
    indexar_pdf,
    remover_documento,
    buscar_trechos_relevantes,
    destacar_termos_html,
    listar_documentos_indexados,
)
from relatorio_rag_pdf import gerar_pdf_consulta_rag
from cerebro_llm import gerar_sintese_llm

st.set_page_config(
    page_title="Acervo Técnico RAG — Estante Inteligente",
    page_icon="📚",
    layout="wide",
)
init_db_rag()

# Estilo customizado: Estante de Livros High-Tech (Clean & Sofisticado)
st.markdown("""
<style>
    /* Fundo azul claro suave em toda a aplicacao */
    .stApp {
        background-color: #E0F2FE;
        color: #0F172A;
    }
    section[data-testid="stSidebar"] {
        background-color: #F0F9FF;
        border-right: 1px solid #BAE6FD;
    }
    /* Garante contraste alto nas letras das abas (inativas e ativas) */
    button[data-baseweb="tab"] {
        background-color: #BAE6FD !important;
        color: #0F172A !important;
        border-radius: 8px 8px 0 0 !important;
        padding: 0.6rem 1.2rem !important;
        margin-right: 4px !important;
        font-weight: 600 !important;
    }
    button[data-baseweb="tab"] p {
        color: #0F172A !important;
        font-size: 0.98rem !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #0284C7 !important;
        border-bottom: 3px solid #0F172A !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] p {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }
    /* Textos gerais, labels e titulos em azul-marinho escuro */
    .stMarkdown, .stTextInput label, .stSelectbox label, .stSlider label, h1, h2, h3, h4 {
        color: #0F172A !important;
    }
    .shelf-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%);
        padding: 1.6rem 2rem;
        border-radius: 14px;
        border-left: 6px solid #38BDF8;
        color: #FFFFFF;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.15);
    }
    .shelf-header h1 {
        color: #FFFFFF !important;
        font-size: 1.75rem;
        margin: 0 0 0.3rem 0;
        font-weight: 700;
    }
    .shelf-header p {
        color: #E0F2FE !important;
        margin: 0;
        font-size: 0.95rem;
    }
    .book-card {
        background: #FFFFFF;
        border: 1px solid #7DD3FC;
        border-left: 5px solid #0284C7;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.06);
    }
    .book-title {
        font-weight: 700;
        color: #0F172A;
        font-size: 1.0rem;
        margin-bottom: 0.25rem;
    }
    .book-meta {
        color: #334155;
        font-size: 0.85rem;
    }
    .ai-verdict {
        background: #FFFFFF;
        border: 1px solid #7DD3FC;
        border-left: 5px solid #0284C7;
        border-radius: 10px;
        padding: 1.2rem 1.4rem;
        color: #0F172A;
        line-height: 1.6;
        box-shadow: 0 2px 8px rgba(2, 132, 199, 0.08);
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="shelf-header">
    <h1>📚 Acervo Técnico RAG — Estante Inteligente de Normas & Leis</h1>
    <p>Consulta auditável em documentos PDF com rastreabilidade de página e síntese generativa 100% offline via Ollama.</p>
</div>
""", unsafe_allow_html=True)

docs = listar_documentos_indexados()
nomes_docs = [list(d).pop(0) for d in docs]

with st.sidebar:
    st.markdown("### ⚙️ Motor de Inteligência")
    provedor = st.selectbox(
        "Provedor LLM:",
        ["Ollama Local (Offline)", "Apenas Busca Extrativa (Sem API)", "Google Gemini", "OpenAI"],
        index=0,
    )

    api_key = ""
    modelo = "qwen2.5:1.5b"
    if provedor == "Ollama Local (Offline)":
        modelo = st.text_input("Modelo Local (Ollama)", value="qwen2.5:1.5b")
        st.caption("🔒 Execução 100% local em `127.0.0.1:11434`.")
    elif provedor == "Google Gemini":
        api_key = st.text_input("Chave API Gemini", type="password")
        modelo = st.selectbox("Modelo", ["gemini-2.5-flash", "gemini-2.5-pro"])
    elif provedor == "OpenAI":
        api_key = st.text_input("Chave API OpenAI", type="password")
        modelo = st.selectbox("Modelo", ["gpt-4o-mini", "gpt-4o"])

    st.divider()
    st.markdown("### 🎯 Escopo da Pesquisa")
    opcoes_filtro = ["Todos os Documentos"] + nomes_docs
    filtro_selecionado = st.selectbox("Filtrar na estante:", opcoes_filtro)
    top_k = st.slider("Trechos por consulta", 1, 8, 4)

    st.divider()
    total_trechos_geral = sum(list(d).pop(1) for d in docs) if docs else 0
    c_s1, c_s2 = st.columns(2)
    c_s1.metric("Volumes", len(docs))
    c_s2.metric("Trechos", total_trechos_geral)

aba1, aba2, aba3 = st.tabs([
    "🔍 1. Pesquisa & Parecer IA",
    "📚 2. Estante Digital (Acervo)",
    "📥 3. Catalogar & Gerir PDFs",
])

with aba1:
    pergunta = st.text_input(
        "Qual norma, artigo, requisito técnico ou cláusula deseja consultar?",
        placeholder="Ex.: Quais são os prazos de garantia, exigências ambientais ou critérios de dimensionamento?",
    )

    if pergunta:
        resultados = buscar_trechos_relevantes(pergunta, top_k=top_k, filtro_arquivo=filtro_selecionado)
        if not resultados:
            st.warning("Nenhum trecho correspondente encontrado no escopo selecionado. Tente termos presentes na norma.")
        else:
            sintese_ia = ""
            if provedor != "Apenas Busca Extrativa (Sem API)":
                with st.spinner(f"Consultando estante e redigindo parecer via {provedor} ({modelo})..."):
                    sintese_ia = gerar_sintese_llm(pergunta, resultados, provedor, api_key, modelo)
                st.markdown("#### 🧠 Parecer Técnico Sintetizado (Auditado por Fontes)")
                st.markdown(f"<div class='ai-verdict'>{sintese_ia.replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
                st.write("")

            pdf_parecer = gerar_pdf_consulta_rag(pergunta, filtro_selecionado, resultados, sintese_ia)
            st.download_button(
                label="📄 Baixar Parecer Técnico Completo (PDF)",
                data=pdf_parecer,
                file_name="Parecer_Tecnico_Estante_RAG.pdf",
                mime="application/pdf",
                type="primary",
            )

            st.divider()
            st.markdown(f"#### 📑 Evidências Originais Recuperadas ({len(resultados)} trechos)")
            for i, item in enumerate(resultados, start=1):
                html_destacado = destacar_termos_html(item.texto, pergunta)
                with st.expander(
                    f"Fonte {i} | 📘 {item.arquivo} — Página {item.pagina} (Relevância: {item.score*100:.1f}%)",
                    expanded=(i <= 2),
                ):
                    st.markdown(html_destacado, unsafe_allow_html=True)
                    st.caption(f"Rastreabilidade: Arquivo `{item.arquivo}` • Página `{item.pagina}` • Registro `#{item.id}`")

with aba2:
    st.markdown("#### 📚 Acervo Digital Catalogado")
    if not docs:
        st.info("Sua estante está vazia. Acesse a aba **3. Catalogar & Gerir PDFs** para adicionar normas e leis.")
    else:
        cols = st.columns(3)
        for idx, doc_info in enumerate(docs):
            nome_arq = list(doc_info).pop(0)
            qtd_ch = list(doc_info).pop(1)
            with cols[idx % 3]:
                st.markdown(f"""
                <div class="book-card">
                    <div class="book-title">📘 {nome_arq}</div>
                    <div class="book-meta">Fragmentos indexados: <b>{qtd_ch} trechos</b><br>Status: Protegido (SQLite 0600)</div>
                </div>
                """, unsafe_allow_html=True)

with aba3:
    col_up, col_del = st.columns(2)
    with col_up:
        st.markdown("#### 📥 Catalogar Novos Documentos (PDF)")
        arquivos_pdf = st.file_uploader("Selecione arquivos PDF técnicos ou jurídicos", type=["pdf"], accept_multiple_files=True)
        if arquivos_pdf and st.button("Indexar na Estante Digital", type="primary"):
            for arq in arquivos_pdf:
                try:
                    with st.spinner(f"Catalogando {arq.name}..."):
                        qtd = indexar_pdf(arq, arq.name)
                    st.success(f"**{arq.name}** catalogado com **{qtd} trechos**!")
                except ValueError as e:
                    st.error(str(e))
            st.rerun()

    with col_del:
        st.markdown("#### 🗂️ Remover Documento do Acervo")
        if nomes_docs:
            doc_remover = st.selectbox("Selecione o volume para remover:", nomes_docs)
            if st.button("Remover Volume Selecionado"):
                remover_documento(doc_remover)
                st.warning(f"Volume `{doc_remover}` removido da estante.")
                st.rerun()
        else:
            st.caption("Nenhum volume disponível para remoção.")
