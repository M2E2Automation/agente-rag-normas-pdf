import json
import ssl
import urllib.request
from pathlib import Path
from typing import List, Dict
from motor_rag import TrechoDocumento

PASTA_PROMPTS = Path(__file__).parent / "prompts"

def carregar_perfis_prompts() -> Dict[str, str]:
    PASTA_PROMPTS.mkdir(parents=True, exist_ok=True)
    perfis = dict()
    arquivos = sorted(PASTA_PROMPTS.glob("*.md"))
    for arq in arquivos:
        nome_legivel = arq.stem.replace("_", " ").title()
        perfis[nome_legivel] = arq.read_text(encoding="utf-8")
    if not perfis:
        perfis["Engenheiro Consultor Padrão"] = (
            "Você é um Engenheiro Consultor Sênior. Responda usando exclusivamente os trechos fornecidos "
            "e cite [Arquivo.pdf, Página X] em cada afirmação."
        )
    return perfis

def montar_mensagens_chat(
    historico: List[Dict[str, str]],
    instrucao_atual: str,
    trechos: List[TrechoDocumento],
    perfil: str,
) -> List[Dict[str, str]]:
    perfis = carregar_perfis_prompts()
    sys_prompt = perfis.get(perfil, list(perfis.values()).pop(0))

    blocos_doc = list()
    for i, t in enumerate(trechos, start=1):
        blocos_doc.append(
            f"[EVIDÊNCIA {i} | TIPO: {t.metodo} | FONTE: {t.arquivo}, Página {t.pagina}]\n{t.texto}"
        )
    contexto_str = "\n\n".join(blocos_doc) if blocos_doc else "Nenhum trecho específico recuperado para esta mensagem."

    mensagens = list()
    mensagens.append({"role": "system", "content": sys_prompt})

    for msg in historico[-6:]:
        mensagens.append({"role": msg["role"], "content": msg["content"]})

    prompt_final = (
        f"TRECHOS EXTRAÍDOS DA ESTANTE DOCUMENTAL PARA ESTA ETAPA:\n"
        f"{contexto_str}\n\n"
        f"INSTRUÇÃO DO USUÁRIO:\n{instrucao_atual}"
    )
    mensagens.append({"role": "user", "content": prompt_final})
    return mensagens

def conversar_com_agente(
    historico: List[Dict[str, str]],
    instrucao_atual: str,
    trechos: List[TrechoDocumento],
    provedor: str,
    api_key: str = "",
    modelo: str = "qwen2.5:1.5b",
    perfil: str = "",
) -> str:
    if provedor == "Apenas Busca Extrativa (Sem API)":
        if not trechos:
            return "Nenhum trecho encontrado na estante para esta consulta."
        linhas = ["**Trechos extraídos da base documental:**\n"]
        for t in trechos:
            linhas.append(f"- **[{t.arquivo}, Página {t.pagina}]**: {t.texto}")
        return "\n".join(linhas)

    mensagens = montar_mensagens_chat(historico, instrucao_atual, trechos, perfil)
    ctx_ssl = ssl.create_default_context()
    ctx_ssl.minimum_version = ssl.TLSVersion.TLSv1_2

    try:
        if provedor == "Ollama Local (Offline)":
            url = "http://127.0.0.1:11434" + chr(47) + "api/chat"
            payload = {
                "model": modelo,
                "stream": False,
                "options": {"temperature": 0.2, "num_ctx": 4096},
                "messages": mensagens,
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["message"]["content"]

        elif provedor == "Google Gemini":
            if not api_key.strip():
                return "⚠️ Informe sua chave de API do Google Gemini na barra lateral."
            base_g = "https://googleapis.com" + chr(47) + "v1beta/models/"
            url = f"{base_g}{modelo}:generateContent?key={api_key.strip()}"
            contents = list()
            for m in mensagens[1:]:
                role_g = "model" if m["role"] == "assistant" else "user"
                contents.append({"role": role_g, "parts": [{"text": m["content"]}]})
            payload = {
                "systemInstruction": {"parts": [{"text": mensagens.pop(0)["content"]}]},
                "contents": contents,
                "generationConfig": {"temperature": 0.2},
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=45, context=ctx_ssl) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                cand = list(data["candidates"]).pop(0)
                part = list(cand["content"]["parts"]).pop(0)
                return part["text"]

        elif provedor == "OpenAI":
            if not api_key.strip():
                return "⚠️ Informe sua chave de API da OpenAI na barra lateral."
            url = "https://openai.com" + chr(47) + "v1/chat/completions"
            payload = {
                "model": modelo,
                "temperature": 0.2,
                "messages": mensagens,
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
            with urllib.request.urlopen(req, timeout=45, context=ctx_ssl) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choice = list(data["choices"]).pop(0)
                return choice["message"]["content"]

        return "Provedor não reconhecido."
    except Exception as e:
        return f"⚠️ Falha na comunicação com o modelo ({provedor}): {str(e)[:140]}"
