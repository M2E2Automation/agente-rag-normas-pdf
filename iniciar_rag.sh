#!/bin/bash
cd /home/joao/projetos-engenharia-ia/agente-rag-normas
source .venv/bin/activate

if ! pgrep -x "ollama" > /dev/null; then
    nohup ollama serve > ollama.log 2>&1 &
    sleep 2
fi

pkill -f "app_rag.py" 2>/dev/null || true
sleep 1
nohup python3 -m streamlit run app_rag.py --server.port 8503 --server.headless true --server.address 127.0.0.1 --server.enableXsrfProtection true > streamlit_rag.log 2>&1 &
sleep 2
nohup xdg-open http://127.0.0.1:8503 >/dev/null 2>&1 &
