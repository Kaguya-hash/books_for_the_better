# PDF Book Converter

This script processes a PDF by extracting a page range, splitting it into parts, converting each part into a book layout, rotating pages, and merging the result into a final PDF.

## What it does

- Reads an input PDF file
- Extracts pages from the specified start and end range into `to_convert.pdf`
- Splits that PDF into parts based on the given part size
- Converts each part to book layout using `pdftops`, `psbook`, `psnup`, and `ps2pdf`
- Rotates the generated pages by 90 degrees
- Merges all book parts into `livro.pdf`
- Optionally applies an extra rotation to even pages when the last parameter is non-zero
- Renames the final output file to the requested output name
- Deletes temporary files after completion

## Requirements

- Python 3
- `PyPDF2`
- `qpdf`
- `pdftops`, `psbook`, `psnup`, `ps2pdf`

## Install

```bash
pip install -r requirements.txt
```

> Install `qpdf`, `poppler`, and `ghostscript` through your system package manager or Windows installers.

## Usage

```bash
python pdf_livro.py <input.pdf> <part_size> <start_page> <end_page> <output.pdf> <0|1>
```

Example:

```bash
python pdf_livro.py book.pdf 20 1 120 final_book.pdf 1
```

- `part_size`: number of pages per part before book layout conversion
- `start_page` and `end_page`: page range to extract from the input PDF
- `output.pdf`: final output file name
- `0|1`: if `1`, applies extra rotation to even pages in the final PDF
