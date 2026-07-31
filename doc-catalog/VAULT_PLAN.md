# Doc Catalog → Personal Field Vault — build plan

> Status: **DRAFT for review.** Nothing built yet. Extracted from the grilling
> session 2026-07-27.

## The reframe (why this plan exists)

The catalog is not a document viewer. The **primary job** is: *pull a field value
— passport number, license number, card number, SSN, policy number — to paste
into a form or email*, mostly at home on desktop. The PDF is just the source of
proof behind the value.

So the product becomes a **field vault backed by documents**: per-doc-type
structured fields (the "Stack app, but metadata-rich and searchable"), surfaced
copy-ready. Documents remain the substrate (ingest / OCR / tags / semantic
search all stay); a new extraction layer pulls **typed PII fields** on top.

## Requirements locked (from grilling)

1. Atom = the **field value**, copy-ready. Home screen is a shelf of values, not a
   document list.
2. **Masking = UX, not crypto.** Values stored plaintext, **masked on screen by
   default; tap to reveal, tap to copy.** No zero-knowledge, no passphrase.
3. **Credit cards included** (no other password manager exists).
4. Vault organized by **entity** (Passport, SSN, License, Card, Insurance,
   Immigration…), each backed by 1..n documents, **newest-valid in front**,
   expired instances tucked behind but retrievable.
5. **Two passports**, linked, latest in front.
6. **Temporal validity**: fields carry expiry. Expired instances auto-demote.
   **Travel itineraries appear only while their trip window is active**, then drop.
7. Extraction is **local** (no egress for SSN/CC), free, offline: NER + patterns.
8. NER finds **candidates**; user **confirms once** per field.

## Security posture (explicit — a conscious choice, not an oversight)

- **Plaintext at rest.** Masking is a UI reveal-gate (anti shoulder-surf / anti
  casual-dump on a borrowed-unlocked machine), *not* encryption.
- **Perimeter = Tailscale**, no public egress (corpus principle #5). The vault is
  never on a `*.ch33ky.org` public hostname — tailnet-only, like Headlamp/Grafana.
- Accepted threat model (user's call): the daily-driver box already holds this PII
  in plaintext, so encrypting this one app buys little against device theft. We do
  **not** build crypto. This is written down so it stays a deliberate decision.
- All extraction (Presidio, spaCy, MRZ) runs **on-node**; PII never leaves the box.
- Credit cards stored + masked; flagged here as the one category with active fraud
  value — revisit if a real password manager ever enters the picture.

## PII taxonomy (entity classes)

**Presidio built-in recognizers (regex + validators + NER context):**
`US_SSN`, `CREDIT_CARD` (Luhn-validated), `US_DRIVER_LICENSE`, `US_PASSPORT`,
`US_BANK_NUMBER`, `PHONE_NUMBER`, `EMAIL_ADDRESS`, plus `PERSON` / `DATE_TIME` /
`LOCATION` for context and expiry pickup.

**Custom `PatternRecognizer`s (this repo — Presidio doesn't ship them):**
- `SEVIS_ID` — `N` + 10 digits (I-20).
- `USCIS_RECEIPT` — `(IOE|EAC|WAC|LIN|SRC|MSC|YSC)` + 10 digits (I-797/I-140/I-129).
- `INSURANCE_POLICY` / `INSURANCE_MEMBER_ID` — issuer-specific patterns + context words.
- `VEHICLE_REGISTRATION` — plate/registration formats.

**Passport specialization:** a **MRZ parser** (`PassportEye` / `fastmrz`) on the
passport image beats generic NER for the #1 doc — pulls number, country, surname,
given names, DOB, sex, **expiry** from the machine-readable zone deterministically.

**Vault entity groups (shelf):** Identity (passport ×2, SSN, license),
Financial (cards, bank), Insurance (policy/member), Immigration (I-20/I-797/I-140),
Travel (itineraries — temporal). Groups derive from field `entity_class`.

## Extraction stack — verdict

Local **Microsoft Presidio** as the engine (fuses pattern recognizers + spaCy NER
+ validators + per-hit confidence) **+ custom recognizers** (immigration/insurance)
**+ MRZ parser** (passports). This supersedes the earlier regex-vs-LLM question: it
is regex *and* NER *and* checksum validation, fused, on-node, free.

Known limits (design around them): (a) extraction quality is gated by OCR quality —
a mangled passport photo yields nothing (MRZ parser mitigates); (b) NER returns
*candidates*, so the confirm-once UX is mandatory, not optional.

Optional later: swap Presidio's spaCy backbone for a transformer PII model
(`iiiorg/piiranha`, `deberta-pii`) if recall on scans disappoints. Start spaCy.

## Architecture (fits existing patterns)

- **New pod `presidio`** — FastAPI analyzer service, like `embedder`. Loads spaCy
  `en_core_web_sm` + Presidio analyzer + custom recognizers at startup; `/analyze`
  takes text → `[{entity_type, start, end, score, text}]`. CPU, ~300–500 MB.
  python:3.12-slim + pip (`presidio-analyzer`, `spacy`, model, `passporteye`).
- **New pipeline stage `fields`** — drained by a `field-worker` (stage-worker
  pattern, `WORKER_STAGES=fields`) or folded into an existing worker. Enqueued
  after `text`/`ocr` completes (alongside `embed`). Steps: gather page text →
  call `presidio /analyze` + MRZ-parse any passport image → candidate fields with
  class/span/score → upsert into `field` table as **unconfirmed**.
- **Migration 007** — new tables (below). No change to existing pipeline.
- **API (api.py)** — `/api/fields` (shelf), `/api/field/{id}/reveal` (returns
  value), `/api/field/{id}/confirm|edit|delete`, `/api/doc/{id}/fields`. SSE
  already pushes on change; add `field` to the NOTIFY triggers.

## Data model (migration 007)

```
field
  id                 bigserial pk
  document_id        bigint fk           -- source of proof
  entity_class       text                -- US_PASSPORT, US_SSN, CREDIT_CARD, SEVIS_ID, …
  label              text                -- human label ("Passport №", "SEVIS ID")
  value              text                -- PLAINTEXT (masked in UI)
  value_masked       text                -- precomputed display mask ("•••• 4831")
  expiry             date null           -- drives validity ranking / temporal shelf
  valid_from         date null           -- itineraries (trip window)
  confirmed          bool default false  -- user confirmed this candidate
  score              real                -- extractor confidence
  source             text                -- 'presidio' | 'mrz' | 'user'
  created_at         timestamptz
  unique (document_id, entity_class, value)
```

Shelf = query fields grouped by `entity_class`, `confirmed=true`, ordered by
validity (non-expired first, newest `expiry`/`created_at`), current instance in
front. "Two passports newest-front" and "expired tucked behind" fall out of this
ordering. Itineraries: shown only where `now()` ∈ `[valid_from, expiry]`.

## UI (SvelteKit — the original "less clutter" ask)

Design principle: **the home screen is the 80% job — grab a number.** Everything
else demotes.

- **Home = Vault shelf.** Entity cards grouped (Identity / Financial / Insurance /
  Immigration / Travel). Each card: label + **masked value + tap-reveal + tap-copy**,
  current instance in front, expired collapsed. Mobile-friendly big tap targets.
- **Search below the shelf** — semantic + FTS for the long tail (tax, itineraries,
  the rare doc). One box, results as doc cards.
- **Pipeline health / job queue / Gmail accounts → a secondary "Status" view**, not
  the home hero (today's SSE JobQueue moves there). The live dot stays in the header.
- **Doc detail** gains a **Fields panel first** (confirm candidates, copy values),
  then existing tags panel, then extracted text. Confirm-once happens here.
- Mask by default everywhere; reveal is per-field, auto-re-mask on blur/navigate.

## Information architecture — the three visibility layers

The whole "less clutter" ask reduces to a discipline about **what surfaces where**.
Three layers, strict:

```
SHOWN ON SHELF (home)        STORED, REACHABLE (drill-down)     HIDDEN UNTIL ACTION
─────────────────────────    ───────────────────────────────   ─────────────────────
current valid field/entity   old / expired field instances     revealed value (tap 👁)
masked value + copy          all backing documents + images    full card PAN
active itinerary only        full extracted text               unconfirmed candidates*
one card per entity          all auto-tags                     (* live in Review queue)
                             past itineraries
                             the long-tail docs (via Search)
```

Rule of thumb: the shelf shows **one current, confirmed, valid value per entity** and
nothing else. Everything historical, raw, or unconfirmed is one tap away, never on the
home screen.

## Navigation map

```
Header (persistent):  ◗ Vault    🔍 search…    Review ⑥    Status ·    ● live
   │
   ├─ HOME = SHELF ............ current valid values, grouped by entity class
   │     └─ tap entity ──► ENTITY PAGE ...... every instance (current+expired),
   │                                          backing docs, history
   │            └─ tap doc ──► DOC PAGE ...... fields, tags, full text, raw file
   ├─ SEARCH .................. long tail (semantic + FTS) ──► DOC / ENTITY PAGE
   ├─ REVIEW (badge N) ........ unconfirmed PII candidates ──► confirm once
   └─ STATUS .................. pipeline / jobs / Gmail (today's JobQueue, demoted)
```

**Dedicated pages (SvelteKit routes), not panels or modals** — each is its own URL,
reachable from the header, deep-linkable:

```
/               Vault shelf (home)
/entity/[class] Entity page (e.g. /entity/US_PASSPORT)
/doc/[id]       Document page (fields + tags + text + raw)
/search         Search + filters
/review         Review queue — confirm/edit/reject candidates (own page)
/status         Pipeline / jobs / Gmail health (own page; today's JobQueue moves here)
```

## UI mockups

### A. Home — the Vault shelf (desktop)

```
┌────────────────────────────────────────────────────────────────────┐
│ ◗ Vault         🔍 search everything…       Review ⑥   Status ·  ●live│
├────────────────────────────────────────────────────────────────────┤
│  IDENTITY                                                            │
│  ┌─────────────────────────┐  ┌─────────────────────────┐          │
│  │ Passport   🇺🇸 · 2 docs   │  │ SSN                     │          │
│  │ ••••  ••••  4831    👁 ⧉  │  │ •••-••-••••         👁 ⧉ │          │
│  │ exp 2031-04 · current    │  │ confirmed               │          │
│  └─────────────────────────┘  └─────────────────────────┘          │
│  ┌─────────────────────────┐                                       │
│  │ Driver License   NJ      │                                       │
│  │ ••••••••  209       👁 ⧉  │                                       │
│  │ exp 2027-09              │                                       │
│  └─────────────────────────┘                                       │
│                                                                     │
│  FINANCIAL                                                          │
│  ┌─────────────────────────┐  ┌─────────────────────────┐          │
│  │ Visa   ····4242          │  │ Amex   ····1005         │          │
│  │ ••••  ••••  ••••  4242 👁⧉│  │ ••••  ••••••  •1005  👁⧉ │          │
│  │ exp 08/27                │  │ exp 11/26               │          │
│  └─────────────────────────┘  └─────────────────────────┘          │
│                                                                     │
│  INSURANCE                                                          │
│  ┌─────────────────────────┐                                       │
│  │ Health · Aetna           │                                       │
│  │ policy •••••••7Q     👁 ⧉ │                                       │
│  │ member W12… · grp 8845   │                                       │
│  └─────────────────────────┘                                       │
│                                                                     │
│  IMMIGRATION                                                        │
│  ┌─────────────────────────┐  ┌─────────────────────────┐          │
│  │ I-140 · Approved         │  │ SEVIS (I-20)            │          │
│  │ IOE•••••••867       👁 ⧉  │  │ N••••••••12         👁 ⧉ │          │
│  │ priority 2023-11         │  │ program ends 2026-05    │          │
│  └─────────────────────────┘  └─────────────────────────┘          │
│                                                                     │
│  TRAVEL · active only                                              │
│  ┌────────────────────────────────────────────────────┐           │
│  │ ✈ NYC → DEL   Jul 28 – Aug 15   AI 102              │           │
│  │ PNR ••••X9   👁 ⧉                itinerary.pdf →      │           │
│  └────────────────────────────────────────────────────┘           │
│                                                                     │
│  ⋯ 51 more documents (tax, letters, transcripts)  →  Search         │
└────────────────────────────────────────────────────────────────────┘
      👁 reveal (auto re-masks on blur / 15s)     ⧉ copy to clipboard
      Shelf shows ONLY current valid confirmed values. "2 docs" = old
      passport exists, tucked on the entity page. Travel card appears
      only while the trip window is active, then disappears.
```

### B. Home — mobile (single column, big tap targets)

```
┌───────────────────────────┐
│ ◗ Vault      🔍   ⑥   ●    │
├───────────────────────────┤
│ IDENTITY                  │
│ ┌───────────────────────┐ │
│ │ Passport 🇺🇸        2  │ │
│ │ ••••  ••••  4831       │ │
│ │ exp 2031-04    👁    ⧉ │ │  ← reveal / copy are thumb-sized
│ └───────────────────────┘ │
│ ┌───────────────────────┐ │
│ │ SSN                    │ │
│ │ •••-••-••••    👁    ⧉ │ │
│ └───────────────────────┘ │
│ FINANCIAL                 │
│ ┌───────────────────────┐ │
│ │ Visa ····4242   👁  ⧉ │ │
│ └───────────────────────┘ │
│ ⋯                         │
└───────────────────────────┘
```

### C. Field interaction (the copy-a-number moment)

```
  masked            tap 👁                 tap ⧉
 ┌──────────┐      ┌──────────┐          ┌──────────┐
 │•••• 4831 │  →   │4 8 3 1 … │    →      │ copied ✓ │  (re-masks after
 │   👁  ⧉  │      │  🔓  ⧉   │           │          │   blur / 15s)
 └──────────┘      └──────────┘          └──────────┘
```

### D. Entity page — Passport (stored-separately-but-reachable)

```
┌────────────────────────────────────────────────────────────────────┐
│ ‹ Vault / Passport                                          ● live  │
├────────────────────────────────────────────────────────────────────┤
│ Passport            🇺🇸 United States                 2 documents    │
│                                                                     │
│ CURRENT                                          exp 2031-04-12  ✓   │
│ ┌─────────────────────────────────────────────────────────────┐    │
│ │ Number     ••••  ••••  4831              👁 ⧉                 │    │
│ │ Surname    JOSHI                            ⧉                 │    │
│ │ Given      RAJEEV                           ⧉                 │    │
│ │ DOB        ••••-••-••                     👁 ⧉                 │    │
│ │ Issued     2021-04-13     Expires  2031-04-12                │    │
│ │ source ▸ Passport.pdf  (MRZ ✓)          open doc →           │    │
│ └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│ PREVIOUS · expired                               exp 2019-03  ⌵      │
│ ┌─────────────────────────────────────────────────────────────┐    │
│ │ Number     ••••  ••••  5567   👁 ⧉      source ▸ Passport_old │    │
│ └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│ DOCUMENTS                                                           │
│  ▸ Passport.pdf         2021 · MRZ ✓ · id:passport                  │
│  ▸ Passport_old.pdf     2016 · MRZ ✓ · expired                     │
└────────────────────────────────────────────────────────────────────┘
   Newest in front; old collapsed (⌵) but present. Two passports linked
   because both parse to entity_class = US_PASSPORT for the same person.
```

### E. Doc page — Fields panel first, then tags, then text

```
┌────────────────────────────────────┬───────────────────────────────┐
│ ‹ Documents / I-140 EB-2 Approval   │  FIELDS                       │
│ PR Joshi, Rajeev · 2025-05-02       │  ┌─────────────────────────┐  │
│ pdf · 1p · text-layer               │  │ USCIS receipt           │  │
│                                     │  │ IOE•••••••867     👁 ⧉   │  │
│ pipeline  text ✓  embed ✓   ✓ Done  │  │ ✓ confirmed             │  │
│                                     │  ├─────────────────────────┤  │
│ [ Open PDF ] [ Reprocess ] [ ⌫ ]    │  │ Priority date           │  │
│                                     │  │ 2023-11-08          ⧉   │  │
│ ── Extracted text ───────────────   │  ├─────────────────────────┤  │
│ DEPARTMENT OF HOMELAND SECURITY     │  │ ? candidate  A-number   │  │
│ I-140 IMMIGRANT PETITION FOR        │  │ A•••••••52              │  │
│ ALIEN WORKER  …full text…           │  │ [✓ confirm] [✎] [✕]     │  │
│                                     │  └─────────────────────────┘  │
│                                     │  TAGS                         │
│                                     │  work · finance · legal:notice│
│                                     │  travel:visa · identity-legal │
│                                     │  [ + organize ]               │
└────────────────────────────────────┴───────────────────────────────┘
   Fields (the values) lead. Unconfirmed candidate shown greyed with
   confirm/edit/reject. Tags + full text remain, below/right.
```

### F. Search — the long tail

```
🔍  2019 tax                                        semantic + text
────────────────────────────────────────────────────────────────────
  filters:  [ type ▾ ]  [ year ▾ ]  [ has field ▾ ]  [ source ▾ ]

 ▸ JoshiRajeev2142018TaxDocs.pdf     tax        match: “form 1040 …”
 ▸ W-2_Form_2017_Joshi.pdf           tax · work match: “wages tips …”
 ▸ View Worker – Rajeev … Workday    work:payslip
 ▸ Rajeev Offer Letter.pdf           work:offer-letter
```

### G. Review — confirm-once queue (drives the shelf)

```
Review · 6 candidates                                    [ confirm all ✓ ]
────────────────────────────────────────────────────────────────────
 Passport.pdf     US_PASSPORT     ••••4831   [✓ confirm] [✎ edit] [✕ not it]
 i-765.pdf        SEVIS_ID        N••••12    [✓]         [✎]      [✕]
 Aetna_card.jpg   INSUR_POLICY    ••••7Q     [✓]         [✎]      [✕]
 amex.pdf         CREDIT_CARD     ••••1005   [✓]         [✎]      [✕]
 …                                                                    
   Confirming promotes a candidate onto the shelf. Rejecting hides it.
```

### H. Status — demoted (today's home JobQueue lives here now)

```
‹ Status                                                       ● live
────────────────────────────────────────────────────────────────────
 PIPELINE                                                            
 text  [12 done]       ocr  [1 run · 4 pend]                         
 embed [57 done]       fields [3 pend]                               
 GMAIL                                                               
 mail.rajeevjoshi   synced · 58 attachments                         
 rjcool.joshi2      synced                                          
 FAILURES  (none)                                                    
```



- **Phase A — extraction backend.** presidio pod; custom recognizers; MRZ parser;
  `fields` stage + worker; migration 007; confirm/reveal API; NOTIFY on `field`.
  Reprocess corpus through `fields`.
- **Phase B — Vault UI.** Entity shelf home (mask/reveal/copy), doc-detail Fields
  panel, demote status/registry to secondary views.
- **Phase C — temporal + linking.** Expiry ranking, itinerary auto-demote, passport
  linking (2 → newest front), expired-tucked-behind interactions.

## Decisions (locked 2026-07-27)

1. **Separate `field-worker` pod** (`WORKER_STAGES=fields`, `WORKER_INGEST=false`),
   stage-worker pattern like `ocr-worker`. Presidio/MRZ deps stay isolated.
2. **Confirm required.** Unconfirmed candidates **never appear on the shelf** — they
   live only in the **Review** queue until confirmed. First-run shelf is empty until
   you work the Review queue; that's accepted.
3. **Store full card PAN** (plaintext at rest, per the security posture), masked to
   last-4 on shelf/entity, full number behind reveal → so you can copy it whole.
4. **Presidio (spaCy default) first**, measure recall on the real corpus, upgrade the
   NER backbone to a transformer PII model (`piiranha`/`deberta-pii`) only if needed.
