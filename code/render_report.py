"""Run official Quarto, then apply deterministic Word table layout settings.

Uses only Python's standard library. Content and results are never rewritten.
"""
import argparse
from pathlib import Path
import subprocess
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NS = {"w": W[1:-1]}


def child(parent, tag):
    item = parent.find(W + tag)
    if item is None:
        item = ET.Element(W + tag)
        if tag in ("pPr", "rPr", "tcPr", "tblPr", "trPr"):
            parent.insert(0, item)
        else:
            parent.append(item)
    return item


def format_tables(path):
    with ZipFile(path) as z:
        contents = {i.filename: z.read(i.filename) for i in z.infolist()}
        infos = z.infolist()
    xml = contents["word/document.xml"]
    # Preserve known namespace prefixes instead of making them ns0, ns1, ...
    import io
    for _, (prefix, uri) in ET.iterparse(io.BytesIO(xml), events=["start-ns"]):
        if prefix and not prefix.startswith("ns"):
            ET.register_namespace(prefix, uri)
    tree = ET.fromstring(xml)
    body = tree.find("w:body", NS)
    # Quarto places a figure/table and its caption inside a one-cell layout
    # table. Unwrap those containers so only actual data tables receive borders
    # and the 6.5-inch graphics retain the full printable width.
    for wrapper in list(body.findall("w:tbl", NS)):
        rows = wrapper.findall("w:tr", NS)
        if len(rows) != 1 or len(rows[0].findall("w:tc", NS)) != 1:
            continue
        cell = rows[0].find("w:tc", NS)
        if cell.find("w:tbl", NS) is None and cell.find(".//w:drawing", NS) is None:
            continue
        index = list(body).index(wrapper)
        body.remove(wrapper)
        for element in list(cell):
            if element.tag == W + "tcPr":
                continue
            body.insert(index, element)
            index += 1
    for paragraph in body.findall("w:p", NS):
        if paragraph.find(".//w:drawing", NS) is not None:
            child(child(paragraph, "pPr"), "keepNext")
    for table in tree.findall(".//w:tbl", NS):
        rows = table.findall("w:tr", NS)
        cols = len(rows[0].findall("w:tc", NS))
        widths = [5040, 2160, 2160] if cols == 3 else [2800, 2380, 1940, 2240]
        assert sum(widths) == 9360  # 6.5 inches
        prop = child(table, "tblPr")
        child(prop, "tblLayout").set(W + "type", "fixed")
        width = child(prop, "tblW")
        width.set(W + "type", "dxa")
        width.set(W + "w", "9360")
        borders = child(prop, "tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            e = child(borders, edge)
            e.attrib.update({W + "val": "single", W + "sz": "4", W + "color": "D9D9D9"})
        grid = child(table, "tblGrid")
        for e in list(grid):
            grid.remove(e)
        for w in widths:
            ET.SubElement(grid, W + "gridCol", {W + "w": str(w)})
        for ri, row in enumerate(rows):
            rprop = child(row, "trPr")
            child(rprop, "cantSplit")
            if ri == 0:
                child(rprop, "tblHeader")
            for ci, cell in enumerate(row.findall("w:tc", NS)):
                cprop = child(cell, "tcPr")
                cwidth = child(cprop, "tcW")
                cwidth.attrib.update({W + "type": "dxa", W + "w": str(widths[ci])})
                child(cprop, "vAlign").set(W + "val", "center")
                margins = child(cprop, "tcMar")
                for edge in ("top", "left", "bottom", "right"):
                    child(margins, edge).attrib.update({W + "type": "dxa", W + "w": "80"})
                child(cprop, "shd").set(W + "fill", "E6EDF2" if ri == 0 else "FFFFFF")
                for p in cell.findall("w:p", NS):
                    pp = child(p, "pPr")
                    child(pp, "jc").set(W + "val", "left" if ci == 0 else "right")
                    child(pp, "spacing").attrib.update({W + "before": "0", W + "after": "0", W + "line": "240", W + "lineRule": "auto"})
                    child(pp, "keepLines")
                    if ri < len(rows) - 1:
                        child(pp, "keepNext")
                    for run in p.findall("w:r", NS):
                        rp = child(run, "rPr")
                        child(rp, "sz").set(W + "val", "20")
                        child(rp, "szCs").set(W + "val", "20")
                        child(rp, "color").set(W + "val", "000000")
                        if ri == 0:
                            child(rp, "b")
    # Keep table captions with the following table; keep figure captions whole.
    elements = list(body)
    for i, element in enumerate(elements[:-1]):
        if element.tag == W + "p" and elements[i + 1].tag == W + "tbl":
            child(child(element, "pPr"), "keepNext")
    contents["word/document.xml"] = ET.tostring(tree, encoding="utf-8", xml_declaration=True)
    with ZipFile(path, "w") as z:
        for info in infos:
            z.writestr(info, contents[info.filename])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quarto", default="quarto")
    args = parser.parse_args()
    subprocess.run([args.quarto, "render", "replication-lab.qmd", "--to", "docx"], cwd=ROOT, check=True)
    format_tables(ROOT / "replication-lab.docx")
    print("Formatted tables in replication-lab.docx without changing content.")
