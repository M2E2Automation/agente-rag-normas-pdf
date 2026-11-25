import os
import re
import pickle
import sqlite3
from dataclasses import dataclass
from typing import List, Tuple
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

DB_RAG = "base_conhecimento_rag.sqlite"
INDEX_PATH = "indice_vetorial_rag.pkl"

@dataclass
class TrechoDocumento:
    id: int
    arquivo: str
    pagina: int
    texto: str
    score: float = 0.0

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
        return []
    chunks = []
    inicio = 0
    while inicio < len(texto):
        fim = inicio + tamanho_chunk
        chunks.append(texto[inicio:fim])
        inicio += (tamanho_chunk - overlap)
    return chunks

def indexar_pdf(caminho_ou_buffer, nome_arquivo: str) -> int:
    init_db_rag()
    reader = PdfReader(caminho_ou_buffer)
    con = sqlite3.connect(DB_RAG)
    cur = con.cursor()

    # Remove versao anterior do mesmo arquivo para evitar duplicidade
    cur.execute("DELETE FROM chunks WHERE arquivo = ?", (nome_arquivo,))

    total_chunks = 0
    for num_pag, page in enumerate(reader.pages, start=1):
        texto_pag = page.extract_text() or ""
        pedacos = fatiar_texto(texto_pag)
        for p in pedacos:
            cur.execute(
                "INSERT INTO chunks (arquivo, pagina, texto) VALUES (?, ?, ?)",
                (nome_arquivo, num_pag, p)
            )
            total_chunks += 1

    con.commit()
    con.close()
    reconstruir_indice_vetorial()
    return total_chunks

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

    textos = [r[3] for r in rows]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=25000)
    matriz = vectorizer.fit_transform(textos)

    with open(INDEX_PATH, "wb") as f:
        pickle.dump({"rows": rows, "vectorizer": vectorizer, "matriz": matriz}, f)
    os.chmod(INDEX_PATH, 0o600)
    return True

def buscar_trechos_relevantes(pergunta: str, top_k: int = 4) -> List[TrechoDocumento]:
    if not os.path.exists(INDEX_PATH):
        return []

    with open(INDEX_PATH, "rb") as f:
        dados = pickle.load(f)

    rows = dados["rows"]
    vectorizer = dados["vectorizer"]
    matriz = dados["matriz"]

    q_vec = vectorizer.transform([limpar_texto(pergunta)])
    scores = cosine_similarity(q_vec, matriz).flatten()
    indices_top = np.argsort(scores)[::-1][:top_k]

    resultados = []
    for idx in indices_top:
        sc = float(scores[idx])
        if sc > 0.02:
            r = rows[idx]
            resultados.append(TrechoDocumento(id=r[0], arquivo=r[1], pagina=r[2], texto=r[3], score=round(sc, 4)))
    return resultados

def listar_documentos_indexados() -> List[Tuple[str, int]]:
    init_db_rag()
    con = sqlite3.connect(DB_RAG)
    cur = con.cursor()
    res = cur.execute("SELECT arquivo, COUNT(*) FROM chunks GROUP BY arquivo ORDER BY arquivo").fetchall()
    con.close()
    return res
