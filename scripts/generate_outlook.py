"""
Global Equity Outlook Generator
Runs monthly via GitHub Actions or manually from the command line.
Calls the Anthropic API with web search enabled, then saves output
as a dated markdown file and optionally emails it.
"""

import anthropic
import os
import sys
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path


def get_month_year(override: str = None) -> tuple[str, str]:
    """Return (month_name, year_str). Override format: 'June 2026'"""
    if override:
        parts = override.strip().split()
        return parts[0], parts[1]
    now = datetime.now()
    return now.strftime("%B"), str(now.year)


def build_prompt(month: str, year: str) -> str:
    return f"""Generate a global equity outlook for the month of {month} {year} in exactly four paragraphs. \
Write in institutional asset management language. Be specific, data-driven, and avoid superficial commentary. \
Use real current macro data, earnings trends, and market conditions as of {month} {year}.

Paragraph 1: US macro backdrop — Fed policy, inflation trends, rate expectations, liquidity, and financial conditions.
Paragraph 2: Corporate earnings — revision trends, margin outlook, sector leadership, AI investment cycle implications.
Paragraph 3: International context — Europe and Asia growth trends, policy stance, geopolitical considerations, \
and relative valuation versus US equities.
Paragraph 4: US small-cap outlook — valuation, earnings recovery trajectory, rate sensitivity, and positioning dynamics.

Output only the four paragraphs, separated by blank lines. No headings, no labels, no preamble, no conclusion. \
Each paragraph must be substantive (5–8 sentences). Integrate key macro developments that have a material impact."""


def generate_outlook(month: str, year: str) -> str:
    """Call Anthropic API with web search and return the outlook text."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    print(f"Generating equity outlook for {month} {year}...")

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": build_prompt(month, year)}],
    )

    # Extract all text blocks (web search may produce intermediate tool blocks)
    text_parts = [block.text for block in response.content if block.type == "text"]
    return "\n\n".join(text_parts).strip()


def save_markdown(text: str, month: str, year: str, output_dir: Path) -> Path:
    """Save outlook as a dated markdown file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{year}-{datetime.strptime(month, '%B').strftime('%m')}-equity-outlook.md"
    filepath = output_dir / filename

    header = f"# Global Equity Outlook — {month} {year}\n\n"
    meta = f"_Generated {datetime.now().strftime('%B %d, %Y')}_\n\n---\n\n"
    disclaimer = (
        "\n\n---\n_For informational purposes only. Not investment advice. "
        "Generated using real-time web research synthesized by AI._\n"
    )

    filepath.write_text(header + meta + text + disclaimer, encoding="utf-8")
    print(f"Saved: {filepath}")
    return filepath


def send_email(text: str, month: str, year: str):
    """Send outlook via email using SMTP. Requires env vars to be set."""
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT") or "587")
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    recipient = os.environ.get("OUTLOOK_RECIPIENT", smtp_user)

    if not smtp_user or not smtp_pass:
        print("SMTP credentials not set — skipping email.")
        return

    subject = f"Global Equity Outlook — {month} {year}"

    # Plain text body
    body = f"Global Equity Outlook — {month} {year}\n"
    body += f"Generated {datetime.now().strftime('%B %d, %Y')}\n"
    body += "-" * 60 + "\n\n"
    body += text
    body += "\n\n" + "-" * 60
    body += "\nFor informational purposes only. Not investment advice.\n"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = recipient
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, recipient, msg.as_string())

    print(f"Email sent to {recipient}")


def main():
    # Allow manual override: python generate_outlook.py "June 2026"
    override = sys.argv[1] if len(sys.argv) > 1 else None
    month, year = get_month_year(override)

    outlook_text = generate_outlook(month, year)

    # Save to output directory (relative to repo root when run from Actions)
    output_dir = Path(__file__).parent.parent / "output"
    save_markdown(outlook_text, month, year, output_dir)

    # Print to stdout (captured by GitHub Actions log)
    print("\n" + "=" * 60)
    print(f"EQUITY OUTLOOK — {month.upper()} {year}")
    print("=" * 60)
    print(outlook_text)

    # Email if configured
    send_email(outlook_text, month, year)


if __name__ == "__main__":
    main()
