Books for the Better — PDF → Booklet Converter
===============================================

A small, pure-Python tool and GUI to convert PDF page ranges into printable booklet (booklet/2-up) layout suitable for saddle-stitch printing.

Key features
------------
- GUI based on PySide6: a friendly interface to pick an input PDF, set page ranges, add page numbers, rotate even pages for duplex, and produce a ready-to-print booklet PDF.
- Command-line interface (CLI) for scripted use and automation.
- Programmatic API: call build_booklet(...) from other Python code.
- Pure-Python PDF processing using pypdf and reportlab (no external CLI tools required).
- Windows-friendly portable setup included (setup.bat creates an embedded Python and installs dependencies locally).

Project layout
--------------
- [programa](/C:/Users/vsara/Desktop/books_for_the_better/programa/) — application folder
  - [app.py](/C:/Users/vsara/Desktop/books_for_the_better/programa/app.py) — PySide6 GUI frontend
  - [booklet_maker.py](/C:/Users/vsara/Desktop/books_for_the_better/programa/booklet_maker.py) — conversion core (CLI + programmatic API)
  - [requirements.txt](/C:/Users/vsara/Desktop/books_for_the_better/programa/requirements.txt) — Python dependencies
  - icon.ico — optional shortcut icon used by setup script
- [setup.bat](/C:/Users/vsara/Desktop/books_for_the_better/setup.bat) — convenience script for Windows that downloads a portable Python and installs dependencies locally

Quick start (Windows)
----------------------
Option A — Use the included portable setup (recommended for Windows users who want a self-contained app):

1. Double-click or run [setup.bat](/C:/Users/vsara/Desktop/books_for_the_better/setup.bat).
   - The script downloads an embedded Python distribution (if missing), enables site-packages, installs pip, and installs the dependencies from [programa/requirements.txt].
   - It also creates a "conversor_booklet.lnk" shortcut in the repository folder and attempts to place one on the Desktop.
2. Use the created shortcut to launch the GUI (it runs app.py with the local pythonw.exe) or run the GUI manually:
   - From a command prompt: C:\Users\...\programa\python_dist\python.exe app.py

Option B — Use your system Python

1. Ensure Python 3.10+ is installed and available on PATH.
2. Install dependencies:
   - pip install -r programa\requirements.txt
3. Run the GUI:
   - python programa\app.py
4. Or run the CLI:
   - python programa\booklet_maker.py input.pdf --part-size 28 --start 1 --end 100 --output livro.pdf

CLI usage example
-----------------
Basic command-line invocation:

python programa\booklet_maker.py <input.pdf> --part-size <pages-per-part> --start <first-page> --end <last-page> --output <final.pdf>

Options and notes:
- --part-size: number of pages per "signature" (e.g., 28 is a reasonable default). The tool splits the extracted range into consecutive parts of up to this size and converts each into booklet layout.
- --start / --end: inclusive 1-based page numbers within the source PDF.
- --output: name or path of the final PDF. If you pass a filename without a directory, the output will be created inside the program folder; otherwise the resolved parent directory is used—but note: the output directory must NOT be the program folder or a subfolder of it.
- --rotate-even: optional flag to rotate even pages (useful for duplex printers that expect alternating rotations).
- --number-start / --number-end: optional page-number stamping on the extracted document (use both together).

Example:

python programa\booklet_maker.py "my_document.pdf" --part-size 28 --start 1 --end 56 --output "my_book.pdf" --rotate-even --number-start 1 --number-end 56

Programmatic usage (from Python)
--------------------------------
The core function build_booklet(...) can be used from other Python code. Example:

from pathlib import Path
from programa.booklet_maker import build_booklet, PipelineError

try:
    out = build_booklet(
        input_pdf=Path("/path/to/input.pdf"),
        output_pdf=Path("/path/to/output.pdf"),
        part_size=28,
        extract_start=1,
        extract_end=56,
        rotate_even=True,
        number_start=1,
        number_end=56,
        impose_margin=10,  # percentage to shrink page content inside imposed slot
        page_number_position=5,  # percentage from bottom for page number placement
    )
    print("Finished:", out)
except PipelineError as exc:
    print("Conversion failed:", exc)

Notes and important behavior
----------------------------
- The code is intentionally pure-Python and does not require qpdf/psbook/psnup external tools.
- The output file is written under a work subfolder whose name is derived from the output file stem (sanitized). For example, --output "my_book.pdf" will place the final PDF at <output_dir>/my_book/my_book.pdf.
- The output directory must not be the application folder (the code checks and raises an error to avoid accidentally overwriting inputs or program files).
- When using the CLI on Windows, ProcessPoolExecutor uses spawn and re-imports __main__, so any scripts that call the pipeline directly must guard entry points with if __name__ == "__main__": (the project already follows this pattern).

Dependencies
------------
- pypdf
- reportlab
- PySide6 (for the GUI)

These are listed in [programa/requirements.txt](/C:/Users/vsara/Desktop/books_for_the_better/programa/requirements.txt).

Troubleshooting
---------------
- "Output directory cannot be the program folder": Make sure the chosen output directory is outside the repo/program folder.
- If the GUI cannot read a PDF or reports an invalid PDF, try opening it in a normal viewer to confirm it's not corrupted. The GUI uses pypdf to determine page count and read pages.
- On Windows, if you run into issues with the bundled portable Python, try using a system Python installation and installing the requirements manually.

Development notes
-----------------
- The GUI implementation is in [app.py](/C:/Users/vsara/Desktop/books_for_the_better/programa/app.py).
- The conversion pipeline and CLI live in [booklet_maker.py](/C:/Users/vsara/Desktop/books_for_the_better/programa/booklet_maker.py). The function build_booklet(...) is the recommended programmatic entry point for other code.
- If adding tests or automation, prefer calling build_booklet(...) directly rather than invoking main() to avoid ProcessPoolExecutor import/Windows spawn pitfalls.

Contributing
------------
Contributions are welcome. Suggestions:
- Add unit tests around page-order generation, range splitting, and PDF assembly.
- Improve internationalization (current UI strings are Portuguese).
- Add an installer or packaging for Windows (MSI) or cross-platform packaging (PyInstaller, Briefcase).

Please open issues or a PR with a focused change. If adding changes that affect packaging or dependencies, include an updated instructions section.

License
-------
No LICENSE file is included in this repository. If this code should be redistributed, add a suitable LICENSE file (MIT, Apache-2.0, etc.).

Support / Contact
-----------------
For quick questions about running the tool, examine the source files:
- [booklet_maker.py](/C:/Users/vsara/Desktop/books_for_the_better/programa/booklet_maker.py)
- [app.py](/C:/Users/vsara/Desktop/books_for_the_better/programa/app.py)

Happy printing!
