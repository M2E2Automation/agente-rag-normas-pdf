import hashlib
import hmac
import os
import re
import secrets
from pathlib import Path

CHAVE_HMAC_PATH = Path(__file__).parent / ".rag_integrity.key"

def obter_chave_integridade() -> bytes:
    """Gera ou carrega chave secreta local (permissao 0600) para assinar indices em disco."""
    if not CHAVE_HMAC_PATH.exists():
        CHAVE_HMAC_PATH.write_bytes(secrets.token_bytes(32))
        os.chmod(CHAVE_HMAC_PATH, 0o600)
    return CHAVE_HMAC_PATH.read_bytes()

def assinar_bytes(dados: bytes) -> str:
    chave = obter_chave_integridade()
    return hmac.new(chave, dados, hashlib.sha256).hexdigest()

def verificar_assinatura_bytes(dados: bytes, assinatura_esperada: str) -> bool:
    assinatura_atual = assinar_bytes(dados)
    return hmac.compare_digest(assinatura_atual, assinatura_esperada.strip())

def sanitizar_caminho_seguro(diretorio_base: Path, nome_arquivo: str, extensao_obrigatoria: str) -> Path:
    """Previne Path Traversal (CWE-22) garantindo que o arquivo permaneca dentro do diretorio_base."""
    base_resolvida = diretorio_base.resolve()
    base_resolvida.mkdir(parents=True, exist_ok=True)
    nome_limpo = os.path.basename(str(nome_arquivo)).strip()
    if not nome_limpo or not nome_limpo.lower().endswith(extensao_obrigatoria.lower()):
        raise ValueError(f"Nome de arquivo invalido. Requer extensao {extensao_obrigatoria}.")
    destino = (base_resolvida / nome_limpo).resolve()
    if destino.parent != base_resolvida:
        raise ValueError("Tentativa de Path Traversal bloqueada.")
    return destino

def neutralizar_prompt_injection(texto_documento: str) -> str:
    """Neutraliza delimitadores XML e padroes classicos de Indirect Prompt Injection vindos de PDFs."""
    limpo = str(texto_documento).replace("<", "[").replace(">", "]")
    padroes_suspeitos = re.compile(
        r"(ignore\s+(all\s+)?previous\s+instructions|system\s*prompt|you\s+are\s+now|disregard\s+above)",
        flags=re.IGNORECASE,
    )
    return padroes_suspeitos.sub("[TRECHO_FILTRADO_SEGURANCA]", limpo)

def validar_expressao_matematica_segura(expr: str, max_len: int = 120) -> str:
    """Whitelist estrita para impedir DoS ou injecao no parser simbolico/AST."""
    expr_limpa = str(expr).strip()
    if not expr_limpa or len(expr_limpa) > max_len:
        raise ValueError("Expressao matematica vazia ou excede limite de 120 caracteres.")
    if not re.fullmatch(r"[0-9a-zA-Z_+\-*/^().,\s]+", expr_limpa):
        raise ValueError("Caracteres nao permitidos na expressao matematica.")
    if "**" in expr_limpa and len(expr_limpa.split("**")) > 3:
        raise ValueError("Exponenciacao encadeada excessiva bloqueada (protecao DoS).")
    return expr_limpa
