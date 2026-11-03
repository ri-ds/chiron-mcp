"""Build askpatch/Chiron-upstream-changes.pdf: the two changes chiron-mcp asks of Chiron
(the engine fixes) and of its React UI (the Ask-tab switch), written up for the Chiron
developers, with the diffs taken from the patch files beside it (reportlab):

    python3 askpatch/guide/make_upstream.py askpatch/Chiron-upstream-changes.pdf
"""
import datetime
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (KeepTogether, ListFlowable, ListItem, PageBreak, Paragraph,
                                Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle)

OUT = sys.argv[1]
HERE = Path(__file__).resolve().parent
ASKPATCH = HERE.parent

TEAL = colors.HexColor("#0f6b6b")
INK = colors.HexColor("#1f2933")
MUTED = colors.HexColor("#5f6b76")
RULE = colors.HexColor("#d9dee3")
CODEBG = colors.HexColor("#f3f5f7")
HEADBG = colors.HexColor("#e6f0f0")
ADD = colors.HexColor("#e8f5e9")
DEL = colors.HexColor("#fdecea")

ss = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=ss["Normal"], fontName="Helvetica", fontSize=10,
                      leading=14.5, textColor=INK, spaceAfter=6)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8.8, leading=12)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8.8, leading=11.5, spaceAfter=0)
CELLB = ParagraphStyle("cellb", parent=CELL, fontName="Helvetica-Bold")
TITLE = ParagraphStyle("title", parent=BODY, fontName="Helvetica-Bold", fontSize=24,
                       leading=30, textColor=TEAL, spaceAfter=4)
SUB = ParagraphStyle("sub", parent=BODY, fontSize=12.5, leading=17, textColor=MUTED, spaceAfter=18)
H1 = ParagraphStyle("h1", parent=BODY, fontName="Helvetica-Bold", fontSize=15.5, leading=20,
                    textColor=TEAL, spaceBefore=16, spaceAfter=8)
H2 = ParagraphStyle("h2", parent=BODY, fontName="Helvetica-Bold", fontSize=11.5, leading=15,
                    textColor=INK, spaceBefore=10, spaceAfter=4)
CODE = ParagraphStyle("code", parent=BODY, fontName="Courier", fontSize=7.6, leading=9.6,
                      backColor=CODEBG, borderPadding=(5, 6, 5, 6), leftIndent=4, spaceBefore=4,
                      spaceAfter=10)
DIFF = ParagraphStyle("diff", parent=CODE, fontSize=7.1, leading=8.9)


def P(text, style=BODY):
    return Paragraph(text, style)


def code(text, style=CODE, width=104):
    return Preformatted(text.strip("\n"), style, maxLineLength=width)


def bullets(items, style=BODY):
    return ListFlowable([ListItem(P(i, style), leftIndent=12) for i in items], bulletType="bullet",
                        start="•", leftIndent=14, bulletFontSize=8, spaceAfter=6)


def numbered(items, style=BODY):
    return ListFlowable([ListItem(P(i, style), leftIndent=14) for i in items], bulletType="1",
                        leftIndent=16, spaceAfter=6)


def table(rows, widths, header=True):
    data = [[P(c, CELLB if header and r == 0 else CELL) for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
             ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), HEADBG), ("LINEBELOW", (0, 0), (-1, 0), 0.8, TEAL)]
    t.setStyle(TableStyle(style))
    t.spaceAfter = 10
    return t


def diff_of(path: Path) -> str:
    """The unified diff in a patch file, from its first '--- a/' line on."""
    text = path.read_text(encoding="utf-8")
    i = text.find("\n--- a/")
    return text[i + 1:] if i >= 0 else text


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(0.9 * inch, 0.72 * inch, letter[0] - 0.9 * inch, 0.72 * inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(0.9 * inch, 0.52 * inch, "Two changes for Chiron, from chiron-mcp")
    canvas.drawRightString(letter[0] - 0.9 * inch, 0.52 * inch, f"page {doc.page}")
    canvas.restoreState()


today = datetime.date.today().strftime("%-d %B %Y")
story = []
story += [P("Two changes for Chiron", TITLE),
          P(f"What chiron-mcp, the Ask tab, asks of is4r-chiron and is4r-chiron-ui. "
            f"For the Chiron developers. {today}.", SUB)]

story += [P("In short", H1), bullets([
    "Ask (chiron-mcp) runs beside an unchanged Chiron. Two things it needs are not in Chiron "
    "yet: <b>a pair of fixes in the query engine</b> (is4r-chiron) and <b>a build-time switch "
    "for the Ask tab</b> in the React UI (is4r-chiron-ui).",
    "Both are ready as patch files in the chiron-mcp repository, "
    "<font face='Courier'>askpatch/chiron-fixes.patch</font> and "
    "<font face='Courier'>askpatch/ui-ask-tab.patch</font>, and this note carries their diffs. "
    "Nothing has been opened against the cchmc repositories; that is for whoever the team "
    "decides.",
    "Ask applies the engine fixes inside its own process at run time, so Ask already works on "
    "any Chiron 6.5.x. Chiron's <i>own</i> query builder gets the relative-date fix only once "
    "Chiron itself carries it: today a \"within N days\" relationship on a dataset whose event "
    "dates are multivalue fails in the Chiron UI.",
    "For people who do not use Ask these changes do two things: a crash becomes a working "
    "query, and a silent overwrite of a cohort entry stops. The UI change is invisible unless "
    "the build names an Ask address.",
])]

# --- 1. the engine ---------------------------------------------------------------------
story += [P("1. Chiron's query engine (is4r-chiron 6.5.4)", H1),
          P("Three files, two fixes. The diff is on the next pages; it applies to a checkout with "
            "<font face='Courier'>git apply chiron-fixes.patch</font> (or "
            "<font face='Courier'>patch -p1 &lt; chiron-fixes.patch</font>).")]

story += [P("1a. A shared default argument in CohortDefProcessor._generate_cd_entry_template", H2),
          P("<b>File.</b> <font face='Courier'>chiron/processors/abstract/cohort_def_processor.py</font>"),
          P("<b>What happens.</b> The method is declared with <font face='Courier'>additional_args={}</font>, "
            "writes <font face='Courier'>entry_id</font> and <font face='Courier'>concept_id</font> into that "
            "argument and returns it. A default argument is created once, so every cohort entry built "
            "without arguments in one process is the <i>same</i> dict: building a second filter "
            "silently rewrites the first, including its values, its exclude flag and its entry id. "
            "A web server or any long-running process that builds more than one entry sees it; a "
            "one-shot script does not, which is why it went unnoticed."),
          P("<b>The fix.</b> <font face='Courier'>additional_args=None</font>, and a fresh "
            "<font face='Courier'>dict(additional_args or {})</font> on every call. The one behaviour "
            "change: a caller's own dict is copied, not written into. chiron-mcp had worked around "
            "the bug by deep-copying around the call; the fix makes every caller safe."),
          P("<b>How it was found.</b> Two filters built in one Ask process came back as one; "
            "README, \"A Chiron bug this project found\".")]

story += [P("1b. The relative-date rule and event dates kept in lookup tables", H2),
          P("<b>Files.</b> <font face='Courier'>chiron/query_engine/postgres/sql_alchemy_queries/"
            "longitudinal_combos.py</font> and <font face='Courier'>.../sections/where_builder.py</font>"),
          P("<b>What happens.</b> <font face='Courier'>LongitudinalCombo.generate_sql_alchemy_clauses_for_event"
            "</font> reads each event date with <font face='Courier'>getattr(table.c, concept.permanent_id)</font>, "
            "the column a single-value concept has on its collection table. When a collection's event "
            "date field is a <i>multivalue</i> concept, its values live in a lookup table "
            "(<font face='Courier'>lkp_…</font>) and the collection table has no such column, so the "
            "query builder fails with <font face='Courier'>AttributeError: &lt;date concept&gt;</font> as soon "
            "as a cohort relates two collections in time (\"within 90 days after\"). Datasets loaded "
            "with every concept multivalue are common: the Synthea bundles are, and so is the "
            "synthea-10k on the genoquery instance that John set up as longitudinal. The failure is "
            "in the engine, so it is the same in Chiron's own query builder."),
          P("<b>The fix.</b> A new method <font face='Courier'>WhereStatementBuilder.get_event_date_column"
            "(oConcept, table, subquery_type, subquery_id)</font> returns the column that holds an "
            "event date concept for a table:"),
          bullets([
              "a single-value concept: the collection table's column, exactly as before;",
              "a multivalue concept inside a subquery: the lookup alias the alias manager registered "
              "for that subquery and concept, joined the way the filters' own lookups are;",
              "a multivalue concept on a table with no subquery of its own (the outer table of a "
              "one-sided combo): a correlated <font face='Courier'>select … limit 1</font> of that "
              "record's value from the lookup table.",
          ], SMALL),
          P("<font face='Courier'>generate_sql_alchemy_clauses_for_event</font> takes an optional "
            "<font face='Courier'>column_for(index, table, oConcept)</font> resolver and the where "
            "builder passes this method; without the argument the method behaves as it did, so no "
            "other caller changes. The <font face='Courier'>limit 1</font> matters only if a multivalue "
            "date concept held several values for one record; an event date holds one."),
          P("<b>Verified.</b> Eight timed cohorts on synthea-10k (metformin within 90 days after a "
            "type 2 diabetes record, an ER visit within 30 days before an asthma record, two records "
            "of one table, either side, from the other record's end date, a follow-up narrowing the "
            "timed group, an \"any of\" with a timed condition) count exactly what raw SQL on the "
            "warehouse counts (<font face='Courier'>tests/within_live.py</font>), on a Mac and on the "
            "genoquery instance on 3 November 2026 (179 and 89 for the first two, on the live site). "
            "The offline test <font face='Courier'>tests/chiron_patches.py</font> covers both fixes "
            "without a database. Through Ask, 21 timing questions on the 100,000-patient benchmark "
            "set were all answered correctly by Haiku 5.5.")]

story += [P("The diff", H2), code(diff_of(ASKPATCH / "chiron-fixes.patch"), DIFF, 110)]

story += [P("What chiron-mcp does meanwhile", H2),
          P("<font face='Courier'>chiron_mcp/chiron_patches.py</font> looks at the host's code right "
            "after Django starts and, only where a fix is missing, replaces the method in memory of "
            "the Ask process: the first by the default argument's type, the second by whether the "
            "where builder has <font face='Courier'>get_event_date_column</font>. Nothing on disk is "
            "written and Chiron's own web app is untouched. A Chiron that carries the fixes is left "
            "alone, so once they are merged the run-time patch stands down by itself.")]

# --- 2. the UI --------------------------------------------------------------------------
story += [PageBreak(), P("2. The React UI (is4r-chiron-ui)", H1),
          P("One file, <font face='Courier'>src/overrideConfig.tsx</font>, about ten lines."),
          P("<b>Today.</b> The develop branch already has the Ask tab: a route "
            "<font face='Courier'>ask</font> under the dataset and an <b>Ask</b> entry in the header, "
            "with the Ask server's address fixed in the source as "
            "<font face='Courier'>http://localhost:8900</font>. Every build shows the tab, and it only "
            "works on a developer's machine with the server on that port."),
          P("<b>The change.</b> The address comes from the build: "
            "<font face='Courier'>VITE_ASK_URL</font>. Unset, the route and the tab are not added and "
            "the UI is as it was. <font face='Courier'>/ask</font> means the site's web server serves "
            "Ask on the UI's own address, which is what lets Ask read the Chiron login cookie; a full "
            "URL is for development. A trailing slash is trimmed."),
          P("<b>Verified.</b> On 3 November 2026 the stock UI built without the variable showed no "
            "Ask tab (header: Dataset Home, Query, Results, Reports, Aggregate) and, rebuilt with "
            "<font face='Courier'>VITE_ASK_URL=/ask</font>, showed it, in a browser against a stock "
            "Chiron 6.5.4. The chiron-mcp deploy bundle builds its UI with "
            "<font face='Courier'>VITE_ASK_URL=${BASE_PATH}/ask</font>."),
          P("The diff", H2), code(diff_of(ASKPATCH / "ui-ask-tab.patch"), DIFF, 110),
          P("Apply with <font face='Courier'>git apply ui-ask-tab.patch</font> in an is4r-chiron-ui "
            "checkout, then <font face='Courier'>VITE_ASK_URL=/ask npm run build</font>, or export it "
            "before <font face='Courier'>npm run dev</font>.", SMALL)]

# --- 3. after merging --------------------------------------------------------------------
story += [KeepTogether([P("3. After merging", H1), table([
    ["", "Now", "Once merged"],
    ["Chiron's own query builder", "A timed relationship on a multivalue-date dataset fails.",
     "Works, on every Chiron that upgrades."],
    ["Ask on a deployment's Chiron", "Works; the run-time patch supplies the fixes.",
     "Works; the run-time patch finds nothing to do."],
    ["The Ask tab in the UI", "Apply ui-ask-tab.patch, then build with VITE_ASK_URL.",
     "Build with VITE_ASK_URL; no patch."],
    ["A Chiron or UI upgrade", "A patch may stop applying and needs a look.", "Nothing to do."],
], [1.7 * inch, 2.45 * inch, 2.45 * inch])])]

story += [KeepTogether([P("Where everything is", H2), table([
    ["What", "Path in github.com/ri-ds/chiron-mcp"],
    ["The engine patch, with this explanation at its top", "askpatch/chiron-fixes.patch"],
    ["The UI patch", "askpatch/ui-ask-tab.patch"],
    ["The run-time version of the engine fixes", "chiron_mcp/chiron_patches.py"],
    ["The fixed sources, as chiron-mcp ships them", "vendor/is4r-chiron/… and vendor/is4r-chiron-ui/src/overrideConfig.tsx"],
    ["Tests", "tests/chiron_patches.py (offline), tests/within_live.py (against a warehouse), tests/within_clause.py"],
    ["The Ask add-on that depends on them", "askpatch/README.md"],
], [2.6 * inch, 4.0 * inch])])]

doc = SimpleDocTemplate(OUT, pagesize=letter, leftMargin=0.9 * inch, rightMargin=0.9 * inch,
                        topMargin=0.85 * inch, bottomMargin=0.95 * inch,
                        title="Two changes for Chiron, from chiron-mcp", author="chiron-mcp")
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print(OUT)
