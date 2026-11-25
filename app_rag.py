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

st.set_page_config(page_title="Agente RAG — Normas Técnicas & Leis (PDF)", layout="wide")
init_db_rag()

st.title("Agente de IA com RAG — Consulta de Normas Técnicas e Leis em PDF")
st.markdown("Pesquise em **normas técnicas, contratos ou leis em PDF** com síntese generativa auditada (**`[Arquivo, Página X]`**), destaque de palavras-chave e parecer em PDF.")

with st.sidebar:
    st.header("1. Cérebro Generativo (LLM)")
    provedor = st.selectbox(
        "Modo de Resposta:",
        ["Apenas Busca Extrativa (Sem API)", "Google Gemini", "OpenAI", "Ollama Local (Offline)"],
        index=0
    )

    api_key = ""
    modelo = ""
    if provedor == "Google Gemini":
        api_key = st.text_input("Chave API Google Gemini", type="password", help="Mantida apenas na memória RAM desta sessão.")
        modelo = st.selectbox("Modelo Gemini", ["gemini-2.5-flash", "gemini-2.5-pro"], index=0)
    elif provedor == "OpenAI":
        api_key = st.text_input("Chave API OpenAI", type="password", help="Mantida apenas na memória RAM desta sessão.")
        modelo = st.selectbox("Modelo OpenAI", ["gpt-4o-mini", "gpt-4o"], index=0)
    elif provedor == "Ollama Local (Offline)":
        modelo = st.text_input("Nome do Modelo no Ollama", value="llama3.2", help="Ex.: llama3.2, qwen2.5, mistral")

    st.divider()
    st.header("2. Base de Conhecimento (PDFs)")
    arquivos_pdf = st.file_uploader("Envie um ou mais documentos PDF", type=["pdf"], accept_multiple_files=True)

    if arquivos_pdf and st.button("Indexar Documentos na Base", type="primary"):
        for arq in arquivos_pdf:
            try:
                with st.spinner(f"Lendo e indexando {arq.name}..."):
                    qtd = indexar_pdf(arq, arq.name)
                st.success(f"**{arq.name}**: {qtd} trechos indexados!")
            except ValueError as e:
                st.error(str(e))

    st.divider()
    st.subheader("3. Filtro e Gestão de Normas")
    docs = listar_documentos_indexados()
    nomes_docs = [list(d).pop(0) for d in docs]

    if docs:
        filtro_selecionado = st.selectbox("Filtrar pesquisa por norma:", ["Todos os Documentos"] + nomes_docs)
        for nome, total in docs:
            st.caption(f"📄 **{nome}** ({total} trechos)")
        with st.expander("Remover documento da base"):
            doc_remover = st.selectbox("Escolha o PDF para excluir:", nomes_docs)
            if st.button("Excluir PDF Selecionado"):
                remover_documento(doc_remover)
                st.rerun()
    else:
        filtro_selecionado = "Todos os Documentos"
        st.info("Nenhum PDF indexado ainda.")

    st.divider()
    top_k = st.slider("Trechos enviados ao contexto", 1, 8, 4)

pergunta = st.text_input(
    "Faça sua pergunta técnica ou jurídica sobre os documentos:",
    placeholder="Ex.: Quais são os requisitos de licenciamento ambiental, taxas ou prazos de garantia?"
)

if pergunta:
    resultados = buscar_trechos_relevantes(pergunta, top_k=top_k, filtro_arquivo=filtro_selecionado)
    if not resultados:
        st.warning("Nenhum trecho correspondente encontrado. Tente usar termos técnicos presentes no documento.")
    else:
        sintese_ia = ""
        if provedor != "Apenas Busca Extrativa (Sem API)":
            with st.spinner(f"Redigindo parecer técnico fundamentado via {provedor}..."):
                sintese_ia = gerar_sintese_llm(pergunta, resultados, provedor, api_key, modelo)
            st.subheader("Parecer Técnico Sintetizado (Auditado por Fontes)")
            st.info(sintese_ia)

        pdf_parecer = gerar_pdf_consulta_rag(pergunta, filtro_selecionado, resultados, sintese_ia)
        st.download_button(
            label="Baixar Parecer Técnico Completo (PDF)",
            data=pdf_parecer,
            file_name="Parecer_Consulta_Normas_RAG.pdf",
            mime="application/pdf",
            type="primary"
        )

        st.subheader(f"Evidências Originais nos Documentos ({len(resultados)} trechos)")
        for i, item in enumerate(resultados, start=1):
            html_destacado = destacar_termos_html(item.texto, pergunta)
            with st.expander(f"Fonte {i}: {item.arquivo} — Página {item.pagina} (Relevância: {item.score*100:.1f}%)", expanded=(i <= 2)):
                st.markdown(html_destacado, unsafe_allow_html=True)
                st.caption(f"Rastreabilidade: Arquivo `{item.arquivo}` | Página `{item.pagina}` | ID Trecho `#{item.id}`")
