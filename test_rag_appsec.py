import os
import pytest
from reportlab.pdfgen import canvas
import io
from motor_rag import (
    init_db_rag,
    indexar_pdf,
    buscar_trechos_relevantes,
    remover_documento,
    sanitizar_nome_arquivo,
    destacar_termos_html,
    DB_RAG,
    INDEX_PATH,
)

def criar_pdf_memoria(texto_pag1: str, texto_pag2: str) -> io.BytesIO:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 720, texto_pag1)
    c.showPage()
    c.drawString(72, 720, texto_pag2)
    c.save()
    buf.seek(0)
    return buf

def test_01_indexacao_busca_e_filtro_norma():
    pdf_teste = criar_pdf_memoria(
        "A norma NBR 5410 estabelece que a queda de tensao maxima em circuitos terminais e de 4 porcento.",
        "O Imposto Industrial em Angola tem aliquota geral de 25 porcento conforme a Lei 26/20."
    )
    qtd = indexar_pdf(pdf_teste, "norma_teste_unit.pdf")
    assert qtd >= 2

    res = buscar_trechos_relevantes("queda de tensao NBR 5410", top_k=2, filtro_arquivo="norma_teste_unit.pdf")
    assert len(res) >= 1
    assert res[0].pagina == 1
    assert "5410" in res[0].texto

    # Limpa documento de teste ao final
    remover_documento("norma_teste_unit.pdf")

def test_02_highlight_e_bloqueio_xss():
    texto_malicioso = "Norma <script>alert('xss')</script> sobre aterramento eletrico."
    html = destacar_termos_html(texto_malicioso, "aterramento")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<mark" in html

def test_03_pentest_path_traversal_e_extensao():
    assert sanitizar_nome_arquivo("../../etc/passwd/norma.pdf") == "norma.pdf"
    with pytest.raises(ValueError):
        sanitizar_nome_arquivo("exploit.exe")

def test_04_permissoes_arquivos_seguranca():
    init_db_rag()
    assert oct(os.stat(DB_RAG).st_mode)[-3:] == "600"
