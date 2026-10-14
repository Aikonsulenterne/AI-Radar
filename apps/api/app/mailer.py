"""Til OK som mail til direktøren, når konsulenten har godkendt forsiden.

Standard SMTP med STARTTLS (smtplib) — ingen ekstern tjeneste eller ny
afhængighed. Uden SMTP_HOST og modtagere sendes intet. Fejl i afsendelsen
stopper aldrig godkendelsen; de logges uden adgangsoplysninger.
"""

import logging
import smtplib
from email.message import EmailMessage
from html import escape
from typing import Any

from app.config import get_settings

logger = logging.getLogger("ai_radar.mail")


def mail_configured() -> bool:
    settings = get_settings()
    return bool(settings.smtp_host and settings.brief_recipient_list)


def _text(brief: dict[str, Any], link: str) -> str:
    lines = [f"Til OK · {brief.get('month_label') or ''}".strip(), ""]
    lines.append("DET SKAL DU VIDE")
    lines += [f"{p['n']}. {p['text']}" for p in brief.get("must_know", [])]
    if brief.get("recommendations"):
        lines += ["", "DET FORESLÅR VI"]
        lines += [
            f"{i}. {r['action']} ({' · '.join(x for x in (r['owner'], r['duration']) if x)})"
            for i, r in enumerate(brief["recommendations"], 1)
        ]
    if brief.get("decisions"):
        lines += ["", "DET SKAL DU TAGE STILLING TIL"]
        lines += [f"Ja / nej: {q}" for q in brief["decisions"]]
    lines += ["", "AI-sammenfattet · tjek kilden.", f"Hele overblikket: {link}" if link else ""]
    return "\n".join(lines).strip() + "\n"


def _html(brief: dict[str, Any], link: str) -> str:
    def items(values: list[str], ordered: bool = True) -> str:
        tag = "ol" if ordered else "ul"
        return f"<{tag}>" + "".join(f"<li>{v}</li>" for v in values) + f"</{tag}>"

    parts = [
        '<div style="font-family:Arial,sans-serif;color:#1A1614;max-width:640px">',
        f'<p style="color:#FF3C3C;font-size:12px;font-weight:bold;letter-spacing:.1em">'
        f"TIL OK · {escape((brief.get('month_label') or '').upper())}</p>",
        '<h1 style="font-weight:normal;font-size:24px">AI i kundecentret – det korte overblik</h1>',
        '<div style="background:#460019;color:#F7EFEB;border-radius:10px;padding:14px 18px">',
        '<h2 style="font-weight:normal;font-size:18px;margin:0 0 8px">Det skal du vide</h2>',
        items([escape(p["text"]) for p in brief.get("must_know", [])]),
        "</div>",
    ]
    if brief.get("recommendations"):
        parts += [
            '<h2 style="font-weight:normal;font-size:18px">Det foreslår vi</h2>',
            items(
                [
                    f'{escape(r["action"])}<br><span style="color:#736762;font-size:12px">'
                    f"{escape(' · '.join(x for x in (r['owner'], r['duration']) if x))}</span>"
                    for r in brief["recommendations"]
                ]
            ),
        ]
    if brief.get("decisions"):
        parts += [
            '<h2 style="font-weight:normal;font-size:18px">Det skal du tage stilling til</h2>',
            items([f"<b>Ja / nej:</b> {escape(q)}" for q in brief["decisions"]], ordered=False),
        ]
    if link:
        parts.append(
            f'<p><a href="{escape(link)}" style="color:#AA2825">Se hele overblikket →</a></p>'
        )
    parts.append('<p style="color:#998C85;font-size:11px">AI-sammenfattet · tjek kilden</p></div>')
    return "".join(parts)


def send_brief(brief: dict[str, Any]) -> str:
    """Send Til OK. Returnerer en kort status til UI'et."""
    settings = get_settings()
    recipients = settings.brief_recipient_list
    if not settings.smtp_host or not recipients:
        return "ikke sat op"
    link = settings.public_web_url.rstrip("/") + "/" if settings.public_web_url else ""
    message = EmailMessage()
    message["Subject"] = f"Til OK · {brief.get('month_label') or ''}: AI i kundecentret".strip()
    message["From"] = settings.smtp_from or settings.smtp_user
    message["To"] = ", ".join(recipients)
    message.set_content(_text(brief, link))
    message.add_alternative(_html(brief, link), subtype="html")
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        logger.error("brief_mail_failed error=%s", type(exc).__name__)
        return "fejlede"
    logger.info("brief_mail_sent recipients=%d", len(recipients))
    return f"sendt til {len(recipients)}"
