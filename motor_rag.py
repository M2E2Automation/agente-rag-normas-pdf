import os
import re
import pickle
import sqlite3
from dataclasses import dataclass
from typing import List, Tuple, Optional
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

DB_RAG = "base_conhecimento_rag.sqlite"
INDEX_PATH = "indice_vetorial_rag.pkl"
MAX_PDF_BYTES = 50 * 1024 * 1024

@dataclass
class TrechoDocumento:
    id: int
    arquivo: str
    pagina: int
    texto: str
    score: float = 0.0

def sanitizar_nome_arquivo(nome: str) -> str:
    base = os.path.basename(str(nome)).strip()
    if not base or not base.lower().endswith(".pdf"):
        raise ValueError("Nome de arquivo invalido. Apenas arquivos .pdf sao permitidos.")
    return base

def init_db_rag():
    con = sqlite3.connect(DB_RAG)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            arquivo TEXT NOT NULL,
            pagina INTEGER NOT NULL,
            texto TEXT NOT NULL
        )
    """)
    con.commit()
    con.close()
    if os.path.exists(DB_RAG):
        os.chmod(DB_RAG, 0o600)

def limpar_texto(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()

def fatiar_texto(texto: str, tamanho_chunk: int = 900, overlap: int = 180) -> List[str]:
    texto = limpar_texto(texto)
    if not texto:
        return list()
    chunks = list()
    inicio = 0
    while inicio < len(texto):
        fim = inicio + tamanho_chunk
        chunks.append(texto[inicio:fim])
        inicio += (tamanho_chunk - overlap)
    return chunks

def indexar_pdf(caminho_ou_buffer, nome_arquivo: str) -> int:
    nome_seguro = sanitizar_nome_arquivo(nome_arquivo)
    if hasattr(caminho_ou_buffer, "size") and caminho_ou_buffer.size > MAX_PDF_BYTES:
        raise ValueError("Arquivo PDF excede o limite de seguranca (50 MB).")

    init_db_rag()
    reader = PdfReader(caminho_ou_buffer)
    con = sqlite3.connect(DB_RAG)
    cur = con.cursor()
    cur.execute("DELETE FROM chunks WHERE arquivo = ?", (nome_seguro,))

    total_chunks = 0
    for num_pag, page in enumerate(reader.pages, start=1):
        texto_pag = page.extract_text() or ""
        pedacos = fatiar_texto(texto_pag)
        for p in pedacos:
            cur.execute(
                "INSERT INTO chunks (arquivo, pagina, texto) VALUES (?, ?, ?)",
                (nome_seguro, num_pag, p)
            )
            total_chunks += 1

    con.commit()
    con.close()
    reconstruir_indice_vetorial()
    return total_chunks

def remover_documento(nome_arquivo: str) -> None:
    nome_seguro = sanitizar_nome_arquivo(nome_arquivo)
    init_db_rag()
    con = sqlite3.connect(DB_RAG)
    cur = con.cursor()
    cur.execute("DELETE FROM chunks WHERE arquivo = ?", (nome_seguro,))
    con.commit()
    con.close()
    reconstruir_indice_vetorial()

def reconstruir_indice_vetorial() -> bool:
    init_db_rag()
    con = sqlite3.connect(DB_RAG)
    cur = con.cursor()
    rows = cur.execute("SELECT id, arquivo, pagina, texto FROM chunks ORDER BY id").fetchall()
    con.close()

    if not rows:
        if os.path.exists(INDEX_PATH):
            os.remove(INDEX_PATH)
        return False

    textos = [r[-1] for r in rows]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=25000)
    matriz = vectorizer.fit_transform(textos)

    with open(INDEX_PATH, "wb") as f:
        pickle.dump({"rows": rows, "vectorizer": vectorizer, "matriz": matriz}, f)
    os.chmod(INDEX_PATH, 0o600)
    return True

def buscar_trechos_relevantes(pergunta: str, top_k: int = 4, filtro_arquivo: Optional[str] = None) -> List[TrechoDocumento]:
    if not os.path.exists(INDEX_PATH):
        return list()

    with open(INDEX_PATH, "rb") as f:
        dados = pickle.load(f)

    rows = dados["rows"]
    vectorizer = dados["vectorizer"]
    matriz = dados["matriz"]

    q_vec = vectorizer.transform([limpar_texto(pergunta)])
    scores = cosine_similarity(q_vec, matriz).flatten()
    indices_ordenados = np.argsort(scores)[::-1]

    resultados = list()
    for idx in indices_ordenados:
        sc = float(scores[idx])
        if sc <= 0.02:
            break
        cid, arq, pag, txt = rows[idx]
        if filtro_arquivo and filtro_arquivo != "Todos os Documentos" and arq != filtro_arquivo:
            continue
        resultados.append(TrechoDocumento(id=cid, arquivo=arq, pagina=pag, texto=txt, score=round(sc, 4)))
        if len(resultados) >= top_k:
            break
    return resultados

def destacar_termos_html(texto: str, pergunta: str) -> str:
    txt_esc = texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    palavras = [re.escape(p) for p in re.findall(r"\w{3,}", pergunta, flags=re.UNICODE)]
    if not palavras:
        return txt_esc
    padrao = re.compile(r"(" + "|".join(set(palavras)) + r")", flags=re.IGNORECASE)
    return padrao.sub(r"<mark style='background-color:#FFF3CD; padding:1px 3px; border-radius:3px;'><b>\\1</b></mark>", txt_esc)

def listar_documentos_indexados() -> List[Tuple[str, int]]:
    init_db_rag()
    con = sqlite3.connect(DB_RAG)
    cur = con.cursor()
    res = cur.execute("SELECT arquivo, COUNT(*) FROM chunks GROUP BY arquivo ORDER BY arquivo").fetchall()
    con.close()
    return res
