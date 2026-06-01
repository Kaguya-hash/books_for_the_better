# Conversor de Livros em PDF

Este script divide um PDF em partes, converte cada parte em layout de livro, gira páginas quando necessário e une tudo em um arquivo final.

## O que ele faz

- Recebe um arquivo PDF de entrada
- Extrai páginas do intervalo informado e salva em `to_convert.pdf`
- Divide o PDF em partes fixas pelo tamanho informado
- Converte cada parte para formato de livro usando `pdftops`, `psbook`, `psnup` e `ps2pdf`
- Gira as páginas resultantes em 90 graus
- Une os arquivos gerados em `livro.pdf`
- Aplica rotação adicional em páginas pares se o último parâmetro for diferente de zero
- Renomeia o resultado final para o nome de saída informado
- Remove arquivos temporários gerados durante o processo

## Requisitos

- Python 3
- `PyPDF2` (depósito Python)
- `qpdf` (CLI)
- `pdftops`, `psbook`, `psnup`, `ps2pdf` (ferramentas de manipulação de PDF/PostScript)

## Instalação

```bash
pip install -r requirements.txt
```

> Instale `qpdf`, `poppler` e `ghostscript` pelo gerenciador do sistema ou pacotes nativos do Windows.

## Uso

```bash
python pdf_livro.py <arquivo_entrada.pdf> <tamanho_parte> <inicio> <fim> <arquivo_saida.pdf> <0|1>
```

Exemplo:

```bash
python pdf_livro.py livro.pdf 20 1 120 livro_final.pdf 1
```

- `tamanho_parte`: número de páginas por parte antes de rearranjar em formato de livro
- `inicio` e `fim`: intervalo de páginas a extrair para conversão inicial
- `arquivo_saida.pdf`: nome do PDF final
- `0|1`: se `1`, roda páginas pares adicionais no resultado final
