#!/usr/bin/env python3
"""generate_pdf.py

Simple helper to convert the guideline Markdown to DOCX and PDF.

Usage:
    python generate_pdf.py MES_Input_Tag_Monitors_Guide.md

Requires either pypandoc (which bundles pandoc) or a system pandoc installation.
"""
import sys
import os

try:
    import pypandoc
    HAVE_PYPANDOC = True
except Exception:
    HAVE_PYPANDOC = False


def convert_with_pypandoc(src_md, out_docx, out_pdf):
    pypandoc.convert_file(src_md, 'docx', outputfile=out_docx)
    # For PDF conversion pypandoc will call pandoc; ensure LaTeX or wkhtmltopdf available for PDF output
    pypandoc.convert_file(src_md, 'pdf', outputfile=out_pdf)


def convert_with_pandoc_cli(src_md, out_docx, out_pdf):
    # Requires pandoc on PATH
    docx_cmd = f"pandoc \"{src_md}\" -o \"{out_docx}\""
    pdf_cmd = f"pandoc \"{src_md}\" -o \"{out_pdf}\""
    ret1 = os.system(docx_cmd)
    if ret1 != 0:
        raise RuntimeError('pandoc docx conversion failed')
    ret2 = os.system(pdf_cmd)
    if ret2 != 0:
        raise RuntimeError('pandoc pdf conversion failed')


def main():
    if len(sys.argv) < 2:
        print('Usage: python generate_pdf.py <source_markdown.md>')
        sys.exit(1)

    src_md = sys.argv[1]
    if not os.path.exists(src_md):
        print('Source markdown not found:', src_md)
        sys.exit(1)

    base = os.path.splitext(src_md)[0]
    out_docx = base + '.docx'
    out_pdf = base + '.pdf'

    try:
        if HAVE_PYPANDOC:
            print('Using pypandoc...')
            convert_with_pypandoc(src_md, out_docx, out_pdf)
        else:
            print('pypandoc not available; trying system pandoc...')
            convert_with_pandoc_cli(src_md, out_docx, out_pdf)
        print('Generated:', out_docx, out_pdf)
    except Exception as e:
        print('Conversion failed:', e)
        sys.exit(2)


if __name__ == '__main__':
    main()
