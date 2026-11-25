import io
from datetime import datetime
from typing import List
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from motor_rag import TrechoDocumento

def gerar_pdf_consulta_rag(pergunta: str, filtro_doc: str, resultados: List[TrechoDocumento]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    titulo = ParagraphStyle("Tit", parent=styles["Heading1"], fontSize=14, textColor=colors.HexColor("#1B365D"), spaceAfter=6)
    sub = ParagraphStyle("Sub", parent=styles["Heading2"], fontSize=10.5, textColor=colors.HexColor("#1B365D"), spaceBefore=10, spaceAfter=4)
    meta = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=8.5, textColor=colors.dimgrey, spaceAfter=8)
    corpo = ParagraphStyle("Corpo", parent=styles["Normal"], fontSize=9.5, leading=13, spaceAfter=8)

    elems = list()
    elems.append(Paragraph("Parecer Técnico & Rastreabilidade Documental (Agente RAG)", titulo))
    elems.append(Paragraph(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Escopo: {filtro_doc}", meta))
    elems.append(Spacer(1, 6))

    pergunta_segura = pergunta.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    elems.append(Paragraph(f"<b>Consulta Realizada:</b> {pergunta_segura}", corpo))
    elems.append(Spacer(1, 6))

    for i, item in enumerate(resultados, start=1):
        arq_seguro = item.arquivo.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        txt_seguro = item.texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        elems.append(Paragraph(f"Evidência {i}: {arq_seguro} — Página {item.pagina} (Relevância: {item.score*100:.1f}%)", sub))
        elems.append(Paragraph(f"<i>\"{txt_seguro}\"</i>", corpo))

    doc.build(elems)
    return buffer.getvalue()
