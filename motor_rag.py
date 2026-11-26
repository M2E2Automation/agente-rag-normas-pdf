import os
import re
import pickle
import sqlite3
import unicodedata
from dataclasses import dataclass
from typing import List, Tuple, Optional
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rank_bm25 import BM25Okapi
import numpy as np

try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_DISPONIVEL = True
except ImportError:
    OCR_DISPONIVEL = False

DB_RAG = "base_conhecimento_rag.sqlite"
INDEX_PATH = "indice_vetorial_rag.pkl"
MAX_PDF_BYTES = 1024 * 1024 * 1024  # 1 GB

@dataclass
class TrechoDocumento:
    id: int
    arquivo: str
    pagina: int
    texto: str
    score: float = 0.0
    metodo: str = "Texto Nativo"


def classificar_categoria_documento(nome_arquivo: str) -> str:
    n = nome_arquivo.lower()
    if any(k in n for k in ["solar", "fotovoltaic", "eolica", "bateria", "bess", "armazenamento", "termoacumul", "energia limpa", "eletrific"]):
        return "Energia Limpa, BESS & Termoacumulação"
    if any(k in n for k in ["termodinamica", "termodinâmica", "calor", "refrigerac", "hvac", "entalpia"]):
        return "Física & Termodinâmica Avançada"
    if any(k in n for k in ["fluido", "hidraulic", "hidráulic", "bomba", "mecanica dos fluidos", "tubulac"]):
        return "Fluidodinâmica & Hidráulica"
    if any(k in n for k in ["eletromag", "maxwell", "eletric", "elétric", "potencia", "potência", "transformador", "motor"]):
        return "Eletromagnetismo & Engenharia Elétrica"
    if any(k in n for k in ["matemat", "calculo", "cálculo", "geometria", "fractal", "algebra", "álgebra", "fisica", "física"]):
        return "Matemática, Física & Geometria/Fractais"
    if any(k in n for k in ["manual", "instruc", "operac", "manutenc", "guia"]):
        return "Manual de Máquina/Equipamento"
    if any(k in n for k in ["catalog", "catálog", "datasheet", "especific", "ficha"]):
        return "Catálogo Técnico / Datasheet"
    if any(k in n for k in ["lei", "decreto", "codigo", "código", "portaria", "resoluc"]):
        return "Legislação & Regulamentos"
    return "Norma Técnica (ABNT/NBR/NR/IEC)"

def sanitizar_nome_arquivo(nome: str) -> str:
    base = os.path.basename(str(nome)).strip()
    if not base or not base.lower().endswith(".pdf"):
        raise ValueError("Nome de arquivo invalido. Apenas arquivos .pdf sao permitidos.")
    return base

def init_db_rag():
    con = sqlite3.connect(DB_RAG, timeout=30.0)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            arquivo TEXT NOT NULL,
            pagina INTEGER NOT NULL,
            texto TEXT NOT NULL,
            metodo TEXT DEFAULT 'Texto Nativo',
            categoria TEXT DEFAULT 'Norma Técnica (ABNT/NBR/NR/IEC)'
        )
    """)
    con.commit()
    con.close()
    if os.path.exists(DB_RAG):
        os.chmod(DB_RAG, 0o600)

def limpar_texto(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()

def normalizar_tokens_bm25(texto: str) -> List[str]:
    texto_norm = unicodedata.normalize("NFKD", texto.lower()).encode("ASCII", "ignore").decode("ASCII")
    return re.findall(r"[a-z0-9_.-]{2,}", texto_norm)

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

def indexar_pdf(caminho_ou_buffer, nome_arquivo: str, atualizar_indice: bool = True) -> int:
    nome_seguro = sanitizar_nome_arquivo(nome_arquivo)
    if hasattr(caminho_ou_buffer, "size") and caminho_ou_buffer.size > MAX_PDF_BYTES:
        raise ValueError("Arquivo PDF excede o limite de seguranca (1 GB).")

    init_db_rag()
    reader = PdfReader(caminho_ou_buffer)
    con = sqlite3.connect(DB_RAG, timeout=30.0)
    cur = con.cursor()
    categoria_doc = classificar_categoria_documento(nome_seguro)
    cur.execute("DELETE FROM chunks WHERE arquivo = ?", (nome_seguro,))

    total_chunks = 0
    eh_caminho_str = isinstance(caminho_ou_buffer, (str, os.PathLike))

    for num_pag, page in enumerate(reader.pages, start=1):
        texto_pag = page.extract_text() or ""
        metodo_pag = "Texto Nativo"

        # Aciona OCR automaticamente se a pagina for imagem escaneada (< 30 caracteres)
        if len(limpar_texto(texto_pag)) < 30 and OCR_DISPONIVEL and eh_caminho_str:
            try:
                imagens = convert_from_path(str(caminho_ou_buffer), first_page=num_pag, last_page=num_pag, dpi=200)
                if imagens:
                    texto_pag = pytesseract.image_to_string(imagens.pop(0), lang="por+eng")
                    metodo_pag = "OCR (Imagem)"
            except Exception:
                pass

        pedacos = fatiar_texto(texto_pag)
        for p in pedacos:
            cur.execute(
                "INSERT INTO chunks (arquivo, pagina, texto, metodo, categoria) VALUES (?, ?, ?, ?, ?)",
                (nome_seguro, num_pag, p, metodo_pag, categoria_doc)
            )
            total_chunks += 1

    con.commit()
    con.close()
    if atualizar_indice:
        reconstruir_indice_vetorial()
    return total_chunks

def remover_documento(nome_arquivo: str) -> None:
    nome_seguro = sanitizar_nome_arquivo(nome_arquivo)
    init_db_rag()
    con = sqlite3.connect(DB_RAG, timeout=30.0)
    cur = con.cursor()
    categoria_doc = classificar_categoria_documento(nome_seguro)
    cur.execute("DELETE FROM chunks WHERE arquivo = ?", (nome_seguro,))
    con.commit()
    con.close()
    if atualizar_indice:
        reconstruir_indice_vetorial()

def reconstruir_indice_vetorial() -> bool:
    init_db_rag()
    con = sqlite3.connect(DB_RAG, timeout=30.0)
    cur = con.cursor()
    rows = cur.execute("SELECT id, arquivo, pagina, texto, metodo, categoria FROM chunks ORDER BY id").fetchall()
    con.close()

    if not rows:
        if os.path.exists(INDEX_PATH):
            os.remove(INDEX_PATH)
        return False

    textos = [r[3] for r in rows]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=35000)
    matriz_tfidf = vectorizer.fit_transform(textos)

    corpus_tokenizado = [normalizar_tokens_bm25(t) for t in textos]
    bm25 = BM25Okapi(corpus_tokenizado)

    with open(INDEX_PATH, "wb") as f:
        pickle.dump({
            "rows": rows,
            "vectorizer": vectorizer,
            "matriz_tfidf": matriz_tfidf,
            "bm25": bm25
        }, f)
    os.chmod(INDEX_PATH, 0o600)
    return True

def buscar_trechos_relevantes(pergunta: str, top_k: int = 4, filtro_arquivo: Optional[str] = None, filtro_categoria: Optional[str] = None) -> List[TrechoDocumento]:
    if not os.path.exists(INDEX_PATH):
        return list()

    with open(INDEX_PATH, "rb") as f:
        dados = pickle.load(f)

    rows = dados["rows"]
    vectorizer = dados["vectorizer"]
    matriz_tfidf = dados["matriz_tfidf"]
    bm25 = dados["bm25"]

    # 1. Ranking Vetorial (TF-IDF + Cosseno)
    q_vec = vectorizer.transform([limpar_texto(pergunta)])
    scores_tfidf = cosine_similarity(q_vec, matriz_tfidf).flatten()
    rank_tfidf = np.argsort(scores_tfidf)[::-1]

    # 2. Ranking Lexical Exato (Okapi BM25)
    tokens_q = normalizar_tokens_bm25(pergunta)
    scores_bm25 = np.array(bm25.get_scores(tokens_q)) if tokens_q else np.zeros(len(rows))
    rank_bm25 = np.argsort(scores_bm25)[::-1]

    # 3. Fusao Reciproca de Rankings (Reciprocal Rank Fusion - RRF, k=60)
    k_rrf = 60.0
    rrf_scores = np.zeros(len(rows))
    for pos, idx in enumerate(rank_tfidf):
        if scores_tfidf[idx] > 0.01:
            rrf_scores[idx] += 1.0 / (k_rrf + pos + 1)
    for pos, idx in enumerate(rank_bm25):
        if scores_bm25[idx] > 0.1:
            rrf_scores[idx] += 1.0 / (k_rrf + pos + 1)

    max_possivel = 2.0 / (k_rrf + 1.0)
    indices_finais = np.argsort(rrf_scores)[::-1]

    resultados = list()
    for idx in indices_finais:
        sc_bruto = float(rrf_scores[idx])
        if sc_bruto <= 0.0:
            break
        cid, arq, pag, txt, met, cat = rows[idx]
        if filtro_categoria and filtro_categoria != "Todas as Categorias" and cat != filtro_categoria:
            continue
        if filtro_arquivo and filtro_arquivo != "Todos os Documentos" and arq != filtro_arquivo:
            continue
        confianca_pct = min(1.0, sc_bruto / max_possivel)
        resultados.append(TrechoDocumento(id=cid, arquivo=arq, pagina=pag, texto=txt, score=round(confianca_pct, 4), metodo=met))
        if len(resultados) >= top_k:
            break
    return resultados

def destacar_termos_html(texto: str, pergunta: str) -> str:
    txt_esc = texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    palavras = [re.escape(p) for p in re.findall(r"\w{3,}", pergunta, flags=re.UNICODE)]
    if not palavras:
        return txt_esc
    padrao = re.compile(r"(" + "|".join(set(palavras)) + r")", flags=re.IGNORECASE)
    return padrao.sub(r"<mark style='background-color:#FEF08A; padding:1px 4px; border-radius:3px;'><b>\1</b></mark>", txt_esc)

def listar_documentos_indexados() -> List[Tuple[str, int]]:
    init_db_rag()
    con = sqlite3.connect(DB_RAG, timeout=30.0)
    cur = con.cursor()
    res = cur.execute("SELECT arquivo, COUNT(*), MAX(categoria) FROM chunks GROUP BY arquivo ORDER BY categoria, arquivo").fetchall()
    con.close()
    return res
