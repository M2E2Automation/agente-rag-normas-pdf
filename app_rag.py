from agente_consultor import conversar_com_agente, carregar_perfis_prompts, PASTA_PROMPTS
from importador_lote import varrer_e_catalogar
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
if 'chat_rag' not in st.session_state: st.session_state['chat_rag'] = list()
if 'ultimos_trechos' not in st.session_state: st.session_state['ultimos_trechos'] = list()
if 'ultima_instrucao' not in st.session_state: st.session_state['ultima_instrucao'] = ''

# Estilo customizado: Estante de Livros High-Tech (Clean & Sofisticado)
st.markdown("""
<style>
    @import url("https://googleapis.com");
    html, body, [class*="css"] {
        font-family: "Inter", -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    code, pre, [data-testid="stMetricValue"] {
        font-family: "JetBrains Mono", monospace !important;
    }
    /* Fundo azul claro suave em toda a aplicacao */
    .stApp {
        background-color: #E0F2FE;
        color: #0F172A;
    }
    section[data-testid="stSidebar"] {
        background-color: #CBE7FA;
        border-right: 2px solid #7DD3FC;
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
    .book-card { transition: transform 0.18s ease, box-shadow 0.18s ease; box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
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
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
        color: #0F172A !important;
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
    perfis_dict = carregar_perfis_prompts()
    perfil_agente = st.selectbox("🎓 Especialidade de Engenharia (prompts/):", list(perfis_dict.keys()), index=0)
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

aba1, aba2, aba3, aba4 = st.tabs([
    "💬 1. Sala Técnica (Chat & Propostas)",
    "📚 2. Estante Digital (Acervo)",
    "📥 3. Catalogar & Gerir PDFs",
    "🧠 4. Editor de Prompts",
])

with aba1:
    st.caption("💡 **Exemplos de instruções:** *'Extraia os dados nominais deste equipamento e monte uma tabela técnica'* • *'Redija o memorial descritivo de conformidade com a NBR para nossa proposta comercial'*")
    janela_chat = st.container(height=440, border=True)
    with janela_chat:
        if not st.session_state["chat_rag"]:
            st.info("👋 **Sala Técnica pronta!** Digite sua instrução abaixo para extrair especificações das normas, manuais ou catálogos e redigir relatórios descritivos ou propostas comerciais.")
        for msg in st.session_state["chat_rag"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    instrucao = st.chat_input("Instrua o agente (ex.: Extraia as especificações do equipamento e redija o texto da proposta comercial)...")
    if instrucao:
        st.session_state["chat_rag"].append({"role": "user", "content": instrucao})
        with st.chat_message("user"):
            st.markdown(instrucao)

        trechos = buscar_trechos_relevantes(
            instrucao,
            top_k=top_k,
            filtro_arquivo=filtro_selecionado,
            filtro_categoria=categoria_sel if "categoria_sel" in locals() else None,
        )
        st.session_state["ultimos_trechos"] = trechos
        st.session_state["ultima_instrucao"] = instrucao

        with st.chat_message("assistant"):
            with st.spinner(f"Analisando estrutura documental e redigindo resposta ({modelo})..."):
                resposta = conversar_com_agente(
                    historico=st.session_state["chat_rag"][:-1],
                    instrucao_atual=instrucao,
                    trechos=trechos,
                    provedor=provedor,
                    api_key=api_key,
                )
            st.markdown(resposta)

        st.session_state["chat_rag"].append({"role": "assistant", "content": resposta})
        st.rerun()

    if st.session_state["chat_rag"]:
        st.divider()
        ultima_resp = st.session_state["chat_rag"][-1]["content"]
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            pdf_bytes = gerar_pdf_consulta_rag(st.session_state["ultima_instrucao"], filtro_selecionado, st.session_state["ultimos_trechos"], ultima_resp)
            st.download_button(label="📄 Baixar Documento / Proposta em PDF", data=pdf_bytes, file_name="Relatorio_Proposta_Tecnica_RAG.pdf", mime="application/pdf", type="primary")
        with col_exp2:
            st.download_button(label="📝 Baixar Texto em Markdown (.MD)", data=ultima_resp.encode("utf-8"), file_name="Proposta_Memorial_Descritivo.md", mime="text/markdown")

        if st.session_state["ultimos_trechos"]:
            with st.expander(f"🔎 Auditar Evidências Originais Utilizadas ({len(st.session_state['ultimos_trechos'])} trechos)"):
                for i, item in enumerate(st.session_state["ultimos_trechos"], start=1):
                    html_dest = destacar_termos_html(item.texto, st.session_state["ultima_instrucao"])
                    st.markdown(f"**Fonte {i}: 📘 {item.arquivo} — Página {item.pagina}** *(Relevância: {item.score*100:.1f}%)*")
                    st.markdown(html_dest, unsafe_allow_html=True)
                    st.divider()

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

    st.divider()
    st.markdown("#### 🤖 Importação Automática do Computador (ABNT, NBR, NR, IEC, Leis, Manuais & Catálogos)")
    pasta_custom = st.text_input("Pastas para varrer:", value="~/Downloads, ~/Documentos, ~/Área de Trabalho")
    apenas_normas = st.checkbox("Filtrar por palavras-chave (ABNT, NBR, NR, IEC, Lei, Manual, Catálogo, Datasheet)", value=True)
    if st.button("Varrer Pastas, Copiar & Indexar Agora", type="primary"):
        lista_pastas = [x.strip() for x in pasta_custom.split(",") if x.strip()]
        with st.spinner("Varrendo diretórios e catalogando documentos na estante..."):
            res = varrer_e_catalogar(lista_pastas, filtrar_por_nome=apenas_normas)
        st.success(f"Concluído! Copiados: {res['copiados']} | Novos indexados: {res['indexados']} | Já existiam: {res['ja_existiam']}")
        if res["indexados"] > 0:
            st.rerun()

with aba4:
    st.markdown("#### 🧠 Editor de Engenharia de Prompt (Perfis de Raciocínio)")
    st.caption("Crie ou personalize como o agente pensa e estrutura relatórios técnicos e propostas comerciais. As alterações atualizam automaticamente o seletor da barra lateral.")

    col_ed1, col_ed2 = st.columns(2)

    with col_ed1:
        st.markdown("##### ✏️ Editar Perfil Existente")
        arquivos_md = sorted(PASTA_PROMPTS.glob("*.md"))
        if arquivos_md:
            mapa_arqs = {arq.stem.replace("_", " ").title(): arq for arq in arquivos_md}
            nome_sel_ed = st.selectbox("Escolha o perfil para editar:", list(mapa_arqs.keys()))
            arq_alvo = mapa_arqs[nome_sel_ed]
            texto_atual = arq_alvo.read_text(encoding="utf-8")

            novo_texto = st.text_area("Instruções de Raciocínio e Formatação:", value=texto_atual, height=280, key="area_ed_prompt")
            if st.button("💾 Salvar Alterações no Perfil", type="primary"):
                arq_alvo.write_text(novo_texto, encoding="utf-8")
                st.success(f"Perfil **{nome_sel_ed}** atualizado com sucesso!")
                st.rerun()
        else:
            st.info("Nenhum arquivo .md encontrado na pasta prompts/.")

    with col_ed2:
        st.markdown("##### ➕ Criar Novo Perfil de Especialidade")
        nome_novo = st.text_input("Nome do arquivo (ex.: 05_engenheiro_automacao):", placeholder="05_engenheiro_automacao")
        texto_novo = st.text_area(
            "Instruções do Novo Perfil:",
            height=280,
            placeholder="Você é um Engenheiro Sênior especialista em [Área]. Extraia [Grandezas], verifique [Normas] e cite obrigatoriamente [Arquivo.pdf, Página X]...",
            key="area_novo_prompt",
        )
        if st.button("✨ Criar Novo Perfil (.md)", type="primary"):
            import re
            nome_limpo = re.sub(r"[^a-zA-Z0-9_-]", "_", nome_novo.strip()).strip("_").lower()
            if not nome_limpo or not texto_novo.strip():
                st.error("Preencha o nome do perfil e as instruções antes de criar.")
            else:
                destino_md = PASTA_PROMPTS / f"{nome_limpo}.md"
                destino_md.write_text(texto_novo.strip(), encoding="utf-8")
                st.success(f"Novo perfil **{destino_md.name}** criado e adicionado à barra lateral!")
                st.rerun()
