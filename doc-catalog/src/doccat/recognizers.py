"""Custom Presidio recognizers tuned to THIS corpus (US immigration + personal).

Presidio already ships US_SSN, CREDIT_CARD (Luhn), US_PASSPORT, US_DRIVER_LICENSE,
US_BANK_NUMBER, PHONE_NUMBER, EMAIL_ADDRESS and DATE_TIME. These add the
document-specific identifiers those miss. Patterns are inferred from the documents
actually present (I-20/DS-2019, I-797/I-140/I-765, I-94, W-2, insurance cards,
itineraries). Each is gated with `context` words so a bare number doesn't fire —
Presidio boosts the score when a context word sits nearby and keeps recall high
without drowning the shelf in false positives.

Confidence notes:
  - high  (~0.85): structurally unique formats (USCIS receipt = fixed 3-letter
                   service-center prefix + 10 digits) — safe to surface.
  - medium(~0.5 ): distinctive but not unique (SEVIS 'N'+digits, A-number).
  - low   (~0.2 ): generic digit runs that ONLY mean something with a context word
                   (I-94, PNR, insurance member id) — context boost does the work.

The presidio import is lazy (inside custom_recognizers) so the field-worker can
import the label/mask constants below without Presidio installed — only the
Presidio pod needs the library.
"""


def custom_recognizers():
    from presidio_analyzer import Pattern, PatternRecognizer
    return [
        # SEVIS ID — I-20 / DS-2019. 'N' followed by 10 digits (often zero-padded,
        # e.g. N0012345678). Printed as "SEVIS ID No. N00XXXXXXXX".
        PatternRecognizer(
            supported_entity="SEVIS_ID",
            patterns=[Pattern("sevis", r"\bN0*\d{7,10}\b", 0.5)],
            context=["sevis", "i-20", "i20", "ds-2019", "ds2019", "sevis id"],
        ),

        # USCIS receipt number — I-797 / I-140 / I-129 / I-765 / I-485. Three-letter
        # service-center prefix + 10 digits. Structurally unique -> high confidence.
        PatternRecognizer(
            supported_entity="USCIS_RECEIPT",
            patterns=[Pattern(
                "uscis_receipt",
                r"\b(?:IOE|EAC|WAC|LIN|SRC|MSC|YSC|NBC|NSC|VSC|CSC|TSC)\d{10}\b",
                0.85)],
            context=["receipt", "receipt number", "notice", "uscis", "i-797",
                     "i-140", "i-129", "i-765", "petition", "case"],
        ),

        # Alien Registration Number (A-Number / USCIS#). 'A' + 8 or 9 digits.
        PatternRecognizer(
            supported_entity="ALIEN_NUMBER",
            patterns=[Pattern("a_number", r"\bA[-\s]?\d{8,9}\b", 0.55)],
            context=["a-number", "a number", "alien", "registration", "uscis#",
                     "a#", "uscis number"],
        ),

        # I-94 arrival/departure admission record number — 11 digits. Meaningless
        # without context (many 11-digit runs exist), so leaned entirely on context.
        PatternRecognizer(
            supported_entity="I94_NUMBER",
            patterns=[Pattern("i94", r"\b\d{11}\b", 0.25)],
            context=["i-94", "i94", "admission", "admission number", "arrival",
                     "departure record"],
        ),

        # Employer Identification Number (EIN) on W-2 / paystubs: NN-NNNNNNN.
        PatternRecognizer(
            supported_entity="EIN",
            patterns=[Pattern("ein", r"\b\d{2}-\d{7}\b", 0.4)],
            context=["ein", "employer id", "employer identification",
                     "federal id", "e.i.n"],
        ),

        # Travel PNR / record locator — 6 alphanumerics. Extremely common shape,
        # so context ("PNR", "booking reference") is what makes it a hit.
        PatternRecognizer(
            supported_entity="TRAVEL_PNR",
            patterns=[Pattern("pnr", r"\b[A-Z0-9]{6}\b", 0.15)],
            context=["pnr", "record locator", "booking reference", "confirmation",
                     "reservation", "airline", "ticket"],
        ),

        # Health-insurance member / policy id — issuer formats vary wildly
        # (optional letter prefix + 6-12 digits). Context-gated on card vocabulary.
        PatternRecognizer(
            supported_entity="INSURANCE_ID",
            patterns=[Pattern("insurance_id", r"\b[A-Z]{0,3}\d{6,12}\b", 0.15)],
            context=["member id", "member", "policy", "policy number", "subscriber",
                     "group number", "group", "plan", "insurance", "aetna", "cigna",
                     "unitedhealthcare", "united healthcare", "hsa", "rxbin"],
        ),

        # Passport MRZ line 2 (TD3): passport# + nationality + DOB + expiry, '<'
        # filler. OCR-fragile, so low weight — a real MRZ parser is the upgrade.
        PatternRecognizer(
            supported_entity="PASSPORT_MRZ",
            patterns=[Pattern(
                "mrz2",
                r"\b[A-Z0-9<]{9}\d[A-Z]{3}\d{6}\d[MFX<]\d{6}\d[A-Z0-9<]{14}\d\b",
                0.5)],
            context=["passport", "mrz", "type p"],
        ),
    ]


# Human labels for the shelf, keyed by Presidio entity type (built-in + custom).
FIELD_LABELS = {
    "US_SSN": "SSN",
    "CREDIT_CARD": "Card",
    "US_PASSPORT": "Passport №",
    "PASSPORT_MRZ": "Passport (MRZ)",
    "US_DRIVER_LICENSE": "Driver License",
    "US_BANK_NUMBER": "Bank account",
    "SEVIS_ID": "SEVIS ID",
    "USCIS_RECEIPT": "USCIS receipt",
    "ALIEN_NUMBER": "A-Number",
    "I94_NUMBER": "I-94 №",
    "EIN": "Employer EIN",
    "TRAVEL_PNR": "Booking PNR",
    "INSURANCE_ID": "Insurance ID",
    "PHONE_NUMBER": "Phone",
    "EMAIL_ADDRESS": "Email",
}

# Which entities are sensitive enough to mask on screen by default.
MASKED_ENTITIES = {
    "US_SSN", "CREDIT_CARD", "US_PASSPORT", "PASSPORT_MRZ", "US_DRIVER_LICENSE",
    "US_BANK_NUMBER", "SEVIS_ID", "USCIS_RECEIPT", "ALIEN_NUMBER", "I94_NUMBER",
    "INSURANCE_ID",
}

# Entities we actually keep as vault fields (drop generic PERSON/DATE_TIME/LOCATION
# noise — those are context, not fields the user wants to copy).
FIELD_ENTITIES = set(FIELD_LABELS)
