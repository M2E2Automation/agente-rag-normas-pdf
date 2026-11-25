import json
import ssl
import urllib.request
from typing import List
from motor_rag import TrechoDocumento

SYSTEM_PROMPT_RAG = (
    "Você é um Engenheiro Consultor e Auditor Normativo rigoroso. "
    "Responda à pergunta do usuário utilizando EXCLUSIVAMENTE os trechos de documentos fornecidos no contexto abaixo. "
    "REGRAS OBRIGATÓRIAS:\n"
    "1. Toda afirmação, valor numérico, prazo ou exigência legal DEVE terminar com a citação exata no formato [Nome_do_Arquivo.pdf, Página X].\n"
    "2. Se a informação não estiver explícita nos trechos fornecidos, responda exatamente: 'A base documental indexada não contém informação suficiente para responder a este ponto.'\n"
    "3. Nunca invente normas, artigos de lei ou valores fora do contexto.\n"
    "4. Estruture a resposta em tópicos objetivos e técnicos em Português."
)

def montar_contexto_rag(pergunta: str, trechos: List[TrechoDocumento]) -> str:
    blocos = []
    for i, t in enumerate(trechos, start=1):
        blocos.append(f"--- TRECHO {i} | FONTE: [{t.arquivo}, Página {t.pagina}] ---\n{t.texto}")
    contexto_str = "\n\n".join(blocos)
    return f"CONTEXTO DOCUMENTAL:\n{contexto_str}\n\nPERGUNTA DO USUÁRIO:\n{pergunta}"

def gerar_sintese_llm(
    pergunta: str,
    trechos: List[TrechoDocumento],
    provedor: str,
    api_key: str = "",
    modelo: str = "gemini-2.5-flash",
) -> str:
    if not trechos:
        return "Nenhum trecho documental foi recuperado para fundamentar a resposta."

    prompt_usuario = montar_contexto_rag(pergunta, trechos)
    ctx_ssl = ssl.create_default_context()
    ctx_ssl.minimum_version = ssl.TLSVersion.TLSv1_2

    try:
        if provedor == "Google Gemini":
            if not api_key.strip():
                return "⚠️ Informe sua chave de API do Google Gemini na barra lateral."
            url = f"https://googleapis.com{modelo}:generateContent?key={api_key.strip()}"
            payload = {
                "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT_RAG}]},
                "contents": [{"parts": [{"text": prompt_usuario}]}],
                "generationConfig": {"temperature": 0.1},
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=25, context=ctx_ssl) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]

        elif provedor == "OpenAI":
            if not api_key.strip():
                return "⚠️ Informe sua chave de API da OpenAI na barra lateral."
            url = "https://openai.com"
            payload = {
                "model": modelo,
                "temperature": 0.1,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT_RAG},
                    {"role": "user", "content": prompt_usuario},
                ],
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key.strip()}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=25, context=ctx_ssl) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]

        elif provedor == "Ollama Local (Offline)":
            url = "http://127.0.0"
            payload = {
                "model": modelo,
                "stream": False,
                "options": {"temperature": 0.1},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT_RAG},
                    {"role": "user", "content": prompt_usuario},
                ],
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["message"]["content"]

        return "Modo Extrativo Local ativo (sem síntese generativa)."

    except Exception as e:
        return f"⚠️ Falha na comunicação com o provedor ({provedor}): {str(e)[:120]}"
