"""
Convert SmartSauda Markdown Project Report into a professional Word (.docx) document.
Applies university academic formatting standards:
- 1-inch margins
- Standard typography (Times New Roman / Arial)
- Proper section page breaks (Title page, Declarations, Chapters)
- Styled tables with borders and header shading
- Monospace styling for code/architecture snippets
- Preserved inline formatting (bold, italics, code, line breaks)
"""

import re
from pathlib import Path
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "PROJECT_REPORT.md"
DOCX_OUT_PATH = ROOT / "SmartSauda_Project_Report.docx"
DOCX_DOCS_PATH = ROOT / "docs" / "SmartSauda_Project_Report.docx"


def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def set_table_borders(table, color="D3D3D3"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
        f'<w:insideV w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)


def format_inlines(paragraph, text, base_bold=False, base_italic=False, font_size=11, font_name="Times New Roman", font_color=None):
    # Normalize <br> or <br/> into newlines
    text = re.sub(r'<br\s*/?>', '\n', text)
    
    # Simple regex tokenizer for bold, italic, inline code, and plain text
    pattern = re.compile(r'(\*\*\*.*?\*\*\*|\*\*.*?\*\*|\*.*?\*|`.*?`|\[.*?\]\(.*?\)|\$.*?\$|[^\*`\[\$]+)')
    tokens = pattern.findall(text)
    
    for token in tokens:
        if not token:
            continue
        run = paragraph.add_run()
        run.font.name = font_name
        run.font.size = Pt(font_size)
        if font_color:
            run.font.color.rgb = font_color

        if token.startswith('***') and token.endswith('***') and len(token) >= 6:
            run.text = token[3:-3]
            run.bold = True
            run.italic = True
        elif token.startswith('**') and token.endswith('**') and len(token) >= 4:
            run.text = token[2:-2]
            run.bold = True
            run.italic = base_italic
        elif token.startswith('*') and token.endswith('*') and len(token) >= 2:
            run.text = token[1:-1]
            run.bold = base_bold
            run.italic = True
        elif token.startswith('`') and token.endswith('`') and len(token) >= 2:
            run.text = token[1:-1]
            run.font.name = 'Consolas'
            run.font.size = Pt(font_size - 0.5)
            run.font.color.rgb = RGBColor(160, 50, 50)
            run.bold = base_bold
        elif token.startswith('$') and token.endswith('$') and len(token) >= 2:
            run.text = token[1:-1]
            run.italic = True
            run.bold = base_bold
        elif token.startswith('[') and '](' in token and token.endswith(')'):
            match = re.match(r'\[(.*?)\]\((.*?)\)', token)
            if match:
                run.text = match.group(1)
                run.underline = True
                run.font.color.rgb = RGBColor(0, 80, 160)
            else:
                run.text = token
                run.bold = base_bold
                run.italic = base_italic
        else:
            run.text = token
            run.bold = base_bold
            run.italic = base_italic


def parse_and_create_docx():
    lines = MD_PATH.read_text(encoding="utf-8").splitlines()
    doc = docx.Document()
    
    # Configure 1-inch margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        section.page_width = Inches(8.5)
        section.page_height = Inches(11.0)

    # Base Normal Style
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(11)
    normal_style.font.color.rgb = RGBColor(30, 30, 30)
    normal_style.paragraph_format.line_spacing = 1.15
    normal_style.paragraph_format.space_after = Pt(6)

    i = 0
    n = len(lines)
    in_title_page = True

    while i < n:
        raw_line = lines[i]
        line = raw_line.strip()

        # Handle page breaks
        if line == "---":
            doc.add_page_break()
            i += 1
            continue

        # Handle Code / Diagram blocks
        if line.startswith("```"):
            code_lines = []
            lang = line[3:].strip()
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # consume closing ```
            
            # Add shaded box for code/diagram
            tbl = doc.add_table(rows=1, cols=1)
            tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
            cell = tbl.cell(0, 0)
            set_cell_background(cell, "F5F6F8")
            set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
            set_table_borders(tbl, color="E0E2E6")
            
            cp = cell.paragraphs[0]
            cp.paragraph_format.line_spacing = 1.05
            cp.paragraph_format.space_after = Pt(2)
            code_text = "\n".join(code_lines)
            run = cp.add_run(code_text)
            run.font.name = "Consolas"
            run.font.size = Pt(9.5)
            run.font.color.rgb = RGBColor(40, 45, 55)
            continue

        # Handle Tables
        if line.startswith("|") and line.endswith("|"):
            table_lines = []
            while i < n and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            
            # Parse markdown table
            headers = [c.strip() for c in table_lines[0].split("|")[1:-1]]
            rows_data = []
            for r in table_lines[1:]:
                # skip separator row
                if re.match(r'^\|[\s\:\-]+(?:\|[\s\:\-]+)*\|$', r):
                    continue
                cells = [c.strip() for c in r.split("|")[1:-1]]
                # match column count
                if len(cells) < len(headers):
                    cells += [""] * (len(headers) - len(cells))
                elif len(cells) > len(headers):
                    cells = cells[:len(headers)]
                rows_data.append(cells)
            
            if headers:
                tbl = doc.add_table(rows=len(rows_data) + 1, cols=len(headers))
                tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                set_table_borders(tbl, color="D0D4DC")
                
                # Format header
                hdr_row = tbl.rows[0]
                for c_idx, h_text in enumerate(headers):
                    cell = hdr_row.cells[c_idx]
                    set_cell_background(cell, "EAECEF")
                    set_cell_margins(cell, top=120, bottom=120, left=140, right=140)
                    p = cell.paragraphs[0]
                    p.paragraph_format.space_after = Pt(2)
                    p.paragraph_format.space_before = Pt(2)
                    format_inlines(p, h_text, base_bold=True, font_size=10, font_name="Arial", font_color=RGBColor(20, 20, 20))
                
                # Format data rows
                for r_idx, row_vals in enumerate(rows_data):
                    data_row = tbl.rows[r_idx + 1]
                    bg = "FFFFFF" if r_idx % 2 == 0 else "F9FAFB"
                    for c_idx, val in enumerate(row_vals):
                        cell = data_row.cells[c_idx]
                        set_cell_background(cell, bg)
                        set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
                        p = cell.paragraphs[0]
                        p.paragraph_format.space_after = Pt(2)
                        p.paragraph_format.space_before = Pt(2)
                        format_inlines(p, val, base_bold=False, font_size=9.5, font_name="Times New Roman")
                
                # Spacer after table
                sp = doc.add_paragraph()
                sp.paragraph_format.space_after = Pt(6)
            continue

        # Handle Headings
        if line.startswith("# ") and not line.startswith("## "):
            heading_text = line[2:].strip()
            # If chapter heading, add a page break if not already at top
            if heading_text.startswith("CHAPTER") or heading_text.startswith("REFERENCES"):
                doc.add_page_break()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(18)
            p.paragraph_format.space_after = Pt(8)
            p.paragraph_format.keep_with_next = True
            format_inlines(p, heading_text, base_bold=True, font_size=16, font_name="Arial", font_color=RGBColor(15, 35, 75))
            i += 1
            continue

        if line.startswith("## "):
            heading_text = line[3:].strip()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.keep_with_next = True
            format_inlines(p, heading_text, base_bold=True, font_size=13.5, font_name="Arial", font_color=RGBColor(25, 45, 85))
            i += 1
            continue

        if line.startswith("### "):
            heading_text = line[4:].strip()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.keep_with_next = True
            format_inlines(p, heading_text, base_bold=True, font_size=12, font_name="Arial", font_color=RGBColor(35, 55, 95))
            i += 1
            continue

        if line.startswith("#### "):
            heading_text = line[5:].strip()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.keep_with_next = True
            format_inlines(p, heading_text, base_bold=True, font_size=11, font_name="Arial", font_color=RGBColor(45, 65, 105))
            i += 1
            continue

        # Handle Bullet Lists
        if line.startswith("- ") or line.startswith("* "):
            bullet_text = line[2:].strip()
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.space_before = Pt(0)
            format_inlines(p, bullet_text, font_size=11, font_name="Times New Roman")
            i += 1
            continue

        # Handle Numbered Lists
        num_match = re.match(r'^(\d+)\.\s+(.*)$', line)
        if num_match:
            item_text = num_match.group(2)
            p = doc.add_paragraph(style='List Number')
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.space_before = Pt(0)
            format_inlines(p, item_text, font_size=11, font_name="Times New Roman")
            i += 1
            continue

        # Handle Empty lines
        if not line:
            i += 1
            continue

        # Normal Paragraph
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.15
        
        # Check if line looks like a figure or table title caption
        if line.startswith("*Figure ") or line.startswith("*Table "):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            format_inlines(p, line, base_italic=True, font_size=10, font_name="Arial", font_color=RGBColor(80, 80, 80))
        elif line.startswith("Submitted By:") or line.startswith("Under the Supervision of:") or line.startswith("PROJECT REPORT ON"):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            format_inlines(p, line, font_size=11, font_name="Times New Roman")
        else:
            format_inlines(p, line, font_size=11, font_name="Times New Roman")

        i += 1

    doc.save(str(DOCX_OUT_PATH))
    doc.save(str(DOCX_DOCS_PATH))
    print(f"Successfully generated DOCX files:\n- {DOCX_OUT_PATH}\n- {DOCX_DOCS_PATH}")


if __name__ == "__main__":
    parse_and_create_docx()
