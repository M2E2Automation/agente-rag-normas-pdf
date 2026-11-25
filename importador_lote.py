import os
import re
import shutil
import argparse
from pathlib import Path
from motor_rag import indexar_pdf, listar_documentos_indexados

PASTA_ACERVO = Path(__file__).parent / "documentos"
PASTA_ACERVO.mkdir(parents=True, exist_ok=True)

PADRAO_NORMAS = re.compile(
    r"\b(ABNT|NBR|NR[\s\-_]?\d+|IEC|ISO|LEI|DECRETO|CODIGO|PORTARIA|RESOLUCAO|MANUAL|CATALOGO|CATÁLOGO|DATASHEET|ESPECIFICACAO|EQUIPAMENTO|MAQUINA|MÁQUINA|BOMBA|MOTOR|INVERSOR|GERADOR|TRANSFORMADOR|GUIA)\b",
    flags=re.IGNORECASE,
)

def varrer_e_catalogar(diretorios_busca: list[str], filtrar_por_nome: bool = True) -> dict:
    ja_indexados = {list(d).pop(0) for d in listar_documentos_indexados()}
    copiados = 0
    indexados = 0
    ignorados_existentes = 0
    erros = 0

    for dir_str in diretorios_busca:
        raiz = Path(dir_str).expanduser()
        if not raiz.exists():
            continue

        for caminho_pdf in raiz.rglob("*.[pP][dD][fF]"):
            if PASTA_ACERVO in caminho_pdf.parents or ".venv" in caminho_pdf.parts:
                continue

            nome_limpo = caminho_pdf.name
            if filtrar_por_nome and not PADRAO_NORMAS.search(nome_limpo):
                continue

            destino = PASTA_ACERVO / nome_limpo
            if not destino.exists():
                try:
                    shutil.copy2(caminho_pdf, destino)
                    copiados += 1
                except Exception:
                    erros += 1
                    continue

            if nome_limpo in ja_indexados:
                ignorados_existentes += 1
                continue

            try:
                indexar_pdf(str(destino), nome_limpo)
                ja_indexados.add(nome_limpo)
                indexados += 1
            except Exception:
                erros += 1

    return {
        "copiados": copiados,
        "indexados": indexados,
        "ja_existiam": ignorados_existentes,
        "erros": erros,
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pastas", nargs="+", default=["~/Downloads", "~/Documentos", "~/Área de Trabalho", "~/Desktop"])
    parser.add_argument("--todos", action="store_true")
    args = parser.parse_args()
    print(varrer_e_catalogar(args.pastas, filtrar_por_nome=not args.todos))
