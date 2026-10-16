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


def _gain_text(gain: dict[str, Any] | None) -> str:
    if not gain:
        return ""
    kpi = f" ({gain['kpi']})" if gain.get("kpi") else ""
    cases = "1 case" if gain["cases"] == 1 else f"{gain['cases']} cases"
    vendor = " · leverandørens tal" if gain.get("vendor_only") else ""
    return f"Andre fik: {gain['text']}{kpi} · {cases}{vendor}"


def _since_lines(brief: dict[str, Any]) -> list[str]:
    since = brief.get("since_last") or {}
    lines = [line["text"] for line in since.get("lines", [])]
    return lines or ([since["note"]] if since.get("note") else [])


def _text(brief: dict[str, Any], link: str) -> str:
    """Kan læses på 30 sekunder: sætningen, siden sidst og spørgsmålene."""
    lines = [f"Til OK · {brief.get('month_label') or ''}".strip(), ""]
    if brief.get("headline"):
        lines += [brief["headline"]["text"], ""]
    lines.append("SIDEN SIDST")
    lines += [f"- {line}" for line in _since_lines(brief)]
    if brief.get("decisions"):
        lines += ["", "DET SKAL DU TAGE STILLING TIL"]
        for d in brief["decisions"]:
            lines.append(f"Ja / nej: {d['question']}")
            meta = " · ".join(x for x in (d.get("owner"), d.get("duration")) if x)
            if meta:
                lines.append(f"  Kræver: {meta}")
            if d.get("gain"):
                lines.append(f"  {_gain_text(d['gain'])}")
            if link:
                lines.append(f"  Svar her: {link}#beslutninger")
    if brief.get("recommendations"):
        lines += ["", "DET FORESLÅR VI"]
        lines += [f"{i}. {r['action']}" for i, r in enumerate(brief["recommendations"], 1)]
    lines += ["", "Alle tal har en kilde på siden.", f"Hele overblikket: {link}" if link else ""]
    return "\n".join(lines).strip() + "\n"


def _html(brief: dict[str, Any], link: str) -> str:
    muted = "color:#736762;font-size:12px"
    h2 = 'style="font-weight:normal;font-size:18px;margin:20px 0 8px"'
    parts = [
        '<div style="font-family:Arial,sans-serif;color:#1A1614;max-width:600px">',
        f'<p style="color:#FF3C3C;font-size:12px;font-weight:bold;letter-spacing:.1em">'
        f"TIL OK · {escape((brief.get('month_label') or '').upper())}</p>",
    ]
    if brief.get("headline"):
        parts.append(
            '<div style="background:#460019;color:#F7EFEB;border-radius:10px;padding:16px 18px">'
            f'<p style="font-size:20px;line-height:1.35;margin:0">'
            f"{escape(brief['headline']['text'])}</p></div>"
        )
    parts.append(f"<h2 {h2}>Siden sidst</h2><ul>")
    parts += [f"<li>{escape(line)}</li>" for line in _since_lines(brief)]
    parts.append("</ul>")
    if brief.get("decisions"):
        parts.append(f"<h2 {h2}>Det skal du tage stilling til</h2>")
        for d in brief["decisions"]:
            meta = " · ".join(x for x in (d.get("owner"), d.get("duration")) if x)
            parts.append(
                '<div style="border:1px solid #E5D9D3;border-radius:10px;padding:12px 14px;'
                'margin:0 0 10px">'
                f'<p style="margin:0 0 6px"><b>Ja / nej:</b> {escape(d["question"])}</p>'
            )
            if meta:
                parts.append(f'<p style="{muted};margin:0">Kræver: {escape(meta)}</p>')
            if d.get("gain"):
                parts.append(f'<p style="{muted};margin:0">{escape(_gain_text(d["gain"]))}</p>')
            if link:
                parts.append(
                    f'<p style="margin:10px 0 0"><a href="{escape(link)}#beslutninger" '
                    'style="background:#460019;color:#FFFFFF;text-decoration:none;'
                    'padding:8px 14px;border-radius:8px;display:inline-block">'
                    "Svar i radaren →</a></p>"
                )
            parts.append("</div>")
    if brief.get("recommendations"):
        parts.append(f"<h2 {h2}>Det foreslår vi</h2><ol>")
        parts += [f"<li>{escape(r['action'])}</li>" for r in brief["recommendations"]]
        parts.append("</ol>")
    if link:
        parts.append(
            f'<p><a href="{escape(link)}" style="color:#AA2825">Se hele overblikket →</a></p>'
        )
    parts.append(f'<p style="{muted}">Alle tal har en kilde på siden.</p></div>')
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
