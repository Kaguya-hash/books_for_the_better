from PyPDF2 import PdfReader, PdfMerger
import subprocess
import os
import sys

def generate_range_pairs(total, step):
    """
    Returns a list of pairs like:
    [[1, step], [step+1, step*2], [step*2+1, step*3], ...]
    
    Continues until the last number in the last pair >= total
    
    If the last number in the last pair == total, returns pairs as is.
    Otherwise, the last number in the last pair is adjusted to the smallest
    value > total of the form p + 4n, where p is the first number in the last pair,
    and n is a natural number (n >= 1).
    """
    if total <= 0 or step <= 0:
        return []

    pairs = []
    start = 1  # First pair starts at 1

    while True:
        end = step * len(pairs) + step  # end for current pair: step, 2*step, 3*step, ...
        pairs.append([start, end])

        if end >= total:
            break

        start = end + 1  # next pair starts after current pair's end

    pairs[-1][1] = total

    return pairs

def get_pdf_page_count(pdf_path):
    reader = PdfReader(pdf_path)
    return len(reader.pages)

def run_pdf_command(file_input, page_start, page_end, chapter_filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pages_range = f"{page_start}-{page_end}"
    
    # qpdf progit.pdf --pages . 7-32 -- chapter3.pdf
    command = [
        "qpdf",
        file_input,
        "--pages",
        ".",
        pages_range,
        "--",
        chapter_filename
    ]
    
    result = subprocess.run(command, cwd=script_dir, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"Success: Created {chapter_filename} for pages {pages_range}")
    else:
        print(f"Error running command for pages {pages_range}:")
        print(result.stderr)

def run_pdf_command_book(chapter_filename, output_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))

    command = (
        f"pdftops {chapter_filename} - | "
        f"psbook | "
        f"psnup -2 -Pa4 | "
        f"ps2pdf - {output_name}"
    )

    result = subprocess.run(
        command,
        cwd=script_dir,
        shell=True,          # <-- key point
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"Success: Created book {output_name}")
    else:
        print(f"Error running command for {output_name}:")
        print(result.stderr)

def rotate_pdf_pages(angle_degrees, pdf_filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # angle_degrees: +90, -90, 180
    rotate_arg = f"--rotate={angle_degrees}:1-z"

    command = [
        "qpdf",
        rotate_arg,
        pdf_filename,
        "--replace-input"
    ]

    result = subprocess.run(
        command,
        cwd=script_dir,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"Success: Rotated all pages in {pdf_filename} by {angle_degrees}°")
    else:
        print(f"Error rotating {pdf_filename}:")
        print(result.stderr)

def merge_pdfs(pdf_list, output_path):
    pdf_writer = PdfMerger()  # New name in PyPDF2 for merging
    
    for pdf in pdf_list:
        pdf_writer.append(pdf)
    
    with open(output_path, 'wb') as out_file:
        pdf_writer.write(out_file)
    
    print(f"Merged {len(pdf_list)} files into {output_path}")




def is_natural_number(s):
    try:
        n = int(s)
        return n > 0
    except ValueError:
        return False

if len(sys.argv) != 7:
    print("Usage: python3 script.py <string> <num1> <num2> <num3> <string_2> <bool:0|1>")
    sys.exit(1)

file_input = sys.argv[1]
num1, num2, num3 = sys.argv[2], sys.argv[3], sys.argv[4]
file_output = sys.argv[5]
bool_number = sys.argv[6]

# Validate numbers
if not (is_natural_number(num1) and is_natural_number(num2) and is_natural_number(num3)):
    print("Error: All three numbers must be natural numbers (positive integers).")
    sys.exit(1)

num1 = int(num1)
num2 = int(num2)
num3 = int(num3)

if num2 > num3:
    print("Error: The second number must be less than or equal to the third number.")
    sys.exit(1)




run_pdf_command(file_input, num2, num3, "to_convert.pdf")

file_input = "to_convert.pdf"

N = get_pdf_page_count(file_input)
print(N)

partes = generate_range_pairs(N, num1)
print(partes)

commands_to_run = [
    (start, end, f"part_{i}.pdf") 
    for i, (start, end) in enumerate(partes, start=1)
]

for start, end, output_file in commands_to_run:
    run_pdf_command(file_input, start, end, output_file)

commands_to_run = [
    (f"part_{i}.pdf", f"book_part_{i}.pdf") 
    for i, (start, end) in enumerate(partes, start=1)
]

for chapter_filename, output_name in commands_to_run:
    run_pdf_command_book(chapter_filename, output_name)

commands_to_run = [
    (f"book_part_{i}.pdf") 
    for i, (start, end) in enumerate(partes, start=1)
]

for pdf_filename in commands_to_run:
    rotate_pdf_pages(90, pdf_filename)

pdf_to_merge = [f"book_part_{i}.pdf" for i in range(1, len(partes) + 1)]

merge_pdfs(pdf_to_merge, "livro.pdf")

bool_number = int(bool_number)

if bool_number != 0:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(script_dir, "livro.pdf")
    reader = PdfReader(pdf_path)
    num_pages = len(reader.pages)
    even_pages = ",".join(str(i) for i in range(2, num_pages + 1, 2))
    command = [
        "qpdf",
        f"--rotate=270:{even_pages}",
        "livro.pdf",
        "--replace-input"
    ]
    subprocess.run(command, cwd=script_dir, check=True)

os.rename("livro.pdf", file_output)

filename = "to_convert.pdf"
if os.path.exists(filename):
    os.remove(filename)
    print(f"Deleted {filename}")
else:
    print(f"{filename} does not exist")

for i in range(1, len(commands_to_run) + 1):
    filename = f"part_{i}.pdf"
    if os.path.exists(filename):
        os.remove(filename)
        print(f"Deleted {filename}")
    else:
        print(f"{filename} does not exist")

for i in range(1, len(commands_to_run) + 1):
    filename = f"book_part_{i}.pdf"
    if os.path.exists(filename):
        os.remove(filename)
        print(f"Deleted {filename}")
    else:
        print(f"{filename} does not exist")