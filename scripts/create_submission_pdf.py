"""Generate the Wolters Kluwer assessment submission PDF."""

# ruff: noqa: E501

import os

from fpdf import FPDF
from fpdf.enums import XPos, YPos

OUT = os.path.join(os.path.dirname(__file__), "..", "submission.pdf")

BRAND = (30, 30, 40)  # near-black text
ACCENT = (255, 107, 53)  # Tagle orange
BLUE = (41, 98, 255)  # link blue
LIGHT = (245, 245, 250)  # section bg
BORDER = (220, 220, 230)  # divider
GREEN = (34, 139, 34)  # status ok
WHITE = (255, 255, 255)
MUTED = (100, 100, 115)


class PDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*MUTED)
        self.cell(
            0,
            8,
            "Observability Watchdog - Wolters Kluwer Assessment Submission",
            align="L",
        )
        self.set_draw_color(*BORDER)
        self.line(10, 16, 200, 16)
        self.ln(6)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")

    def section_box(self, title: str, number: str):
        self.set_fill_color(*LIGHT)
        self.set_draw_color(*BORDER)
        self.rect(10, self.get_y(), 190, 9, style="FD")
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*ACCENT)
        self.cell(12, 9, number, align="C")
        self.set_text_color(*BRAND)
        self.cell(178, 9, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(3)

    def kv(self, key: str, val: str, link: str = ""):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*MUTED)
        self.cell(45, 7, key)
        self.set_font("Helvetica", "", 10)
        if link:
            self.set_text_color(*BLUE)
            self.cell(0, 7, val, link=link, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            self.set_text_color(*BRAND)
            self.cell(0, 7, val, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def hr(self):
        self.set_draw_color(*BORDER)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)


def build():
    pdf = PDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()

    # ── Cover ─────────────────────────────────────────────────────────────
    pdf.set_fill_color(*BRAND)
    pdf.rect(0, 0, 210, 60, style="F")

    pdf.set_y(14)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*WHITE)
    pdf.cell(
        0, 10, "Observability Watchdog", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT
    )

    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(190, 200, 220)
    pdf.cell(
        0,
        7,
        "Wolters Kluwer Engineering Assessment - Final Submission",
        align="C",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(150, 165, 185)
    pdf.cell(
        0,
        6,
        "Candidate: Kuldeep Singh Chouhan   |   May 2026",
        align="C",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    pdf.set_y(68)
    pdf.set_text_color(*BRAND)

    # ── Checklist overview ────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*BRAND)
    pdf.cell(0, 9, "Final Submission Checklist", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(*ACCENT)
    pdf.line(10, pdf.get_y(), 80, pdf.get_y())
    pdf.ln(5)

    items = [
        ("[x]", 'Tagle.ai "Tag" output summary', "Page 2"),
        ("[x]", "Public GitHub Repository (source code)", "Page 3"),
        ("[x]", "prompts.md - full AI instruction audit log", "Page 3"),
        ("[x]", "AI-generated Architecture Deck (ARCHITECTURE.md)", "Page 4"),
    ]
    for tick, label, loc in items:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*GREEN)
        pdf.cell(8, 8, tick)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(*BRAND)
        pdf.cell(155, 8, label)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 8, loc, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(6)
    pdf.hr()

    # ── Project summary ───────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*BRAND)
    pdf.cell(0, 7, "Project Summary", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 75)
    pdf.multi_cell(
        0,
        6,
        "Observability Watchdog is a Python-based, API-first service that ingests "
        "structured application logs, detects error spikes using Z-score statistical "
        "analysis, enriches every anomaly with a Claude AI incident narrative "
        "(claude-sonnet-4-6), fires simulated webhook alerts, and visualises health "
        "trends in a live minimal Streamlit dashboard. Built end-to-end using "
        "AI-assisted Vibe Coding on a fully async Python stack.",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*MUTED)
    pdf.cell(
        0,
        6,
        "Stack: FastAPI . PostgreSQL (Neon.tech) . asyncpg . SQLAlchemy async . "
        "Alembic . Claude API . Streamlit . uv . slowapi . pytest",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*MUTED)
    pdf.cell(
        0,
        6,
        "Tests: 148 passing  |  Coverage: 88%  |  Branch: feat/minimal-dashboard-redesign",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    # ── PAGE 2: Tagle.ai ──────────────────────────────────────────────────
    pdf.add_page()
    pdf.section_box("Tagle.ai - AI Readiness Profile (Kuldeep Singh Chouhan)", "1")

    # Profile type card
    pdf.set_fill_color(255, 248, 240)
    pdf.set_draw_color(*ACCENT)
    pdf.set_line_width(0.6)
    pdf.rect(10, pdf.get_y(), 190, 42, style="FD")
    pdf.set_line_width(0.2)

    y0 = pdf.get_y() + 4
    pdf.set_y(y0)
    pdf.set_x(18)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 5, "YOUR AI READINESS TYPE", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(18)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*BRAND)
    pdf.cell(0, 10, "The Architect", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(18)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(*MUTED)
    pdf.cell(
        0, 6, "with a Catalyst edge  .  Developing", new_x=XPos.LMARGIN, new_y=YPos.NEXT
    )
    pdf.set_x(18)
    pdf.set_font("Helvetica", "I", 11)
    pdf.set_text_color(60, 60, 75)
    pdf.cell(
        0,
        7,
        '"You master what others skim - depth is your edge"',
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(6)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 75)
    pdf.multi_cell(
        0,
        6,
        "Architects go deep while others scan the headlines. You're the one who actually "
        "reads the model card, runs the benchmark, and understands why one prompting pattern "
        "outperforms another by three percent. Your risk is waiting until you're 'ready'; "
        "your edge is that when you ship, it holds.",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(5)

    # Journey position
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 6, "WHERE YOU ARE ON THE JOURNEY", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*BRAND)
    pdf.cell(0, 7, "Confident Operator", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*MUTED)
    pdf.cell(
        0, 6, "Developing mindset . High skills", new_x=XPos.LMARGIN, new_y=YPos.NEXT
    )
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 75)
    pdf.multi_cell(
        0,
        6,
        "Next focus: You're genuinely fluent; let's add depth - prompt patterns, "
        "evaluation habits, or a tool you've been avoiding.",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(5)

    # Dimensions
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*BRAND)
    pdf.cell(0, 7, "Your Dimensions", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    dims = [
        ("Growth Mindset", 65, (34, 139, 34)),
        ("Autonomy", 60, (41, 98, 255)),
        ("Competence", 65, (200, 130, 30)),
        ("Relatedness", 60, (180, 50, 180)),
        ("Innovation Readiness", 55, (160, 60, 60)),
    ]
    bar_x, bar_y = 55, pdf.get_y()
    for name, score, color in dims:
        pdf.set_y(bar_y)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*BRAND)
        pdf.cell(50, 7, name)
        # bar track
        pdf.set_fill_color(220, 220, 230)
        pdf.rect(bar_x, bar_y + 1.5, 110, 4, style="F")
        # filled portion
        pdf.set_fill_color(*color)
        pdf.rect(bar_x, bar_y + 1.5, 110 * score / 100, 4, style="F")
        # score label
        pdf.set_x(bar_x + 115)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*color)
        pdf.cell(15, 7, str(score), align="R")
        bar_y += 8

    pdf.set_y(bar_y + 4)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*MUTED)
    pdf.cell(
        0,
        6,
        "Source: Tagle.ai personal assessment - tagle.ai . TAG. LEARN. EVOLVE.",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    # ── PAGE 3: Repository Links ──────────────────────────────────────────
    pdf.add_page()
    pdf.section_box("Public GitHub Repository", "2")

    REPO = "https://github.com/kool7/observability-watchdog"
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 75)
    pdf.multi_cell(
        0,
        6,
        "All source code, configuration, tests, and documentation are in the public "
        "GitHub repository below. The repo includes the full git history of the Vibe Coding "
        "session with incremental commits per task.",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(3)
    pdf.kv("Repository", REPO, link=REPO)
    pdf.kv("Branch", "main (protected - all PRs merged via review)")
    pdf.kv("Tests", "148 passing  .  88% coverage")
    pdf.kv("Stack", "FastAPI . PostgreSQL . Claude AI . Streamlit . uv")
    pdf.ln(4)
    pdf.hr()

    pdf.section_box("prompts.md - Full AI Instruction Audit Log", "3")

    PROMPTS_URL = "https://github.com/kool7/observability-watchdog/blob/main/prompts.md"
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 75)
    pdf.multi_cell(
        0,
        6,
        "The prompts.md file contains the verbatim architect prompt issued at every turn "
        "of the Vibe Coding session - from Turn 1 (project kick-off) through the final "
        "dashboard polish. It demonstrates the full AI-assisted development loop: spec -> "
        "plan -> implement -> review -> iterate.",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(3)
    pdf.kv("File (public)", PROMPTS_URL, link=PROMPTS_URL)
    pdf.kv("Turns logged", "60+ turns covering all 14 implementation tasks")
    pdf.kv("Content", "Exact architect prompts . agent decisions . iteration notes")
    pdf.ln(4)
    pdf.hr()

    # Features snapshot
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*BRAND)
    pdf.cell(0, 7, "Key Features Shipped", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    features = [
        "Log ingestion - single + batch REST endpoint with per-IP rate limiting (slowapi)",
        "Z-score anomaly detection - self-calibrating to each service's baseline",
        "Claude AI incident narratives - 2-3 sentence SRE summaries per anomaly",
        "Webhook alert pipeline - fires + persists on every threshold breach",
        "Minimal Streamlit dashboard - hero status, 24h sparkline, recent timeline",
        "Auto-refresh every 10s via streamlit-autorefresh (no JS hacks)",
        "Synthetic log generator with configurable error spike injection",
        "148 tests across routers, services, and middleware; 88% line coverage",
    ]
    for f in features:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*ACCENT)
        pdf.cell(6, 6, "->")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(60, 60, 75)
        pdf.cell(0, 6, f, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── PAGE 4: Architecture ──────────────────────────────────────────────
    pdf.add_page()
    ARCH_URL = (
        "https://github.com/kool7/observability-watchdog/blob/main/ARCHITECTURE.md"
    )
    pdf.section_box("AI-Generated Architecture Deck (ARCHITECTURE.md)", "4")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 75)
    pdf.multi_cell(
        0,
        6,
        "ARCHITECTURE.md is the AI-generated architecture walkthrough, produced during "
        "the Vibe Coding session. It covers all 11 sections below. The full document is "
        "available on GitHub:",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(2)
    pdf.kv("Architecture Deck", ARCH_URL, link=ARCH_URL)
    pdf.ln(4)

    sections = [
        ("1", "What It Is", "System purpose and five core capabilities"),
        (
            "2",
            "Problem Statement",
            "Why raw log counts are insufficient - the 'so what' layer",
        ),
        (
            "3",
            "System Architecture",
            "Mermaid flowchart: ingest -> detect -> narrate -> alert -> visualise",
        ),
        ("4", "Data Models", "log_entries . anomalies . webhook_events schemas"),
        (
            "5",
            "Log Ingestion Pipeline",
            "Rate limiter -> Pydantic -> persist -> background anomaly check",
        ),
        (
            "6",
            "Anomaly Detection",
            "Z-score algorithm, stdev floor, severity bands LOW/MEDIUM/HIGH/CRITICAL",
        ),
        (
            "7",
            "Claude AI Integration",
            "AsyncAnthropic client, SRE persona prompt, test isolation via AsyncMock",
        ),
        (
            "8",
            "Webhook Pipeline",
            "fire_webhook -> httpx -> /webhook/receive sink -> WebhookEvent row",
        ),
        (
            "9",
            "Streamlit Dashboard",
            "Minimal single-page: hero -> sparkline -> recent timeline -> footer",
        ),
        (
            "10",
            "Key Technical Decisions",
            "DB choice, async driver, uv, Claude model, Z-score rationale",
        ),
        (
            "11",
            "Gaps & Roadmap",
            "Auth, Docker, cloud deploy, OpenTelemetry, real webhook targets",
        ),
    ]
    for num, title, desc in sections:
        pdf.set_fill_color(*LIGHT)
        pdf.set_draw_color(*BORDER)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*ACCENT)
        pdf.cell(8, 7, num, align="C")
        pdf.set_text_color(*BRAND)
        pdf.cell(55, 7, title)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(80, 80, 95)
        pdf.cell(0, 7, desc, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(*BORDER)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())

    pdf.ln(6)

    # Architecture flow summary
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*BRAND)
    pdf.cell(0, 7, "Data Flow Summary", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    pdf.set_fill_color(245, 245, 250)
    pdf.set_font("Courier", "", 9)
    pdf.set_text_color(50, 50, 65)
    flow = (
        "Application logs\n"
        "   -> POST /logs/ingest  (rate-limited, Pydantic validated)\n"
        "        -> log_service  ->  INSERT log_entries\n"
        "              -> anomaly_service (Z-score, 5-min rolling window)\n"
        "                    [z > threshold]  ->  claude_service  ->  ai_narrative\n"
        "                    [severity breach]  ->  webhook_service  ->  POST WEBHOOK_URL\n"
        "\n"
        "PostgreSQL (Neon.tech)\n"
        "   -> GET /health/trends  ->  Streamlit sparkline\n"
        "   -> GET /anomalies      ->  Streamlit hero + recent timeline\n"
        "   -> GET /webhook/events ->  available via API\n"
    )
    pdf.multi_cell(
        0, 5, flow, new_x=XPos.LMARGIN, new_y=YPos.NEXT, border=1, fill=True, padding=4
    )

    pdf.output(OUT)
    print(f"PDF written -> {OUT}")


if __name__ == "__main__":
    build()
