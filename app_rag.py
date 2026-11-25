import os
import streamlit as st
from motor_rag import (
    init_db_rag,
    indexar_pdf,
    buscar_trechos_relevantes,
    listar_documentos_indexados,
)

st.set_page_config(page_title="Agente RAG — Normas Técnicas & Leis (PDF)", layout="wide")
init_db_rag()

st.title("Agente de IA com RAG — Consulta de Normas Técnicas e Leis em PDF")
st.markdown("Faça upload de **leis, regulamentos ou normas técnicas em PDF** na barra lateral e faça perguntas com **citação exata de página e fonte**.")

with st.sidebar:
    st.header("1. Base de Conhecimento (PDFs)")
    arquivos_pdf = st.file_uploader(
        "Envie um ou mais documentos PDF",
        type=["pdf"],
        accept_multiple_files=True,
        help="Limite recomendado: até 50 MB por arquivo."
    )

    if arquivos_pdf and st.button("Indexar Documentos na Base", type="primary"):
        for arq in arquivos_pdf:
            if arq.size > 50 * 1024 * 1024:
                st.error(f"Arquivo {arq.name} excede 50 MB.")
                continue
            with st.spinner(f"Lendo e indexando {arq.name}..."):
                qtd = indexar_pdf(arq, arq.name)
            st.success(f"**{arq.name}**: {qtd} trechos indexados!")

    st.divider()
    st.subheader("Documentos Ativos no Banco")
    docs = listar_documentos_indexados()
    if docs:
        for nome, total in docs:
            st.caption(f"📄 **{nome}** ({total} trechos)")
    else:
        st.info("Nenhum PDF indexado ainda.")

    st.divider()
    top_k = st.slider("Quantidade de trechos citados por resposta", 1, 8, 4)

# Area principal de consulta
pergunta = st.text_input(
    "Faça sua pergunta técnica ou jurídica sobre os documentos indexados:",
    placeholder="Ex.: Quais são os requisitos de licenciamento ambiental ou prazo de garantia estrutural?"
)

if pergunta:
    resultados = buscar_trechos_relevantes(pergunta, top_k=top_k)
    if not resultados:
        st.warning("Nenhum trecho correspondente foi encontrado nos documentos indexados. Tente usar palavras-chave presentes no PDF.")
    else:
        st.subheader("Evidências Encontradas nos Documentos")
        for i, item in enumerate(resultados, start=1):
            with st.expander(f"Fonte {i}: {item.arquivo} — Página {item.pagina} (Relevância: {item.score*100:.1f}%)", expanded=(i <= 2)):
                st.markdown(f"> {item.texto}")
                st.caption(f"Rastreabilidade: Arquivo `{item.arquivo}` | Página `{item.pagina}` | ID Trecho `#{item.id}`")
