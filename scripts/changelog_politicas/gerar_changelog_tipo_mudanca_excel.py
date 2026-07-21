"""
Gera "changelog politicas/changelog_politicas_tipo_mudanca.xlsx": mesma estrutura do
changelog_politicas_completo.xlsx, mas com a coluna "Tipo de Mudança" preenchida.

Diferente do resto da extração (mecânica, via regex/estrutura HTML), esta coluna é
classificação semântica de texto -- não dá pra fazer de forma confiável só com regras.
Por isso ela vem de "changelog politicas/classificacoes_tipo_mudanca.json", um arquivo
{chave: categoria} montado lendo a descrição de cada mudança (ver
chave_classificacao() em gerar_changelog_completo_excel.py para o formato da chave).

Fica em arquivo separado do changelog_politicas_completo.xlsx de propósito: aquele é
100% mecânico/reproduzível a qualquer momento; este depende de uma classificação que
precisa ser atualizada manualmente quando aparecem entradas novas (rode
gerar_changelog_completo_excel.py primeiro, veja quais chaves não estão em
classificacoes_tipo_mudanca.json, classifique-as e rode este script de novo).

Uso:
    python gerar_changelog_tipo_mudanca_excel.py
"""

from __future__ import annotations

import json

import openpyxl

from gerar_changelog_completo_excel import (
    HTML_PATH,
    PASTA_CHANGELOG,
    chave_classificacao,
    montar_planilha_detalhe,
    montar_planilha_produto_cia,
    montar_planilha_resumo,
    parse_changelog,
)

SAIDA_PATH = PASTA_CHANGELOG / "changelog_politicas_tipo_mudanca.xlsx"
CLASSIFICACOES_PATH = PASTA_CHANGELOG / "classificacoes_tipo_mudanca.json"


def main() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")
    linhas = parse_changelog(html)

    classificacoes = json.loads(CLASSIFICACOES_PATH.read_text(encoding="utf-8"))
    sem_classificacao = 0
    for linha in linhas:
        tipo = classificacoes.get(chave_classificacao(linha))
        if tipo:
            linha["Tipo de Mudanca"] = tipo
        else:
            sem_classificacao += 1

    wb = openpyxl.Workbook()
    montar_planilha_detalhe(wb, linhas)
    montar_planilha_resumo(wb, linhas)
    montar_planilha_produto_cia(wb, linhas)

    SAIDA_PATH.parent.mkdir(parents=True, exist_ok=True)
    wb.save(SAIDA_PATH)

    print(f"{len(linhas)} linhas geradas -> {SAIDA_PATH}")
    print(f"{sem_classificacao} linha(s) sem Tipo de Mudança classificado (entradas novas desde a última classificação).")


if __name__ == "__main__":
    main()
