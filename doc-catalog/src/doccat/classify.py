"""Semantic tagging: assign taxonomy tags to a document from its embedding.

Approach (no LLM): each top-level category has a natural-language description
that we embed once to form a zero-shot *prototype* vector. A document is tagged
with every category whose cosine similarity to its doc vector clears a threshold
(multi-label — a payslip is work AND finance). Sub-tags are decided by cheap
keyword/sender rules over the document text, which sharpen what the embedding
blurs (payslip vs invoice vs statement).

The prototypes start from these descriptions; as the user corrects tags in the
UI those confirmed documents become labelled data and the prototype for a
category can be replaced by the centroid of its confirmed members (see
centroids_from_confirmed) — the zero-shot start improves into a fitted one with
zero manual model work.
"""
from . import config

# name -> (prototype description, [(subtag, keywords, sender_substrings), ...]).
# The description is what gets embedded; keep it a concrete list of the document
# kinds that belong in the category.
CATEGORIES = {
    "finance": (
        "financial documents: bank and credit card statements, brokerage and "
        "retirement investment statements, loan and mortgage statements, "
        "invoices, bills and payment receipts, account balances and transactions",
        [
            ("finance:bank-statement", ["statement period", "account summary",
             "beginning balance", "ending balance", "available balance"], []),
            ("finance:investment", ["brokerage", "retirement", "401(k)", "ira",
             "portfolio", "shares", "dividend", "net asset value"],
             ["vanguard", "fidelity", "schwab", "morganstanley"]),
            ("finance:loan", ["loan", "mortgage", "principal", "interest rate",
             "amortization", "payoff"], []),
            ("finance:invoice", ["invoice", "amount due", "bill to", "due date"], []),
            ("finance:receipt", ["receipt", "amount paid", "transaction id"], []),
        ],
    ),
    "work": (
        "employment and workplace documents: pay stubs and earnings statements, "
        "job offer letters, employment contracts and agreements, resumes",
        [
            ("work:payslip", ["gross pay", "net pay", "year to date", "ytd",
             "earnings statement", "pay period", "deductions"],
             ["adp", "workday", "gusto", "paychex"]),
            ("work:offer-letter", ["offer of employment", "annual salary",
             "start date", "compensation"], []),
            ("work:contract", ["employment agreement", "terms of employment",
             "at-will"], []),
            ("work:resume", ["resume", "curriculum vitae", "work experience",
             "professional summary"], []),
        ],
    ),
    "tax": (
        "tax documents: income tax returns, W-2 wage statements, 1099 forms, "
        "tax receipts and deduction records from the IRS or a tax preparer",
        [
            ("tax:w2", ["w-2", "wage and tax statement", "wages, tips"], []),
            ("tax:1099", ["1099", "nonemployee compensation", "1099-int",
             "1099-div"], []),
            ("tax:return", ["form 1040", "adjusted gross income", "tax return",
             "refund"], ["irs.gov"]),
            ("tax:receipt", ["deductible", "charitable contribution"], []),
        ],
    ),
    "housing": (
        "housing and property documents: apartment lease and rental agreements, "
        "utility bills for electricity gas water and internet, mortgage and HOA "
        "statements",
        [
            ("housing:lease", ["lease contract", "lease agreement", "tenant",
             "landlord", "monthly rent", "security deposit"], []),
            ("housing:utility", ["kwh", "meter", "billing period", "electric",
             "natural gas", "water usage"], ["comcast", "xfinity", "coned",
             "pge", "verizon"]),
            ("housing:mortgage", ["escrow", "principal and interest",
             "mortgage statement"], []),
            ("housing:hoa", ["homeowners association", "hoa dues"], []),
        ],
    ),
    "health": (
        "medical and health documents: doctor and hospital records, lab and test "
        "results, medical bills and explanation of benefits, prescriptions",
        [
            ("health:lab-result", ["laboratory", "reference range", "specimen",
             "test result"], []),
            ("health:bill", ["explanation of benefits", "eob", "patient balance",
             "amount you owe"], []),
            ("health:prescription", ["prescription", "rx number", "refills",
             "pharmacy"], ["cvs", "walgreens"]),
            ("health:record", ["patient", "diagnosis", "visit summary",
             "provider"], []),
        ],
    ),
    "insurance": (
        "insurance documents: health, auto, home or renters, and life insurance "
        "policies, coverage summaries, premiums and claims",
        [
            ("insurance:health", ["health plan", "copay", "deductible",
             "member id"], []),
            ("insurance:auto", ["auto policy", "vehicle", "collision",
             "liability coverage"], ["geico", "progressive", "statefarm",
             "allstate"]),
            ("insurance:home", ["homeowners policy", "renters policy",
             "dwelling coverage"], []),
            ("insurance:life", ["life insurance", "beneficiary",
             "death benefit"], []),
        ],
    ),
    "identity-legal": (
        "official identity and legal documents: passports, driver licenses, "
        "social security cards, contracts, agreements and legal notices",
        [
            ("id:passport", ["passport", "place of birth", "date of issue"], []),
            ("id:license", ["driver license", "driver's license", "class d",
             "dmv"], []),
            ("id:ssn", ["social security", "ssn"], []),
            ("legal:contract", ["agreement", "hereby", "party of the",
             "governing law"], []),
            ("legal:notice", ["notice", "hereby notified", "cease"], []),
        ],
    ),
    "education": (
        "education documents: academic transcripts, diplomas and degree "
        "certificates, enrollment and registration records from a school or "
        "university",
        [
            ("edu:transcript", ["transcript", "gpa", "credits", "semester",
             "grade"], []),
            ("edu:diploma", ["diploma", "degree of", "conferred"], []),
            ("edu:enrollment", ["enrollment", "registration", "course schedule"],
             ["nyu.edu", ".edu"]),
        ],
    ),
    "purchases": (
        "shopping and purchase documents: order confirmations, purchase receipts, "
        "and product warranties from online and retail stores",
        [
            ("purchases:order", ["order confirmation", "order number", "shipped",
             "tracking"], ["amazon", "ebay"]),
            ("purchases:receipt", ["your receipt", "subtotal", "sales tax"], []),
            ("purchases:warranty", ["warranty", "coverage period", "serial "
             "number"], []),
        ],
    ),
    "travel": (
        "travel documents: flight and hotel bookings, trip itineraries, and visa "
        "or travel authorization documents",
        [
            ("travel:booking", ["booking confirmation", "reservation",
             "check-in", "flight"], ["expedia", "booking.com", "airbnb"]),
            ("travel:itinerary", ["itinerary", "departure", "arrival",
             "confirmation number"], []),
            ("travel:visa", ["visa", "authorization", "entry"], []),
        ],
    ),
}

# When nothing clears the threshold, fall back to this rather than force-fitting.
FALLBACK = ("personal", "personal:misc")


def category_descriptions():
    """Ordered (name, description) — embed these once to build the prototypes."""
    return [(name, spec[0]) for name, spec in CATEGORIES.items()]


def category_members(name):
    """All tag names that count as this category: the category itself + its
    sub-tags. Used to gather a category's confirmed documents for its centroid."""
    spec = CATEGORIES.get(name)
    if spec:
        return [name] + [st for st, _, _ in spec[1]]
    if name == "personal":
        return ["personal", "personal:misc", "personal:correspondence"]
    return [name]


def taxonomy_tags():
    """[(category, [subtag, ...]), ...] for the UI tag picker. Includes the
    'personal' fallback group so the human can apply it deliberately too."""
    groups = [(name, [st for st, _, _ in spec[1]])
              for name, spec in CATEGORIES.items()]
    groups.append(("personal", ["personal:misc", "personal:correspondence"]))
    return groups


def _cos(a, b):
    import numpy as np
    return float(np.dot(a, b))  # inputs are L2-normalized -> dot == cosine


def classify(doc_vec, prototypes, text, sender=""):
    """Return a set of tags for a document.

    doc_vec: L2-normalized document embedding.
    prototypes: {category: L2-normalized prototype vector}.
    text/sender: lowercased-internally, used for sub-tag rules.
    """
    hay = f"{text}\n{sender}".lower()
    scores = {n: _cos(doc_vec, p) for n, p in prototypes.items() if p is not None}
    tags = set()
    if scores:
        # Relative: keep categories within CLASSIFY_MARGIN of the top score, but
        # never below the absolute floor. Adapts to bge's compressed cosine band.
        cutoff = max(config.CLASSIFY_THRESHOLD, max(scores.values()) - config.CLASSIFY_MARGIN)
        for name, score in scores.items():
            if score < cutoff:
                continue
            tags.add(name)
            for subtag, keywords, senders in CATEGORIES[name][1]:
                if any(k in hay for k in keywords) or any(s in hay for s in senders):
                    tags.add(subtag)
    if not tags:
        tags.update(FALLBACK)
    return tags
