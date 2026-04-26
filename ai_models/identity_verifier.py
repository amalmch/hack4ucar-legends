"""
ai_models/identity_verifier.py
───────────────────────────────
Smart AI-powered identity verification pipeline for UCAR signup.

Step-by-step flow:
  1. Detect file type  → image (JPG/PNG/WEBP) or PDF
  2. Extract raw text  → OCR (Tesseract) for images, pdfplumber for PDFs
  3. Classify document → CIN | Carte Étudiant | Attestation Enseignant |
                         Carte Professionnelle | Document Inconnu
  4. Parse fields      → strategy depends on detected document type
  5. Cross-reference   → fuzzy match against MongoDB + scoring
  6. Decision          → APPROVED / PENDING / REJECTED

Scoring guide:
  Document type detected correctly : +20 pts (bonus)
  Name fuzzy match ≥ 80%           : +35 pts
  Name fuzzy match 50–79%          : +15 pts
  Institution match                : +25 pts
  CIN number found in DB           : +20 pts
  CIN format valid (8 digits)      : +5  pts
  ─────────────────────────────────────────────
  ≥ 70 pts → APPROVED automatically
  40–69    → PENDING (manual review by superucaradmin)
  < 40     → REJECTED
"""

import re
import io
import os
from datetime import datetime, timezone
from loguru import logger

# ─── Optional: Tesseract OCR ───────────────────────────────────────────────
try:
    import pytesseract
    from PIL import Image

    # Common Windows install paths — tries both
    for _path in [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\bousl\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
    ]:
        if os.path.exists(_path):
            pytesseract.pytesseract.tesseract_cmd = _path
            break

    TESSERACT_AVAILABLE = True
    logger.info("Tesseract OCR available")
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("Tesseract not installed — OCR disabled")

# ─── Optional: pdfplumber for PDF text extraction ─────────────────────────
try:
    import pdfplumber
    PDF_AVAILABLE = True
    logger.info("pdfplumber available")
except ImportError:
    PDF_AVAILABLE = False
    logger.warning("pdfplumber not installed — PDF text extraction disabled")

# ─── Optional: fuzzywuzzy ─────────────────────────────────────────────────
try:
    from fuzzywuzzy import fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False

# ─── UCAR institution keywords ────────────────────────────────────────────
INSTITUTION_KEYWORDS = [
    # Specific UCAR institution codes (checked first for higher priority)
    "supcom", "insat", "ihec", "enau", "ipest", "ipein", "ipeib",
    "esti", "essai", "esac", "islt", "islain", "isste", "isccb",
    "isepbg", "isban", "isteub", "intes", "isce", "inat", "ihet",
    "inrgref", "inrat", "esam", "esiat", "ispa",
    # City/place keywords
    "gammarth", "mateur", "soukra", "borj cedria", "la marsa",
    "bizerte", "nabeul", "carthage",
    # Generic institution keywords (lower priority)
    "polytechnique", "ucar",
    "université", "universite", "faculté", "faculte",
    "ecole", "école", "institut", "tunisie", "tunisian",
]

# ─── Document classification keywords ─────────────────────────────────────
DOC_SIGNATURES = {
    "cin": [
        "carte nationale", "carte d'identité", "identité nationale",
        "cin", "تونس", "الجمهورية التونسية", "بطاقة التعريف الوطنية",
        "republique tunisienne", "nationalité tunisienne",
        "numéro national", "national identity",
    ],
    "carte_etudiant": [
        "carte d'étudiant", "carte étudiant", "student card",
        "numéro d'inscription", "بطاقة الطالب", "année universitaire",
        "annee universitaire", "étudiant inscrit", "inscrit",
    ],
    "attestation_enseignant": [
        "attestation de travail", "corps enseignant", "enseignant",
        "maître assistant", "maitre assistant", "professeur",
        "charge de cours", "chargé de cours", "département",
        "شهادة عمل", "أستاذ",
    ],
    "carte_professionnelle": [
        "carte professionnelle", "employee id", "staff card",
        "personnel administratif", "administration", "fonction publique",
    ],
    "attestation_inscription": [
        "attestation d'inscription", "certifie que", "certifié que",
        "est inscrit", "régulièrement inscrit", "شهادة تسجيل",
    ],
}


# ══════════════════════════════════════════════════════════════════════════
#  1. FILE TYPE DETECTION
# ══════════════════════════════════════════════════════════════════════════
def detect_file_type(data: bytes, filename: str = "") -> str:
    """
    Detect whether the upload is a PDF or an image.
    Uses magic bytes first, then filename extension.
    Returns: 'pdf' | 'image' | 'unknown'
    """
    if len(data) >= 4:
        if data[:4] == b'%PDF':
            return 'pdf'
        # JPEG
        if data[:2] == b'\xff\xd8':
            return 'image'
        # PNG
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            return 'image'
        # GIF
        if data[:6] in (b'GIF87a', b'GIF89a'):
            return 'image'
        # BMP
        if data[:2] == b'BM':
            return 'image'
        # WEBP
        if data[8:12] == b'WEBP':
            return 'image'

    # Fallback: check extension
    ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
    if ext == 'pdf':
        return 'pdf'
    if ext in ('jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff', 'tif'):
        return 'image'

    return 'unknown'


# ══════════════════════════════════════════════════════════════════════════
#  2. TEXT EXTRACTION
# ══════════════════════════════════════════════════════════════════════════
def extract_text(data: bytes, file_type: str) -> str:
    """Extract raw text from image (OCR) or PDF."""
    if file_type == 'pdf':
        return _extract_pdf_text(data)
    elif file_type == 'image':
        return _extract_image_text(data)
    # Unknown type: try both
    text = _extract_image_text(data)
    if not text.strip():
        text = _extract_pdf_text(data)
    return text


def _extract_image_text(data: bytes) -> str:
    if not TESSERACT_AVAILABLE:
        return ""
    try:
        img = Image.open(io.BytesIO(data))
        # Try Arabic + French + English (covers CIN and student cards)
        text = pytesseract.image_to_string(img, lang='fra+ara+eng')
        logger.debug(f"OCR extracted {len(text)} chars from image")
        return text
    except Exception as e:
        logger.error(f"Image OCR failed: {e}")
        return ""


def _extract_pdf_text(data: bytes) -> str:
    if not PDF_AVAILABLE:
        return ""
    try:
        text_parts = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        text = "\n".join(text_parts)
        logger.debug(f"PDF text extracted: {len(text)} chars ({len(text_parts)} pages)")
        return text
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return ""


# ══════════════════════════════════════════════════════════════════════════
#  3. DOCUMENT CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════
def classify_document(text: str) -> str:
    """
    Return the most likely document type:
    'cin' | 'carte_etudiant' | 'attestation_enseignant' |
    'carte_professionnelle' | 'attestation_inscription' | 'unknown'
    """
    text_lower = text.lower()
    scores = {}
    for doc_type, keywords in DOC_SIGNATURES.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        scores[doc_type] = score

    best = max(scores, key=scores.get) if scores else 'unknown'
    if scores.get(best, 0) == 0:
        return 'unknown'

    logger.info(f"Document classified as: '{best}' (scores: {scores})")
    return best


# ══════════════════════════════════════════════════════════════════════════
#  4. FIELD PARSERS (strategy per document type)
# ══════════════════════════════════════════════════════════════════════════
def parse_cin_number(text: str) -> str:
    """Extract 8-digit Tunisian CIN number."""
    matches = re.findall(r'\b(\d{8})\b', text)
    return matches[0] if matches else ""


def parse_name(text: str, doc_type: str) -> str:
    """
    Extract person's name based on document type.
    Strategy:
      - CIN: look for lines labelled 'NOM' / 'PRÉNOM' / 'اللقب' / 'الاسم'
      - Student card: look for 'Nom:' / 'Prénom:'
      - Attestations: look for 'M.' / 'Mme' prefix or quoted names
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # Strategy A: Labelled fields (NOM:, PRÉNOM:, Nom :)
    nom = prenom = ""
    for line in lines:
        low = line.lower()
        if re.match(r'^(nom\s*:|اللقب\s*:)', low):
            nom = re.split(r':', line, 1)[-1].strip()
        elif re.match(r'^(pr[eé]nom\s*:|الاسم\s*:)', low):
            prenom = re.split(r':', line, 1)[-1].strip()
    if nom and prenom:
        return f"{prenom} {nom}"
    if nom:
        return nom

    # Strategy B: M. / Mme prefix (attestation style)
    for line in lines:
        m = re.search(r'\b(M\.|Mme\.?|Mr\.?)\s+([A-ZÀ-Ü][a-zà-ü]+(?:\s+[A-ZÀ-Ü][a-zà-ü]+)+)', line)
        if m:
            return m.group(2)

    # Strategy C: Heuristic — 2-4 capitalised words
    for line in lines:
        words = line.split()
        if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w.isalpha() and len(w) > 1):
            return line

    return lines[0] if lines else ""


def parse_inscription_number(text: str) -> str:
    """Extract student inscription number (various formats)."""
    patterns = [
        r'\b(\d{6,10})\b',           # generic long number
        r'N°\s*(\d+)',               # N° 12345
        r'numéro\s*:?\s*(\d+)',      # numéro: 12345
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return ""


def parse_institution(text: str) -> str:
    """Detect institution name from text."""
    text_lower = text.lower()
    for kw in INSTITUTION_KEYWORDS:
        if kw in text_lower:
            return kw
    return ""


def parse_academic_year(text: str) -> str:
    """Extract academic year like 2023-2024."""
    m = re.search(r'20\d{2}\s*[-/]\s*20\d{2}', text)
    return m.group(0) if m else ""


# ══════════════════════════════════════════════════════════════════════════
#  5. FUZZY MATCHING UTILITIES
# ══════════════════════════════════════════════════════════════════════════
def fuzzy_score(a: str, b: str) -> int:
    if not FUZZY_AVAILABLE or not a or not b:
        return 0
    return fuzz.token_sort_ratio(a.lower(), b.lower())


# ══════════════════════════════════════════════════════════════════════════
#  6. MAIN VERIFICATION PIPELINE
# ══════════════════════════════════════════════════════════════════════════
def verify_document(
    image_data: bytes,
    declared_name: str,
    declared_institution: str,
    db=None,
    filename: str = "",
) -> dict:
    """
    Full verification pipeline.
    Returns:
      {
        status: 'approved' | 'pending' | 'rejected',
        score: int (0–100),
        file_type: str,
        doc_type: str,
        ocr_name: str,
        ocr_cin: str,
        ocr_inscription: str,
        ocr_institution: str,
        academic_year: str,
        details: [str],
        verified_at: ISO str,
      }
    """
    result = {
        "status": "pending",
        "score": 0,
        "file_type": "unknown",
        "doc_type": "unknown",
        "ocr_name": "",
        "ocr_cin": "",
        "ocr_inscription": "",
        "ocr_institution": "",
        "academic_year": "",
        "details": [],
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }

    # ── 0. No document uploaded ────────────────────────────────────────────
    if not image_data:
        result["details"].append("⚠️  Aucun document fourni — dossier en attente de vérification manuelle")
        return result

    # ── 1. Detect file type ────────────────────────────────────────────────
    file_type = detect_file_type(image_data, filename)
    result["file_type"] = file_type
    result["details"].append(f"📎 Type de fichier détecté : {file_type.upper()}")

    if file_type == 'unknown':
        result["details"].append("⚠️  Format de fichier non reconnu — dossier en attente")
        return result

    if file_type == 'image' and not TESSERACT_AVAILABLE:
        result["details"].append("⚠️  OCR non disponible (Tesseract non installé) — dossier en attente")
        return result

    if file_type == 'pdf' and not PDF_AVAILABLE:
        result["details"].append("⚠️  Extraction PDF non disponible (pdfplumber non installé) — dossier en attente")
        return result

    # ── 2. Extract text ────────────────────────────────────────────────────
    raw_text = extract_text(image_data, file_type)
    if not raw_text.strip():
        result["details"].append("⚠️  Impossible d'extraire du texte — document illisible ou scanné en basse résolution")
        return result

    # ── 3. Classify document ───────────────────────────────────────────────
    doc_type = classify_document(raw_text)
    result["doc_type"] = doc_type

    DOC_LABELS = {
        "cin": "Carte Nationale d'Identité (CIN)",
        "carte_etudiant": "Carte Étudiant",
        "attestation_enseignant": "Attestation Enseignant",
        "carte_professionnelle": "Carte Professionnelle",
        "attestation_inscription": "Attestation d'Inscription",
        "unknown": "Document non classifié",
    }
    result["details"].append(f"📄 Document identifié : {DOC_LABELS.get(doc_type, doc_type)}")

    score = 0

    # Bonus for recognising a specific document type
    if doc_type != "unknown":
        score += 20
        result["details"].append("✅ Type de document reconnu (+20 pts)")

    # ── 4. Parse fields based on doc type ─────────────────────────────────
    ocr_name = parse_name(raw_text, doc_type)
    ocr_cin = parse_cin_number(raw_text) if doc_type in ('cin', 'unknown') else ""
    ocr_inscription = parse_inscription_number(raw_text) if doc_type in ('carte_etudiant', 'attestation_inscription', 'unknown') else ""
    ocr_institution = parse_institution(raw_text)
    academic_year = parse_academic_year(raw_text)

    result["ocr_name"] = ocr_name
    result["ocr_cin"] = ocr_cin
    result["ocr_inscription"] = ocr_inscription
    result["ocr_institution"] = ocr_institution
    result["academic_year"] = academic_year

    # ── 5. Name matching ───────────────────────────────────────────────────
    name_match = fuzzy_score(ocr_name, declared_name)
    if name_match >= 80:
        score += 35
        result["details"].append(f"✅ Nom correspondant : {name_match}% de similarité (+35 pts)")
    elif name_match >= 50:
        score += 15
        result["details"].append(f"⚠️  Correspondance partielle du nom : {name_match}% (+15 pts)")
    elif ocr_name:
        result["details"].append(f"❌ Nom non correspondant : '{ocr_name}' ≠ '{declared_name}' ({name_match}%)")
    else:
        result["details"].append("❌ Impossible d'extraire le nom du document")

    # ── 6. Institution matching ────────────────────────────────────────────
    if ocr_institution:
        inst_match = fuzzy_score(ocr_institution, declared_institution)
        if ocr_institution in declared_institution.lower() or inst_match >= 60:
            score += 25
            result["details"].append(f"✅ Établissement reconnu : '{ocr_institution}' (+25 pts)")
        else:
            result["details"].append(f"⚠️  Établissement différent dans le document : '{ocr_institution}'")
    else:
        result["details"].append("⚠️  Aucun établissement détecté dans le document")

    # ── 7. CIN validation ─────────────────────────────────────────────────
    if ocr_cin:
        score += 5  # CIN format valid
        result["details"].append(f"✅ Numéro CIN valide trouvé : {ocr_cin} (+5 pts)")

        # Cross-reference DB
        if db is not None:
            found = (
                db.students.find_one({"cin": ocr_cin}) or
                db.teachers.find_one({"cin": ocr_cin})
            )
            if found:
                score += 20
                result["details"].append(f"✅ CIN {ocr_cin} trouvé dans le registre UCAR (+20 pts)")
            else:
                result["details"].append(f"⚠️  CIN {ocr_cin} non trouvé dans le registre (nouvelle inscription possible)")

    # ── 8. Student inscription number cross-ref ───────────────────────────
    if ocr_inscription and db is not None:
        found_stu = db.students.find_one({"student_id": {"$regex": ocr_inscription}})
        if found_stu:
            score += 15
            result["details"].append(f"✅ Numéro d'inscription {ocr_inscription} trouvé (+15 pts)")

    # ── 9. Academic year info ─────────────────────────────────────────────
    if academic_year:
        result["details"].append(f"📅 Année universitaire détectée : {academic_year}")

    # ── 10. Final decision ────────────────────────────────────────────────
    result["score"] = min(score, 100)

    if score >= 70:
        result["status"] = "approved"
    elif score >= 40:
        result["status"] = "pending"
    else:
        result["status"] = "rejected"

    logger.info(
        f"Verification complete | doc={doc_type} | file={file_type} | "
        f"score={score} → {result['status']} | name='{ocr_name}'"
    )
    return result
