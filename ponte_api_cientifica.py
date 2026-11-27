import json
import re
import urllib.request
from pathlib import Path
from typing import Optional

URL_BASE_API = "http://127.0.0.1:8000"
KEY_PROJETO3 = Path.home() / "projetos-engenharia-ia" / "api-engenharia-risco-rag" / ".api_secret.key"

def _ler_chave_api() -> str:
    if KEY_PROJETO3.exists():
        return KEY_PROJETO3.read_text(encoding="utf-8").strip()
    return ""

def _post_api(rota: str, payload: dict) -> Optional[dict]:
    chave = _ler_chave_api()
    if not chave:
        return None
    try:
        req = urllib.request.Request(
            f"{URL_BASE_API}{rota}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-API-Key": chave},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

def consultar_ferramentas_api_automatico(instrucao: str, buscar_artigos_publicos: bool = False) -> str:
    """Detecta necessidades de HVAC/ASHRAE, Calculo Simbolico ou Pesquisa Federada e consulta a API (porta 8000)."""
    txt = instrucao.lower()
    blocos_retorno = list()

    # 1. Deteccao de Carga Termica HVAC (ASHRAE + 7 Fabricantes)
    gatilhos_hvac = ("carga termica", "carga térmica", "hvac", "climatiz", "ar condicionado", "vrf", "chiller", "ashrae", "daikin", "trane", "trox", "midea", "gree", "hitachi", "lg")
    if any(g in txt for g in gatilhos_hvac):
        m_area = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:m2|m²|metros)", txt)
        m_pessoas = re.search(r"(\d+)\s*(?:pessoas|ocupantes|usuarios|usuários)", txt)
        if m_area:
            area_val = float(m_area.group(1).replace(",", "."))
            pessoas_val = int(m_pessoas.group(1)) if m_pessoas else max(1, int(round(area_val / 10.0)))
            res_hvac = _post_api(
                "/api/v1/hvac/carga-termica-ashrae",
                {
                    "nome_projeto": "Consulta Sala Técnica RAG",
                    "area_piso_m2": area_val,
                    "numero_pessoas": pessoas_val,
                },
            )
            if res_hvac:
                blocos_retorno.append(
                    f"[RESULTADO MOTOR HVAC ASHRAE (API PORTA 8000)]\n{json.dumps(res_hvac, ensure_ascii=False, indent=2)}"
                )

    # 2. Deteccao de Calculo Simbolico (SymPy)
    m_sym = re.search(r"(derivar|integrar|simplificar)\s+([0-9a-zA-Z_+\-*/^().\s]+)", instrucao, flags=re.IGNORECASE)
    if m_sym:
        op = m_sym.group(1).lower()
        expr = m_sym.group(2).strip().rstrip("?.!")
        res_sym = _post_api("/api/v1/ciencia/calculo-simbolico", {"expressao": expr, "variavel": "x", "operacao": op})
        if res_sym:
            blocos_retorno.append(
                f"[RESULTADO CÁLCULO SIMBÓLICO SYMPY (API PORTA 8000)]\n{json.dumps(res_sym, ensure_ascii=False)}"
            )

    # 3. Pesquisa Federada (arXiv + Crossref/DOI) quando ativada ou solicitada
    if buscar_artigos_publicos or any(k in txt for k in ("arxiv", "artigo cientifico", "artigo científico", "literatura internacional", "doi")):
        res_fed = _post_api(
            "/api/v1/conhecimento/pesquisa-federada",
            {
                "termo": instrucao[:180],
                "incluir_acervo_privado_rag": False,
                "incluir_arxiv_publico": True,
                "incluir_crossref_publico": True,
                "limite_por_fonte": 2,
            },
        )
        if res_fed:
            blocos_retorno.append(
                f"[FONTES CIENTÍFICAS PÚBLICAS (ARXIV / CROSSREF)]\n{json.dumps(res_fed, ensure_ascii=False, indent=2)}"
            )

    return "\n\n".join(blocos_retorno)
