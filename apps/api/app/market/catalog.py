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
    "focalscope": "Kundeservicesystem",
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
    # Det tal, OK selv skal slå op internt. Radaren kender aldrig OK's tal
    # (den kører ikke i et internt miljø) — regnestykket laves i regnearket
    # på OK's egen pc.
    lookup: str = ""
    # Regnestykket i regnearket: tid = antal × minutter / 60 × timepris ×
    # effekt · timer = antal × timer × timepris × effekt · vaerdi = antal ×
    # kr. pr. stk. × effekt.
    calc: str = "tid"
    count_label: str = "Antal pr. år"
    unit_label: str = "Minutter pr. stk."


# OK's problemliste for Til OK. Startliste — tilpasses af konsulenten.
OK_PROBLEMS: tuple[OkProblem, ...] = (
    OkProblem(
        "ventetid",
        "kundeservice",
        "Lange ventetider i telefon og chat",
        "Kunder venter for længe, især i spidsbelastning.",
        lookup="Henvendelser pr. år i telefon og chat og gennemsnitlig samtaletid (FocalScope).",
        calc="tid",
        count_label="Henvendelser pr. år (telefon + chat)",
        unit_label="Minutter pr. henvendelse",
    ),
    OkProblem(
        "gentagne",
        "kundeservice",
        "Mange gentagne, simple henvendelser",
        "Samme spørgsmål om regning, aflæsning og levering fylder køen.",
        lookup=(
            "Antal simple henvendelser pr. år om regning, aflæsning og levering, "
            "og tid pr. henvendelse (FocalScope)."
        ),
        calc="tid",
        count_label="Simple henvendelser pr. år",
        unit_label="Minutter pr. henvendelse",
    ),
    OkProblem(
        "efterbehandling",
        "kundeservice",
        "Tid brugt på efterbehandling",
        "Medarbejdere bruger tid på noter og registrering efter hver samtale.",
        lookup="Antal samtaler pr. år og gennemsnitlig efterbehandling pr. samtale (FocalScope).",
        calc="tid",
        count_label="Samtaler pr. år",
        unit_label="Minutters efterbehandling pr. samtale",
    ),
    OkProblem(
        "routing",
        "kundeservice",
        "Henvendelser lander i forkert kø",
        "Overdragelser mellem køer giver længere sager og utilfredse kunder.",
        lookup=(
            "Antal henvendelser pr. år, der flyttes til en anden kø, "
            "og ekstra tid pr. overdragelse (FocalScope)."
        ),
        calc="tid",
        count_label="Overdragelser pr. år",
        unit_label="Ekstra minutter pr. overdragelse",
    ),
    OkProblem(
        "kvalitet",
        "kundeservice",
        "Manuel kvalitetssikring",
        "Kun en lille stikprøve af samtaler bliver gennemgået.",
        lookup="Antal samtaler, der gennemgås pr. år, og tid pr. gennemgang.",
        calc="tid",
        count_label="Gennemgåede samtaler pr. år",
        unit_label="Minutter pr. gennemgang",
    ),
    OkProblem(
        "viden",
        "support",
        "Medarbejdere mangler hurtig adgang til viden",
        "Svar skal findes i mange systemer og vejledninger.",
        lookup=(
            "Antal henvendelser pr. år og tid brugt på at finde svar "
            "pr. henvendelse (FocalScope, G4)."
        ),
        calc="tid",
        count_label="Henvendelser pr. år",
        unit_label="Minutter brugt på opslag pr. henvendelse",
    ),
    OkProblem(
        "selvbetjening",
        "support",
        "Kunder kan ikke selv løse tekniske problemer",
        "Fx fejl på ladestander eller app kræver en supportsag.",
        lookup="Antal supportsager pr. år om ladestander og app, og tid pr. sag.",
        calc="tid",
        count_label="Supportsager pr. år",
        unit_label="Minutter pr. sag",
    ),
    OkProblem(
        "oplaering",
        "support",
        "Lang oplæring af nye medarbejdere",
        "Det tager lang tid, før nye medarbejdere kan løse sager selv.",
        lookup="Antal nye medarbejdere pr. år og timer brugt på oplæring pr. medarbejder.",
        calc="timer",
        count_label="Nye medarbejdere pr. år",
        unit_label="Timers oplæring pr. medarbejder",
    ),
    OkProblem(
        "konvertering",
        "salg",
        "Lav konvertering i salgssamtaler",
        "For få samtaler ender i et salg.",
        lookup="Antal salg pr. år fra salgssamtaler og dækningsbidrag pr. salg.",
        calc="vaerdi",
        count_label="Salg pr. år i dag",
        unit_label="Kr. pr. salg (dækningsbidrag)",
    ),
    OkProblem(
        "mersalg",
        "salg",
        "Mersalg i kundeservicesamtaler udnyttes ikke",
        "Kundeservice taler med mange kunder, men sjældent om relevante produkter.",
        lookup="Antal mersalg pr. år i kundeservice og dækningsbidrag pr. mersalg.",
        calc="vaerdi",
        count_label="Mersalg pr. år i dag",
        unit_label="Kr. pr. mersalg (dækningsbidrag)",
    ),
    OkProblem(
        "churn",
        "salg",
        "Kunder opsiger uden varsel",
        "Opsigelser opdages først, når de er sket.",
        lookup="Antal opsigelser pr. år og dækningsbidrag pr. kunde pr. år.",
        calc="vaerdi",
        count_label="Opsigelser pr. år",
        unit_label="Kr. pr. kunde pr. år (dækningsbidrag)",
    ),
)

PROBLEMS_BY_KEY = {problem.key: problem for problem in OK_PROBLEMS}

# OK i dag — sendes med til Til OK, så forslagene passer til OK's systemer.
# Oplyst af AI-konsulenten 2026-10-14; udvides, når flere fakta kendes.
OK_PROFILE: tuple[str, ...] = (
    "Kundeservicesystem: FocalScope (henvendelser i kundeservice).",
    "Legacy-system: G4 (ældre system; integration kan være en begrænsning).",
)
# OK's nuværende leverandør: radaren følger, hvad den lancerer af AI.
OK_CURRENT_VENDORS: tuple[str, ...] = ("FocalScope",)


# Dem, der ligner OK: danske selskaber inden for OK's brancher (energi,
# brændstof og ladning, mobil). Deres cases står øverst under Sådan gør andre,
# og radaren viser også, hvem der endnu ikke har en AI-case. Kun offentlige
# kilder; listen tilpasses af konsulenten.
@dataclass(frozen=True)
class Peer:
    name: str
    group: str
    aliases: tuple[str, ...] = ()


PEERS: tuple[Peer, ...] = (
    Peer("Norlys", "Energi"),
    Peer("Andel", "Energi", ("andel energi", "seas-nve")),
    Peer("Ørsted", "Energi", ("orsted",)),
    Peer("Energi Fyn", "Energi"),
    Peer("EWII", "Energi"),
    Peer("Vattenfall", "Energi"),
    Peer("Circle K", "Brændstof og ladning"),
    Peer("Q8", "Brændstof og ladning"),
    Peer("Shell", "Brændstof og ladning"),
    Peer("Uno-X", "Brændstof og ladning"),
    Peer("Clever", "Brændstof og ladning"),
    Peer("TDC", "Mobil og internet", ("tdc net", "nuuday", "yousee")),
    Peer("Telenor", "Mobil og internet"),
    Peer("Telia", "Mobil og internet"),
    Peer("3", "Mobil og internet", ("3 danmark", "hi3g")),
)


def peer_for(company: str | None, country: str | None = "DK") -> Peer | None:
    """Selskabet er en af dem, der ligner OK, når navnet er peerens navn
    eller et alias — alene eller efterfulgt af fx "A/S" eller "Danmark" — og
    casen er fra Danmark. Shell i Storbritannien, Vattenfall i Sverige og
    Telenor i Norge er ikke "dem, der ligner OK" (stresstest 2026-10-19)."""
    if not company or (country or "").strip().upper() != "DK":
        return None
    name = " ".join(company.casefold().split())
    for peer in PEERS:
        for alias in (peer.name.casefold(), *peer.aliases):
            if name == alias or name.startswith(alias + " "):
                return peer
    return None


# Region ud fra ISO-landekode.
_NORDIC = {"SE", "NO", "FI", "IS", "FO", "GL", "AX"}
REGION_LABELS = {"danmark": "Danmark", "norden": "Norden", "verden": "Resten af verden"}


COUNTRY_NAMES = {
    "DK": "Danmark",
    "SE": "Sverige",
    "NO": "Norge",
    "FI": "Finland",
    "IS": "Island",
    "FO": "Færøerne",
    "GL": "Grønland",
    "DE": "Tyskland",
    "GB": "Storbritannien",
    "NL": "Holland",
    "FR": "Frankrig",
    "ES": "Spanien",
    "IT": "Italien",
    "IE": "Irland",
    "BE": "Belgien",
    "CH": "Schweiz",
    "AT": "Østrig",
    "PL": "Polen",
    "US": "USA",
    "CA": "Canada",
    "AU": "Australien",
    "IN": "Indien",
}


def country_name(country_code: str | None) -> str | None:
    if not country_code:
        return None
    return COUNTRY_NAMES.get(country_code.strip().upper(), country_code)


def region(country_code: str | None) -> str:
    code = (country_code or "").strip().upper()
    if code == "DK":
        return "danmark"
    if code in _NORDIC:
        return "norden"
    return "verden"
