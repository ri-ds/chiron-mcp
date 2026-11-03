"""Build askpatch/Ask-add-on-guide.pdf, the guide for the person who looks after a Chiron
deployment (reportlab):

    python3 askpatch/guide/make_guide.py askpatch/Ask-add-on-guide.pdf askpatch/guide/ask-tab.jpg
"""
import sys
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (Image, KeepTogether, ListFlowable, ListItem, PageBreak,
                                Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table,
                                TableStyle)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon

OUT = sys.argv[1]
SHOT = sys.argv[2]

TEAL = colors.HexColor("#0f6b6b")
INK = colors.HexColor("#1f2933")
MUTED = colors.HexColor("#5f6b76")
RULE = colors.HexColor("#d9dee3")
CODEBG = colors.HexColor("#f3f5f7")
HEADBG = colors.HexColor("#e6f0f0")

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
CAP = ParagraphStyle("cap", parent=BODY, fontName="Helvetica-Oblique", fontSize=8.8,
                     leading=12, textColor=MUTED, spaceBefore=4, spaceAfter=10)
CODE = ParagraphStyle("code", parent=BODY, fontName="Courier", fontSize=8.4, leading=10.8,
                      textColor=INK, spaceAfter=0)


def P(text, style=BODY):
    return Paragraph(text, style)


def code(text):
    pre = Preformatted(text.strip("\n"), CODE)
    t = Table([[pre]], colWidths=[6.7 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODEBG),
        ("BOX", (0, 0), (-1, -1), 0.5, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return [t, Spacer(1, 8)]


def bullets(items, style=BODY):
    return ListFlowable([ListItem(P(i, style), leftIndent=12) for i in items],
                        bulletType="bullet", start="•", leftIndent=14, bulletFontSize=9,
                        spaceAfter=6)


def numbered(items, style=BODY):
    return ListFlowable([ListItem(P(i, style), leftIndent=14) for i in items],
                        bulletType="1", leftIndent=16, bulletFontSize=9.5, spaceAfter=6)


def table(rows, widths, header=True):
    data = []
    for r_i, row in enumerate(rows):
        data.append([P(c, CELLB if (header and r_i == 0) else CELL) for c in row])
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), HEADBG))
    t.setStyle(TableStyle(style))
    return [t, Spacer(1, 10)]


# --- the architecture figure ------------------------------------------------------

def arrow(d, x1, y1, x2, y2, color=INK, width=0.9):
    d.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=width))
    # arrow head at (x2, y2)
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    L = 6
    p1 = (x2 - L * math.cos(ang - 0.45), y2 - L * math.sin(ang - 0.45))
    p2 = (x2 - L * math.cos(ang + 0.45), y2 - L * math.sin(ang + 0.45))
    d.add(Polygon([x2, y2, p1[0], p1[1], p2[0], p2[1]], fillColor=color, strokeColor=color,
                  strokeWidth=0.5))


def box(d, x, y, w, h, lines, added=False, fill=None):
    d.add(Rect(x, y, w, h, rx=4, ry=4, fillColor=fill or colors.white,
               strokeColor=TEAL if added else colors.HexColor("#8a97a3"),
               strokeWidth=1.6 if added else 0.9))
    n = len(lines)
    for i, (text, bold) in enumerate(lines):
        fs = 8.6 if i == 0 else 7.4
        ty = y + h / 2 + (n - 1) * 5.4 - i * 10.8 - 3
        d.add(String(x + w / 2, ty, text, fontName="Helvetica-Bold" if bold else "Helvetica",
                     fontSize=fs, textAnchor="middle",
                     fillColor=TEAL if (added and i == 0) else INK))


def label(d, x, y, text, anchor="middle", bg=False):
    if bg:
        from reportlab.pdfbase.pdfmetrics import stringWidth
        w = stringWidth(text, "Helvetica", 6.8) + 6
        x0 = x - w / 2 if anchor == "middle" else (x - 3 if anchor == "start" else x - w + 3)
        d.add(Rect(x0, y - 2.4, w, 10, fillColor=colors.white, strokeColor=None))
    d.add(String(x, y, text, fontName="Helvetica", fontSize=6.8, textAnchor=anchor, fillColor=MUTED))


def figure():
    d = Drawing(482, 330)
    # browser
    box(d, 131, 286, 220, 36, [("The person's browser", True),
                               ("Chiron's UI, with the Ask tab (an iframe of /ask)", False)])
    # web server
    box(d, 101, 214, 280, 40, [("The web server already in front of Chiron", True),
                               ("Caddy, nginx or Apache; one added route: /ask", False)])
    arrow(d, 241, 286, 241, 254)
    label(d, 247, 268, "https://chiron.example.org  (one address, one login cookie)", anchor="start")
    # chiron and ask
    box(d, 14, 118, 196, 58, [("Chiron (Django)", True), ("as it was: not changed", False),
                              ("its code, settings, databases", False)])
    box(d, 262, 104, 206, 72, [("The Ask container", True),
                               ("the Ask server", False),
                               ("a copy of your Chiron code + its tools", False),
                               ("the Claude Code CLI (Chiron tools only)", False)], added=True,
        fill=colors.HexColor("#f2fbfb"))
    arrow(d, 170, 214, 112, 176)
    label(d, 118, 198, "/api  /accounts  /admin  /static", anchor="start")
    arrow(d, 330, 214, 365, 176)
    label(d, 352, 198, "/ask  (served on the same address)", anchor="start")
    # databases and the model
    box(d, 14, 22, 128, 46, [("Chiron metadata", True), ("Postgres: dictionary,", False),
                             ("users, sessions, reports", False)])
    box(d, 162, 22, 128, 46, [("The warehouse", True), ("Postgres: the records", False),
                              ("(SQLAlchemy)", False)])
    box(d, 326, 22, 142, 46, [("The model", True), ("a Claude account, or", False),
                              ("Amazon Bedrock", False)], added=True,
        fill=colors.HexColor("#f2fbfb"))
    arrow(d, 70, 118, 70, 68)
    arrow(d, 150, 118, 210, 68)
    arrow(d, 300, 104, 100, 68)
    label(d, 178, 80, "who is logged in; the dictionary; saved reports", bg=True)
    arrow(d, 340, 104, 240, 68)
    label(d, 318, 95, "the cohort queries, as that person", bg=True)
    arrow(d, 400, 104, 400, 68)
    label(d, 406, 88, "the question, the", anchor="start")
    label(d, 406, 80, "variable names and", anchor="start")
    label(d, 406, 72, "the figures returned", anchor="start")
    # legend
    d.add(Rect(14, 300, 10, 10, fillColor=colors.HexColor("#f2fbfb"), strokeColor=TEAL, strokeWidth=1.6))
    label(d, 29, 303, "added by the add-on", anchor="start")
    d.add(Rect(14, 286, 10, 10, fillColor=colors.white, strokeColor=colors.HexColor("#8a97a3"), strokeWidth=0.9))
    label(d, 29, 289, "already there, unchanged", anchor="start")
    return d


# --- page furniture ------------------------------------------------------------------

def on_page(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(0.9 * inch, 0.72 * inch, letter[0] - 0.9 * inch, 0.72 * inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(0.9 * inch, 0.52 * inch, "Ask for Chiron: the add-on guide")
    canvas.drawRightString(letter[0] - 0.9 * inch, 0.52 * inch, f"page {doc.page}")
    canvas.restoreState()


doc = SimpleDocTemplate(OUT, pagesize=letter, leftMargin=0.9 * inch, rightMargin=0.9 * inch,
                        topMargin=0.85 * inch, bottomMargin=0.95 * inch,
                        title="Ask for Chiron: the add-on guide", author="chiron-mcp",
                        subject="How the Ask add-on works and how to add it to a Chiron you run")
s = []

# --- title -----------------------------------------------------------------------------
s.append(P("Ask for Chiron: the add-on guide", TITLE))
s.append(P("How it works, how to add it to a Chiron you already run, and how to take it out again. "
           "Written for the person who looks after a Chiron deployment.", SUB))
s.append(P("chiron-mcp, <font face='Courier'>askpatch/</font>, 2 November 2026", SMALL))
s.append(Spacer(1, 10))

# --- 1 what it is ----------------------------------------------------------------------
s.append(P("1. What Ask is", H1))
s.append(P("Ask is a tab in Chiron's interface where a person types a question in plain words, such as "
           "<i>How many patients have type 2 diabetes and were started on metformin within 90 days of the "
           "diagnosis?</i>, and gets an answer with Chiron's own figures. Follow-up questions keep the "
           "earlier patients in mind, answers can be broken down and charted, and one button loads the "
           "exact filters behind an answer into Chiron's query builder, where the person carries on as usual."))
s.append(P("It is an <b>add-on</b>. Ask is a separate service that a deployment adds beside its Chiron when "
           "it wants it, and removes the same way. Chiron's code, settings and databases are not modified. "
           "Three things are added: one container, one route in the web server that already serves "
           "Chiron, and one switch in the interface build. Take the three away and Chiron is as it was."))
s.append(P("Two rules hold for every answer. <b>Every number comes from a Chiron query</b> made as the "
           "person who asked, with their own Chiron permissions: the model never estimates. And "
           "<b>the model can only call Chiron</b>: it runs with no shell, no file access and no web "
           "access, only the Chiron query tools, so nobody can talk it into anything else."))

# --- 2 how it works ----------------------------------------------------------------------
s.append(KeepTogether([
    P("2. How it works", H1),
    figure(),
    P("Figure 1. The pieces, and what travels between them. The teal pieces are what the add-on adds; "
      "the grey ones are the deployment's, unchanged.", CAP),
]))

s.append(P("The pieces", H2))
s += table([
    ["Piece", "What it does", "Added by the add-on?"],
    ["Chiron", "The Django application, its two Postgres databases, and the web server in front of it: "
               "all as before.", "No"],
    ["The /ask route", "One snippet in that web server sends everything under /ask to the Ask container. "
                       "Ask is then on Chiron's own address, which is what lets the browser send it the "
                       "Chiron login.", "Yes, one snippet (Caddy, nginx or Apache)"],
    ["The Ask container", "The Ask server; a copy of your Chiron's code, built from your checkout, so its "
                          "processors and dependencies are yours; chiron-mcp's Chiron tools; and the "
                          "Claude Code command-line client that runs each question.", "Yes, one container"],
    ["The Ask tab", "A page in the interface that embeds Ask for the dataset being viewed. It is built in "
                    "only when the build is told where Ask is (VITE_ASK_URL); otherwise the interface is "
                    "exactly as before.", "Yes, one build switch"],
    ["The model", "Claude, through a Claude account the container is logged in to, or through Amazon "
                  "Bedrock in your AWS account. Which models the page offers is a line in the "
                  "configuration.", "Configuration"],
], [1.15 * inch, 3.9 * inch, 1.65 * inch])

s.append(P("What happens when someone asks", H2))
s.append(numbered([
    "The person is logged into Chiron and opens the Ask tab of a dataset. The tab shows the Ask page, "
    "served at <font face='Courier'>/ask</font> on Chiron's own address, so the browser sends Chiron's "
    "login cookie along with it, as it does for every Chiron page.",
    "Ask looks the cookie up in Chiron's own session records and learns who is asking. No login, no "
    "answer: there is no service account to fall back to.",
    "Ask starts a run of the model for that question, as that person. The model gets the dataset's "
    "variables and the Chiron tools, nothing else. The person's Chiron access level (aggregate, "
    "de-identified or identified) applies, capped by a ceiling in the configuration, de-identified "
    "by default.",
    "The tools build the cohort with Chiron's own query engine and count it against the warehouse. "
    "Each figure in the answer is the result of such a call. A follow-up reuses the patients behind "
    "the earlier answer.",
    "The answer streams back to the page as it is written. Under it: <b>Query · N</b> (the filters "
    "behind the answer, recounted as the person before the button appears; one click puts them in "
    "the query builder), <b>Report</b> or <b>Results</b> when the answer saved or changed one, and "
    "<b>Traces</b>, which shows what happened: each tool call, how long it took and which model answered.",
]))
s.append(P("What leaves the machine", H2))
s.append(P("The question, the names of the dataset's variables, and the figures and rows the tools return "
           "go to the model's provider: Anthropic for a Claude account, or your own AWS account for "
           "Bedrock. With synthetic data that is fine; with real data, check your rules and set the "
           "ceiling accordingly. Everything else, the databases included, stays where it is."))
s.append(P("Two things the design needs", H2))
s.append(bullets([
    "<b>Ask must be on Chiron's address.</b> A browser sends a login cookie only to the host that set it. "
    "A Chiron whose interface is served from another host name than its API cannot carry the login to "
    "Ask; the route is not optional.",
    "<b>Chiron's metadata must be in Postgres</b> for the container. A container and the host cannot share "
    "SQLite's file locks safely, and reads then fail at random. A deployment that keeps its metadata in a "
    "SQLite file runs Ask on the host instead (section 7).",
]))
s.append(P("Two fixes Chiron needs, carried inside Ask", H2))
s.append(P("Ask relies on two corrections to Chiron 6.5.4: a mutable default argument in the cohort "
           "entry builder, and the relative-date rule (\"within 90 days of\") reading event dates that a "
           "dataset keeps in lookup tables. Your Chiron will not have them until they are merged upstream, "
           "so Ask applies both inside its own process when it starts and finds them missing, and says so "
           "in its log. Chiron's files are not written to, and Chiron's own query builder keeps its "
           "behaviour. A deployment that wants the query builder fixed too applies "
           "<font face='Courier'>askpatch/chiron-fixes.patch</font> to its checkout."))

# --- 3 before you start --------------------------------------------------------------
s.append(P("3. Before you start", H1))
s.append(bullets([
    "Chiron 6.5 on Postgres, with its metadata in Postgres as well.",
    "On the machine that will run Ask: the Chiron source checkout, the Django project (the directory "
    "with <font face='Courier'>manage.py</font>, its settings module and custom processors), and the two "
    "databases reachable from a container there.",
    "A web server in front of Chiron that can take one more route: Caddy, nginx or Apache.",
    "Docker with Compose 2.17 or newer.",
    "A model: a Claude account (Pro or Max) to log the container in to, or Bedrock with the model ids "
    "allowed for the machine's role or an AWS profile.",
    "For the Ask tab: the way this deployment builds its interface (the React UI with npm), or the "
    "built-in Django pages.",
]))

# --- 4 install -------------------------------------------------------------------------
s.append(P("4. Adding it, step by step", H1))
s.append(P("4.1 Get the code and describe your Chiron", H2))
s += code("""
git clone https://github.com/ri-ds/chiron-mcp.git
cd chiron-mcp/askpatch
cp env.example .env && chmod 600 .env
""")
s.append(P("Fill in <font face='Courier'>.env</font>. It stays on this machine (git ignores it) and holds "
           "the database passwords, so keep it readable by you only."))
s += table([
    ["Line", "What to put"],
    ["CHIRON_SRC", "The Chiron checkout: the directory holding <font face='Courier'>chiron/</font> and "
                   "<font face='Courier'>requirements/</font>. The image is built from it."],
    ["CHIRON_PROJECT_DIR", "The Django project directory (with manage.py). Mounted read-only into the "
                           "container. CHIRON_SETTINGS names the settings module if it is not "
                           "<font face='Courier'>project.settings</font>."],
    ["CHIRON_MCP_METADATA_DB", "The metadata database, as a <font face='Courier'>postgresql://</font> URL "
                               "<b>as the container reaches it</b>: a Postgres on this same machine is "
                               "<font face='Courier'>host.docker.internal</font>, not localhost."],
    ["CHIRON_MCP_WAREHOUSE_URL", "The warehouse, the same way: what CHIRON_SQL_ALCHEMY_CONNECTION_STRING "
                                 "says, written for the container."],
    ["PUBLIC_URL", "Where people open Chiron, with its path prefix if it has one, for example "
                   "<font face='Courier'>https://chiron.example.org</font> or "
                   "<font face='Courier'>https://example.org/chiron</font>."],
    ["ASK_BIND", "The port the web server forwards /ask to; <font face='Courier'>127.0.0.1:8900</font> "
                 "unless changed."],
    ["CHIRON_MCP_MAX_ACCESS_LEVEL", "The ceiling on what Ask may see: agg, deid (the default) or phi."],
    ["CHIRON_MCP_ASK_MODELS", "The models the page may switch between, as <font face='Courier'>id=Label</font> "
                              "pairs separated by commas. Unset: the model the client is set to, and no menu."],
    ["The model lines", "For Bedrock: CLAUDE_CODE_USE_BEDROCK=1, AWS_REGION, ANTHROPIC_MODEL, and AWS_PROFILE "
                        "when the credentials come from a profile. For a Claude account: nothing; you log "
                        "the container in once (4.5)."],
], [2.35 * inch, 4.35 * inch])
s.append(P("Everything in <font face='Courier'>.env</font> reaches the container. If your settings module "
           "reads an environment variable of its own, add that line too. Python packages your project "
           "needs beyond Chiron's requirements go in <font face='Courier'>requirements-extra.txt</font> "
           "before the build."))

s.append(P("4.2 Start the container", H2))
s += code("""
docker compose up -d --build
docker compose ps                  # "healthy" after a few seconds
docker compose logs ask            # ends with "Chiron Ask running at http://localhost:8900"
""")
s.append(P("The build installs your Chiron's requirements, copies its code in, adds chiron-mcp and the "
           "Claude Code client, and takes a few minutes the first time. The log also names the two fixes "
           "it applied (section 2), one line each, when your Chiron lacks them. The container listens on "
           "this machine only, on the port in ASK_BIND; nothing else is published."))

s.append(P("4.3 Add the route to the web server", H2))
s.append(P("Put the snippet for your server inside the site that serves Chiron, then reload it. The "
           "snippets are in <font face='Courier'>askpatch/proxy/</font>; this is what they say."))
s.append(P("<b>Caddy</b>, inside the site block, before its catch-all:", SMALL))
s += code("""
redir /ask {http.request.orig_uri.path}/ 308
handle_path /ask/* {
    reverse_proxy 127.0.0.1:8900 {
        flush_interval -1        # answers stream as events; pass each one on at once
    }
}
""")
s.append(P("<b>nginx</b>, inside the server block, before a catch-all location:", SMALL))
s += code("""
location = /ask { return 308 /ask/; }
location /ask/ {
    proxy_pass http://127.0.0.1:8900/;      # the trailing slash strips /ask
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_buffering off;                     # answers stream as events
    proxy_cache off;
    proxy_read_timeout 300s;
}
""")
s.append(P("<b>Apache httpd</b> (mod_proxy_http), in the virtual host, before any broader ProxyPass:", SMALL))
s += code("""
RedirectMatch 308 ^/ask$ /ask/
ProxyPass        /ask/ http://127.0.0.1:8900/ timeout=300 retry=0
ProxyPassReverse /ask/ http://127.0.0.1:8900/
""")
s.append(P("If Chiron is served under a path prefix, such as <font face='Courier'>/chiron</font>, the "
           "route is <font face='Courier'>/chiron/ask</font>. The streaming line matters: without it some "
           "servers hold the whole answer back and the page shows nothing until the end."))

s.append(P("4.4 Turn the tab on", H2))
s.append(P("<b>The React interface</b> (is4r-chiron-ui). The tab is a build-time switch: a build made with "
           "<font face='Courier'>VITE_ASK_URL=/ask</font> has it, a build without the variable is as "
           "before. A checkout that does not have the switch yet gets it from a patch of one file:"))
s += code("""
cd is4r-chiron-ui
git apply /path/to/chiron-mcp/askpatch/ui-ask-tab.patch     # or: patch -p1 < ...
VITE_ASK_URL=/ask npm run build                              # then deploy the build as usual
""")
s.append(P("<b>The built-in Django pages.</b> Two lines in the deployment's settings put an Ask link in "
           "Chiron's own navigation bar:"))
s += code("""
TEMPLATES[0]["DIRS"].append("/path/to/chiron-mcp/askpatch/templates")
CHIRON_EXTRA_NAVBAR_ITEMS = "askpatch/ask_navbar.html"
""")

s.append(P("4.5 Connect a model", H2))
s.append(P("<b>A Claude account.</b> Once, in a real terminal, log the container in:"))
s += code("""
docker compose exec -it ask claude
""")
s.append(P("Choose the subscription login, open the link it prints, approve it in your browser, paste the "
           "code back, then type <font face='Courier'>/exit</font>. The login is kept in the container's "
           "home volume, so this is once per machine. Every question then uses that account's limits."))
s.append(P("<b>Amazon Bedrock.</b> Set <font face='Courier'>CLAUDE_CODE_USE_BEDROCK=1</font>, "
           "<font face='Courier'>AWS_REGION</font> and <font face='Courier'>ANTHROPIC_MODEL</font> in "
           "<font face='Courier'>.env</font>. On an EC2 instance the instance role is used; its metadata "
           "hop limit must be 2, or a container cannot reach it. Elsewhere, name an AWS profile and start "
           "with the extra file that mounts your credentials read-only:"))
s += code("""
docker compose -f compose.yml -f compose.aws.yml up -d
""")
s.append(P("The role must be allowed to invoke each listed model; the first call to a model also "
           "subscribes the account to it, which needs the Marketplace actions in the policy. A model "
           "Bedrock refuses is dropped from the page's menu and the question is answered by the next one."))

s.append(P("4.6 Check it", H2))
s += code("""
python3 check.py                       # or: python3 check.py --user alice --dataset <id>
""")
s.append(P("The check goes through the same front door a browser uses. It makes a login session for the "
           "account inside the container, so no password is typed or sent, and prints one line per check:"))
s += table([
    ["Line", "What it confirms"],
    ["the Ask container answers", "The container is up and healthy on its port."],
    ["Ask answers only people logged into Chiron", "No fallback account is configured."],
    ["Chiron's login page", "The site itself answers through PUBLIC_URL."],
    ["the Ask page through the site", "The /ask route reaches the container."],
    ["a Chiron session for the user", "The container can read Chiron's metadata and the account exists."],
    ["Ask knows who is logged in", "The login cookie reaches Ask and is accepted: same address, same database."],
    ["the user can see a dataset", "The account has access to at least one dataset."],
    ["Chiron counts the dataset", "Chiron's own engine works inside the container, against the warehouse."],
    ["Ask answers a question with Chiron's count", "A real question; the figure in the answer equals Chiron's count."],
    ["answers stream through the web server", "The events arrived over the run, not all at once at the end."],
], [2.6 * inch, 4.1 * inch])
s.append(P("Every line should say PASS. Then open Chiron, log in, open a dataset, and the Ask tab is "
           "there."))
s.append(Image(SHOT, width=6.4 * inch, height=6.4 * inch * 896 / 1356))
s.append(P("Figure 2. The Ask tab in a stock Chiron interface, served through the web server's /ask route, "
           "with the model menu at the bottom right and starter questions built from the dataset's own values.", CAP))

# --- 5 using it ------------------------------------------------------------------------
s.append(P("5. For the people who use it", H1))
s.append(bullets([
    "<b>Ask in plain words.</b> Counts, combined filters, dates and timing between records, "
    "\"without\", comparisons, breakdowns by one or two variables, rankings, patient lists, saved "
    "reports, the Results tab. The starter cards show six questions the dataset can answer.",
    "<b>Follow up.</b> \"Of those, how many are women?\" refers to the patients behind the previous "
    "answer. New chat starts afresh; the sidebar keeps past conversations, per person and dataset.",
    "<b>Check the figures.</b> Query · N under an answer puts its exact filters into the query builder, "
    "where N is Chiron's count for them. Traces shows how the answer was produced.",
    "<b>Pick a model</b> in the menu by the question box when the deployment offers several; the trace "
    "names the one that answered.",
    "<b>Limits.</b> An answer takes ten to forty seconds. A conversation idle for twelve hours is closed "
    "and its transcript deleted; deleting a conversation in the sidebar deletes it at once.",
]))

# --- 6 day to day ----------------------------------------------------------------------
s.append(P("6. Day to day", H1))
s += table([
    ["Task", "How"],
    ["See the log", "<font face='Courier'>docker compose logs -f ask</font>"],
    ["Restart", "<font face='Courier'>docker compose restart ask</font>"],
    ["Change the models or the ceiling", "Edit <font face='Courier'>.env</font>, then "
                                         "<font face='Courier'>docker compose up -d</font>"],
    ["Update Ask", "<font face='Courier'>git pull</font> in chiron-mcp, then "
                   "<font face='Courier'>docker compose up -d --build</font>"],
    ["After upgrading Chiron", "Rebuild the image the same way: it carries a copy of Chiron's code."],
    ["Where its data lives", "The <font face='Courier'>ask-home</font> volume: the model login, conversation "
                             "state and traces. Nothing of Ask's is in Chiron's databases except reports "
                             "people chose to save, which are ordinary Chiron reports."],
    ["Who can use it", "Anyone who can log into Chiron, with what Chiron lets them see, under the ceiling. "
                       "There is no separate user list."],
], [2.0 * inch, 4.7 * inch])

# --- 7 host ------------------------------------------------------------------------------
s.append(P("7. Running it on the host instead", H1))
s.append(P("A deployment that keeps Chiron's metadata in a SQLite file, or that does not run Docker, runs "
           "the same Ask server in its own Python environment: install chiron-mcp's dependencies there "
           "(its <font face='Courier'>constraints.txt</font> pins what was tested; SQLAlchemy must stay "
           "below 2.1), install Node 22 with the Claude Code client "
           "(<font face='Courier'>npm install -g @anthropic-ai/claude-code</font>), and start "
           "<font face='Courier'>python -m chiron_mcp.webapp</font> under systemd with the same variables "
           "as <font face='Courier'>.env</font> (CHIRON_MCP_REQUIRE_SESSION=1, CHIRON_MCP_ALLOW_SAVE=1, "
           "CHIRON_MCP_UI_URL set to the site). The route and the tab are the same. Keep the Ask process "
           "on the machine that holds the SQLite file."))

# --- 8 removing ------------------------------------------------------------------------
s.append(P("8. Taking it out", H1))
s.append(numbered([
    "<font face='Courier'>docker compose down -v</font> in <font face='Courier'>askpatch/</font>: removes "
    "the container, its model login and its conversations.",
    "Delete the /ask snippet from the web server and reload it.",
    "Rebuild the interface without <font face='Courier'>VITE_ASK_URL</font> (or "
    "<font face='Courier'>git apply -R ui-ask-tab.patch</font>), or remove the two navbar settings lines.",
]))
s.append(P("Chiron's code, settings and databases were never changed, so there is nothing there to undo. "
           "Reports people saved through Ask remain, as any saved report would."))

# --- 9 troubleshooting -----------------------------------------------------------------
s.append(P("9. When something goes wrong", H1))
s += table([
    ["What you see", "What it means, and what to do"],
    ["<font face='Courier'>docker compose up</font> stops with \"set CHIRON_SRC in askpatch/.env\"",
     "<font face='Courier'>.env</font> is missing or incomplete. Copy env.example and fill it in."],
    ["The build fails in pip with a version conflict",
     "Your Chiron's pins differ from chiron-mcp's constraints. Put USE_CONSTRAINTS=0 in .env and rebuild."],
    ["The container keeps restarting; the log shows a KeyError or ImportError inside your settings module",
     "Your settings read a variable or import a package the container does not have. Add the variable "
     "to .env, or the package to requirements-extra.txt, and rebuild."],
    ["\"connection refused\" or \"could not translate host name\" for a database",
     "The URL is written for the host, not the container: use host.docker.internal or the database's "
     "network address, and check that Postgres accepts connections from it."],
    ["/ask on the site gives 502 or 404",
     "The route is missing or points at the wrong port, or the container is down: "
     "<font face='Courier'>docker compose ps</font>."],
    ["The Ask page says \"Log in to Chiron first\" although you are logged in",
     "The cookie is not reaching Ask: Ask is not on Chiron's address, or the metadata database in .env is "
     "not the one Chiron writes its sessions to."],
    ["\"Ask is not connected to a Claude account\"",
     "No model yet: <font face='Courier'>docker compose exec -it ask claude</font>, or the Bedrock lines."],
    ["Bedrock refuses with 403, or \"not authorized to perform the required AWS Marketplace actions\"",
     "The role lacks invoke or Marketplace rights for that model, or the instance metadata hop limit is 1."],
    ["The answer appears all at once at the end",
     "The web server buffers the stream. Add the streaming line from the snippet "
     "(proxy_buffering off; flush_interval -1)."],
    ["\"Timing between records needs an event date ... this dataset gives them none\"",
     "That table has no event date field in the data dictionary. Set it in the Django admin "
     "(the collection's event date field), and the timing questions work."],
    ["No Ask tab after the build",
     "VITE_ASK_URL was not set for the build, or the patch was not applied to that checkout."],
], [2.5 * inch, 4.2 * inch])

# --- appendix ------------------------------------------------------------------------------
s.append(P("Appendix. Everything .env can hold", H1))
s += table([
    ["Variable", "Default", "Meaning"],
    ["CHIRON_SRC", "required", "The Chiron checkout the image is built from"],
    ["CHIRON_PROJECT_DIR", "required", "The Django project, mounted read-only"],
    ["CHIRON_SETTINGS", "project.settings", "The settings module"],
    ["CHIRON_MCP_METADATA_DB", "required", "Metadata Postgres URL, as the container reaches it"],
    ["CHIRON_MCP_WAREHOUSE_URL", "required", "Warehouse Postgres URL, as the container reaches it"],
    ["PUBLIC_URL", "required", "Where people open Chiron, prefix included"],
    ["ASK_BIND", "127.0.0.1:8900", "Host address and port the web server forwards /ask to"],
    ["CHIRON_MCP_MAX_ACCESS_LEVEL", "deid", "Ceiling: agg, deid or phi"],
    ["CHIRON_MCP_ASK_MODELS", "unset", "Models offered on the page, id=Label pairs"],
    ["CHIRON_MCP_THREAD_TTL_HOURS", "12", "Idle hours before a conversation is closed and deleted"],
    ["CHIRON_MCP_TURN_SECONDS", "240", "Longest an answer may run"],
    ["CHIRON_MCP_PG_CHECK_INTERVAL", "2000", "Postgres client check interval (0 for a Postgres on macOS)"],
    ["CLAUDE_CODE_USE_BEDROCK, AWS_REGION, AWS_PROFILE, ANTHROPIC_MODEL", "unset", "Bedrock instead of a Claude account"],
    ["CLAUDE_CODE_VERSION", "2.1.283", "The Claude Code client version the image installs"],
    ["USE_CONSTRAINTS", "1", "0 lets your Chiron's own version pins win"],
    ["ASK_CHECK_USER, ASK_CHECK_DATASET", "demouser, first seen", "What check.py signs in as and asks about"],
], [2.5 * inch, 1.0 * inch, 3.2 * inch])
s.append(P("What was proven before this guide was written: the add-on installed as above against an "
           "unmodified Chiron 6.5.4 checkout with its own settings, the stock interface built with the "
           "switch, and Caddy in front with the snippet. The container started on that Chiron's settings "
           "and applied the two fixes; the check passed every line but the model step, which waits for "
           "the operator's login; the timing, safety and smoke test suites passed inside the container; "
           "and the tab and the logged-in identity showed in the browser (Figure 2). The record is in "
           "<font face='Courier'>docs/plan-askpatch.md</font> in the repository.", SMALL))

doc.build(s, onFirstPage=on_page, onLaterPages=on_page)
print("wrote", OUT)
