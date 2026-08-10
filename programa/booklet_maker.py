"""Convert PDF page ranges into printable booklet layout (pure Python)."""

from __future__ import annotations

import argparse
import io
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Sequence

from pypdf import PageObject, PdfReader, PdfWriter, Transformation
from reportlab.pdfgen import canvas

# ---------------------------------------------------------------------------
# Constants and shared configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
INVALID_DIR_CHARS = re.compile(r'[<>:"/\\|?*]')

# Landscape A4 in PDF points (1/72 inch)
A4_LANDSCAPE_WIDTH = 842
A4_LANDSCAPE_HEIGHT = 595
IMPOSE_MARGIN_PT = 14


class PipelineError(RuntimeError):
    """Raised when a pipeline step fails."""


def check_external_tools() -> None:
    """No external CLI tools are required."""


# ---------------------------------------------------------------------------
# Interactive input helpers
# ---------------------------------------------------------------------------

def is_natural_number(value: str) -> bool:
    """Return True when ``value`` is a positive integer written as text."""
    try:
        return int(value) > 0
    except ValueError:
        return False


def ask(
    prompt: str,
    validator: Callable[[str], bool],
    error_message: str,
) -> str:
    """Read text from stdin until ``validator`` accepts the answer."""
    while True:
        answer = input(prompt).strip()
        if validator(answer):
            return answer
        #print(error_message)


def ask_int(prompt: str, validator: Callable[[int], bool], error_message: str) -> int:
    """Read and validate an integer from stdin."""
    def validate_raw(raw: str) -> bool:
        if not is_natural_number(raw):
            return False
        return validator(int(raw))

    raw = ask(prompt, validate_raw, error_message)
    return int(raw)


def ask_existing_file(prompt: str) -> Path:
    """Ask for a path and return it only when the file exists."""
    def validate(path_str: str) -> bool:
        return Path(path_str).expanduser().is_file()

    raw = ask(
        prompt,
        validate,
        "Ficheiro não encontrado. Verifique o caminho e tente novamente.",
    )
    return Path(raw).expanduser().resolve()


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    """Ask a yes/no question; blank input uses ``default``."""
    suffix = " [S/n]" if default else " [s/N]"
    while True:
        answer = input(f"{prompt}{suffix}: ").strip().lower()
        if not answer:
            return default
        if answer in {"s", "sim", "y", "yes"}:
            return True
        if answer in {"n", "nao", "não", "no"}:
            return False
        #print("Resposta inválida. Escreva 's' para sim ou 'n' para não.")


def ask_optional_yes_no(prompt: str) -> bool | None:
    """Return True/False for explicit answers, None when the user skips."""
    while True:
        answer = input(f"{prompt} [s/N] (Enter para saltar): ").strip().lower()
        if not answer:
            return None
        if answer in {"s", "sim", "y", "yes"}:
            return True
        if answer in {"n", "nao", "não", "no"}:
            return False
        #print("Resposta inválida. Escreva 's', 'n', ou Enter para saltar.")


def confirm_overwrite(path: Path) -> bool:
    """Ask whether an existing output file may be replaced."""
    if not path.exists():
        return True
    return ask_yes_no(f"'{path.name}' já existe. Substituir?", default=False)


# ---------------------------------------------------------------------------
# Path and page-range helpers
# ---------------------------------------------------------------------------

def sanitize_dir_name(name: str) -> str:
    """Make a filesystem-safe folder name from the output PDF stem."""
    cleaned = INVALID_DIR_CHARS.sub("_", name.strip())
    cleaned = cleaned.rstrip(". ")
    if not cleaned or not cleaned.strip("_"):
        return "livro"
    return cleaned


def is_path_under_script_dir(path: Path) -> bool:
    """Return True when ``path`` is the script directory or inside it."""
    resolved = path.expanduser().resolve()
    script = SCRIPT_DIR.resolve()
    if resolved == script:
        return True
    try:
        resolved.relative_to(script)
        return True
    except ValueError:
        return False


def resolve_booklet_output_path(output_base: Path, output_name: str) -> Path:
    """Return the final PDF path inside a work subfolder named after the output stem."""
    base = output_base.expanduser().resolve()
    name = Path(output_name).name
    return base / sanitize_dir_name(Path(name).stem) / name


def generate_range_pairs(total: int, step: int) -> list[list[int]]:
    """
    Split ``total`` pages into consecutive ranges of up to ``step`` pages.

    Each pair is ``[start, end]`` using 1-based inclusive page numbers.
    Ranges cover the document without gaps or overlaps, e.g. for total=25
    and step=10: ``[[1, 10], [11, 20], [21, 25]]``.
    """
    if total <= 0 or step <= 0:
        return []

    pairs: list[list[int]] = []
    start = 1

    while True:
        end = step * len(pairs) + step
        pairs.append([start, end])
        if end >= total:
            break
        start = end + 1

    pairs[-1][1] = total
    return pairs


def get_pdf_page_count(pdf_path: Path) -> int:
    """Return the number of pages in a PDF file."""
    reader = PdfReader(str(pdf_path))
    return len(reader.pages)


# ---------------------------------------------------------------------------
# Pure-Python PDF extract and booklet imposition
# ---------------------------------------------------------------------------

def run_qpdf_extract(
    file_input: Path,
    page_start: int,
    page_end: int,
    output_path: Path,
    *,
    cwd: Path,
) -> None:
    """Extract an inclusive 1-based page range from a PDF (qpdf-compatible semantics)."""
    del cwd  # kept for call-site compatibility with pdf_livro.py
    reader = PdfReader(str(file_input))
    writer = PdfWriter()
    first_index = page_start - 1
    last_index = page_end  # exclusive upper bound for range()
    if first_index < 0 or last_index > len(reader.pages):
        raise PipelineError(
            f"Intervalo inválido {page_start}-{page_end} "
            f"(documento tem {len(reader.pages)} páginas)."
        )
    for page_index in range(first_index, last_index):
        writer.add_page(reader.pages[page_index])
    with output_path.open("wb") as out_file:
        writer.write(out_file)


def booklet_page_order(padded_count: int) -> list[int]:
    """
    Return 1-based page indices in saddle-stitch order (``psbook`` equivalent).

    ``padded_count`` must be a positive multiple of 4.
    """
    if padded_count <= 0 or padded_count % 4 != 0:
        raise ValueError("padded_count must be a positive multiple of 4")

    low = 1
    high = padded_count
    order: list[int] = []

    while low <= high:
        order.append(high)
        high -= 1
        if low > high:
            break
        order.append(low)
        low += 1
        if low > high:
            break
        order.append(low)
        low += 1
        if low > high:
            break
        order.append(high)
        high -= 1

    return order


def _page_size_points(page: PageObject) -> tuple[float, float]:
    box = page.mediabox
    return float(box.width), float(box.height)


def _fit_transform(
    src_width: float,
    src_height: float,
    box_x: float,
    box_y: float,
    box_width: float,
    box_height: float,
    impose_margin: float
) -> Transformation:
    """Uniform scale and translate to center ``src`` inside a layout box."""
    inner_width = box_width - (box_width * impose_margin / 100)
    inner_height = box_height - (box_height * impose_margin / 100)
    scale = min(inner_width / src_width, inner_height / src_height)
    scaled_width = src_width * scale
    scaled_height = src_height * scale
    tx = box_x + (box_width - scaled_width) / 2
    ty = box_y + (box_height - scaled_height) / 2
    return Transformation().scale(scale, scale).translate(tx, ty)


def run_booklet_pipeline(chapter_filename: Path, output_name: Path, *, cwd: Path) -> None:
    """
    Convert a PDF chunk into 2-up booklet layout (``psbook`` + ``psnup -2 -Pa4``).

    Operates on one signature-sized part at a time.
    """
    del cwd
    try:
        reader = PdfReader(str(chapter_filename))
        num_pages = len(reader.pages)
        padded_count = ((num_pages + 3) // 4) * 4
        order = booklet_page_order(padded_count)

        sheet_width = A4_LANDSCAPE_WIDTH
        sheet_height = A4_LANDSCAPE_HEIGHT
        half_width = sheet_width / 2

        writer = PdfWriter()
        for pair_start in range(0, len(order), 2):
            left_num = order[pair_start]
            right_num = order[pair_start + 1]
            out_page = PageObject.create_blank_page(
                width=sheet_width,
                height=sheet_height,
            )

            for slot, page_num in enumerate((left_num, right_num)):
                if page_num > num_pages:
                    continue
                source_page = reader.pages[page_num - 1]
                src_w, src_h = _page_size_points(source_page)
                box_x = slot * half_width
                transform = _fit_transform(
                    src_w,
                    src_h,
                    box_x,
                    0,
                    half_width,
                    sheet_height,
                )
                out_page.merge_transformed_page(source_page, transform)

            writer.add_page(out_page)

        with output_name.open("wb") as out_file:
            writer.write(out_file)
    except Exception as exc:
        raise PipelineError(
            f"Falha na conversão booklet de {chapter_filename.name}: {exc}"
        ) from exc


def run_booklet_pipeline_from_range(
    source_pdf: Path,
    page_start: int,
    page_end: int,
    output_name: Path,
    impose_margin: float,
    *,
    cwd: Path,
) -> None:
    """
    Convert an inclusive page range from a PDF into 2-up booklet layout.

    Operates on one signature-sized part at a time without an intermediate extract.
    """
    del cwd
    reader = PdfReader(str(source_pdf))
    total_pages = len(reader.pages)
    if page_start < 1 or page_end > total_pages:
        raise PipelineError(
            f"Intervalo inválido {page_start}-{page_end} "
            f"(documento tem {total_pages} páginas)."
        )

    try:
        num_pages = page_end - page_start + 1
        padded_count = ((num_pages + 3) // 4) * 4
        order = booklet_page_order(padded_count)

        sheet_width = A4_LANDSCAPE_WIDTH
        sheet_height = A4_LANDSCAPE_HEIGHT
        half_width = sheet_width / 2

        writer = PdfWriter()
        for pair_start in range(0, len(order), 2):
            left_num = order[pair_start]
            right_num = order[pair_start + 1]
            out_page = PageObject.create_blank_page(
                width=sheet_width,
                height=sheet_height,
            )

            for slot, page_num in enumerate((left_num, right_num)):
                if page_num > num_pages:
                    continue
                global_index = (page_start - 1) + (page_num - 1)
                source_page = reader.pages[global_index]
                src_w, src_h = _page_size_points(source_page)
                box_x = slot * half_width
                transform = _fit_transform(
                    src_w,
                    src_h,
                    box_x,
                    0,
                    half_width,
                    sheet_height,
                    impose_margin=impose_margin
                )
                out_page.merge_transformed_page(source_page, transform)

            writer.add_page(out_page)

        with output_name.open("wb") as out_file:
            writer.write(out_file)
    except PipelineError:
        raise
    except Exception as exc:
        raise PipelineError(
            f"Falha na conversão booklet de {source_pdf.name}: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# PDF assembly and page numbering
# ---------------------------------------------------------------------------

def merge_pdfs(pdf_list: Sequence[Path], output_path: Path) -> None:
    """Append several PDF files into a single output file."""
    writer = PdfWriter()
    paths = list(pdf_list)
    for pdf in paths:
        reader = PdfReader(str(pdf))
        for page in reader.pages:
            writer.add_page(page)

    with output_path.open("wb") as out_file:
        writer.write(out_file)


def create_page_number_overlay(page_width: float, page_height: float, number: int, page_number_position: float) -> PdfReader:
    """Build a one-page PDF overlay with a centered page number."""
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    pdf.setFont("Helvetica", 10)
    text = str(number)
    pdf.drawCentredString(page_width / 2, page_height * page_number_position / 100, text)
    pdf.save()
    buffer.seek(0)
    return PdfReader(buffer)


def add_page_numbers(pdf_path: Path, number_start: int, number_end: int, page_number_position: float) -> None:
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    current_number = 1

    for index, page in enumerate(reader.pages, start=1):
        if number_start <= index <= number_end:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            overlay_reader = create_page_number_overlay(width, height, current_number, page_number_position)
            page.merge_page(overlay_reader.pages[0])
            current_number += 1
        writer.add_page(page)

    tmp_path = pdf_path.with_suffix(".tmp.pdf")
    with tmp_path.open("wb") as out_file:
        writer.write(out_file)
    tmp_path.replace(pdf_path)


def rotate_even_pages(pdf_path: Path) -> None:
    """Rotate only even pages, used for duplex printing alignment."""
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    for index, page in enumerate(reader.pages, start=1):
        if index % 2 == 0:
            page.rotate(270)
        writer.add_page(page)

    tmp_path = pdf_path.with_suffix(".tmp.pdf")
    with tmp_path.open("wb") as out_file:
        writer.write(out_file)
    tmp_path.replace(pdf_path)


# ---------------------------------------------------------------------------
# Parallel worker for one booklet part
# ---------------------------------------------------------------------------

def process_part(
    part_num: int,
    source_pdf: str,
    page_start: int,
    page_end: int,
    impose_margin: float,
    work_dir: str,
) -> str:
    """
    Convert one page range into booklet layout in a worker process.

    Returns the path to the finished booklet PDF for this part.
    """
    work_path = Path(work_dir)
    source = Path(source_pdf)
    book_pdf = work_path / f"book_part_{part_num}.pdf"

    try:
        run_booklet_pipeline_from_range(
            source,
            page_start,
            page_end,
            book_pdf,
            impose_margin=impose_margin,
            cwd=work_path,
        )
        return str(book_pdf)
    except Exception as exc:
        raise PipelineError(f"Parte {part_num} (páginas {page_start}-{page_end}): {exc}") from exc


# ---------------------------------------------------------------------------
# Job configuration
# ---------------------------------------------------------------------------

class JobConfig:
    """All user-selected parameters for one conversion run."""

    def __init__(
        self,
        input_pdf: Path,
        part_size: int,
        extract_start: int,
        extract_end: int,
        output_pdf: Path,
        rotate_even: bool,
        number_start: int | None = None,
        number_end: int | None = None,
        impose_margin: float = 10,
        page_number_position: float = 5,
    ) -> None:
        self.input_pdf = input_pdf
        self.part_size = part_size
        self.extract_start = extract_start
        self.extract_end = extract_end
        self.output_pdf = output_pdf
        self.rotate_even = rotate_even
        self.number_start = number_start
        self.number_end = number_end
        self.impose_margin = impose_margin
        self.page_number_position = page_number_position

    @property
    def extracted_page_count(self) -> int:
        return self.extract_end - self.extract_start + 1

    @property
    def work_dir(self) -> Path:
        return self.output_pdf.parent


# ---------------------------------------------------------------------------
# Main conversion pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    config: JobConfig,
    *,
    on_progress: Callable[[str], None] | None = None,
) -> None:
    """Run the full extract → split → booklet → merge workflow."""
    report = on_progress if on_progress is not None else print

    work_dir = config.work_dir
    work_dir.mkdir(parents=True, exist_ok=True)

    report(f"A processar {config.input_pdf.name}...")

    # Step 1: extract the requested page range from the source PDF.
    to_convert = work_dir / "primitive_book.pdf"
    run_qpdf_extract(
        config.input_pdf,
        config.extract_start,
        config.extract_end,
        to_convert,
        cwd=work_dir,
    )

    # Step 2: optionally stamp page numbers on the extracted document.
    if config.number_start is not None and config.number_end is not None:
        add_page_numbers(to_convert, config.number_start, config.number_end, page_number_position=config.page_number_position)

    page_count = get_pdf_page_count(to_convert)
    partes = generate_range_pairs(page_count, config.part_size)
    report(f"A converter {len(partes)} partes...")

    # Step 3: convert each part in parallel worker processes.
    max_workers = max(1, (os.cpu_count() or 2) - 1)
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                process_part,
                index,
                str(to_convert),
                start,
                end,
                impose_margin=config.impose_margin,
                work_dir=str(work_dir),
            ): index
            for index, (start, end) in enumerate(partes, start=1)
        }

        results: dict[int, str] = {}
        for future in as_completed(futures):
            part_index = futures[future]
            results[part_index] = future.result()

    book_paths = [Path(results[index]) for index in sorted(results)]

    # Step 4: merge all booklet parts into the final PDF (same folder as intermediates).
    if config.output_pdf.exists():
        config.output_pdf.unlink()

    merge_pdfs(book_paths, config.output_pdf)

    # Step 5: optional rotation of even pages for duplex printing.
    if config.rotate_even:
        rotate_even_pages(config.output_pdf)

    report(f"Concluído: {config.output_pdf}")


def build_booklet(
    input_pdf: Path | str,
    output_pdf: Path | str,
    part_size: int,
    extract_start: int,
    extract_end: int,
    rotate_even: bool = False,
    number_start: int | None = None,
    number_end: int | None = None,
    impose_margin: float = 10,
    page_number_position: float = 5,
    on_progress: Callable[[str], None] | None = None,
) -> Path:
    """Programmatic entry point for GUI/other callers. Builds a JobConfig
    and runs the existing extract -> optional numbering -> split ->
    booklet -> merge -> optional rotate pipeline. Returns the final
    output path. Raises PipelineError on any failure. Never calls
    input(), sys.exit(), or blocks on stdin."""
    input_path = Path(input_pdf).expanduser().resolve()
    requested_output = Path(output_pdf).expanduser().resolve()
    output_base = requested_output.parent
    output_path = resolve_booklet_output_path(output_base, requested_output.name)

    if not input_path.is_file():
        raise PipelineError(f"Ficheiro de entrada não encontrado: {input_path}")

    if part_size <= 0 or extract_start <= 0 or extract_end <= 0:
        raise PipelineError("part_size, extract_start e extract_end devem ser números naturais.")

    if extract_start > extract_end:
        raise PipelineError("extract_start deve ser menor ou igual a extract_end.")

    total_pages = get_pdf_page_count(input_path)
    if extract_end > total_pages:
        raise PipelineError(
            f"extract_end ({extract_end}) excede o total de páginas ({total_pages})."
        )

    if impose_margin < 0 or impose_margin > 100:
        raise PipelineError("impose_margin deve estar entre 0 e 100.")

    if page_number_position < 0 or page_number_position > 100:
        raise PipelineError("page_number_position deve estar entre 0 e 100.")

    if (number_start is None) ^ (number_end is None):
        raise PipelineError("number_start e number_end devem ser usados em conjunto.")

    if is_path_under_script_dir(output_base):
        raise PipelineError(
            "A pasta de saída não pode ser a pasta do programa nem uma subpasta dela."
        )

    extracted_count = extract_end - extract_start + 1
    if number_start is not None and number_end is not None:
        if number_start > number_end:
            raise PipelineError("number_start deve ser menor ou igual a number_end.")
        if number_end > extracted_count:
            raise PipelineError(
                f"number_end ({number_end}) excede as páginas extraídas ({extracted_count})."
            )

    config = JobConfig(
        input_pdf=input_path,
        part_size=part_size,
        extract_start=extract_start,
        extract_end=extract_end,
        output_pdf=output_path,
        rotate_even=rotate_even,
        number_start=number_start,
        number_end=number_end,
        impose_margin=impose_margin,
        page_number_position=page_number_position,
    )
    run_pipeline(config, on_progress=on_progress)
    return output_path


# Scripts that call build_booklet must be guarded with `if __name__ == "__main__":`
# because ProcessPoolExecutor uses spawn on Windows and re-imports __main__.


def collect_params_interactive() -> JobConfig:
    """Collect conversion settings through terminal prompts."""
    #print("Conversor PDF para livro — preencha os dados abaixo.\n")

    input_pdf = ask_existing_file("PDF de entrada: ")

    total_pages = get_pdf_page_count(input_pdf)
    #print(f"Total de páginas no PDF: {total_pages}\n")

    extract_start = ask_int(
        "Página inicial a extrair: ",
        lambda value: value <= total_pages,
        f"Introduza um número entre 1 e {total_pages}.",
    )
    extract_end = ask_int(
        "Página final a extrair: ",
        lambda value: extract_start <= value <= total_pages,
        f"Introduza um número entre {extract_start} e {total_pages}.",
    )

    part_size = ask_int(
        "Páginas por parte (antes da conversão booklet): ",
        lambda value: True,
        "Introduza um número maior que zero.",
    )

    while True:
        output_name = ask(
            "Nome do PDF final (ex.: livro.pdf): ",
            lambda value: bool(value.strip()),
            "O nome não pode estar vazio.",
        )
        output_pdf = SCRIPT_DIR / output_name
        if confirm_overwrite(output_pdf):
            break

    rotate_even = ask_yes_no("Rodar páginas pares no PDF final?", default=False)

    extracted_count = extract_end - extract_start + 1
    number_start: int | None = None
    number_end: int | None = None

    numbering_choice = ask_optional_yes_no("Adicionar numeração de páginas?")
    if numbering_choice:
        number_start = ask_int(
            "Primeira página a numerar (no documento extraído): ",
            lambda value: value <= extracted_count,
            f"Introduza um número entre 1 e {extracted_count}.",
        )
        number_end = ask_int(
            "Última página a numerar (no documento extraído): ",
            lambda value: number_start <= value <= extracted_count,
            f"Introduza um número entre {number_start} e {extracted_count}.",
        )

    return JobConfig(
        input_pdf=input_pdf,
        part_size=part_size,
        extract_start=extract_start,
        extract_end=extract_end,
        output_pdf=output_pdf,
        rotate_even=rotate_even,
        number_start=number_start,
        number_end=number_end,
    )


def parse_args(argv: Sequence[str] | None = None) -> JobConfig | None:
    """Parse CLI arguments into a ``JobConfig``."""
    parser = argparse.ArgumentParser(
        description="Converte um intervalo de páginas PDF para layout de livro (booklet).",
    )
    parser.add_argument("input", type=Path, help="PDF de entrada")
    parser.add_argument("--part-size", type=int, required=True, help="Páginas por parte")
    parser.add_argument("--start", type=int, required=True, help="Página inicial a extrair")
    parser.add_argument("--end", type=int, required=True, help="Página final a extrair")
    parser.add_argument("--output", type=Path, required=True, help="Nome do PDF final")
    parser.add_argument(
        "--rotate-even",
        action="store_true",
        help="Rodar páginas pares no PDF final",
    )
    parser.add_argument(
        "--number-start",
        type=int,
        default=None,
        help="Página inicial da numeração (no documento extraído)",
    )
    parser.add_argument(
        "--number-end",
        type=int,
        default=None,
        help="Página final da numeração (no documento extraído)",
    )

    args = parser.parse_args(argv)

    if (args.number_start is None) ^ (args.number_end is None):
        parser.error("--number-start e --number-end devem ser usados em conjunto.")

    if args.part_size <= 0 or args.start <= 0 or args.end <= 0:
        parser.error("part-size, start e end devem ser números naturais.")

    if args.start > args.end:
        parser.error("start deve ser menor ou igual a end.")

    input_pdf = args.input.expanduser().resolve()
    if not input_pdf.is_file():
        parser.error(f"Ficheiro de entrada não encontrado: {input_pdf}")

    total_pages = get_pdf_page_count(input_pdf)
    if args.end > total_pages:
        parser.error(f"end ({args.end}) excede o total de páginas ({total_pages}).")

    extracted_count = args.end - args.start + 1
    if args.number_start is not None and args.number_end is not None:
        if args.number_start > args.number_end:
            parser.error("number-start deve ser menor ou igual a number-end.")
        if args.number_end > extracted_count:
            parser.error(
                f"number-end ({args.number_end}) excede as páginas extraídas ({extracted_count})."
            )

    output_pdf = SCRIPT_DIR / args.output.name if args.output.parent == Path(".") else args.output.resolve()

    return JobConfig(
        input_pdf=input_pdf,
        part_size=args.part_size,
        extract_start=args.start,
        extract_end=args.end,
        output_pdf=output_pdf,
        rotate_even=args.rotate_even,
        number_start=args.number_start,
        number_end=args.number_end,
    )



def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for interactive mode and CLI usage."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError, ValueError):
        pass

    try:
        check_external_tools()
    except PipelineError as exc:
        #print(exc)
        return 1

    args = list(argv if argv is not None else sys.argv[1:])

    try:
        config = parse_args(args) if args else collect_params_interactive()
        if config is None:
            return 1
        run_pipeline(config)
    except PipelineError as exc:
        #print(f"Erro: {exc}")
        return 1
    except KeyboardInterrupt:
        #print("Operação cancelada.")
        return 130

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
