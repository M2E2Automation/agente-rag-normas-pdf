# Agente de IA com RAG — Consulta Auditável de Normas Técnicas e Leis em PDF

Sistema de **Retrieval-Augmented Generation (RAG)** desenvolvido em Python para indexação de normas técnicas de engenharia, contratos e legislação em PDF, oferecendo busca vetorial local, destaque visual (*highlight*) de termos, exportação de parecer técnico em PDF e síntese generativa **100% offline via Ollama (`qwen2.5:1.5b`)** ou APIs (Google Gemini / OpenAI).

## Arquitetura do Sistema

- `motor_rag.py`: Extração de texto por página (`pypdf`), fragmentação com sobreposição (*chunking* 900/180 caracteres), indexação TF-IDF + Similaridade de Cosseno (`scikit-learn`) e persistência em SQLite com permissões restritas (`0600`).
- `cerebro_llm.py`: Camada generativa com *System Prompt* anti-alucinação exigindo citação obrigatória `[Arquivo.pdf, Página X]`. Suporta **Ollama Local (Offline)**, Google Gemini e OpenAI.
- `relatorio_rag_pdf.py`: Geração nativa de pareceres técnicos auditáveis em PDF (`ReportLab`).
- `app_rag.py`: Interface web interativa (`Streamlit`) com filtro por norma, gerenciamento de documentos e destaque visual sanitizado contra XSS.
- `test_rag_appsec.py`: Suíte automatizada de testes unitários e segurança AppSec (`pytest`).

## Como Executar Localmente

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -v
python3 -m streamlit run app_rag.py --server.address 127.0.0.1
```
