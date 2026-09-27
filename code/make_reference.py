"""Style the Pandoc reference DOCX used by the official Quarto renderer.

Optional regeneration: provide the default Pandoc reference as the first arg.
The committed reference.docx is sufficient to reproduce the report.
"""
from pathlib import Path
import sys

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
doc = Document(sys.argv[1])
for style in doc.styles:
    if style.type in (WD_STYLE_TYPE.PARAGRAPH, WD_STYLE_TYPE.CHARACTER):
        style.font.name = "Times New Roman"
        style.font.color.rgb = RGBColor(0, 0, 0)
        if style.type == WD_STYLE_TYPE.PARAGRAPH:
            style.paragraph_format.widow_control = True
    for border in list(style.element.xpath(".//w:pBdr")):
        border.getparent().remove(border)

normal = doc.styles["Normal"]
normal.font.size = Pt(11)
normal.paragraph_format.line_spacing = 1.10
normal.paragraph_format.space_after = Pt(6)
for name in ("Body Text", "First Paragraph"):
    if name in doc.styles:
        doc.styles[name].base_style = normal
        doc.styles[name].font.size = Pt(11)
        doc.styles[name].paragraph_format.space_after = Pt(6)
        doc.styles[name].paragraph_format.line_spacing = 1.10
for name, size in (("Title", 21), ("Subtitle", 12), ("Heading 1", 14), ("Heading 2", 12), ("Heading 3", 11)):
    s = doc.styles[name]
    s.font.size = Pt(size)
    s.font.bold = name != "Subtitle"
    s.font.color.rgb = RGBColor(0, 0, 0)
    s.font.underline = False
    s.paragraph_format.space_before = Pt(13 if name.startswith("Heading") else 0)
    s.paragraph_format.space_after = Pt(6)
    s.paragraph_format.keep_with_next = True
for name in ("Caption", "Image Caption", "Table Caption"):
    if name in doc.styles:
        s = doc.styles[name]
        s.font.size = Pt(9.5)
        s.font.italic = False
        s.paragraph_format.space_before = Pt(5)
        s.paragraph_format.space_after = Pt(9)
        s.paragraph_format.keep_together = True
for name in ("Author", "Date"):
    if name in doc.styles:
        doc.styles[name].font.size = Pt(11)
        doc.styles[name].paragraph_format.space_after = Pt(4)
if "Bibliography" in doc.styles:
    s = doc.styles["Bibliography"]
    s.font.size = Pt(10)
    s.paragraph_format.space_after = Pt(5)

for s in doc.styles:
    if s.type != WD_STYLE_TYPE.TABLE:
        continue
    s.font.size = Pt(10)
    s.font.name = "Times New Roman"
    pr = s.element.find(qn("w:tblPr"))
    if pr is None:
        pr = OxmlElement("w:tblPr")
        s.element.append(pr)
    for old in list(pr.findall(qn("w:tblBorders"))):
        pr.remove(old)
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement("w:" + edge)
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), "4")
        e.set(qn("w:color"), "D9D9D9")
        borders.append(e)
    pr.append(borders)
    margins = OxmlElement("w:tblCellMar")
    for edge in ("top", "left", "bottom", "right"):
        e = OxmlElement("w:" + edge)
        e.set(qn("w:w"), "80")
        e.set(qn("w:type"), "dxa")
        margins.append(e)
    pr.append(margins)
    first = OxmlElement("w:tblStylePr")
    first.set(qn("w:type"), "firstRow")
    tcpr = OxmlElement("w:tcPr")
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), "E6EDF2")
    tcpr.append(shading)
    first.append(tcpr)
    s.element.append(first)

for section in doc.sections:
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    section.top_margin = section.bottom_margin = Inches(0.75)
    section.left_margin = section.right_margin = Inches(1)
    section.footer_distance = Inches(0.35)
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.style = doc.styles["Normal"]
    run = p.add_run()
    run.font.size = Pt(9)
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    run._r.addnext(field)
doc.core_properties.title = "ANLY 735 laboratory report styles"
doc.core_properties.author = "Suryansh Soni"
doc.save(ROOT / "reference.docx")
print("Saved reference.docx")
