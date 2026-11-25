import io
from datetime import datetime
from typing import List
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from motor_rag import TrechoDocumento

def _esc(texto: str) -> str:
    return str(texto).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def gerar_pdf_consulta_rag(pergunta: str, filtro_doc: str, resultados: List[TrechoDocumento], sintese_ia: str = "") -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    titulo = ParagraphStyle("Tit", parent=styles["Heading1"], fontSize=14, textColor=colors.HexColor("#1B365D"), spaceAfter=6)
    sub = ParagraphStyle("Sub", parent=styles["Heading2"], fontSize=10.5, textColor=colors.HexColor("#1B365D"), spaceBefore=10, spaceAfter=4)
    meta = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=8.5, textColor=colors.dimgrey, spaceAfter=8)
    corpo = ParagraphStyle("Corpo", parent=styles["Normal"], fontSize=9.5, leading=13, spaceAfter=8)

    elems = list()
    elems.append(Paragraph("Parecer Técnico & Rastreabilidade Documental (Agente RAG)", titulo))
    elems.append(Paragraph(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Escopo: {_esc(filtro_doc)}", meta))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph(f"<b>Consulta Realizada:</b> {_esc(pergunta)}", corpo))

    if sintese_ia and not sintese_ia.startswith("⚠️"):
        elems.append(Paragraph("Parecer Técnico Sintetizado (IA Auditada por Fontes)", sub))
        for linha in sintese_ia.split("\n"):
            if linha.strip():
                elems.append(Paragraph(_esc(linha.strip()), corpo))

    elems.append(Spacer(1, 6))
    elems.append(Paragraph("Evidências Originais Extraídas dos Documentos", sub))

    for i, item in enumerate(resultados, start=1):
        elems.append(Paragraph(f"Fonte {i}: {_esc(item.arquivo)} — Página {item.pagina} (Relevância: {item.score*100:.1f}%)", sub))
        elems.append(Paragraph(f"<i>\"{_esc(item.texto)}\"</i>", corpo))

    doc.build(elems)
    return buffer.getvalue()
