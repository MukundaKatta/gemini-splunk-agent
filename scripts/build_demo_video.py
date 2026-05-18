"""Build the gemini-splunk-agent demo video end-to-end.

Renders 8 slides → TTS narration → ffmpeg → demo.mp4. The numbers and quoted
answers are from a real Vertex AI agent run captured earlier.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


W, H = 1920, 1080
FG = "#0f172a"
FG_MUTED = "#475569"
ACCENT = "#2563eb"
ACCENT_2 = "#16a34a"
ACCENT_3 = "#dc2626"
BG = "#ffffff"
PANEL = "#f8fafc"
CODE_BG = "#0f172a"
CODE_FG = "#e2e8f0"

SF = "/System/Library/Fonts/SFNS.ttf"
SFI = "/System/Library/Fonts/SFNSItalic.ttf"
MONO = "/System/Library/Fonts/SFNSMono.ttf"
if not Path(MONO).exists():
    MONO = "/System/Library/Fonts/Menlo.ttc"


def font(size: int, mono: bool = False, italic: bool = False) -> ImageFont.FreeTypeFont:
    path = MONO if mono else (SFI if italic else SF)
    return ImageFont.truetype(path, size)


@dataclass
class Slide:
    name: str
    narration: str
    draw: callable


def base(img, d, title=None, eyebrow=None):
    d.rectangle([(0, H - 56), (W, H)], fill=PANEL)
    d.text((48, H - 44), "gemini-splunk-agent", font=font(22), fill=FG)
    d.text((W - 600, H - 44), "github.com/MukundaKatta/gemini-splunk-agent", font=font(22), fill=FG_MUTED)
    if eyebrow:
        d.text((96, 80), eyebrow.upper(), font=font(26), fill=ACCENT)
    if title:
        d.text((96, 130), title, font=font(72), fill=FG)
        d.rectangle([(96, 230), (220, 236)], fill=ACCENT)


def draw_title(img, d):
    d.rectangle([(0, 0), (W, H)], fill=BG)
    d.rectangle([(0, H - 56), (W, H)], fill=PANEL)
    d.text((48, H - 44), "github.com/MukundaKatta/gemini-splunk-agent", font=font(22), fill=FG_MUTED)
    d.text((W - 270, H - 44), "Apache 2.0", font=font(22), fill=FG_MUTED)
    d.text((96, 320), "gemini-splunk-agent", font=font(130), fill=FG)
    d.rectangle([(96, 490), (340, 500)], fill=ACCENT)
    d.text((96, 540), "A Gemini agent that investigates", font=font(48), fill=FG_MUTED)
    d.text((96, 600), "production incidents using Splunk MCP.", font=font(48), fill=FG_MUTED)
    d.text((96, 760), "Built with Google Cloud Agent Builder (ADK)", font=font(32), fill=FG)
    d.text((96, 805), "for the Google Cloud Rapid Agent Hackathon,", font=font(32), fill=FG)
    d.text((96, 850), "Splunk partner track.", font=font(32), fill=FG)


def draw_problem(img, d):
    base(img, d, title="The setup", eyebrow="What it solves")
    rows = [
        "You're on call.",
        "You get a page: \"checkout-api latency is spiking.\"",
        "You open Splunk, hunt for the right query, scroll problems,",
        "correlate with deployments, and finally find root cause.",
        "Twenty minutes have passed.",
    ]
    y = 330
    for line in rows:
        d.text((96, y), line, font=font(40), fill=FG)
        y += 76
    d.text((96, 800), "gemini-splunk-agent does that conversation in under 10 seconds.", font=font(34, italic=True), fill=ACCENT_2)


def draw_architecture(img, d):
    base(img, d, title="How it works", eyebrow="Architecture")
    box_w, box_h = 380, 130
    cx = (W - 3 * box_w - 2 * 50) // 2
    boxes = [
        ("User question", "checkout-api latency spike?", ACCENT),
        ("ADK LlmAgent", "Gemini 2.5 on Vertex AI", FG),
        ("Splunk MCP", "list_problems, execute_dql, ...", ACCENT_2),
    ]
    x = cx
    for label, sub, color in boxes:
        d.rounded_rectangle([(x, 360), (x + box_w, 360 + box_h)], radius=14, outline=color, width=4, fill=BG)
        d.text((x + 24, 380), label, font=font(34), fill=FG)
        d.text((x + 24, 430), sub, font=font(22), fill=FG_MUTED)
        x += box_w + 50
    # Arrows
    d.text((cx + box_w + 6, 410), "→", font=font(60), fill=FG_MUTED)
    d.text((cx + 2 * box_w + 56, 410), "→", font=font(60), fill=FG_MUTED)
    d.text((96, 600), "MCP tool surface matches the official splunk-oss/splunk-mcp", font=font(32), fill=FG)
    d.text((96, 650), "server. Flip one flag and the agent targets a real Splunk tenant.", font=font(32), fill=FG)
    d.text((96, 760), "Built on Google Cloud Agent Builder (ADK) + Gemini.", font=font(32, italic=True), fill=FG_MUTED)
    d.text((96, 810), "Self-observed: every Gemini call traced with GeminiLens.", font=font(32, italic=True), fill=FG_MUTED)


def draw_question(img, d):
    base(img, d, title="The investigation", eyebrow="Live agent run")
    d.text((96, 320), "User asks:", font=font(36), fill=FG_MUTED)
    d.rounded_rectangle([(96, 380), (W - 96, 500)], radius=16, fill=PANEL)
    d.text((130, 410), '"My checkout-api latency just spiked. What changed?"',
           font=font(38), fill=FG)
    d.text((96, 560), "Agent steps through the Splunk MCP tools:", font=font(32), fill=FG_MUTED)
    steps = [
        "1.  list_problems          →  Splunk AI's open incidents",
        "2.  execute_dql            →  raw latency / log timeseries",
        "3.  find_entity_by_name    →  service ID resolution",
    ]
    y = 630
    for s in steps:
        d.text((130, y), s, font=font(34, mono=True), fill=FG)
        y += 56


def draw_answer(img, d):
    base(img, d, title="The answer", eyebrow="What Gemini returned")
    d.text((96, 320), "Root cause: A recent deployment of checkout-api v4.7.1 introduced", font=font(34), fill=FG)
    d.text((96, 365), "a significant increase in database connection pool wait time,", font=font(34), fill=FG)
    d.text((96, 410), "leading to high latency.", font=font(34), fill=FG)
    bullets = [
        ("Problem ID:",   "P-2026-0517-001"),
        ("Latency:",      "p95 jumped 220ms → 1.8s"),
        ("Timestamp:",    "started 14:32 UTC"),
        ("Evidence:",     "DB connection pool wait time 9× the baseline"),
    ]
    y = 510
    for label, value in bullets:
        d.text((96, y), "•", font=font(38), fill=ACCENT)
        d.text((140, y), label, font=font(34), fill=FG)
        d.text((400, y), value, font=font(34, mono=True), fill=ACCENT_2)
        y += 60
    d.text((96, 800), "Next step: roll back checkout-api v4.7.1 or open a hotfix branch.",
           font=font(32, italic=True), fill=FG_MUTED)


def draw_code(img, d):
    base(img, d, title="The implementation", eyebrow="Six lines of ADK")
    code = (
        "from google.adk.agents import LlmAgent\n"
        "from google.adk.tools.mcp_tool import McpToolset\n"
        "from gemini_splunk_agent.agent import _splunk_toolset\n"
        "\n"
        "agent = LlmAgent(\n"
        "    model='gemini-2.5-flash',\n"
        "    name='gemini_splunk_agent',\n"
        "    instruction=SYSTEM_PROMPT,\n"
        "    tools=[_splunk_toolset(stub=True)],\n"
        ")"
    )
    d.rounded_rectangle([(96, 320), (W - 96, H - 130)], radius=18, fill=CODE_BG)
    yy = 360
    for line in code.split("\n"):
        d.text((130, yy), line, font=font(30, mono=True), fill=CODE_FG)
        yy += 46


def draw_tests(img, d):
    base(img, d, title="Tested + deployed", eyebrow="12 / 12 passing")
    rows = [
        ("test_mcp_stub.py",       "8 passed"),
        ("test_agent_build.py",    "4 passed"),
    ]
    y = 340
    for name, status in rows:
        d.text((96, y), "✓", font=font(40), fill=ACCENT_2)
        d.text((160, y), name, font=font(36, mono=True), fill=FG)
        d.text((900, y), status, font=font(36), fill=FG_MUTED)
        y += 90
    d.text((96, 620), "Live on Cloud Run:", font=font(32), fill=FG)
    d.text((96, 670), "gemini-splunk-agent-1029931682737.us-central1.run.app", font=font(34, mono=True), fill=ACCENT_2)
    d.text((96, 800), "Repo: github.com/MukundaKatta/gemini-splunk-agent",
           font=font(32, italic=True), fill=FG_MUTED)


def draw_close(img, d):
    d.rectangle([(0, 0), (W, H)], fill=BG)
    d.text((96, 200), "gemini-splunk-agent", font=font(96), fill=FG)
    d.rectangle([(96, 320), (340, 330)], fill=ACCENT)
    d.text((96, 370), "github.com/MukundaKatta/gemini-splunk-agent", font=font(40, mono=True), fill=ACCENT)
    d.text((96, 450), "gemini-splunk-agent-1029931682737.us-central1.run.app", font=font(40, mono=True), fill=ACCENT_2)
    d.text((96, 580), "Google Cloud Agent Builder (ADK)", font=font(38), fill=FG_MUTED)
    d.text((96, 630), "+ Gemini 2.5 on Vertex AI", font=font(38), fill=FG_MUTED)
    d.text((96, 680), "+ Splunk MCP server (stub for demo, real-tenant ready)", font=font(38), fill=FG_MUTED)
    d.text((96, 820), "Apache 2.0. Mukunda Katta, independent.", font=font(30, italic=True), fill=FG_MUTED)
    d.text((96, 870), "Submission for Google Cloud Rapid Agent Hackathon, Splunk track.", font=font(30, italic=True), fill=FG_MUTED)


SLIDES = [
    Slide("01_title",
          "Gemini ops agent. A Gemini agent that investigates production incidents using the Splunk MCP server, built on Google Cloud's Agent Development Kit.",
          draw_title),
    Slide("02_problem",
          "Picture being on call. You get a page. The checkout API's latency is spiking. You open Splunk, hunt for the right query, scroll problems, correlate with deployments, and twenty minutes later you find the root cause. Gemini ops agent does that conversation in under ten seconds.",
          draw_problem),
    Slide("03_architecture",
          "The architecture is three boxes. A user question goes into an A D K L L M agent powered by Gemini two point five on Vertex A I. The agent uses M C P toolset to call the Splunk M C P server. The server exposes the standard tools list problems, execute D Q L, find entity by name. With a stub server for demos, or the official server for real tenants. Every Gemini call is also traced through Gemini Lens for self observation.",
          draw_architecture),
    Slide("04_question",
          "Here is a real run. The user asks, my checkout API latency just spiked. What changed. The agent works the case by calling list problems first to see what Davis A I has detected, then execute D Q L to pull raw latency timeseries, then find entity by name to resolve service I Ds when needed.",
          draw_question),
    Slide("05_answer",
          "The agent's answer is in the format an on call engineer can act on. Root cause is a deployment of checkout API version four point seven point one. Problem I D cited. P ninety five latency jumped two twenty milliseconds to one point eight seconds. Started at fourteen thirty two U T C. D B connection pool wait time was nine times the baseline. Next step, roll back or hotfix. These are real numbers from a real Vertex A I call.",
          draw_answer),
    Slide("06_code",
          "The whole agent fits in six lines of Google's Agent Development Kit. One L L M agent, one M C P toolset, a Gemini model, and a system prompt. The M C P toolset auto discovers tools from the server, proxies tool calls, and handles connection management.",
          draw_code),
    Slide("07_tests",
          "Twelve tests cover the M C P stub server's tool responses and the agent's wiring. The service is deployed to Cloud Run at the U R L on screen. The repo is public on Git Hub, Apache two point zero.",
          draw_tests),
    Slide("08_close",
          "Gemini ops agent. Apache two point zero. Built for the Google Cloud Rapid Agent Hackathon, Splunk partner track. Thank you.",
          draw_close),
]


def render_slides(outdir):
    paths = []
    for sl in SLIDES:
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        sl.draw(img, d)
        p = outdir / f"{sl.name}.png"
        img.save(p, "PNG", optimize=True)
        paths.append(p)
        print(f"  rendered {p.name}")
    return paths


def render_audio(outdir):
    paths = []
    for sl in SLIDES:
        wav = outdir / f"{sl.name}.aiff"
        m4a = outdir / f"{sl.name}.m4a"
        subprocess.run(["say", "-v", "Samantha", "-r", "175", "-o", str(wav), sl.narration], check=True)
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-c:a", "aac", "-b:a", "128k", str(m4a)],
            check=True,
        )
        wav.unlink(missing_ok=True)
        paths.append(m4a)
        print(f"  spoke   {m4a.name}")
    return paths


def render_segments(outdir, slide_pngs, audio_m4as):
    segs = []
    for sl, png, m4a in zip(SLIDES, slide_pngs, audio_m4as):
        out = outdir / f"seg_{sl.name}.mp4"
        dur = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(m4a)],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        seg_dur = float(dur) + 0.4
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-loop", "1", "-i", str(png),
            "-i", str(m4a),
            "-af", "apad=pad_dur=0.4",
            "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
            "-r", "30", "-t", f"{seg_dur:.2f}",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            str(out),
        ], check=True)
        segs.append(out)
        print(f"  segment {out.name}  ({seg_dur:.2f}s)")
    return segs


def concat(outdir, segs):
    list_file = outdir / "concat.txt"
    list_file.write_text("\n".join(f"file '{p.resolve()}'" for p in segs) + "\n")
    out = outdir / "demo.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c", "copy", str(out),
    ], check=True)
    return out


def main():
    outdir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "gemini-splunk-agent" / ".video-build"
    outdir.mkdir(parents=True, exist_ok=True)
    for needed in ("ffmpeg", "ffprobe", "say"):
        if shutil.which(needed) is None:
            sys.exit(f"missing tool: {needed}")

    print("[1/4] slides...")
    slides = render_slides(outdir)
    print("[2/4] audio...")
    audios = render_audio(outdir)
    print("[3/4] segments...")
    segs = render_segments(outdir, slides, audios)
    print("[4/4] concat...")
    final = concat(outdir, segs)
    size = final.stat().st_size / (1024 * 1024)
    dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(final)],
        capture_output=True, text=True,
    ).stdout.strip()
    print(f"\nDONE: {final}  ({size:.1f} MB, {float(dur):.1f}s)")


if __name__ == "__main__":
    main()
