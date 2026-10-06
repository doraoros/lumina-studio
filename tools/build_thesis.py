# -*- coding: utf-8 -*-
"""Build the Lumina bachelor-thesis draft as a Word document."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt, RGBColor
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "Lumina-lucrare-licenta.docx"
FIG = ROOT / "docs" / "figuri"

TIMES = Path(r"C:\Windows\Fonts\times.ttf")
if TIMES.exists():
    font_manager.fontManager.addfont(str(TIMES))
    plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["axes.unicode_minus"] = False


def _set_run_font(run, name="Times New Roman", size=12, bold=False, italic=False, color=None):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color is not None:
        run.font.color.rgb = RGBColor(*color)


def _shade(cell, hex_color):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    shd.set(qn("w:val"), "clear")
    tcPr.append(shd)


def _borders(table):
    tbl = table._tbl
    tblPr = tbl.tblPr if tbl.tblPr is not None else OxmlElement("w:tblPr")
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), "444444")
        borders.append(element)
    tblPr.append(borders)


def _paragraph_format(paragraph, *, indent=True, align="justify", before=0, after=8, spacing=1.5):
    fmt = paragraph.paragraph_format
    fmt.line_spacing = spacing
    fmt.space_before = Pt(before)
    fmt.space_after = Pt(after)
    fmt.first_line_indent = Cm(1.25) if indent else Cm(0)
    paragraph.alignment = {
        "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "left": WD_ALIGN_PARAGRAPH.LEFT,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
    }[align]


def _add_field(paragraph, instruction):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(separate)
    shown = paragraph.add_run("Cuprinsul se actualizează la deschiderea în Word.")
    _set_run_font(shown, size=12, italic=True)
    run2 = paragraph.add_run()
    run2._r.append(end)


class Thesis:
    def __init__(self):
        self.doc = Document()
        self._setup()

    def _setup(self):
        section = self.doc.sections[0]
        section.page_width = Mm(210)
        section.page_height = Mm(297)
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(3.0)
        section.right_margin = Cm(2.0)
        section.header_distance = Cm(1.25)
        section.footer_distance = Cm(1.25)

        normal = self.doc.styles["Normal"]
        normal.font.name = "Times New Roman"
        normal.font.size = Pt(12)
        normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        pf = normal.paragraph_format
        pf.line_spacing = 1.5
        pf.space_after = Pt(8)

        for style_name, size in (("Heading 1", 16), ("Heading 2", 14), ("Heading 3", 12)):
            style = self.doc.styles[style_name]
            style.font.name = "Times New Roman"
            style.font.size = Pt(size)
            style.font.bold = True
            style.font.color.rgb = RGBColor(0, 0, 0)
            style.font.italic = False
            style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
            style.paragraph_format.space_before = Pt(16 if style_name != "Heading 1" else 0)
            style.paragraph_format.space_after = Pt(8)
            style.paragraph_format.line_spacing = 1.5
            style.paragraph_format.first_line_indent = Cm(0)
            style.paragraph_format.page_break_before = style_name == "Heading 1"

        footer = section.footer
        footer.is_linked_to_previous = False
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        left = fp.add_run("Lumina  ·  lucrare de licență  ·  ")
        _set_run_font(left, size=10)
        _add_page_only(fp)
        settings = self.doc.settings.element
        update = OxmlElement("w:updateFields")
        update.set(qn("w:val"), "true")
        settings.append(update)

        core = self.doc.core_properties
        core.title = (
            "Sistem inteligent de selecție și organizare automată a fotografiilor "
            "pentru studiouri foto"
        )
        core.subject = "Lucrare de licență — prototipul Lumina"
        core.category = "Lucrare de licență"
        core.language = "ro-RO"

    def page(self):
        self.doc.add_page_break()

    def center(self, text, size=12, bold=False, italic=False, after=6, before=0):
        p = self.doc.add_paragraph()
        _paragraph_format(p, indent=False, align="center", before=before, after=after)
        run = p.add_run(text)
        _set_run_font(run, size=size, bold=bold, italic=italic)
        return p

    def left(self, text, size=12, bold=False, italic=False, after=6):
        p = self.doc.add_paragraph()
        _paragraph_format(p, indent=False, align="left", after=after)
        run = p.add_run(text)
        _set_run_font(run, size=size, bold=bold, italic=italic)
        return p

    def h1(self, text):
        p = self.doc.add_heading(text, level=1)
        for run in p.runs:
            _set_run_font(run, size=16, bold=True)
        return p

    def h2(self, text):
        p = self.doc.add_heading(text, level=2)
        for run in p.runs:
            _set_run_font(run, size=14, bold=True)
        return p

    def h3(self, text):
        p = self.doc.add_heading(text, level=3)
        for run in p.runs:
            _set_run_font(run, size=12, bold=True)
        return p

    def p(self, text):
        paragraph = self.doc.add_paragraph()
        _paragraph_format(paragraph, indent=True, align="justify")
        run = paragraph.add_run(text)
        _set_run_font(run, size=12)
        return paragraph

    def items(self, rows, numbered=False):
        for index, row in enumerate(rows, start=1):
            paragraph = self.doc.add_paragraph()
            _paragraph_format(paragraph, indent=False, align="justify", after=4)
            paragraph.paragraph_format.left_indent = Cm(1.25)
            label = f"{index}. " if numbered else "• "
            run = paragraph.add_run(label + row)
            _set_run_font(run, size=12)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(0)

    def caption(self, text):
        paragraph = self.doc.add_paragraph()
        _paragraph_format(paragraph, indent=False, align="center", before=10, after=4, spacing=1.15)
        run = paragraph.add_run(text)
        _set_run_font(run, size=11, italic=True)
        return paragraph

    def image(self, path, width=14.5):
        paragraph = self.doc.add_paragraph()
        _paragraph_format(paragraph, indent=False, align="center", before=6, after=2)
        run = paragraph.add_run()
        run.add_picture(str(path), width=Cm(width))

    def table(self, headers, rows, widths=None):
        table = self.doc.add_table(rows=1 + len(rows), cols=len(headers))
        table.autofit = True
        _borders(table)
        for i, header in enumerate(headers):
            cell = table.rows[0].cells[i]
            cell.text = ""
            para = cell.paragraphs[0]
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = para.add_run(header)
            _set_run_font(run, size=10, bold=True)
            _shade(cell, "E8E4DC")
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                cell = table.rows[r + 1].cells[c]
                cell.text = ""
                para = cell.paragraphs[0]
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER if c else WD_ALIGN_PARAGRAPH.LEFT
                run = para.add_run(str(value))
                _set_run_font(run, size=10)
        if widths:
            for row in table.rows:
                for idx, width in enumerate(widths):
                    row.cells[idx].width = Cm(width)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(6)
        return table

    def formula(self, text):
        paragraph = self.doc.add_paragraph()
        _paragraph_format(paragraph, indent=False, align="center", before=4, after=4, spacing=1.15)
        run = paragraph.add_run(text)
        _set_run_font(run, name="Cambria Math", size=12, italic=True)
        return paragraph

    def bib(self, text):
        paragraph = self.doc.add_paragraph()
        _paragraph_format(paragraph, indent=False, align="justify", after=6, spacing=1.15)
        paragraph.paragraph_format.left_indent = Cm(1.0)
        paragraph.paragraph_format.first_line_indent = Cm(-1.0)
        run = paragraph.add_run(text)
        _set_run_font(run, size=12)
        return paragraph

    def code(self, text):
        for line in text.splitlines():
            paragraph = self.doc.add_paragraph()
            _paragraph_format(paragraph, indent=False, align="left", before=0, after=0, spacing=1.0)
            run = paragraph.add_run(line if line else " ")
            _set_run_font(run, name="Consolas", size=9)

    def save(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.doc.save(path)


def _add_page_only(paragraph):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(end)
    _set_run_font(run, size=10)


def make_figures():
    FIG.mkdir(parents=True, exist_ok=True)
    ink = "#1c1915"
    gold = "#8a6a32"
    paper = "#f7f4ee"
    bars = ["#5c5346", "#8a6a32", "#2f4a3c", "#6e2e2e"]

    # Figure 1 — pipeline
    fig, ax = plt.subplots(figsize=(10.2, 2.6), dpi=160)
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 20)
    ax.axis("off")
    labels = [
        "56 surse\nreale",
        "3000\ncadre",
        "Calitate",
        "Duplicate",
        "Fețe și\npersoane",
        "Album\n160",
        "SQLite și\ndouă vederi",
    ]
    xs = [4, 18, 32, 46, 60, 74, 88]
    for x, label in zip(xs, labels):
        box = plt.Rectangle((x, 5), 12, 10, facecolor=paper, edgecolor=ink, linewidth=1.0)
        ax.add_patch(box)
        ax.text(x + 6, 10, label, ha="center", va="center", fontsize=8, color=ink)
    for x in xs[:-1]:
        ax.annotate(
            "",
            xy=(x + 14.2, 10),
            xytext=(x + 12.2, 10),
            arrowprops=dict(arrowstyle="-|>", color=gold, lw=1.2),
        )
    fig.tight_layout()
    p1 = FIG / "fig_1_flux.png"
    fig.savefig(p1, bbox_inches="tight", facecolor="white")
    plt.close()

    # Figure 2 — partition
    fig, ax = plt.subplots(figsize=(8.4, 4.2), dpi=160)
    names = ["Respinse", "Duplicate", "Păstrate\nîn afara albumului", "Album"]
    values = [563, 2174, 103, 160]
    colors = ["#6e2e2e", "#8a6a32", "#5c5346", "#2f4a3c"]
    ypos = list(range(len(names)))[::-1]
    ax.barh(ypos, values, color=colors, height=0.62)
    ax.set_yticks(ypos)
    ax.set_yticklabels(names, fontsize=10)
    ax.set_xlabel("Număr de cadre", fontsize=10)
    ax.set_xlim(0, 2600)
    for y, value in zip(ypos, values):
        ax.text(value + 30, y, str(value), va="center", fontsize=10, color=ink)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    p2 = FIG / "fig_2_distributie.png"
    fig.savefig(p2, bbox_inches="tight", facecolor="white")
    plt.close()

    # Figure 3 — baseline
    fig, ax = plt.subplots(figsize=(8.6, 4.4), dpi=160)
    import numpy as np

    cats = ["good", "dup", "bad"]
    series = {
        "Top 160 după scor": [13, 147, 0],
        "Un cadru pe scenă": [10, 46, 0],
        "Albumul Lumina": [94, 65, 1],
    }
    x = np.arange(len(cats))
    width = 0.24
    palette = ["#5c5346", "#a89880", "#2f4a3c"]
    for i, (name, vals) in enumerate(series.items()):
        ax.bar(x + (i - 1) * width, vals, width, label=name, color=palette[i])
    ax.set_xticks(x)
    ax.set_xticklabels(["Eticheta good", "Eticheta dup", "Eticheta bad"], fontsize=10)
    ax.set_ylabel("Cadre în selecție", fontsize=10)
    ax.legend(frameon=False, fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    p3 = FIG / "fig_3_baseline.png"
    fig.savefig(p3, bbox_inches="tight", facecolor="white")
    plt.close()

    # Figure 4 — album sections
    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=160)
    sec = ["Portrete", "Cuplu", "Invitați", "Detalii"]
    sec_v = [89, 57, 9, 5]
    ax.bar(sec, sec_v, color=["#2f4a3c", "#8a6a32", "#5c5346", "#a89880"], width=0.66)
    for i, value in enumerate(sec_v):
        ax.text(i, value + 1.5, str(value), ha="center", fontsize=10, color=ink)
    ax.set_ylabel("Cadre în album", fontsize=10)
    ax.set_ylim(0, 110)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    p4 = FIG / "fig_4_album.png"
    fig.savefig(p4, bbox_inches="tight", facecolor="white")
    plt.close()

    # Figure 5 — people
    fig, ax = plt.subplots(figsize=(8.2, 4.2), dpi=160)
    sizes = [2, 3, 4, 5, 6, 8, 9, 10, 14, 15, 17]
    freq = [2, 11, 7, 29, 1, 2, 3, 7, 1, 1, 1]
    ax.bar([str(s) for s in sizes], freq, color=gold, width=0.72)
    ax.set_xlabel("Fotografii distincte în grup", fontsize=10)
    ax.set_ylabel("Număr de persoane", fontsize=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    p5 = FIG / "fig_5_persoane.png"
    fig.savefig(p5, bbox_inches="tight", facecolor="white")
    plt.close()
    return p1, p2, p3, p4, p5


def econ(seconds, hourly=150.0, elapsed=268.3, n=3000, grouping=70, review=18, events=6):
    manual = n * seconds / 3600 + grouping / 60
    lumina = elapsed / 3600 + review / 60
    saved = manual - lumina
    return manual, lumina, saved, saved * hourly, saved * events, saved * events * hourly


def front(doc: Thesis):
    for _ in range(2):
        doc.center("")
    doc.center("[UNIVERSITATEA]", 14, bold=True, after=2)
    doc.center("[FACULTATEA]", 13, bold=True, after=2)
    doc.center("[DEPARTAMENTUL]", 12, after=2)
    doc.center("Programul de studii: [PROGRAMUL DE STUDII]", 12, after=18)
    doc.center("LUCRARE DE LICENȚĂ", 14, bold=True, before=18, after=16)
    doc.center(
        "SISTEM INTELIGENT DE SELECȚIE ȘI ORGANIZARE AUTOMATĂ",
        16,
        bold=True,
        after=2,
    )
    doc.center("A FOTOGRAFIILOR PENTRU STUDIOURI FOTO", 16, bold=True, after=2)
    doc.center(
        "FOLOSIND VEDEREA COMPUTERIZATĂ ȘI ÎNVĂȚAREA AUTOMATĂ",
        16,
        bold=True,
        after=10,
    )
    doc.center("Prototipul Lumina", 13, italic=True, after=28)
    doc.center("Coordonator științific:", 12, after=2)
    doc.center("[Gradul didactic, Prenume NUME]", 12, bold=True, after=16)
    doc.center("Absolvent:", 12, after=2)
    doc.center("[Prenume NUME]", 12, bold=True, after=28)
    doc.center("[ORAȘUL]", 12, after=2)
    doc.center("2026", 12, bold=True, after=2)

    doc.page()
    doc.center("DECLARAȚIE PRIVIND ORIGINALITATEA", 14, bold=True, before=12, after=16)
    doc.p(
        "Subsemnatul / Subsemnata [Prenume NUME], absolvent(ă) al(a) programului de studii "
        "[PROGRAMUL DE STUDII] din cadrul [FACULTATEA], [UNIVERSITATEA], declar pe propria "
        "răspundere că prezenta lucrare de licență, intitulată „Sistem inteligent de selecție "
        "și organizare automată a fotografiilor pentru studiouri foto folosind vederea "
        "computerizată și învățarea automată”, este rezultatul activității mele. Declar că "
        "lucrarea nu a fost prezentată anterior, în aceeași formă, la o altă facultate sau "
        "universitate din țară ori din străinătate în vederea obținerii unui titlu sau a unei "
        "diplome."
    )
    doc.p(
        "Declar că am menționat în text și în bibliografie toate sursele folosite, că am "
        "respectat legislația privind drepturile de autor și că am luat cunoștință de "
        "prevederile referitoare la plagiat. Datele numerice din capitolul experimental "
        "provin din rularea prototipului Lumina asupra setului de demonstrație descris în "
        "lucrare și pot fi regăsite în baza de date produsă de această rulare."
    )
    doc.p(
        "Câmpurile dintre paranteze drepte de pe pagina de titlu se completează cu datele "
        "instituției, ale coordonatorului și ale absolventului înainte de depunere. Prezenta "
        "declarație se semnează olograf."
    )
    doc.left("")
    doc.left("Data: ____________________", after=12)
    doc.left("Semnătura: ____________________", after=6)

    doc.page()
    # Heading 1 forces a page break; the abstract should not use that style if we already broke.
    # Use a local heading without the style's page break by writing a bold centered title plus body,
    # but TOC needs Heading styles. The first h1 will add an extra break. Accept one blank page
    # rather than fight the style: disable page_break on Heading 1 and break manually.
    doc.doc.styles["Heading 1"].paragraph_format.page_break_before = False

    doc.h1("Rezumat")
    doc.p(
        "Lucrarea prezintă Lumina, un prototip care triază o ședință foto de nuntă pentru un "
        "studio. Din fiecare cadru se calculează o măsură de claritate, o măsură de expunere "
        "și o amprentă perceptuală. Cadrele moi sau expuse greșit sunt respinse. Rafalele "
        "aproape identice, din aceeași scenă, sunt reduse la fișierul cu scorul cel mai mare. "
        "Fețele rămase sunt detectate cu YuNet și grupate cu vectori SFace. Din cadrele "
        "păstrate se compune un album de cel mult 160 de fotografii, împărțit în cuplu, "
        "portrete, invitați și detalii. Rezultatul se scrie într-o bază SQLite și se arată "
        "în două vederi ale aceluiași eveniment: masa de lucru a studioului și albumul cuplului."
    )
    doc.p(
        "Setul pe care s-a măsurat prototipul nu este o colecție de 3000 de fotografii "
        "independente. El pornește de la 56 de fotografii reale de nuntă, preluate din "
        "colecții publice, și este extins controlat cu decupaje, rafale cu zgomot ușor, "
        "neclaritate puternică și expuneri eșuate, până la 3000 de cadre. Etichetele good, "
        "dup și bad există doar pentru verificare. Decizia de selecție nu le citește."
    )
    doc.p(
        "Pe această rulare, din 3000 de cadre au fost respinse 563, au fost marcate ca "
        "duplicate 2174 și au rămas 263 de cadre unice, dintre care 160 intră în album. "
        "S-au format 65 de grupuri de persoane. Acordul cu etichetele generate este 0,957 "
        "pentru cadrele good care nu sunt respinse, 1,000 pentru duplicatele prinse după "
        "poarta de calitate și 0,991 pentru cadrele bad respinse. Un cadru generat ca eșec "
        "a ajuns totuși în album. Un baseline care păstrează cele mai mari 160 de scoruri, "
        "fără tratarea rafalelor, acoperă doar 10 scene și este format aproape numai din "
        "copii. Albumul Lumina acoperă 55 de scene."
    )
    doc.p(
        "Timpul și costul afișate în interfață sunt un scenariu de lucru, nu un studiu de "
        "piață. La 6,5 secunde pe cadru pentru decizia manuală, 70 de minute pentru grupare "
        "și ordonare, 18 minute pentru revizia propunerii și 150 de lei pe oră, rularea "
        "măsurată lasă o diferență de 6,21 ore și 931 de lei pe eveniment. Lucrarea tratează "
        "aceste valori ca ipoteze și arată cum se mișcă rezultatul când ipotezele se schimbă. "
        "Modelele de fețe sunt preantrenate. Contribuția proprie este fluxul de decizie, "
        "modul în care rafalele și scenele sunt separate, persistența rezultatului și "
        "evaluarea cinstită a ceea ce cifrele dovedesc."
    )
    doc.p("Cuvinte-cheie: selecție fotografică, claritate, amprentă perceptuală, detectarea fețelor, YuNet, SFace, album, studio foto.")

    doc.h1("Abstract")
    doc.p(
        "This thesis presents Lumina, a prototype that culls a wedding shoot for a photo "
        "studio. Each frame receives a sharpness score, an exposure score, and a perceptual "
        "hash. Soft and badly exposed frames are rejected. Near-duplicate bursts inside one "
        "scene collapse to the highest-scoring file. Faces on the remaining frames are "
        "detected with YuNet and grouped with SFace embeddings. At most 160 keepers become "
        "an album with four sections: couple, portraits, guests, and details. The result is "
        "stored in SQLite and shown as two views of the same wedding, one for the studio and "
        "one for the couple."
    )
    doc.p(
        "The measured set is not 3,000 independent photographs. It starts from 56 real "
        "wedding photographs taken from public collections and is expanded, under a fixed "
        "generator, with crops, lightly noised bursts, strong blur, and failed exposures. "
        "The labels good, dup, and bad are used only for validation. The culling decision "
        "does not read them."
    )
    doc.p(
        "On the stored run, 563 of 3,000 frames were rejected, 2,174 were marked as "
        "duplicates, and 263 unique frames remained, of which 160 entered the album. "
        "Sixty-five people were grouped. Agreement with the generated labels is 0.957 for "
        "good frames that are not rejected, 1.000 for duplicates caught after the quality "
        "gate, and 0.991 for bad frames that are rejected. One generated failure still "
        "entered the album. A baseline that keeps the 160 highest scores, without burst "
        "handling, covers 10 scenes and is almost entirely copies. The Lumina album covers "
        "55 scenes."
    )
    doc.p(
        "The hours and money shown in the interface are a worked scenario, not a market "
        "study. Face models are pretrained. The contribution is the decision pipeline, the "
        "separation of bursts from scenes, the stored result, the two-role interface, and "
        "an evaluation that states exactly what the figures do and do not prove."
    )
    doc.p("Keywords: photo culling, sharpness, perceptual hash, face detection, YuNet, SFace, wedding album, photo studio.")

    doc.h1("Lista abrevierilor")
    doc.table(
        ["Abreviere", "Înțeles în lucrare"],
        [
            ["API", "Interfața prin care pagina cere evenimentul, imaginile și starea prelucrării"],
            ["dHash", "Amprentă perceptuală pe 64 de biți, obținută din comparații între pixeli vecini"],
            ["ONNX", "Formatul în care sunt încărcate modelele YuNet și SFace"],
            ["SQLite", "Baza de date locală în care se scrie evenimentul"],
            ["WAL", "Modul jurnal al bazei, care permite citirea în timpul scrierii"],
            ["YuNet", "Detector de fețe mic, folosit ca model preantrenat"],
            ["SFace", "Funcție de cost și, aici, modelul de recunoaștere încărcat din OpenCV Zoo"],
        ],
        widths=[4.0, 12.0],
    )

    doc.h1("Cuprins")
    p = doc.doc.add_paragraph()
    _paragraph_format(p, indent=False, align="left")
    _add_field(p, ' TOC \\o "1-2" \\h \\z \\u ')
    doc.p(
        "Dacă la deschidere cuprinsul nu s-a completat singur, în Word se apasă clic dreapta "
        "pe el și se alege actualizarea întregului tabel. Numerotarea paginilor din subsol "
        "este continuă."
    )


def body(doc: Thesis, figs):
    f1, f2, f3, f4, f5 = figs

    doc.h1("1. Introducere")
    doc.h2("1.1. Motivația")
    doc.p(
        "O nuntă fotografiată cap-coadă nu se încheie când se închide aparatul. Studioul "
        "primește câteva mii de cadre: rafale făcute ca să prindă o expresie, încercări "
        "mișcate, cadre arse de bliț sau rămase în umbră, și un număr mult mai mic de "
        "fotografii care merită să ajungă la client. Munca care urmează este de triere. "
        "Fotograful parcurge ședința, aruncă ce nu se poate folosi, păstrează o singură "
        "variantă dintr-o rafală și abia apoi construiește albumul. Timpul acesta se plătește "
        "din același onorariu cu fotografierea, iar clientul nu îl vede."
    )
    doc.p(
        "Uneltele comerciale care promit selecție automată există și sunt folosite în "
        "studio. Ele sunt însă închise: nu arată regula prin care un cadru a căzut, nu lasă "
        "de verificat un experiment pe un set descris, și amestecă adesea trierea tehnică "
        "cu un scor de „frumusețe” pe care fotograful nu îl poate reconstitui. Pentru o "
        "lucrare de licență, obiectul util nu este încă un produs care să concureze cu "
        "aceste unelte. Obiectul util este un flux ale cărui decizii se pot urmări de la "
        "pixel până la rândul din baza de date, împreună cu o măsurătoare care spune ce "
        "anume a fost dovedit."
    )
    doc.p(
        "Lumina a fost construită pe această distincție. Prototipul primește o ședință, "
        "respinge cadrele ilizibile, moi sau expuse greșit, strânge rafalele, grupază "
        "fețele care revin și propune un album de lungime limitată. Aceeași nuntă se deschide "
        "apoi în două vederi. Studioul vede pâlnia, motivele de respingere, orele și lei. "
        "Cuplul vede albumul, persoanele și fotografiile pe care le păstrează cu inima. "
        "Lista cuplului se întoarce în studio. Nu există conturi, plăți sau trimitere de "
        "e-mail: lucrarea se oprește la decizie, la memorie și la predarea selecției."
    )

    doc.h2("1.2. Problema")
    doc.p(
        "Problema tratată se poate formula astfel. Dat fiind un dosar de imagini produs "
        "la un eveniment, să se construiască o partiție a cadrelor în patru stări — respins, "
        "duplicat, păstrat, album — plus o grupare a fețelor care apar în cel puțin două "
        "fotografii păstrate, astfel încât albumul să acopere scene diferite și să aibă o "
        "lungime pe care studioul o poate preda. Decizia trebuie să depindă de conținutul "
        "imaginii. Numele fișierului și o etichetă scrisă de cel care a generat setul nu "
        "sunt dovezi."
    )
    doc.p(
        "Problema are trei straturi, care nu trebuie amestecate. Primul este tehnic: cadrul "
        "este necitibil, mișcat sau expus în afara unei benzi utilizabile. Al doilea este "
        "redundant: mai multe fișiere înfățișează aceeași clipă, cu diferențe de zgomot sau "
        "de compresie. Al treilea este editorial: dintre cadrele bune și diferite, albumul "
        "nu poate încăpea tot, iar o nuntă nu este bine povestită de o sută șaizeci de copii "
        "ale celei mai clare fotografii. Un scor unic, de la rău la bun, ascunde aceste "
        "straturi. Lumina le ține separate în starea fiecărui cadru și în motivul scris "
        "lângă respingere sau duplicat."
    )
    doc.p(
        "Mai există o problemă de măsurare. Dacă setul de test este fabricat de același "
        "autor care a scris pragurile, acordul dintre etichete și decizii arată că regulile "
        "sunt consistente cu generatorul. Nu arată că un fotograf ar fi ales aceleași cadre. "
        "Lucrarea își asumă această limită în loc să o acopere cu un procent rotund. "
        "Experimentul din capitolul 7 este construit ca să se vadă și consistența, și locul "
        "în care ea nu este suficientă."
    )

    doc.h2("1.3. Obiective")
    doc.p("Obiectivele lucrării sunt următoarele.")
    doc.items(
        [
            "Să definească o procedură reproductibilă prin care un cadru trece de la pixeli la una dintre stările respins, duplicat, păstrat sau album.",
            "Să separe eșecul tehnic de redundanța de rafală și de selecția editorială a albumului.",
            "Să grupăze persoanele care revin în mai multe fotografii păstrate, fără etichetare manuală, folosind modele preantrenate.",
            "Să păstreze evenimentul, scorurile, motivele și grupurile într-o bază care poate fi interogată după rulare.",
            "Să arate același eveniment în două roluri, studio și cuplu, cu o listă scurtă care închide drumul de la client înapoi la fotograf.",
            "Să raporteze un scenariu de timp și de cost cu ipotezele scrise explicit și cu sensibilitate la schimbarea lor.",
            "Să evalueze rularea pe setul generat și să spună, în aceleași pagini, ce nu măsoară cifrele.",
        ],
        numbered=True,
    )
    doc.p(
        "Nu este obiectiv antrenarea unui model nou de detectare sau de recunoaștere a "
        "fețelor. Nu este obiectiv un sondaj în studiouri și nu este obiectiv o aplicație "
        "cu utilizatori, parole și plăți. Aceste limite sunt alese ca să rămână verificabil "
        "ceea ce prototipul chiar face."
    )

    doc.h2("1.4. Contribuția")
    doc.p(
        "Contribuția este un sistem integrat, nu un algoritm nou de vedere computerizată. "
        "Piesele de claritate, de amprentă și de fețe sunt cunoscute. Modul în care sunt "
        "puse cap la cap este al lucrării: poarta de calitate se aplică înainte de duplicate, "
        "duplicatele se caută doar în interiorul scenei, rădăcina unei rafale este cadrul "
        "cu scorul mai mare, iar albumul nu ia pur și simplu primele scoruri, ci limitează "
        "câte cadre pot veni din aceeași scenă. Persoanele se grupează doar pe fețele "
        "cadrelor rămase după triere, cu un prag de similaritate cosinus și cu regula că "
        "o persoană trebuie să apară în cel puțin două fotografii."
    )
    doc.p(
        "A doua contribuție este evaluarea. Pe lângă ratele de acord cu etichetele "
        "generatorului, lucrarea compară albumul cu două proceduri mai simple, calculate "
        "pe aceleași rânduri din baza de date: cele 160 de scoruri cele mai mari dintre "
        "cadrele care trec poarta de calitate, și cel mai bun cadru din fiecare scenă. "
        "Comparația arată la ce folosește tratarea rafalei și plafonul pe scenă. Fără ele, "
        "selecția se strânge în câteva scene și în copii."
    )
    doc.p(
        "A treia contribuție este produsul demonstrativ care face rezultatul lizibil. "
        "Baza SQLite păstrează evenimentul. Pagina deschide studio și cuplu peste aceleași "
        "identificatori de fotografii. Inimile cuplului sunt o listă de identificatori în "
        "browser, iar studioul poate deschide întâi cadrele alese. Codul care deschide "
        "vedere de studio este o poartă de demonstrație, nu un sistem de autentificare. "
        "Și această distincție face parte din contribuție, pentru că oprește o pretenție "
        "pe care prototipul nu o susține."
    )

    doc.h2("1.5. Organizarea lucrării")
    doc.p(
        "Capitolul 2 descrie munca de selecție într-un studio și poziția lucrării față de "
        "uneltele comerciale și față de literatura de claritate, de amprente și de fețe. "
        "Capitolul 3 fixează noțiunile folosite mai departe: varianța laplacianului, banda "
        "de expunere, distanța Hamming, detectorul YuNet, vectorul SFace și gruparea prin "
        "componente conexe. Capitolul 4 traduce problema în cerințe funcționale și spune "
        "ce rămâne în afara sistemului."
    )
    doc.p(
        "Capitolul 5 proiectează arhitectura, modelul de date, fluxul și cele două vederi. "
        "Capitolul 6 urmărește implementarea, de la construirea setului până la interfață, "
        "cu pragurile așa cum sunt ele în cod. Capitolul 7 raportează rularea de 3000 de "
        "cadre, baseline-urile și limitele metricilor. Capitolul 8 calculează scenariul "
        "economic și sensibilitatea lui. Capitolul 9 închide obiectivele și enumeră ce ar "
        "merita măsurat într-o continuare. Anexele adună pragurile, schema bazei și modul "
        "de rulare."
    )

    doc.h1("2. Contextul selecției fotografice")
    doc.h2("2.1. Ședința de nuntă ca problemă de triere")
    doc.p(
        "Fotografia de eveniment produce volum dintr-un motiv practic. Expresia, gestul și "
        "clipirea durează mai puțin decât răbdarea de a verifica fiecare cadru pe ecranul "
        "aparatului. Fotograful trage o rafală și alege mai târziu. Aceeași logică umple "
        "cardul cu variante apropiate ale aceluiași sărut, ale aceleiași intrări și ale "
        "aceleiași mese. La celălalt capăt stau cadrele ratate: mișcarea invitataului, "
        "focalizarea căzută pe fundal, cadranul lăsat pe o expunere de interior când "
        "ceremonia a ieșit afară."
    )
    doc.p(
        "Clientul nu cumpără cardul. Clientul cumpără o selecție pe care o poate privi și, "
        "adesea, un album cu o lungime stabilită în înțelegerea cu studioul. Drumul de la "
        "card la album are deci un pas de eliminare și un pas de compunere. Eliminarea "
        "răspunde la întrebarea „se poate folosi acest fișier?”. Compunerea răspunde la "
        "„încape în poveste și nu repetă scena dinainte?”. Un sistem care rezolvă doar "
        "prima întrebare predă fotografului totuși sute de cadre foarte asemănătoare. Un "
        "sistem care rezolvă doar pe a doua, fără poartă tehnică, riscă să promoveze un "
        "cadru spectaculos și nefolosibil."
    )
    doc.p(
        "În practică, trierea manuală amestecă cele două întrebări în aceeași trecere cu "
        "ochiul. Omul vede dintr-o dată că cadrul este mișcat, că este a cincea variantă "
        "și că nu își are locul lângă portretul de dinainte. Pentru un program, amestecul "
        "este o sursă de eroare, pentru că un singur număr nu spune de ce a căzut cadrul. "
        "De aceea Lumina scrie un motiv: ilizibil, moale, expunere slabă sau duplicat. "
        "Albumul este o a doua decizie, peste cadrele care au trecut."
    )

    doc.h2("2.2. Ce se poate automatiza și ce rămâne la fotograf")
    doc.p(
        "Claritatea, expunerea grosieră și asemănarea unei rafale sunt proprietăți ale "
        "imaginii pe care un algoritm le poate măsura stabil. Un cadru cu varianța "
        "laplacianului prăbușită este moale pentru orice privitor rezonabil. Două fișiere "
        "care diferă prin zgomot de compresie sunt, pentru album, aceeași fotografie. "
        "Aceste judecăți nu cer gust."
    )
    doc.p(
        "Gustul începe acolo unde două cadre sunt deopotrivă clare și înfățișează lucruri "
        "diferite: o mână pe o rochie, o masă văzută de departe, o privire care nu este "
        "„cea mai clară” dar este cea care spune seara. Nici laplacianul, nici un vector "
        "de față nu aleg între ele în sens editorial. Lumina nu pretinde că o face. "
        "Albumul este o propunere de lungime fixă, construită din scor tehnic și din "
        "plafon pe scenă, pe care fotograful o revizuiește. În scenariul de timp, "
        "revizia are un loc explicit: optsprezece minute, nu zero."
    )
    doc.p(
        "Gruparea persoanelor stă la mijloc. Faptul că aceeași față revine în mai multe "
        "cadre este, în limitele unui model de recunoaștere, o măsurătoare. Faptul că "
        "studioul vrea persoana respectivă în album, sau că două fețe apropiate din "
        "lumină proastă sunt de fapt oameni diferiți, rămâne de verificat. Prototipul "
        "arată grupurile și câte fotografii conțin. Nu pune nume și nu garantează "
        "identitatea juridică a unei persoane."
    )

    doc.h2("2.3. Unelte comerciale")
    doc.p(
        "În ultimii ani, selecția asistată a intrat în fluxul obișnuit al studiourilor "
        "prin produse precum Aftershoot sau Imagen. Ele promit parcurgerea rapidă a "
        "rafalelor, note pe cadre și, la unele dintre ele, o legătură cu developarea. "
        "Fotograful rămâne în buclă: acceptă, corectează, exportă. Din perspectiva unui "
        "studio, valoarea stă în orele scoase din noaptea de după nuntă, nu într-o "
        "înlocuire a autorului."
    )
    doc.p(
        "Din perspectiva acestei lucrări, produsele sunt context, nu etalon. Nu există "
        "acces la regulile lor, la seturile pe care au fost măsurate sau la modul în "
        "care tratează un cadru mișcat față de un duplicat. O comparație de acuratețe "
        "cu ele, făcută din afară, ar fi o părere. Lucrarea nu o face. Ce se poate "
        "spune fără să se inventeze cifre este că piața a validat nevoia — trierea este "
        "destul de scumpă ca să existe produse pentru ea — și că un prototip academic "
        "trebuie să fie mai transparent decât ele, nu mai „inteligent” pe o reclamă."
    )
    doc.p(
        "Transparența, aici, înseamnă lucruri concrete. Fiecare cadru respins are un "
        "motiv dintr-o listă scurtă. Fiecare duplicat indică fișierul păstrat în locul "
        "lui. Pragurile sunt constante în cod, nu un scor opac. Baza poate fi deschisă "
        "după rulare și interogată. Experimentul spune din ce fotografii a fost construit "
        "setul. Acestea sunt proprietăți pe care un produs închis nu le datorează "
        "clientului, dar pe care o lucrare de licență le datorează cititorului."
    )

    doc.h2("2.4. Literatură folosită de prototip")
    doc.p(
        "Măsura de claritate aleasă este varianța laplacianului, o măsură clasică de "
        "focalizare. Pech-Pacheco și colaboratorii o compară cu alte funcții de focus "
        "în microscopie și arată că energia muchiilor răspunde la defocalizare [10]. "
        "Crete și colaboratorii tratează neclaritatea ca pe o mărime perceptuală, nu "
        "doar ca pe o varianță, și propun o metrică fără imagine de referință [4]. "
        "Lumina rămâne la varianța laplacianului pentru că este ieftină pe mii de cadre "
        "și pentru că eșecurile din setul de demonstrație sunt neclarități grosiere, "
        "nu diferențe fine de gust. Măsura este apoi trecută printr-o transformare "
        "mărginită, descrisă în capitolul 3, ca să stea în același interval cu expunerea."
    )
    doc.p(
        "Pentru rafale se folosește o amprentă perceptuală de tip difference hash. "
        "Zauner compară mai multe funcții de hash perceptual, între care varianta pe "
        "diferențe dintre pixeli vecini, și arată că ele rezistă la comprimare și la "
        "zgomot mic, dar nu la schimbări mari de conținut [16]. Descrierea de lucru a "
        "lui dHash, pe o grilă de nouă pe opt, circulă din nota tehnică a lui Krawetz [9]. "
        "Lumina nu folosește hash-ul ca să găsească aceeași fotografie pe internet, ci "
        "ca să decidă, în interiorul unei scene, care fișiere sunt aceeași clipă."
    )
    doc.p(
        "Detectarea fețelor are o istorie lungă înainte de rețele. Cascada Viola–Jones "
        "a făcut detectarea suficient de rapidă pentru imagini obișnuite, cu trăsături "
        "Haar și un clasificator în trepte [13]. Detectorul folosit aici, YuNet, este "
        "un model mic, fără ancore, proiectat pentru dispozitive cu resurse limitate. "
        "Wu, Peng și Yu raportează un model de sub o sută de mii de parametri și un "
        "rezultat de 81,1% mAP pe pista dificilă de validare WIDER FACE, la o inferență "
        "de ordinul milisecundelor pe un procesor de birou [14], [15]. Prototipul nu "
        "reantrenează YuNet și nu reface acel benchmark. Îl încarcă ca detector și "
        "filtrează căsuțele prea mici pentru o grupare stabilă."
    )
    doc.p(
        "Recunoașterea, în sensul de „este aceeași persoană”, s-a mutat spre vectori "
        "învățați. FaceNet a arătat că o rețea poate plasa fețele astfel încât distanța "
        "din spațiul vectorial să aproximeze identitatea [11]. ArcFace a împins separarea "
        "unghiulară dintre clase [5]. SFace, metoda lui Zhong și colaboratorii, "
        "modulează optimizarea pe hipersferă cu două sigmoide, ca să nu se lipească "
        "modelul de exemplele zgomotoase din bazele mari de antrenare [17]. În OpenCV "
        "Zoo, fișierul folosit de Lumina este o rețea de tip MobileFaceNet [2] antrenată "
        "cu această funcție de cost. Prototipul consumă vectorul gata calculat. Nu "
        "modifică funcția de cost și nu vede bazele CASIA-WebFace, VGGFace2 sau MS-Celeb "
        "pe care a fost studiată metoda."
    )
    doc.p(
        "Manualele de vedere computerizată și de prelucrare a imaginii acoperă restul "
        "instrumentelor elementare: reprezentarea unei imagini ca matrice, operatorul "
        "laplacian, histograma și compresia JPEG [6], [12]. Noțiunea de vector învățat "
        "și faptul că un model preantrenat este tot o formă de învățare automată, chiar "
        "dacă antrenarea nu are loc în această lucrare, sunt luate în sensul din "
        "Goodfellow, Bengio și Courville [7]. Structura de mulțimi disjuncte folosită "
        "la rafale și la persoane este union-find, cu compresia căii, ca în tratatele "
        "de algoritmi [3]. Biblioteca care execută operațiile pe imagine și inferența "
        "modelelor este OpenCV [1]."
    )

    doc.h2("2.5. Locul lucrării")
    doc.p(
        "Lumina nu propune o măsură nouă de claritate și nu propune o pierdere nouă "
        "pentru recunoașterea fețelor. Locul ei este între literatura de componente și "
        "uneltele închise. Componentele sunt folosite cu reguli explicite, pe un set "
        "a cărui construcție este descrisă, iar rezultatul este un album și un registru, "
        "nu doar un grafic de acuratețe."
    )
    doc.p(
        "Poziția aceasta impune o formulare atentă a învățării automate. Sistemul este "
        "inteligent în sensul că folosește modele învățate pentru fețe și o procedură "
        "de decizie peste măsurători. Sistemul nu învață din nunțile pe care le triază. "
        "Pragurile sunt alese de proiectant și rămân constante. Dacă o comisie întreabă "
        "unde este antrenarea, răspunsul corect este că antrenarea aparține autorilor "
        "YuNet și SFace, iar lucrarea de față contribuie cu integrarea, cu regula de "
        "rafală, cu construcția albumului și cu evaluarea. Capitolul 3 dezvoltă această "
        "delimitare, ca să nu apară prima dată la susținere."
    )

    doc.h1("3. Fundamente folosite")
    doc.h2("3.1. Imaginea ca măsurătoare")
    doc.p(
        "Un fișier JPEG citit de prototip devine o matrice de pixeli cu trei canale. "
        "Pentru claritate, expunere și amprentă se folosește varianta de luminanță, "
        "obținută prin conversia la niveluri de gri. Culoarea rămâne în joc la fețe: "
        "detectorul și recunoscătorul primesc imaginea color, iar calea de rezervă, "
        "când modelul SFace lipsește, compară histograme în spațiul HSV."
    )
    doc.p(
        "Două consecințe practice contează pentru reproducere. Prima este că un fișier "
        "pe care decodorul nu îl poate citi nu primește un scor mic, ci starea respins "
        "și motivul „Unreadable”. A doua este că operațiile de mai jos nu privesc "
        "metadatele aparatului. Un cadru poate fi, în EXIF, o rafală a aceluiași "
        "declanșator; Lumina nu citește acest fapt. Scena, în setul de demonstrație, "
        "vine din generator: toate variantele unei fotografii-sursă împart aceeași "
        "scenă. La un dosar încărcat de utilizator, scena este o grupare de câte opt "
        "fișiere în ordinea numelui, o aproximație care trebuie spusă ca limită, nu "
        "ca înțelegere a evenimentului."
    )

    doc.h2("3.2. Claritatea")
    doc.p(
        "Laplacianul unei imagini în gri răspunde la variații locale de intensitate. "
        "Într-un cadru clar, muchiile produc valori mari și varianța lor este mare. "
        "Într-un cadru mișcat sau defocalizat, muchiile se turtesc și varianța cade. "
        "Fie v această varianță. Valoarea brută nu este comodă ca scor, pentru că "
        "poate crește mult pe texturi fine fără ca percepția să crească la fel. "
        "Prototipul o aduce în intervalul (0, 1) prin"
    )
    doc.formula("S = v / (v + 90)")
    doc.p(
        "La v = 90, claritatea este 0,5. La v mult mai mare, S se apropie de 1 fără "
        "să îl atingă. Constanta 90 este o alegere de scară, nu o constantă a naturii. "
        "Ea face ca pragul de respingere, S < 0,38, să corespundă unor cadre vizibil "
        "moi în generatorul de eșecuri, care construiește neclaritatea prin "
        "micșorare agresivă urmată de un filtru gaussian lat. Pe o altă colecție, "
        "același număr poate fi prea aspru sau prea îngăduitor. Lucrarea îl raportează "
        "ca prag de operare al prototipului, nu ca optim universal."
    )
    doc.p(
        "Respingerea pentru claritate primează asupra expunerii. Dacă S este sub 0,38, "
        "motivul scris este „Soft”, chiar dacă și expunerea ar fi fost slabă. Ordinea "
        "reflectă faptul că un cadru mișcat nu se repară din expunere, în timp ce un "
        "cadru întunecat dar clar mai poate fi folosit la developare. Aceasta este o "
        "preferință de studio codificată în ordine, nu un rezultat învățat."
    )

    doc.h2("3.3. Expunerea")
    doc.p(
        "Expunerea este judecată pe media nivelurilor de gri și pe fracția de pixeli "
        "lipiți de capete. Fie m media. Dacă m stă între 98 și 168, pe scara 0–255, "
        "cadrul este în banda considerată utilizabilă și componenta de centru este 1. "
        "Sub 98, componenta scade liniar cu m / 98. Peste 168, scade liniar cu "
        "depărtarea de 168, împărțită la 75, și nu coboară sub zero. Separat se "
        "calculează fracția de pixeli sub 8 plus fracția de pixeli peste 248. Această "
        "fracție, plafonată la 0,85, reduce scorul de centru. Rezultatul final este "
        "tăiat la intervalul [0, 1]."
    )
    doc.p(
        "Regula prinde două eșecuri diferite, care în generator sunt produse separat: "
        "cadrul înmulțit cu 0,16, care cade în întuneric, și cadrul înmulțit cu 3,1 "
        "și apoi deplasat cu 40, care se lipește de alb. Un cadru poate avea media "
        "acceptabilă și totuși multe pixeli arși; penalizarea de capete există pentru "
        "acest caz. Pragul de respingere este 0,50. Sub el, motivul este „Poor exposure”."
    )
    doc.p(
        "Măsura nu este un exponometru și nu citește compensarea de bliț. Ea nu distinge "
        "o scenă de noapte, intenționat întunecată și frumoasă, de o greșeală. În setul "
        "de demonstrație, întunericul este produs ca eșec, deci acordul cu eticheta bad "
        "este favorizat de construcție. Pe o ședință reală de seară, același prag poate "
        "respinge cadre pe care fotograful le-ar păstra. Limitarea se notează aici ca "
        "să nu fie descoperită abia din exemplele adverse."
    )

    doc.h2("3.4. Scorul tehnic")
    doc.p(
        "Cadrul care trece de ambele praguri primește scorul"
    )
    doc.formula("Q = 0,72 · S + 0,28 · E")
    doc.p(
        "unde E este expunerea. Ponderea mai mare pe claritate spune că, între două "
        "cadre utilizabile, prototipul preferă muchia tare unei expuneri ușor mai "
        "centrale. Ponderile nu sunt învățate pe un set de preferințe. Sunt o "
        "alegere declarată."
    )
    doc.p(
        "După eliminarea duplicatelor, cadrele rămase trec prin detectorul de fețe. "
        "Dacă există cel puțin o față reținută, scorul se actualizează:"
    )
    doc.formula("Q' = 0,82 · Q + 0,18 · min(n, 2) / 2")
    doc.p(
        "n este numărul de fețe păstrate în cadru. Împărțirea la 2 și plafonul la "
        "două fețe opresc un cadru de grup să urce în scor doar pentru că are mai "
        "multe capete. Bonusul este mic față de claritate. Un cadru moale nu ajunge "
        "aici, pentru că fețele se caută doar pe starea păstrat."
    )

    doc.h2("3.5. Amprenta și distanța Hamming")
    doc.p(
        "Amprenta se calculează pe imaginea în gri, adusă la 9×8 pixeli. Pe fiecare "
        "rând se compară pixelul cu vecinul din dreapta. Rezultatul este un bit: 1 "
        "dacă pixelul din stânga este strict mai luminos. Opt comparații pe opt rânduri "
        "fac 64 de biți, împachetați într-un întreg. Două cadre se compară prin distanța "
        "Hamming, adică numărul de biți diferiți, obținut din populația de biți ai "
        "operației SAU-EXCLUSIV între cele două amprente."
    )
    doc.p(
        "Pragul din prototip este 5. Sub sau egal cu 5, cadrele din aceeași scenă sunt "
        "considerate aceeași rafală. Pragul a fost strâns după o observație de construcție: "
        "la o distanță mai largă, în jurul lui 9, decupajele diferite ale aceleiași "
        "fotografii-sursă se lipeau unele de altele, deși pentru album sunt compoziții "
        "diferite. Distanța 5 păstrează împreună variantele cu zgomot ușor și comprimare "
        "JPEG de calitate 78, care sunt duplicatele generate intenționat. Ca și pragul "
        "de claritate, valoarea este de operare pe acest generator. Nu este prezentată "
        "ca optim pe o colecție publică de hash-uri."
    )
    doc.p(
        "Căutarea nu este globală. Două cadre din scene diferite nu se declară duplicate, "
        "chiar dacă amprentele sunt apropiate. Motivația este de produs: o ceremonie și "
        "un portret făcut mai târziu pot semăna în hash fără să fie o rafală, iar "
        "lipirea lor ar șterge o scenă din album. Prețul este că generatorul trebuie să "
        "spună scena, ori că la încărcarea unui dosar propriu scena este aproximată. "
        "Complexitatea este pătratică în numărul de cadre păstrate ale unei scene. La "
        "câteva zeci de cadre pe scenă și la 56 de scene, costul este neglijabil față "
        "de citirea imaginilor și față de fețe."
    )

    doc.h2("3.6. Componentele unei rafale")
    doc.p(
        "Într-o scenă, relația „este duplicat al” nu se rezolvă prin lipirea fiecărui "
        "cadru de primul găsit. Această euristică lacomă greșește când A seamănă cu B, "
        "B seamănă cu C, iar A și C stau imediat peste prag, și greșește și când copia "
        "mai zgomotoasă are, din întâmplarea măsurătorii, scorul mai mare. Prototipul "
        "construiește componente conexe cu union-find. Muchia există între două cadre "
        "păstrate dacă distanța Hamming este cel mult 5. La unire, părintele devine "
        "cadrul cu scorul mai mare. La final, rădăcina componentei rămâne păstrată, iar "
        "celelalte cadre primesc starea duplicat, motivul „Duplicate” și numele "
        "fișierului-rădăcină."
    )
    doc.p(
        "Consecința este importantă pentru citirea metricilor. Fișierul păstrat poate "
        "purta, în generator, eticheta dup. Eticheta dup înseamnă „acest JPEG a fost "
        "scris ca copie cu zgomot”, nu „acest JPEG este mai prost decât originalul”. "
        "Dacă zgomotul și recompresia urcă scorul, rădăcina este copia. Pentru studio, "
        "comportamentul este cel dorit: se predă fișierul cu scorul tehnic mai bun. "
        "Pentru o metrică naivă, care cere ca orice fișier etichetat dup să fie aruncat, "
        "comportamentul arată ca o eroare. Capitolul 7 definește metrica astfel încât "
        "rădăcina unei componente să conteze ca duplicat prins, nu ca duplicat scăpat."
    )

    doc.h2("3.7. Fețe: detecție și vector")
    doc.p(
        "YuNet este încărcat prin interfața FaceDetectorYN din OpenCV 4.11, cu prag de "
        "încredere 0,68, prag de suprimare a căsuțelor suprapuse 0,3 și cel mult 12 "
        "candidaturi interne. Imaginea de lucru este micșorată astfel încât latura mare "
        "să aibă cel mult 720 de pixeli, apoi detectorul își primește dimensiunea reală "
        "a acestei imagini. Căsuțele sunt proiectate înapoi la coordonatele originale. "
        "O căsuță cu lățimea sau înălțimea sub 24 de pixeli este aruncată. Se păstrează "
        "cel mult opt fețe pe cadru."
    )
    doc.p(
        "Versiunea de OpenCV este parte din metodă, nu un detaliu de instalare. O "
        "încercare cu generația 5 a bibliotecii, pe aceleași fotografii, aproape nu "
        "a întors fețe pentru modelul YuNet folosit. Prototipul fixează de aceea "
        "pachetul opencv-python-headless la versiunea 4.11.0.86. Rezultatele din "
        "capitolul 7 sunt obținute cu această versiune. Ele nu se transferă automat "
        "la o altă ramură majoră a bibliotecii."
    )
    doc.p(
        "Pentru fiecare față păstrată, recunoscătorul SFace aliniază decupajul după "
        "reperul primit de la detector și produce un vector. Vectorul este împărțit "
        "la norma euclidiană, astfel încât produsul scalar dintre doi vectori să fie "
        "similaritatea cosinus. Dacă fișierul SFace nu poate fi descărcat, prototipul "
        "cade pe o histogramă de nuanță și saturație, normalizată la fel, cu un prag "
        "mai sever, 0,93. Rularea raportată a avut la dispoziție modelul SFace; "
        "histograma este o cale de rezervă, nu calea măsurată. Pragul de unire pentru "
        "SFace este 0,45. Două fețe ale căror vectori au produsul scalar cel puțin "
        "0,45 ajung în aceeași componentă."
    )
    doc.p(
        "Gruparea persoanelor folosește din nou union-find, de data aceasta fără "
        "preferință de scor: componentele sunt doar mulțimi de fețe. O componentă "
        "devine persoană doar dacă fețele ei stau în cel puțin două fișiere diferite. "
        "O față văzută o singură dată nu produce o persoană în interfață. Regulă "
        "reduce zgomotul detectorului cu prețul de a ascunde invitații care apar "
        "într-un singur cadru. Pentru un album de nuntă, persoanele care revin sunt "
        "cele pe care studioul le caută întâi."
    )

    doc.h2("3.8. Ce înseamnă învățare automată în acest sistem")
    doc.p(
        "YuNet și SFace sunt modele învățate. Parametrii lor au fost estimați de "
        "autorii citați pe colecții mari de fețe, cu funcții de cost și cu protocoale "
        "publice. În Lumina, parametrii sunt înghețați. Nicio nuntă prelucrată de "
        "prototip nu modifică o pondere. În taxonomia obișnuită, acesta este un sistem "
        "care inferă cu modele preantrenate și decide cu reguli. Nu este un sistem "
        "care se antrenează pe datele utilizatorului și nu este un sistem de învățare "
        "activă."
    )
    doc.p(
        "Delimitarea nu micșorează rolul modelelor. Fără un detector învățat, numărul "
        "de fețe și secțiunile albumului ar cădea pe euristici de culoare, iar grupurile "
        "de persoane nu ar exista în forma raportată. Învățarea automată este deci în "
        "sistem, în componentele de față. Ea nu este în pragul 0,38, în distanța Hamming "
        "5 sau în lungimea 160 a albumului. Acestea sunt decizii de proiectare și se "
        "apără ca atare: prin efectul lor asupra setului descris, nu prin invocarea "
        "cuvântului „model”."
    )

    doc.h1("4. Cerințele sistemului")
    doc.h2("4.1. Actorii")
    doc.p(
        "Sistemul are doi actori și un singur eveniment. Fotograful, în vedere de "
        "studio, pornește prelucrarea, inspectează respingerile și duplicatele, vede "
        "albumul propus, persoanele și scenariul de timp. Cuplul, în vedere proprie, "
        "privește albumul, poate parcurge o prezentare și o carte, caută persoanele "
        "și marchează fotografiile pe care vrea să le păstreze. Niciunul dintre actori "
        "nu are cont. Diferența dintre ei, în prototip, este o stare a paginii, iar "
        "trecerea la studio cere un cod ținut minte pe durata filei de browser."
    )
    doc.p(
        "Ipoteza de demonstrație este că cele două roluri se arată pe același calculator, "
        "în aceeași aplicație. Lista de inimi stă în memoria locală a browserului, sub "
        "cheia lumina-shortlist, nu pe server. Dacă cuplul ar deschide adresa de pe alt "
        "telefon, nu ar vedea evenimentul studioului și nu ar trimite inimile înapoi. "
        "Pentru o susținere, ipoteza este suficientă și trebuie spusă. Pentru un produs "
        "în care clientul alege de acasă, ar trebui un identificator de eveniment pe "
        "server. Lucrarea nu construiește acel pas."
    )

    doc.h2("4.2. Cerințe funcționale")
    doc.p("Sistemul trebuie să îndeplinească următoarele.")
    doc.items(
        [
            "Să poată porni o ședință de demonstrație de 3000 de cadre, construită din fotografii reale publice, și să arate progresul pe faze: surse, cadre, calitate, duplicate, persoane, album, registru.",
            "Să poată primi un dosar propriu de imagini JPEG, PNG sau WebP și să aplice aceeași decizie, fără etichete de validare.",
            "Să respingă cadrele ilizibile, moi sau slab expuse și să păstreze motivul.",
            "Să marcheze duplicatele în interiorul scenei și să indice fișierul păstrat.",
            "Să detecteze fețe pe cadrele rămase, să le grupăze și să păstreze o copertă pentru fiecare persoană cu cel puțin două fotografii.",
            "Să compună un album de cel mult 160 de cadre, cu secțiuni după numărul de fețe și cu un plafon de cadre pe scenă.",
            "Să scrie evenimentul în SQLite, inclusiv scorurile, stările și sumarul.",
            "Să deschidă albumul în vedere de cuplu, fără scoruri, fără registrul de respingeri și fără lei.",
            "Să permită cuplului să marcheze fotografii și studioului să le deschidă primele.",
            "Să calculeze un scenariu de ore și de lei din ipoteze afișate, nu din constante ascunse.",
        ],
        numbered=True,
    )

    doc.h2("4.3. Cerințe nefuncționale")
    doc.p(
        "Prototipul rulează pe un singur calculator, fără serviciu de conturi. Pagină, "
        "server și bază stau în același dosar de proiect. Imaginile nu sunt trimise "
        "la un API comercial de vedere computerizată. Modelele ONNX se descarcă o dată "
        "în data/models și se reutilizează. Baza folosește jurnalul WAL, astfel încât "
        "o citire a evenimentului să nu aștepte o scriere lungă."
    )
    doc.p(
        "Interfața de demonstrație este în engleză, pentru că prototipul a fost "
        "pregătit să poată fi arătat și în afara textului de față. Lucrarea este în "
        "română. Numele stărilor din bază — rejected, duplicate, kept, album — rămân "
        "în engleză, ca în cod, iar textul le traduce la fiecare capitol în care "
        "apar. Timpul de răspuns urmărit nu este un timp real de cameră. Ședința se "
        "prelucrează în fundal, iar pagina întreabă starea lucrării până la final. "
        "Rularea măsurată, care include și pregătirea setului, a durat 268,3 secunde."
    )
    doc.p(
        "Datele personale sunt o cerință de proiectare chiar dacă prototipul nu este "
        "un produs. Fotografiile unei nunți reale înfățișează persoane și sunt date "
        "cu caracter personal. Setul de demonstrație folosește imagini din colecții "
        "publice, Wikimedia Commons și Unsplash, reținute doar dacă trec un filtru "
        "tehnic. Dosarul data/ nu este versionat. O folosire pe nunți de client ar "
        "avea nevoie de temei, de o politică de păstrare și de o separare între "
        "calculatorul studioului și orice mașină de demonstrație. Prototipul arată "
        "unde stau fișierele. Nu oferă, prin el însuși, conformitatea."
    )

    doc.h2("4.4. În afara sistemului")
    doc.p(
        "Ca să rămână clar ce se susține, următoarele nu fac parte din Lumina. Nu "
        "există antrenare și nu există ajustarea pragurilor pe un set ținut separat "
        "de setul măsurat: aceleași constante construiesc și judecă demonstrația, iar "
        "capitolul 7 tratează acest fapt ca pe o limită. Nu există developare, "
        "corecție de culoare sau încadrare automată pentru tipar. Nu există plată, "
        "contract sau trimitere a albumului prin e-mail. Nu există garanția că două "
        "fețe unite sunt aceeași persoană în sensul unei baze de identitate. Nu "
        "există măsurarea timpului real al unui fotograf care triază aceeași ședință "
        "cu ceasul lângă el. Orele din capitolul 8 sunt un model aritmetic."
    )

    doc.h1("5. Proiectarea")
    doc.h2("5.1. Arhitectura")
    doc.p(
        "Sistemul are trei straturi. Primul construiește sau primește imaginile. Al "
        "doilea decide și scrie. Al treilea citește baza și o arată. Pagina nu "
        "calculează laplacianul și nu încarcă modelele. Serverul, scris cu FastAPI, "
        "expune evenimentul, starea lucrării, fișierele imaginilor și copertele "
        "persoanelor. O lucrare de prelucrare rulează în fundal, ca să nu blocheze "
        "cererile de citire."
    )
    doc.caption("Figura 5.1. Fluxul de la fotografiile-sursă până la cele două vederi.")
    doc.image(f1, 15.5)
    doc.p(
        "Separarea merită păstrată și la citirea codului. dataset.py știe cum se "
        "obțin sursele și cum se fabrică cele 3000 de cadre. pipeline.py știe măsurătorile "
        "și nu știe de HTTP. economics.py știe ipotezele și nu știe de imagini. "
        "db.py știe schema. service.py leagă o lucrare de o scriere în bază. main.py "
        "leagă scrierea de URL-uri. static/ este pagina. Un defect de prag se caută "
        "în pipeline, nu în marcajul HTML."
    )

    doc.h2("5.2. Modelul de date")
    doc.p(
        "Unitatea de lucru este evenimentul: o nuntă de demonstrație sau un dosar "
        "încărcat. Evenimentul păstrează numele, felul, momentul creării, numărul de "
        "cadre, durata rulării și un sumar în JSON. Sumarul repetă conteurile, "
        "motivele, secțiunile albumului, validarea când există etichete, și scenariul "
        "economic. Repetarea în JSON există ca să poată fi citită de pagină fără un "
        "șir de interogări; conteurile se pot și reconstrui din tabelul de fotografii."
    )
    doc.p(
        "Fotografia păstrează calea relativă, scena, eticheta de generator dacă există, "
        "claritatea, expunerea, scorul, numărul de fețe, starea, motivul, duplicatul "
        "căruia îi este subordonată, secțiunea și ordinea în album. Stările legale "
        "sunt rejected, duplicate, kept și album. Un cadru de album este un cadru "
        "care a fost păstrat și apoi ales în selecția de 160. Cadrele păstrate care "
        "nu încap în album rămân kept. Astfel, unicul utilizabil este suma dintre "
        "kept și album, nu doar albumul."
    )
    doc.p(
        "Persoana păstrează eticheta afișată, numărul de fotografii și calea copertii. "
        "Fața păstrează căsuța și legătura către fotografie și, când gruparea a reușit, "
        "către persoană. Coperțile sunt decupaje scrise pe disc, nu imagini servite "
        "din original la fiecare cerere. Schema este creată la pornirea serverului "
        "dacă lipsește. Nu există migrări: prototipul are o singură formă de tabel, "
        "iar ștergerea dosarului data/ reface experimentul de la surse."
    )

    doc.h2("5.3. Fluxul de decizie")
    doc.p(
        "Ordinea fazelor este fixă. Se măsoară toate cadrele, fără fețe. Se marchează "
        "duplicatele între cele rămase. Se încarcă modelele și se măsoară fețele doar "
        "pe cadrele cu starea păstrat. Se construiește albumul. Se grupază persoanele "
        "pe fețele cadrelor care sunt încă păstrate sau au devenit album. Se calculează "
        "sumarul, validarea și economia. Se scrie baza."
    )
    doc.p(
        "Fețele nu se caută pe respinse și nici pe duplicate. Economia de timp este "
        "reală, pentru că inferența este partea scumpă, dar există și un efect de "
        "metodă: o persoană care apare doar în cadre moi nu va avea grup. Pentru "
        "album, cadrul moale nu ar fi intrat oricum. Pentru o statistică de prezență "
        "la eveniment, omisiunea ar conta. Lumina nu produce o statistică de prezență."
    )
    doc.p(
        "Durata scrisă în eveniment se măsoară de la începutul lucrării de demonstrație, "
        "deci include și descărcarea surselor, când ele lipsesc, și scrierea celor "
        "3000 de cadre, când manifestul lipsește. Valoarea 268,3 secunde este durata "
        "acestei rulări complete, nu durata pură a laplacianului. Folosirea ei în "
        "scenariul economic este conservatoare: orele atribuite sistemului sunt mai "
        "mari decât ale unei reluări în care fișierele sunt deja pe disc. O reluare "
        "ar fi mai scurtă. Cifra din lucrare rămâne cea stocată."
    )

    doc.h2("5.4. Albumul")
    doc.p(
        "După duplicate, fiecare cadru păstrat primește o secțiune după numărul de "
        "fețe. Trei sau mai multe fețe înseamnă invitați. Două fețe înseamnă cuplu. "
        "O față înseamnă portret. Nicio față înseamnă detalii. Regulile sunt grosiere. "
        "Două fețe pot fi doi invitați, nu mirii, iar un detaliu de inel pe care "
        "detectorul a pus o față falsă pleacă din secțiunea de detalii. Ele există "
        "ca să aibă albumul o ordine povestibilă, nu ca să clasifice relațiile de "
        "la nuntă."
    )
    doc.p(
        "Umplerea nu ia primele 160 de scoruri. Pentru fiecare secțiune există un "
        "țel — 56 pentru cuplu, 40 pentru portrete, 40 pentru invitați, 24 pentru "
        "detalii — și un plafon de două cadre din aceeași scenă. Se parcurg cadrele "
        "secțiunii în ordinea scorului și se acceptă cadrul dacă plafonul scenei "
        "nu este atins. Dacă după această trecere albumul are mai puțin de 160, se "
        "completează din toate cadrele păstrate, tot după scor, cu plafonul de scenă "
        "urcat la trei. Țelurile sunt dorințe. Dacă o secțiune nu are destule cadre, "
        "ea rămâne scurtă, iar locul se umple din ce există. Capitolul 7 arată că "
        "exact aceasta s-a întâmplat cu invitații și cu detaliile."
    )
    doc.p(
        "Plafonul de scenă este decizia editorială a prototipului. Fără el, scorul "
        "tehnic concentrează selecția în scenele cu multă textură clară, adică tocmai "
        "în scenele din care generatorul a produs multe copii bune. Cu el, albumul "
        "este obligat să meargă mai departe în ședință. Prețul este că al 161-lea "
        "cadru, poate mai clar decât unul păstrat dintr-o scenă slabă, rămâne pe "
        "din afară. Fotograful îl vede în masa de cadre păstrate, nu doar în album."
    )

    doc.h2("5.5. Cele două vederi")
    doc.p(
        "Pagina pornește în vederea cuplului. Vederea de studio se deschide după un "
        "cod introdus într-un formular din pagină. Codul de demonstrație este "
        "lumina, comparat fără să se țină cont de litere mari, și este reținut în "
        "sessionStorage pentru fila curentă. O filă nouă cere codul din nou. "
        "Mecanismul oprește situația în care cuplul, deschizând aceeași adresă, "
        "intră direct în registru și în lei. El nu oprește pe cineva care citește "
        "fișierul JavaScript. De aceea lucrarea îl numește poartă de demonstrație."
    )
    doc.p(
        "În vedere de cuplu, scorurile, comparația dintre un cadru respins și unul "
        "păstrat, economia și registrul nu se desenează. Albumul, prezentarea, cartea "
        "și persoanele rămân. Marcajul de inimă adaugă identificatorul fotografiei "
        "într-o listă locală. În vedere de studio, aceeași listă se numește listă "
        "scurtă. Dacă lista este goală, studio vede că cuplul nu a ales încă și poate "
        "trece la vederea cuplului. Dacă lista are elemente, un mesaj spune câte "
        "fotografii au fost păstrate, iar deschiderea lor le arată înaintea restului. "
        "Cartea albumului începe tot cu ele. Baza de date nu se modifică: inimile "
        "sunt o preferință de sesiune peste albumul deja scris."
    )
    doc.p(
        "Linia de tăiere din studio este tot o preferință de afișare. Cursorul "
        "stabilește un prag între scorul minim și scorul maxim din album și ascunde "
        "cadrele de dedesubt. La zero, se arată albumul întreg. Cuplul nu are acest "
        "cursor: pentru el, tăierea este mereu zero. Cursorul nu rescrie starea album "
        "din bază. El servește la discuția din studio despre cât de sus se taie "
        "propunerea, nu la o a doua selecție persistentă."
    )

    doc.h2("5.6. Scenariul economic")
    doc.p(
        "Modelul economic nu măsoară un studio. El înmulțește ipoteze. Timpul manual "
        "este numărul de cadre înmulțit cu 6,5 secunde, plus 70 de minute pentru "
        "gruparea persoanelor și pentru ordonarea albumului. Timpul cu Lumina este "
        "durata măsurată a lucrării, plus 18 minute de revizie. Diferența, dacă este "
        "pozitivă, se înmulțește cu 150 de lei pe oră. Luna de lucru presupune șase "
        "evenimente de aceeași mărime. Pachetul mediu de 6500 de lei este afișat ca "
        "context, nu intră în diferența de cost a trierii."
    )
    doc.p(
        "Toate cele șase numere sunt vizibile în interfața de studio și sunt repetate "
        "în sumarul JSON. Schimbarea lor în cod schimbă lei fără să schimbe un pixel "
        "din album. Capitolul 8 folosește această proprietate ca să arate sensibilitatea. "
        "Un cititor care nu acceptă 6,5 secunde pe cadru poate înlocui ipoteza și "
        "păstra aceeași durată măsurată. Ce nu poate face, pe baza acestei lucrări, "
        "este să trateze 931 de lei ca pe un câștig observat într-un contabilitate "
        "de studio."
    )

    doc.h1("6. Implementarea")
    doc.h2("6.1. Tehnologii")
    doc.p(
        "Serverul este un proces Python 3.12. Interfața HTTP este FastAPI, servită "
        "de uvicorn pe adresa locală 127.0.0.1 și pe portul 8741. Imaginile și "
        "modelele trec prin OpenCV 4.11.0.86, construit fără ferestre, și prin NumPy. "
        "Baza este SQLite, în data/lumina.db. Pagina este HTML, CSS și JavaScript "
        "fără un pas de compilare: serverul o servește ca fișiere statice, iar o "
        "reîmprospătare vede modificarea de interfață. O modificare în Python cere "
        "repornirea procesului."
    )
    doc.p(
        "Alegerea este deliberat mică. Nu există un serviciu separat de cozi, pentru "
        "că există o singură lucrare grea la un moment dat; a doua pornire este "
        "refuzată cât timp prima nu s-a încheiat. Nu există un cadru de interfață "
        "cu pachete proprii, pentru că pagina are două stări și un număr limitat de "
        "gesturi. Dependențele declarate sunt FastAPI, uvicorn, python-multipart, "
        "OpenCV la versiunea fixată și NumPy. Reproducerea pornește de la un mediu "
        "virtual și de la acest fișier de dependențe, descris în anexă."
    )

    doc.h2("6.2. Construirea setului")
    doc.p(
        "Sursele se caută în două locuri publice. O listă de identificatori Unsplash "
        "dă URL-uri de previzualizare la lățime de o mie de pixeli. Categoriile "
        "Wikimedia Commons folosite sunt cele de miri, de ceremonii, de fotografii "
        "de nuntă, de recepții și de miri. Din titlurile Commons se sar fișierele "
        "ale căror nume conțin cuvinte de genul pictură, ulei, gravură sau afiș, "
        "pentru că o căutare de nuntă întoarce și lucrări de artă. O sursă este "
        "păstrată doar dacă claritatea ei este cel puțin 0,42, expunerea cel puțin "
        "0,48 și conține o față de cel puțin 48 de pixeli pe latura mare a căsuței. "
        "Filtrul este mai sever decât poarta de triere. El există ca să nu se "
        "genereze o ședință din imagini deja inutilizabile."
    )
    doc.p(
        "Rularea stocată a păstrat 56 de surse. Fiecare sursă este o scenă. Din ea "
        "se scriu cinci variante good, prin decupaje fixe și o ușoară ridicare de "
        "lumină la una dintre ele, opt variante bad și atâtea duplicate câte sunt "
        "necesare ca totalul să fie 3000. Variantele bad alternează neclaritatea "
        "puternică, întunecarea și arderea. Duplicatul adaugă zgomot gaussian de "
        "abatere 1 și se rescrie JPEG la calitate 78. Generatorul de numere are "
        "sămânța 7. Latura mare a cadrelor scrise este cel mult 840 de pixeli."
    )
    doc.p(
        "Aritmetica iese rotund. 56 de surse ori 5 dau 280 de cadre good. 56 ori 8 "
        "dau 448 de cadre bad. Restul, 2272, sunt dup. Aceste numere sunt proprietăți "
        "ale generatorului, nu o măsurătoare a unei nunți reale. Proporția mare de "
        "duplicate, cam trei sferturi din ședință, este pusă intenționat, ca trierea "
        "să aibă o rafală de rezolvat. Un studio real poate avea altă proporție. "
        "Manifestul și un fișier de versiune opresc reconstruirea la fiecare pornire: "
        "dacă versiunea și numărul de cadre coincid, se reîncarcă lista existentă."
    )

    doc.h2("6.3. Măsurarea și duplicatele")
    doc.p(
        "Fiecare cadru este citit, convertit la gri și măsurat cum s-a descris în "
        "capitolul 3. Implementarea parcurge cele 3000 de fișiere în serie și "
        "raportează progresul la fiecare 40 de cadre. Nu există paralelism pe "
        "procese. Pentru dimensiunea aceasta, citirea discului și calculul pe imagini "
        "de cel mult 840 de pixeli încap într-o lucrare de câteva minute, împreună "
        "cu restul fazelor."
    )
    doc.p(
        "Duplicatele se calculează după ce toate stările de calitate sunt cunoscute. "
        "Se grupează pe scenă doar cadrele păstrate. Union-find folosește compresia "
        "căii. La unire, părintele este indicele cadrului cu scorul mai mare, scorul "
        "fiind încă Q, fără bonusul de fețe, pentru că fețele nu au rulat. Astfel, "
        "rădăcina rafalei este aleasă pe claritate și expunere, nu pe numărul de "
        "fețe. Bonusul de fețe poate reordona ulterior albumul, dar nu mută un "
        "duplicat înapoi între păstrate."
    )

    doc.h2("6.4. Fețe, persoane, album")
    doc.p(
        "Modelele se descarcă în data/models dacă lipsesc sau dacă fișierul este "
        "sub o dimensiune minimă: YuNet din depozitul OpenCV Zoo, ediția din martie "
        "2023, și SFace ediția din decembrie 2021. Eșecul la SFace nu oprește "
        "lucrarea; recunoscătorul rămâne neinițializat și se folosesc histogramele. "
        "Pe cadrele păstrate, detectorul rulează și, când există vector, acesta se "
        "normalizează. O eroare de aliniere pe un decupaj sare fața respectivă, nu "
        "întreaga ședință."
    )
    doc.p(
        "Albumul se construiește în memorie, prin funcția descrisă la proiectare, "
        "apoi persoanelor li se scriu coperți. Coperta este un decupaj al unei fețe "
        "din grup, suficient ca interfața să aibă un chip de persoană, nu un portret "
        "ales editorial. Eticheta afișată este de forma „Person” urmat de un număr "
        "de ordine după mărimea grupului. Nu se încearcă recunoașterea numelui."
    )
    doc.p(
        "Validarea se calculează doar dacă există etichete good, dup și bad. La un "
        "dosar încărcat, rolul cadrului este gol și validarea lipsește din sumar. "
        "Pagină tratează lipsa ca pe o ședință fără notă de acord, nu ca pe o eroare. "
        "Definițiile celor trei rapoarte sunt în capitolul 7, lângă cifre, ca să nu "
        "existe două formulări."
    )

    doc.h2("6.5. Persistența și interfața")
    doc.p(
        "Scrierea înlocuiește fotografiile evenimentului de demonstrație când evenimentul "
        "există deja, astfel încât o rerulare să nu lase rânduri duble. Căile stocate "
        "sunt relative la dosarul data/, iar servirea unei imagini refuză o cale care "
        "ar ieși din acest dosar. Persoanele și fețele se scriu după fotografii, cu "
        "legături la identificatorii proaspăt creați."
    )
    doc.p(
        "Pagina, la încărcare, cere ultimul eveniment. Dacă există, desenează albumul "
        "fără să ceară o nouă prelucrare. Butonul de demonstrație pornește lucrare "
        "nouă doar la cerere. Vederea este o clasă pe corpul paginii: regulile de "
        "stil ascund blocurile de studio în fața cuplului și invers. Această alegere "
        "face ca cele două roluri să fie două prezentări ale aceluiași document, nu "
        "două aplicații care ar putea diverge."
    )
    doc.p(
        "Gesturile de studio includ comparația dintre un cadru moale și un cadru "
        "păstrat din aceeași scenă, când o astfel de pereche există, și inspectarea "
        "respingerilor. Gesturile de cuplu includ prezentarea și cartea. Niciun gest "
        "nu schimbă scorul din bază. Singura stare scrisă de pagină este locală: "
        "rolul ales, poarta de studio și lista de inimi."
    )

    doc.h2("6.6. Decizii care s-au văzut abia la rulare")
    doc.p(
        "Câteva decizii din cod sunt urmarea unei rulări mai mici, nu a unui plan "
        "rămas neatins. Pragul Hamming a fost coborât pentru că decupajele se lipeau. "
        "Neclaritatea generată a fost întărită pentru că o încețoșare ușoară încă "
        "trecea poarta și făcea ca eticheta bad să nu însemne un eșec vizibil. "
        "OpenCV a fost fixat pe ramura 4 pentru că detectorul nu producea fețe "
        "utilizabile pe ramura încercată întâi. Union-find a înlocuit o potrivire "
        "lacomă care pierdea duplicate ale unui părinte deja unit cu alt cadru."
    )
    doc.p(
        "Aceste fapte se scriu pentru că pragurile finale nu sunt independente de "
        "set. Ele au fost mișcate până când generatorul și poarta au ajuns în acord "
        "rezonabil, iar apoi au fost înghețate pentru rularea de 3000. Este exact "
        "procedura pe care capitolul 7 refuză să o numească test orb. Este, în "
        "schimb, o procedură onestă de construcție a unui prototip: regulile s-au "
        "stabilizat pe observație, iar măsurătoarea finală se publică împreună cu "
        "definițiile, inclusiv cu cadrul bad care a trecut."
    )

    doc.h1("7. Experiment și rezultate")
    doc.h2("7.1. Ce s-a rulat")
    doc.p(
        "Experimentul raportat este o singură prelucrare completă a setului de "
        "demonstrație, stocată ca evenimentul 1, „Demo wedding”, de fel demo. Baza "
        "conține 3000 de rânduri în tabelul de fotografii, 65 de persoane și 375 "
        "de fețe. Durata stocată este 268,3 secunde. Nu s-a făcut o medie pe mai "
        "multe semințe. Generatorul are sămânța fixă 7, iar manifestul de versiune "
        "4 reproduce aceleași fișiere cât timp sursele nu se schimbă. Cifrele de "
        "mai jos se pot reconstrui prin interogări asupra data/lumina.db."
    )
    doc.p(
        "Nu există un al doilea set, ținut deoparte, pe care pragurile să nu fi fost "
        "privite. Nu există note date de un fotograf. Comparațiile din acest capitol "
        "sunt interne: acordul cu etichetele generatorului și diferența față de două "
        "proceduri mai simple pe aceleași scoruri. Ambele sunt utile. Niciuna nu "
        "înlocuiește un set etichetat de un om."
    )

    doc.h2("7.2. Partiția ședinței")
    doc.p(
        "Cele 3000 de cadre se împart în patru stări care se adună exact la total: "
        "563 respinse, 2174 duplicate, 103 păstrate în afara albumului și 160 de "
        "album. Unicele sunt 263, adică păstrate plus album. Albumul este 60,8% din "
        "unice și 5,3% din ședință. Respingerile sunt 18,8% din ședință. Duplicatele "
        "sunt 72,5%. Proporția mare de duplicate urmărește proporția pusă de generator, "
        "2272 de fișiere dup, din care o parte au fost respinse pe calitate înainte "
        "să apuce să fie unite în rafale."
    )
    doc.caption("Figura 7.1. Partiția celor 3000 de cadre după starea finală.")
    doc.image(f2, 14.2)
    doc.caption("Tabelul 7.1. Starea finală a cadrelor.")
    doc.table(
        ["Stare", "Cadre", "Pondere din 3000"],
        [
            ["Respinse", "563", "18,8%"],
            ["Duplicate", "2174", "72,5%"],
            ["Păstrate, în afara albumului", "103", "3,4%"],
            ["Album", "160", "5,3%"],
            ["Unice (păstrate + album)", "263", "8,8%"],
        ],
    )
    doc.p(
        "Motivele de respingere și de duplicat sunt în tabelul 7.2. Nu există cadre "
        "ilizibile în această rulare: toate fișierele generate s-au putut citi. "
        "Dintre respingeri, 402 sunt pentru claritate și 161 pentru expunere. "
        "Neclaritatea este deci eșecul dominant dintre cele fabricate, ceea ce este "
        "coerent cu numărul mai mare de variante blur din ciclul de eșecuri."
    )
    doc.caption("Tabelul 7.2. Motivele scrise pe cadrele care nu rămân candidate unice.")
    doc.table(
        ["Motiv", "Stare", "Cadre"],
        [
            ["Duplicate", "duplicat", "2174"],
            ["Soft", "respins", "402"],
            ["Poor exposure", "respins", "161"],
        ],
    )

    doc.h2("7.3. Acordul cu etichetele generatorului")
    doc.p(
        "Etichetele se distribuie, după starea finală, ca în tabelul 7.3. Totalurile "
        "pe rând sunt cele puse de generator: 280 good, 2272 dup, 448 bad."
    )
    doc.caption("Tabelul 7.3. Eticheta de generator față de starea decisă de prototip.")
    doc.table(
        ["Etichetă", "Album", "Păstrat", "Duplicat", "Respins", "Total"],
        [
            ["good", "94", "71", "103", "12", "280"],
            ["dup", "65", "31", "2069", "107", "2272"],
            ["bad", "1", "1", "2", "444", "448"],
        ],
    )
    doc.p(
        "Trei rapoarte sunt stocate în sumar. good_kept este fracția de cadre good "
        "care nu au starea respins. 12 din 280 au fost respinse, deci 268 din 280 "
        "rămân, adică 0,957. Respingerea unui good nu este întotdeauna o greșeală de "
        "produs: unele decupaje coboară claritatea sub 0,38. Este însă o dezacordare "
        "cu eticheta, și se raportează ca atare."
    )
    doc.p(
        "rejects_caught este fracția de cadre bad cu starea respins: 444 din 448, "
        "adică 0,991. Patru cadre bad nu au fost respinse. Două au devenit duplicate, "
        "deci nu au intrat în album. Unul a rămas păstrat în afara albumului. Unul "
        "a intrat în album. Ultimul este eșecul cel mai vizibil al rulării: poarta "
        "de calitate nu a recunoscut un cadru fabricat ca eșec, iar regulile de "
        "album nu l-au lăsat pe dinafară. Un cadru din 160 este 0,6% din predare. "
        "Pentru un prototip este o eroare localizată. Pentru un text de lucrare este "
        "o eroare care trebuie arătată, nu netezită în 0,991."
    )
    doc.p(
        "duplicates_caught se calculează doar pe cadrele dup care nu au fost deja "
        "respinse. Un astfel de cadru contează ca prins dacă starea lui este duplicat "
        "sau dacă numele lui este rădăcina indicată de alte cadre. A doua ramură "
        "există tocmai pentru copiile care au câștigat rafala. Pe rulare, raportul "
        "este 1,000. El spune că niciun dup trecut de poarta de calitate nu a rămas "
        "în afara componentei sale. Nu spune că fișierele dup lipsesc din album. "
        "Tabelul 7.3 arată 65 de dup în album și 31 păstrate: sunt rădăcini de rafală "
        "sau cadre dup pe care hash-ul nu le-a unit cu un good, dar pe care metrica, "
        "prin definiția cu rădăcina, le consideră tratate. Cititorul trebuie să țină "
        "ambele numere. 1,000 fără tabelul 7.3 ar ascunde că albumul conține copii "
        "alese ca reprezentant."
    )

    doc.h2("7.4. Baseline-uri pe aceleași scoruri")
    doc.p(
        "Acordul cu etichetele nu spune dacă regulile de rafală și de scenă schimbă "
        "albumul față de o procedură mai simplă. S-au calculat două proceduri pe "
        "rândurile deja stocate, fără o nouă inferență."
    )
    doc.p(
        "Prima păstrează orice cadru cu claritatea cel puțin 0,38 și expunerea cel "
        "puțin 0,50, apoi ia primele 160 de scoruri. Trec poarta 2437 de cadre. "
        "Cele 160 de scoruri de vârf conțin 13 etichete good, 147 etichete dup și "
        "niciun bad, și acoperă 10 scene. Selecția este tehnic „bună” și editorial "
        "strânsă: vârfurile de scor sunt copiile scenelor cu textură puternică."
    )
    doc.p(
        "A doua păstrează, dintre cadrele trecute de poartă, un singur cadru pe "
        "scenă, pe cel cu scorul maxim. Ies 56 de cadre, câte scena, dintre care "
        "10 good și 46 dup, niciun bad. Diversitatea de scene este maximă pe acest "
        "set, iar lungimea este prea mică pentru albumul cerut. Faptul că reprezentantul "
        "scenei este adesea etichetat dup repetă observația de la rădăcină: scorul "
        "maxim nu coincide cu fișierul pe care generatorul l-a numit good."
    )
    doc.p(
        "Albumul Lumina are 160 de cadre, 94 good, 65 dup și 1 bad, pe 55 de scene. "
        "Față de primele 160 de scoruri, câștigă acoperirea: 55 de scene față de 10, "
        "și urcă numărul de good de la 13 la 94. Față de un cadru pe scenă, câștigă "
        "lungimea și păstrează aproape toate scenele, 55 din 56. Prețul este cadrul "
        "bad și cei 65 de reprezentanți etichetați dup. Figura 7.2 pune cele trei "
        "selecții una lângă alta."
    )
    doc.caption("Figura 7.2. Trei selecții pe aceleași cadre: după scor, un cadru pe scenă, albumul Lumina.")
    doc.image(f3, 14.5)
    doc.caption("Tabelul 7.4. Comparația cu proceduri mai simple.")
    doc.table(
        ["Procedură", "Cadre", "good", "dup", "bad", "Scene"],
        [
            ["Top 160 după scor, peste poarta de calitate", "160", "13", "147", "0", "10"],
            ["Cel mai bun cadru pe scenă", "56", "10", "46", "0", "56"],
            ["Albumul Lumina", "160", "94", "65", "1", "55"],
        ],
    )
    doc.p(
        "Tabelul nu se citește ca o victorie de acuratețe împotriva unei etichete "
        "de fotograf. Se citește ca un efect de structură. Plafonul de scenă și "
        "scoaterea copiilor din cursa pentru scor sunt ceea ce împiedică albumul "
        "să devină o sută șaizeci de variante a zece imagini. Acesta este rezultatul "
        "cel mai folositor al capitolului, tocmai pentru că nu depinde de povestea "
        "că eticheta good ar fi gustul unui om."
    )

    doc.h2("7.5. Compunerea albumului și persoanele")
    doc.p(
        "Secțiunile albumului nu au atins țelurile din proiectare. Portretele țin "
        "89 de cadre, cuplul 57, invitații 9, detaliile 5. Țelul de cuplu, 56, este "
        "practic atins. Portretele depășesc țelul de 40 pentru că completarea până "
        "la 160 s-a sprijinit pe ce exista. Invitații și detaliile rămân subțiri."
    )
    doc.caption("Figura 7.3. Secțiunile albumului de 160 de cadre.")
    doc.image(f4, 12.5)
    doc.caption("Tabelul 7.5. Albumul pe secțiuni, față de țelul din cod.")
    doc.table(
        ["Secțiune", "Regulă de fețe", "Țel", "Obținut"],
        [
            ["Couple", "exact 2", "56", "57"],
            ["Portraits", "exact 1", "40", "89"],
            ["Guests", "3 sau mai multe", "40", "9"],
            ["Details", "niciuna", "24", "5"],
        ],
    )
    doc.p(
        "Dezechilibrul are o cauză în set, nu doar în umplere. Sursele au fost "
        "filtrate ca să conțină o față destul de mare, iar variantele generate "
        "nu adaugă mese largi sau săli pline. Detectorul găsește deci mai des una "
        "sau două fețe decât un grup, iar cadrele fără față sunt rare între cele "
        "păstrate. Un album real de nuntă ar avea mai multe detalii și mai mulți "
        "invitați. Rezultatul de față arată limita de conținut a demonstrației. "
        "Algoritmul de secțiuni nu poate inventa cadre care nu au trecut poarta."
    )
    doc.p(
        "Pe fețe, rularea a păstrat 375 de căsuțe și 65 de persoane. O persoană "
        "are cel puțin două fotografii distincte. Mediana este 5 fotografii. "
        "Grupul cel mai mare are 17. Distribuția este strânsă în jurul lui 5, cu "
        "o coadă de grupuri de 10 și cu trei grupuri de 14, 15 și 17. Numărul mic "
        "de fotografii pe persoană este coerent cu generatorul: fețele vin din "
        "aceeași sursă și din decupajele ei, nu din zeci de apariții independente "
        "ale unui invitat în sală."
    )
    doc.caption("Figura 7.4. Câte persoane au un anumit număr de fotografii distincte. Lipsesc dimensiunile fără niciun grup.")
    doc.image(f5, 14.2)
    doc.caption("Tabelul 7.6. Mărimea grupurilor de persoane.")
    doc.table(
        ["Fotografii în grup", "Persoane"],
        [
            ["2", "2"],
            ["3", "11"],
            ["4", "7"],
            ["5", "29"],
            ["6", "1"],
            ["8", "2"],
            ["9", "3"],
            ["10", "7"],
            ["14", "1"],
            ["15", "1"],
            ["17", "1"],
        ],
    )
    doc.p(
        "Grupurile nu au fost verificate ochi cu ochi, cadru cu cadru, de un "
        "evaluator. Nu se raportează deci o precizie de identitate. Ce se poate "
        "spune este că procedura a produs grupuri de mărime plauzibilă pentru "
        "felul setului și că o față izolată nu a umflat lista de persoane. "
        "Erorile de identitate, dacă există, stau în interiorul acestor 65 de "
        "grupuri și nu au o cifră în această lucrare."
    )

    doc.h2("7.6. Ce nu susțin cifrele")
    doc.p(
        "good_kept de 0,957 nu este acuratețea unui fotograf. Este fracția de "
        "variante pe care generatorul le-a numit bune și pe care poarta nu le-a "
        "aruncat. duplicates_caught de 1,000 nu este o măsură de diversitate a "
        "albumului. Este comportamentul hash-ului pe copii fabricate cu zgomot "
        "mic, plus convenția că rădăcina contează ca prinsă. rejects_caught de "
        "0,991 nu contrazice cadrul bad din album; îl include la numitor și îl "
        "lasă în afara numărătorului, împreună cu alte trei scăpări."
    )
    doc.p(
        "Durata de 268,3 secunde nu este timpul unui fotograf și nu este nici "
        "timpul pur de triere pe fișiere deja scrise. Scenariul de 6,21 ore nu "
        "este o observare. Cele 55 de scene ale albumului sunt un fapt despre "
        "această bază. Ele arată la ce folosește plafonul, în comparație cu topul "
        "de scor. Nu arată că un client ar fi mulțumit de cele 160 de cadre."
    )
    doc.p(
        "Continuarea cinstită a experimentului este un set mic, de ordinul a "
        "câteva sute de cadre, notat de un fotograf în trei clase — păstrează, "
        "duplicat, aruncă — pe care pragurile actuale să fie aplicate fără să "
        "mai fie mișcate. Până la acel set, capitolul de față își ține concluzia "
        "în interiorul generatorului și al comparației structurale."
    )

    doc.h1("8. Scenariul de timp și de cost")
    doc.h2("8.1. Ipotezele")
    doc.p(
        "Scenariul folosește ipotezele din tabelul 8.1. Ele sunt aceleași cu cele "
        "afișate în vederea de studio. Durata măsurată care intră în calcul este "
        "268,3 secunde."
    )
    doc.caption("Tabelul 8.1. Ipotezele scenariului, neschimbate în rularea stocată.")
    doc.table(
        ["Ipoteză", "Valoare"],
        [
            ["Decizie manuală pe cadru", "6,5 secunde"],
            ["Grupare și ordonare manuală", "70 minute"],
            ["Revizia propunerii Lumina", "18 minute"],
            ["Tarif de postproducție", "150 lei / oră"],
            ["Evenimente pe lună", "6"],
            ["Pachet mediu, doar ca context", "6500 lei"],
            ["Duratei măsurate a lucrării", "268,3 secunde"],
        ],
    )
    doc.p(
        "6,5 secunde pe cadru înseamnă, la 3000 de cadre, puțin peste cinci ore "
        "doar de parcurs, înainte de grupare. Este o ipoteză de lucru pentru o "
        "trecere atentă, nu un timp mediu publicat de o asociație de profil. "
        "70 de minute acoperă, în model, ceea ce prototipul încearcă să propună "
        "gata: persoanele și o ordine de album. 18 minute sunt timpul în care "
        "fotograful nu este înlocuit. Tariful de 150 de lei pe oră este un preț "
        "de calcul pentru munca de selecție, nu onorariul întregii nunți. Pachetul "
        "de 6500 de lei spune doar ordinul de mărime al unui eveniment față de "
        "care 931 de lei de triere se pot compara. El nu se adaugă și nu se scade "
        "în formulele de mai jos."
    )

    doc.h2("8.2. Calculul pe rularea stocată")
    doc.p(
        "Timpul manual este"
    )
    doc.formula("Tm = 3000 · 6,5 / 3600 + 70 / 60 = 6,58 ore")
    doc.p("Timpul cu Lumina, inclusiv revizia, este")
    doc.formula("Tl = 268,3 / 3600 + 18 / 60 = 0,37 ore")
    doc.p(
        "Diferența este 6,21 ore. Înmulțită cu 150 de lei, dă 931 de lei pe "
        "eveniment. La șase evenimente, modelul dă 37,3 ore și 5588 de lei pe "
        "lună. Raportul dintre orele eliberate într-o lună și timpul manual al "
        "unui eveniment este 5,7: în ipoteza că ziua de fotografiere nu este cea "
        "care limitează studioul, timpul de triere eliberat ar acoperi selecția "
        "a încă 5,7 evenimente de aceeași mărime. Aceasta este o capacitate de "
        "calcul, nu o cerere de piață. Dacă studioul nu are evenimentele, orele "
        "eliberate nu se transformă în pachete."
    )
    doc.caption("Tabelul 8.2. Rezultatul stocat pentru ipotezele din tabelul 8.1.")
    doc.table(
        ["Mărime", "Valoare stocată"],
        [
            ["Timp manual", "6,58 ore"],
            ["Timp Lumina cu revizie", "0,37 ore"],
            ["Diferență", "6,21 ore"],
            ["Diferență în bani, pe eveniment", "931 lei"],
            ["Ore eliberate pe lună", "37,3 ore"],
            ["Bani corespunzători pe lună", "5588 lei"],
            ["Capacitate de selecție în timpul eliberat", "5,7 evenimente"],
        ],
    )
    doc.p(
        "Rotunjirile sunt cele ale prototipului. Diferența de ore se rotunjește "
        "la două zecimale înainte de a fi afișată, iar lei pe lună se calculează "
        "din produsul nerotunjit al orelor eliberate cu tariful, de aceea 37,3 "
        "înmulțit cu 150 nu este numărul care trebuie căutat: valoarea stocată "
        "este 5588. Refacerea de mână a tabelului trebuie să plece de la 268,3 "
        "și de la formule, nu de la înmulțirea cifrelor deja rotunjite."
    )

    doc.h2("8.3. Sensibilitate")
    doc.p(
        "Singurul fapt măsurat în acest capitol este 268,3 secunde. Restul se "
        "mișcă când se schimbă o ipoteză. Tabelul 8.3 păstrează durata măsurată, "
        "cele 70 de minute, cele 18 minute și șase evenimente, și variază secunde "
        "pe cadru și tariful. Valorile sunt recalculate din formule, cu orele "
        "la două zecimale și lei rotunjiți la întreg, și nu înlocuiesc rândul "
        "stocat din tabelul 8.2."
    )
    doc.caption("Tabelul 8.3. Aceeași durată măsurată, alte ipoteze de timp pe cadru și de tarif.")
    # filled below in code path — placeholder replaced by caller via table built here
    rows = []
    for seconds, hourly in ((4.0, 150), (6.5, 150), (10.0, 150), (6.5, 100), (6.5, 200)):
        manual, lumina, saved, ron, month_h, month_ron = econ(seconds, hourly)
        rows.append(
            [
                f"{seconds:.1f} s",
                f"{int(hourly)} lei",
                f"{manual:.2f}",
                f"{saved:.2f}",
                f"{round(ron)}",
                f"{month_h:.1f}",
                f"{round(month_ron)}",
            ]
        )
    doc.table(
        ["Pe cadru", "Tarif", "Ore manual", "Ore câștigate", "Lei / eveniment", "Ore / lună", "Lei / lună"],
        rows,
    )
    doc.p(
        "La 4 secunde pe cadru, diferența coboară la circa 4,13 ore și la circa "
        "619 lei pe eveniment, la același tarif de 150. La 10 secunde, urcă la "
        "circa 9,13 ore și la circa 1369 lei. Tariful schimbă banii fără să schimbe "
        "orele: la 6,5 secunde, 100 de lei pe oră și 200 de lei pe oră pun "
        "diferența de o parte și de alta a celor 931 de lei stocați. Concluzia "
        "de lucru este că semnul economiei nu este fragil pe acest interval — "
        "timpul manual rămâne mult peste 0,37 ore — dar cuantumul în lei este "
        "la fel de precis ca ipoteza. Susținerea corectă este intervalul și "
        "ipoteza, nu un singur leu."
    )
    doc.p(
        "Mai există o sensibilitate care nu încape într-un rând. Dacă revizia "
        "nu este 18 minute, ci o oră, pentru că propunerea trebuie refăcută, "
        "Tl crește cu 42 de minute și diferența scade, fără să dispară la "
        "3000 de cadre. Dacă ședința are 800 de cadre, nu 3000, timpul manual "
        "se contractă aproape liniar, iar timpul fix de grupare, 70 de minute, "
        "cântărește mai greu. Prototipul nu a fost rulat pe o distribuție de "
        "lungimi de ședință. Formula este suficientă ca, la susținere, un alt "
        "număr de cadre să poată fi înlocuit fără a pretinde o nouă măsurătoare "
        "de acuratețe."
    )

    doc.h1("9. Concluzii")
    doc.h2("9.1. Obiectivele, înapoi")
    doc.p(
        "Procedura de la pixeli la stare este închisă și reproductibilă: claritate, "
        "expunere, amprentă în scenă, fețe pe rămase, album cu plafon, scriere în "
        "bază. Cele trei straturi — eșec tehnic, rafală, selecție de album — au "
        "stări și motive distincte. Persoanele sunt grupate cu modele preantrenate, "
        "cu prag de cosinus 0,45 și cu minim două fotografii, iar rularea a produs "
        "65 de grupuri din 375 de fețe. Evenimentul stă în SQLite și poate fi "
        "interogat după ce pagina s-a închis."
    )
    doc.p(
        "Cele două vederi există peste același eveniment. Cuplul nu vede scorurile "
        "și lei. Lista lui de inimi se întoarce în studio ca listă scurtă, în "
        "limita aceluiași browser. Scenariul economic își arată ipotezele și, în "
        "capitolul 8, și mișcarea cifrei când ipotezele se schimbă. Evaluarea spune "
        "atât acordul cu generatorul, cât și comparația cu topul de scor, din care "
        "se vede rolul plafonului de scenă: 55 de scene față de 10."
    )

    doc.h2("9.2. Limite")
    doc.p(
        "Limitele nu sunt un paragraf de politețe. Ele definesc ce se poate "
        "susține. Setul are 56 de fotografii reale și 2944 de cadre derivate. "
        "Pragurile au fost stabilizate privind acest generator. Metricile de "
        "acord măsoară consistența cu etichetele, iar unul dintre cadrele bad "
        "este în album. Grupurile de persoane nu au o precizie de identitate "
        "raportată. Scenele unui dosar încărcat de utilizator sunt grupuri de "
        "câte opt fișiere, nu rafale citite din aparat. Poarta de studio nu este "
        "autentificare. Orele câștigate nu sunt un studiu de teren. Secțiunile "
        "de invitați și de detalii sunt subțiri pentru că setul este subțire acolo."
    )
    doc.p(
        "O limită de poziționare merită repetată în încheiere. Lumina nu este un "
        "argument că modelele preantrenate „rezolvă” selecția de nuntă. Este un "
        "argument că o parte tehnică a selecției se poate face cu măsuri simple "
        "și cu două modele de fețe, că rafala trebuie tratată înainte de topul "
        "de scor, și că albumul are nevoie de o regulă de diversitate pe care "
        "scorul singur nu o dă."
    )

    doc.h2("9.3. Continuări")
    doc.p(
        "Continuarea cu cel mai mare efect asupra lucrării, nu asupra interfeței, "
        "este un set notat de un fotograf. Câteva sute de cadre reale, cu trei "
        "decizii pe cadru, aplicând pragurile înghețate, ar spune dacă 0,38 și "
        "distanța 5 supraviețuiesc în afara generatorului. A doua continuare este "
        "separarea timpului de generare de timpul de triere, ca scenariul economic "
        "să poată folosi durata pură fără să supraestimeze. A treia este o scenă "
        "citită din rafala aparatului, când metadatele există, ca dosarul încărcat "
        "să nu mai fie tăiat din opt în opt."
    )
    doc.p(
        "Pe produs, pasul următor firesc este ca lista scurtă să trăiască în "
        "eveniment, nu doar în browser, dacă cele două roluri trebuie să se "
        "deschidă pe telefoane diferite. Acest pas nu schimbă pipeline-ul. El "
        "schimbă ipoteza de demonstrație. Până atunci, prototipul își ține "
        "promisiunea pe care o poate verifica oricine are codul și baza: din "
        "3000 de cadre derivate din 56 de fotografii, o procedură explicită "
        "predă 160, spune de ce au căzut celelalte și nu pretinde că fotograful "
        "a fost măsurat."
    )

    doc.h1("Bibliografie")
    refs = [
        "[1] Bradski, G. The OpenCV Library. Dr. Dobb’s Journal of Software Tools, 2000.",
        "[2] Chen, S., Liu, Y., Gao, X., Han, Z. MobileFaceNets: Efficient CNNs for Accurate Real-Time Face Verification on Mobile Devices. Chinese Conference on Biometric Recognition, LNCS 10996, Springer, 2018.",
        "[3] Cormen, T. H., Leiserson, C. E., Rivest, R. L., Stein, C. Introduction to Algorithms, ediția a 3-a. MIT Press, 2009.",
        "[4] Crete, F., Dolmiere, T., Ladret, P., Nicolas, M. The Blur Effect: Perception and Estimation with a New No-Reference Perceptual Blur Metric. Proceedings of SPIE, vol. 6492, 2007.",
        "[5] Deng, J., Guo, J., Xue, N., Zafeiriou, S. ArcFace: Additive Angular Margin Loss for Deep Face Recognition. IEEE/CVF Conference on Computer Vision and Pattern Recognition, 2019.",
        "[6] Gonzalez, R. C., Woods, R. E. Digital Image Processing, ediția a 4-a. Pearson, 2018.",
        "[7] Goodfellow, I., Bengio, Y., Courville, A. Deep Learning. MIT Press, 2016.",
        "[8] Huang, G. B., Ramesh, M., Berg, T., Learned-Miller, E. Labeled Faces in the Wild: A Database for Studying Face Recognition in Unconstrained Environments. Technical Report 07-49, University of Massachusetts, Amherst, 2007.",
        "[9] Krawetz, N. Looks Like It. The Hacker Factor Blog, 2011. Notă tehnică despre difference hash. Disponibilă la https://hackerfactor.com/blog/index.php?/archives/529-Looks-Like-It.html (accesată la 6 octombrie 2026).",
        "[10] Pech-Pacheco, J. L., Cristóbal, G., Chamorro-Martínez, J., Fernández-Valdivia, J. Diatom autofocusing in brightfield microscopy: a comparative study. Proceedings of the 15th International Conference on Pattern Recognition, vol. 3, 2000.",
        "[11] Schroff, F., Kalenichenko, D., Philbin, J. FaceNet: A Unified Embedding for Face Recognition and Clustering. IEEE Conference on Computer Vision and Pattern Recognition, 2015.",
        "[12] Szeliski, R. Computer Vision: Algorithms and Applications, ediția a 2-a. Springer, 2022.",
        "[13] Viola, P., Jones, M. Rapid Object Detection using a Boosted Cascade of Simple Features. IEEE Conference on Computer Vision and Pattern Recognition, 2001.",
        "[14] Wu, W., Peng, H., Yu, S. YuNet: A Tiny Millisecond-level Face Detector. Machine Intelligence Research, vol. 20, nr. 5, pp. 656–665, 2023.",
        "[15] Yang, S., Luo, P., Loy, C. C., Tang, X. WIDER FACE: A Face Detection Benchmark. IEEE Conference on Computer Vision and Pattern Recognition, 2016.",
        "[16] Zauner, C. Implementation and Benchmarking of Perceptual Image Hash Functions. Lucrare de master, Upper Austria University of Applied Sciences, Hagenberg, 2010.",
        "[17] Zhong, Y., Deng, W., Hu, J., Zhao, D., Li, X., Wen, D. SFace: Sigmoid-Constrained Hypersphere Loss for Robust Face Recognition. IEEE Transactions on Image Processing, vol. 30, pp. 2587–2598, 2021.",
        "[18] OpenCV Zoo. Modelele face_detection_yunet și face_recognition_sface. https://github.com/opencv/opencv_zoo (accesat la 6 octombrie 2026).",
        "[19] Aftershoot. Prezentarea produsului de selecție pentru fotografi. https://aftershoot.com (accesat la 6 octombrie 2026).",
        "[20] Imagen. Prezentarea produsului de postproducție pentru fotografi. https://imagen-ai.com (accesat la 6 octombrie 2026).",
        "[21] Hipp, D. R. SQLite. https://sqlite.org (accesat la 6 octombrie 2026).",
        "[22] Ramírez, S. FastAPI documentation. https://fastapi.tiangolo.com (accesat la 6 octombrie 2026).",
        "[23] Unsplash License. https://unsplash.com/license (accesat la 6 octombrie 2026).",
        "[24] Wikimedia Commons. https://commons.wikimedia.org (accesat la 6 octombrie 2026).",
    ]
    for ref in refs:
        doc.bib(ref)

    doc.h1("Anexa A. Pragurile de operare")
    doc.p(
        "Valorile de mai jos sunt cele din codul prototipului la momentul rulării "
        "stocate. Ele nu sunt prezentate ca optim pe un set ținut deoparte."
    )
    doc.table(
        ["Constantă", "Valoare", "Rol"],
        [
            ["Claritate minimă la triere", "0,38", "Sub prag, motivul Soft"],
            ["Expunere minimă la triere", "0,50", "Sub prag, motivul Poor exposure"],
            ["Pondere claritate în Q", "0,72", "Restul, 0,28, este expunerea"],
            ["Constanta de scară a laplacianului", "90", "S = v / (v + 90)"],
            ["Distanța Hamming maximă", "5", "Doar în interiorul scenei"],
            ["Prag de similaritate SFace", "0,45", "Produs scalar după normalizare"],
            ["Prag histogramă de rezervă", "0,93", "Doar dacă SFace lipsește"],
            ["Încredere YuNet", "0,68", "Căsuțe sub prag nu se întorc"],
            ["Căsuță minimă", "24 px", "Fețe mai mici se ignoră"],
            ["Fețe păstrate pe cadru", "8", "După filtrul de dimensiune"],
            ["Latura mare la detecție", "720 px", "Imaginea de lucru"],
            ["Persoană minimă", "2 fotografii", "Grupurile de o fotografie se aruncă"],
            ["Lungime album", "160", "Plafon dur"],
            ["Plafon de scenă", "2, apoi 3", "La umplere, apoi la completare"],
            ["Claritate minimă la sursă", "0,42", "Filtrul de descărcare, mai sever"],
            ["Expunere minimă la sursă", "0,48", "Filtrul de descărcare"],
            ["Față minimă la sursă", "48 px", "Altfel sursa se respinge"],
            ["Cadre țintă", "3000", "56 de surse în rularea stocată"],
            ["Sămânța generatorului", "7", "Zgomotul duplicatelor"],
        ],
    )

    doc.h1("Anexa B. Tabelele bazei")
    doc.p(
        "Baza data/lumina.db conține patru tabele. Evenimentul ține sumarul. "
        "Fotografia ține decizia. Persoana și fața țin gruparea. Nu sunt declarate "
        "chei străine în schema efectivă dincolo de pragma pornită la conectare; "
        "legăturile sunt convenții de identificator păstrate de codul de scriere."
    )
    doc.table(
        ["Tabel", "Ce păstrează"],
        [
            ["events", "Nume, fel (demo sau upload), data, numărul de cadre, durata, sumarul JSON"],
            ["photos", "Cale, scenă, rol de generator, scoruri, starea, motivul, duplicatul, secțiunea, ordinea"],
            ["people", "Etichetă, număr de fotografii, calea copertii"],
            ["faces", "Căsuța, fotografia și persoana"],
        ],
    )
    doc.p(
        "Indecșii sunt pe eveniment și stare pentru fotografii, pe eveniment pentru "
        "fețe și pe eveniment pentru persoane. Jurnalul este WAL. O interogare "
        "tipică de reconstrucție a tabelului 7.1 grupează fotografiile după stare. "
        "Tabelul 7.3 grupează după rol și stare. Ștergerea fișierului de bază nu "
        "șterge cadrele de pe disc; ștergerea întregului dosar data/ obligă la o "
        "rulare nouă, cu descărcare de surse și de modele."
    )

    doc.h1("Anexa C. Rularea prototipului")
    doc.p(
        "Mediul folosit la dezvoltare este Python 3.12, pe Windows, într-un mediu "
        "virtual în rădăcina proiectului. Pașii sunt:"
    )
    doc.code(
        "py -3.12 -m venv .venv\n"
        ".\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt\n"
        ".\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8741"
    )
    doc.p(
        "Pagina se deschide la http://127.0.0.1:8741 . Prima vedere este a cuplului. "
        "Codul de demonstrație pentru studio este lumina. Dacă evenimentul de "
        "demonstrație este deja în bază, albumul apare fără o nouă prelucrare. "
        "Butonul de rulare reface lucrarea. Prima rulare fără dosarul data/ "
        "descarcă modelele și sursele și durează mai mult decât o reluare."
    )
    doc.p(
        "Dosarul proiectului este organizat astfel. app/config.py ține căile și "
        "limitele 3000 și 160. app/dataset.py construiește sursele și ședința. "
        "app/pipeline.py măsoară, unește rafalele, grupează fețele și compune "
        "albumul. app/economics.py ține ipotezele. app/db.py ține schema. "
        "app/service.py leagă lucrarea de bază. app/main.py expune HTTP. "
        "static/ este pagina. data/ nu se versionează."
    )

    doc.h1("Anexa D. Pseudocodul albumului")
    doc.p(
        "Pseudocodul următor rezumă construirea albumului. El nu înlocuiește "
        "codul, dar fixează ordinea în care se aplică țelul de secțiune și "
        "plafonul de scenă."
    )
    doc.code(
        "pentru fiecare cadru păstrat:\n"
        "    secțiune = secțiune_după_numărul_de_fețe(cadru)\n"
        "sortează fiecare secțiune descrescător după scor\n"
        "pentru fiecare secțiune, în ordinea Cuplu, Portrete, Invitați, Detalii:\n"
        "    ia până la țelul secțiunii, sărind cadrele din scene deja pline (plafon 2)\n"
        "dacă albumul are mai puțin de 160:\n"
        "    completează după scor, cu plafon de scenă 3\n"
        "ordonează cadrele alese pe secțiuni și scrie starea album"
    )
    doc.p(
        "Linia de tăiere din interfață nu apare în acest pseudocod. Ea filtrează "
        "doar ce se desenează în studio și lasă rândurile de album neschimbate."
    )


def main():
    figs = make_figures()
    doc = Thesis()
    # Heading 1 would insert a break before the title page if enabled too early.
    doc.doc.styles["Heading 1"].paragraph_format.page_break_before = False
    front(doc)
    doc.doc.styles["Heading 1"].paragraph_format.page_break_before = True
    body(doc, figs)
    doc.save(OUT)
    words = 0
    for paragraph in doc.doc.paragraphs:
        words += len(paragraph.text.split())
    print(f"saved {OUT}")
    print(f"words {words}")
    print(f"paragraphs {len(doc.doc.paragraphs)}")


if __name__ == "__main__":
    main()
