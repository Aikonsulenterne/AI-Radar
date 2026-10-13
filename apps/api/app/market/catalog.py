"""Kurateret katalog: teknologier, OK's problemliste og regioner.

Kataloget er kuratering, ikke fakta: det giver AI'en faste navne at bruge
og direktøren en dansk forklaring pr. teknologi. Hvad leverandører sælger,
og hvem der bruger det, kommer altid fra kilderne (market_items).
"""

from dataclasses import dataclass

AREAS = ("salg", "kundeservice", "support")
AREA_LABELS = {"salg": "Salg", "kundeservice": "Kundeservice", "support": "Support"}


@dataclass(frozen=True)
class CatalogTechnology:
    # Kanonisk navn = technologies.name (eksisterende rækker genbruges).
    name: str
    label: str
    areas: tuple[str, ...]
    what: str
    value: str
    aliases: tuple[str, ...] = ()


TECH_CATALOG: tuple[CatalogTechnology, ...] = (
    CatalogTechnology(
        "Virtual Agent",
        "Chatbot / virtuel agent",
        ("kundeservice", "support"),
        "Besvarer og løser kundens henvendelse selv i chat, mail eller app — døgnet rundt.",
        "Færre simple henvendelser til medarbejderne og kortere ventetid for kunden.",
        ("chatbot", "virtual assistant", "ai agent for customers", "conversational ai"),
    ),
    CatalogTechnology(
        "Voice AI",
        "Stemmeagenter og voicebots",
        ("kundeservice", "support"),
        "Tager telefonen, forstår hvad kunden siger, og løser eller viderestiller opkaldet.",
        "Aflaster telefonkøen, især i spidsbelastning, og sorterer opkald før en medarbejder.",
        ("voicebot", "voice bot", "voice agent", "speech recognition", "ivr"),
    ),
    CatalogTechnology(
        "Agent Assist",
        "Agent Assist",
        ("kundeservice", "salg", "support"),
        "Foreslår svar, slår viden op og viser næste skridt, mens medarbejderen taler med kunden.",
        "Kortere samtaler, mere ensartede svar og hurtigere oplæring af nye medarbejdere.",
        ("copilot", "co-pilot", "agent copilot", "suggested replies"),
    ),
    CatalogTechnology(
        "Call Summarization",
        "Samtaleopsummering",
        ("kundeservice", "support", "salg"),
        "Skriver referat og registrerer sagen automatisk, når samtalen er slut.",
        "Mindre tid på efterbehandling — typisk det første sted, kundecentre henter tid.",
        ("summarization", "after-call work", "call summary", "auto notes", "samtaleopsummering"),
    ),
    CatalogTechnology(
        "Intelligent Routing",
        "Automatisk kategorisering af henvendelser",
        ("kundeservice", "support"),
        "Læser henvendelsen, finder emnet og sender den til den rigtige kø eller medarbejder.",
        "Færre overdragelser og hurtigere løsning ved første kontakt.",
        ("routing", "classification", "ticket triage", "intent detection", "auto-tagging"),
    ),
    CatalogTechnology(
        "Knowledge AI",
        "Videnssøgning til medarbejdere",
        ("kundeservice", "support"),
        "Finder det rigtige svar i interne vejledninger og systemer på sekunder.",
        "Mindre tid på at lede efter svar og færre forkerte svar til kunden.",
        ("knowledge base", "enterprise search", "knowledge search"),
    ),
    CatalogTechnology(
        "Automated QA",
        "Kvalitetssikring af samtaler",
        ("kundeservice", "salg", "support"),
        "Gennemgår alle samtaler i stedet for stikprøver og markerer dem, der kræver opfølgning.",
        "Bedre kvalitet og målrettet coaching uden manuel aflytning.",
        ("quality assurance", "qa", "quality management"),
    ),
    CatalogTechnology(
        "Conversation Intelligence",
        "Samtaleanalyse",
        ("salg", "kundeservice"),
        "Analyserer samtaler for årsager, stemning og hvad der virker i salg.",
        "Viser hvorfor kunder ringer, og hvad de bedste sælgere gør anderledes.",
        (
            "speech analytics",
            "conversation analytics",
            "sentiment analysis",
            "interaction analytics",
        ),
    ),
    CatalogTechnology(
        "Sales Assistant",
        "AI-salgsassistent",
        ("salg",),
        "Hjælper sælgeren med forberedelse, opfølgning og tilbud — fx udkast til mails og noter.",
        "Mere tid til kunderne og hurtigere opfølgning på leads.",
        ("sales copilot", "ai sdr", "sales agent"),
    ),
    CatalogTechnology(
        "Next Best Offer",
        "Mersalg i kundesamtaler (next best offer)",
        ("salg", "kundeservice"),
        "Foreslår det mest relevante produkt eller tilbud til netop denne kunde under samtalen.",
        "Øget mersalg fra de samtaler, kundeservice allerede har.",
        ("next best action", "cross-sell", "upsell", "recommendation engine"),
    ),
    CatalogTechnology(
        "Lead Scoring",
        "Prioritering af leads",
        ("salg",),
        "Vurderer, hvilke leads og kunder der mest sandsynligt køber, så de ringes op først.",
        "Højere konvertering for samme indsats.",
        ("lead qualification", "predictive lead scoring"),
    ),
    CatalogTechnology(
        "Churn Prediction",
        "Forudsigelse af opsigelser og fastholdelse",
        ("salg", "kundeservice"),
        "Finder kunder, der er tæt på at opsige, så de kan kontaktes i tide.",
        "Færre opsigelser og mere målrettet fastholdelse.",
        ("churn", "retention", "customer retention", "attrition prediction"),
    ),
    CatalogTechnology(
        "Self-service Troubleshooting",
        "Selvbetjent fejlsøgning",
        ("support",),
        "Guider kunden trin for trin til selv at løse et teknisk problem, fx med en lader.",
        "Færre supportsager og hurtigere hjælp uden for åbningstid.",
        ("guided troubleshooting", "self-service", "self service"),
    ),
    CatalogTechnology(
        "Workflow Automation",
        "Automatisering af sagsbehandling",
        ("support", "kundeservice"),
        "Udfører rutineopgaver i systemerne automatisk, fx adresseændring eller kreditering.",
        "Kortere behandlingstid og færre manuelle fejl.",
        ("rpa", "process automation", "case automation"),
    ),
    CatalogTechnology(
        "Agentic AI",
        "AI-agenter, der løser hele henvendelsen",
        ("kundeservice", "support", "salg"),
        "AI, der selv gennemfører en opgave fra start til slut på tværs af systemer — under opsyn.",
        "Kan løse hele henvendelser uden medarbejder; kræver styr på data og kontrol.",
        ("ai agents", "autonomous agents", "agentic"),
    ),
)

CATALOG_BY_NAME = {entry.name: entry for entry in TECH_CATALOG}

# "Det kan betyde for OK" — kurateret analyse pr. teknologi (vises stiplet).
FOR_OK: dict[str, str] = {
    "Virtual Agent": "Kan tage simple spørgsmål om regning, aflæsning og levering i chat og app.",
    "Voice AI": "Kan aflaste telefonen, OK's dyreste kanal, især i spidsbelastning.",
    "Agent Assist": "Kan give nye medarbejdere de rigtige svar under samtalen.",
    "Call Summarization": "Ofte den hurtigste gevinst: mindre tid på noter efter samtalen.",
    "Intelligent Routing": "Kan sende mails og beskeder direkte til det rette team første gang.",
    "Knowledge AI": "Kan samle svarene fra OK's mange vejledninger ét sted.",
    "Automated QA": "Kan erstatte stikprøver med gennemgang af alle samtaler.",
    "Conversation Intelligence": "Kan vise, hvorfor kunderne ringer, og hvad der virker i salg.",
    "Sales Assistant": "Kan give sælgerne mere tid til kunderne og hurtigere opfølgning.",
    "Next Best Offer": "Kan gøre kundeservicesamtaler til salg af relevante produkter.",
    "Lead Scoring": "Kan vise, hvilke leads salg skal ringe til først.",
    "Churn Prediction": "Kan finde kunder, der er ved at opsige, mens der stadig er tid.",
    "Self-service Troubleshooting": "Kan hjælpe kunder med fx ladestandere uden en supportsag.",
    "Workflow Automation": "Kan klare rutineændringer som flytning uden manuel sagsbehandling.",
    "Agentic AI": "Det nyeste i markedet; kræver styr på data og menneskelig kontrol.",
}

# Leverandørtyper til tabellen "Leverandører på markedet". Ukendte står
# som "Ikke oplyst" — typen gættes aldrig.
VENDOR_TYPES: dict[str, str] = {
    "microsoft": "Platform",
    "salesforce": "Platform",
    "google": "Platform",
    "amazon": "Platform",
    "aws": "Platform",
    "oracle": "Platform",
    "sap": "Platform",
    "ibm": "Platform",
    "openai": "Platform",
    "genesys": "Kundecenterplatform",
    "nice": "Kundecenterplatform",
    "puzzel": "Kundecenterplatform",
    "five9": "Kundecenterplatform",
    "talkdesk": "Kundecenterplatform",
    "avaya": "Kundecenterplatform",
    "twilio": "Kundecenterplatform",
    "telavox": "Kundecenterplatform",
    "zendesk": "Kundeservicesystem",
    "freshworks": "Kundeservicesystem",
    "intercom": "Kundeservicesystem",
    "dixa": "Kundeservicesystem",
    "servicenow": "Kundeservicesystem",
    "hubspot": "Kundeservicesystem",
    "boost.ai": "Specialist",
    "polyai": "Specialist",
    "parloa": "Specialist",
    "sierra": "Specialist",
    "decagon": "Specialist",
    "capturi": "Specialist",
    "ultimate": "Specialist",
    "cognigy": "Specialist",
    "kore.ai": "Specialist",
    "observe.ai": "Specialist",
    "gong": "Specialist",
}


@dataclass(frozen=True)
class OkProblem:
    key: str
    area: str
    name: str
    description: str


# OK's problemliste for Til OK. Startliste — tilpasses af konsulenten.
OK_PROBLEMS: tuple[OkProblem, ...] = (
    OkProblem(
        "ventetid",
        "kundeservice",
        "Lange ventetider i telefon og chat",
        "Kunder venter for længe, især i spidsbelastning.",
    ),
    OkProblem(
        "gentagne",
        "kundeservice",
        "Mange gentagne, simple henvendelser",
        "Samme spørgsmål om regning, aflæsning og levering fylder køen.",
    ),
    OkProblem(
        "efterbehandling",
        "kundeservice",
        "Tid brugt på efterbehandling",
        "Medarbejdere bruger tid på noter og registrering efter hver samtale.",
    ),
    OkProblem(
        "routing",
        "kundeservice",
        "Henvendelser lander i forkert kø",
        "Overdragelser mellem køer giver længere sager og utilfredse kunder.",
    ),
    OkProblem(
        "kvalitet",
        "kundeservice",
        "Manuel kvalitetssikring",
        "Kun en lille stikprøve af samtaler bliver gennemgået.",
    ),
    OkProblem(
        "viden",
        "support",
        "Medarbejdere mangler hurtig adgang til viden",
        "Svar skal findes i mange systemer og vejledninger.",
    ),
    OkProblem(
        "selvbetjening",
        "support",
        "Kunder kan ikke selv løse tekniske problemer",
        "Fx fejl på ladestander eller app kræver en supportsag.",
    ),
    OkProblem(
        "oplaering",
        "support",
        "Lang oplæring af nye medarbejdere",
        "Det tager lang tid, før nye medarbejdere kan løse sager selv.",
    ),
    OkProblem(
        "konvertering",
        "salg",
        "Lav konvertering i salgssamtaler",
        "For få samtaler ender i et salg.",
    ),
    OkProblem(
        "mersalg",
        "salg",
        "Mersalg i kundeservicesamtaler udnyttes ikke",
        "Kundeservice taler med mange kunder, men sjældent om relevante produkter.",
    ),
    OkProblem(
        "churn",
        "salg",
        "Kunder opsiger uden varsel",
        "Opsigelser opdages først, når de er sket.",
    ),
)

PROBLEMS_BY_KEY = {problem.key: problem for problem in OK_PROBLEMS}

# Region ud fra ISO-landekode.
_NORDIC = {"SE", "NO", "FI", "IS", "FO", "GL", "AX"}
REGION_LABELS = {"danmark": "Danmark", "norden": "Norden", "verden": "Resten af verden"}


def region(country_code: str | None) -> str:
    code = (country_code or "").strip().upper()
    if code == "DK":
        return "danmark"
    if code in _NORDIC:
        return "norden"
    return "verden"
