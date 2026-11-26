import sys
import sqlite3
import subprocess
from pathlib import Path
from pypdf import PdfReader
from motor_rag import DB_RAG, init_db_rag, fatiar_texto, classificar_categoria_documento, reconstruir_indice_vetorial

def indexar_um_arquivo(caminho_pdf: str):
    p = Path(caminho_pdf)
    nome = p.name
    cat = classificar_categoria_documento(nome)
    reader = PdfReader(str(p), strict=False)
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            sys.exit(2)

    con = sqlite3.connect(DB_RAG, timeout=30.0)
    cur = con.cursor()
    cur.execute("DELETE FROM chunks WHERE arquivo = ?", (nome,))
    total = 0
    for num_pag, page in enumerate(reader.pages[:600], start=1):
        txt = page.extract_text() or ""
        for pedaco in fatiar_texto(txt):
            cur.execute(
                "INSERT INTO chunks (arquivo, pagina, texto, metodo, categoria) VALUES (?, ?, ?, ?, ?)",
                (nome, num_pag, pedaco, "Texto Nativo", cat),
            )
            total += 1
    con.commit()
    con.close()
    print(f"OK:{total}")

if __name__ == "__main__":
    if len(sys.argv) == 3 and "--worker" in sys.argv:
        caminho_alvo = sys.argv.pop()
        indexar_um_arquivo(caminho_alvo)
        sys.exit(0)

    init_db_rag()
    con = sqlite3.connect(DB_RAG, timeout=30.0)
    ja_indexados = {list(r).pop(0) for r in con.execute("SELECT DISTINCT arquivo FROM chunks").fetchall()}
    con.close()

    ignorar = ("cnh", "cpf", "cert_", "certificado0", "comp_res", "comprovante", "conta_", "contaigua", "cupom", "danfe", "crlv", "declaracao_etefv", "declaração_etefv", "cnpj_")
    pdfs = sorted(Path("documentos").glob("*.[pP][dD][fF]"))

    novos = 0
    travados = 0
    vazios = 0

    print(f"=== INICIANDO INDEXACAO BLINDADA ({len(pdfs)} PDFs na pasta | {len(ja_indexados)} ja no banco) ===")
    for pdf in pdfs:
        nome = pdf.name
        if any(k in nome.lower() for k in ignorar) or nome in ja_indexados:
            continue
        try:
            proc = subprocess.run(
                [sys.executable, __file__, "--worker", str(pdf)],
                capture_output=True,
                text=True,
                timeout=15,
            )
            saida = proc.stdout.strip()
            if proc.returncode == 0 and "OK:" in saida:
                qtd = int(saida.split("OK:").pop())
                if qtd > 0:
                    novos += 1
                    print(f"[+{novos}] {nome} ({qtd} trechos)")
                else:
                    vazios += 1
            else:
                vazios += 1
        except subprocess.TimeoutExpired:
            travados += 1
            print(f"[TIMEOUT >15s - PULADO] {nome}")

    print("\nReconstruindo indice vetorial unificado (BM25 + TF-IDF)...")
    reconstruir_indice_vetorial()

    con = sqlite3.connect(DB_RAG, timeout=30.0)
    tot_vols, tot_chunks = con.execute("SELECT COUNT(DISTINCT arquivo), COUNT(*) FROM chunks").fetchone()
    con.close()
    print(f"=== FINALIZADO! Banco agora tem {tot_vols} volumes e {tot_chunks} trechos (+{novos} novos | {travados} lentos pulados | {vazios} sem texto) ===")
