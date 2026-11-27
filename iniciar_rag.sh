#!/bin/bash
cd "/home/joao/projetos-engenharia-ia/agente-rag-normas"
source .venv/bin/activate
if ! pgrep -x "ollama" > /dev/null; then
    nohup ollama serve > ollama.log 2>&1 &
    sleep 2
fi
fuser -k 8503/tcp 2>/dev/null || true
sleep 1
nohup python3 -m streamlit run app_rag.py --server.port 8503 --server.headless true --server.address 127.0.0.1 --server.enableXsrfProtection true > streamlit_rag.log 2>&1 &
sleep 2
python3 -c 'import webbrowser; webbrowser.open("http://localhost:8503")'
