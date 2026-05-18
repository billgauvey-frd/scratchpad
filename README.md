# MES Input Tag Monitors - README

This repository contains the MES Input Tag Monitors guideline and helper script to generate DOCX/PDF locally.

Files:
- MES_Input_Tag_Monitors_Guide.md - Full guideline document (Markdown)
- generate_pdf.py - Helper script to convert the Markdown to DOCX and PDF using pypandoc or pandoc

How to generate DOCX and PDF locally:

Prerequisites:
- Python 3.8+
- pip
- pypandoc (optional) and pandoc installed, or pandoc available on PATH

Option A: Using pypandoc (preferred)
1. pip install pypandoc
2. Run: python generate_pdf.py MES_Input_Tag_Monitors_Guide.md

Option B: Using pandoc directly
1. Install pandoc (https://pandoc.org/installing.html)
2. Run: python generate_pdf.py MES_Input_Tag_Monitors_Guide.md --use-pandoc

The script will produce:
- MES_Input_Tag_Monitors_Guide.docx
- MES_Input_Tag_Monitors_Guide.pdf

If you have issues, ensure pandoc is installed and available on your PATH. If you need me to generate the PDF on my side and provide a base64 stream, I can also do that.
