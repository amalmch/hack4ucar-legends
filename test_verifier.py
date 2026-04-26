"""
test_verifier.py
─────────────────
Quick self-test for the identity verification pipeline.
Run: python test_verifier.py
"""
import sys
from ai_models.identity_verifier import (
    detect_file_type,
    classify_document,
    parse_cin_number,
    parse_name,
    parse_institution,
    verify_document,
)

PASS = "✅ PASS"
FAIL = "❌ FAIL"

errors = 0

def check(label, got, expected):
    global errors
    if got == expected:
        print(f"  {PASS}  {label}")
    else:
        print(f"  {FAIL}  {label}")
        print(f"         Expected: {repr(expected)}")
        print(f"         Got:      {repr(got)}")
        errors += 1

print("\n── File Type Detection ─────────────────────────")
check("PDF magic bytes", detect_file_type(b'%PDF-1.4 hello', 'doc.pdf'), 'pdf')
check("JPEG magic bytes", detect_file_type(b'\xff\xd8\xff\xe0content', 'photo.jpg'), 'image')
check("PNG magic bytes", detect_file_type(b'\x89PNG\r\n\x1a\ncontent', 'img.png'), 'image')
check("PDF by extension fallback", detect_file_type(b'random', 'document.pdf'), 'pdf')
check("JPG by extension fallback", detect_file_type(b'random', 'photo.jpg'), 'image')
check("Unknown type", detect_file_type(b'random random', 'noext'), 'unknown')

print("\n── Document Classification ─────────────────────")
cin_text = "République Tunisienne - Carte Nationale d'Identité\nNOM: BEN ALI\nPRÉNOM: AHMED\n12345678"
check("CIN detection", classify_document(cin_text), 'cin')

student_text = "Carte d'étudiant\nAnnée universitaire 2023-2024\nNom: Mariem Trabelsi\nNuméro d'inscription: 2023456"
check("Carte étudiant detection", classify_document(student_text), 'carte_etudiant')

teacher_text = "Attestation de travail\nM. Yassine Hamdi, Maître Assistant A\nDépartement Informatique\nChargé de cours"
check("Attestation enseignant detection", classify_document(teacher_text), 'attestation_enseignant')

check("Unknown doc detection", classify_document("random text without keywords"), 'unknown')

print("\n── CIN Number Parsing ──────────────────────────")
check("8-digit CIN", parse_cin_number("Your CIN is 12345678 on this document"), "12345678")
check("CIN in French text", parse_cin_number("N° 98765432 délivré le 12/05/2018"), "98765432")
check("No CIN in text", parse_cin_number("No numbers here at all"), "")

print("\n── Name Parsing ────────────────────────────────")
labelled_text = "NOM: BEN AHMED\nPRÉNOM: YASSINE\nDate: 01/01/2000"
name = parse_name(labelled_text, 'cin')
print(f"  INFO  Labelled name extracted: '{name}'")

check("Institution — carthage", parse_institution("Université de Carthage, Tunis"), "carthage")
check("Institution — supcom", parse_institution("Sup'Com - École Supérieure"), "supcom")
check("Institution — none", parse_institution("Ministry of Agriculture"), "")

print("\n── Full Pipeline (no OCR — synthetic data) ─────")
# Test with no document
result = verify_document(b'', declared_name='Ahmed Ben Ali', declared_institution='UCAR-INSAT')
check("No doc → pending", result['status'], 'pending')

# Test with fake PDF bytes (will fail extraction but should return pending gracefully)
result = verify_document(b'%PDF-1.4 test', declared_name='Ahmed', declared_institution='UCAR')
print(f"  INFO  Fake PDF result: status={result['status']}, doc_type={result['doc_type']}, score={result['score']}")
print(f"        Details: {result['details'][:3]}")

print(f"\n{'='*50}")
if errors == 0:
    print(f"✅ All tests passed!")
else:
    print(f"❌ {errors} test(s) failed")
    sys.exit(1)
