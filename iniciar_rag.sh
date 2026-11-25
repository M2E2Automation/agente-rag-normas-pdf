#!/bin/bash
cd /home/joao/projetos-engenharia-ia/agente-rag-normas
source .venv/bin/activate

# Garante que o servidor Ollama esteja ativo em segundo plano
if ! pgrep -x "ollama" > /dev/null; then
    nohup ollama serve > ollama.log 2>&1 &
    sleep 2
fi

pkill -f "streamlit run" 2>/dev/null
nohup python3 -m streamlit run app_rag.py --server.headless true --server.address 127.0.0.1 --server.enableXsrfProtection true > streamlit_rag.log 2>&1 &
sleep 2
xdg-open http://127.0.0.1:8501
