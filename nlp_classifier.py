
"""
NLP Classifier module.
Uses a hybrid approach (Regex + Zero-Shot Classification via DeBERTa) 
to determine the physical condition of a phone from its raw description.
"""
import torch
import re
from transformers import pipeline


CONFIDENCE_THRESHOLD = 0.4

CATEGORY_LABELS = {
    "Good":     "appareil neuf sans aucun défaut visible",
    "Normal":   "légère usure cosmétique sans rayures ni chocs",
    "Scratched":"rayures ou éraflures superficielles sur la coque",
    "Cracked":  "fissure ou écran cassé, verre fendu",       # <-- "fissure" explicite
    "Pieces":   "en panne, ne fonctionne plus, vendu pour pièces détachées",
}
FLAGS = re.IGNORECASE | re.UNICODE

REGEX_RULES: list[tuple[re.Pattern, str]] = [
    # Pieces
    (re.compile(r"pour\s+pieces?|hors[\s\-]service|ne\s+s['´`']\s*allume\s+plus|ne\s+fonctionne\s+plus|bloque\s+sur|vendu\s+pour\s+pieces?", FLAGS), "Pieces"),
    # Cracked — vitre/écran/dalle + cassé/fendu, ou fissure seul
    (re.compile(r"fissur|fendu|verre\s+bris|vitre\s+cass|ecran\s+cass|ecran\s+fendu|dalle\s+cass", FLAGS), "Cracked"),
    # Scratched
    (re.compile(r"rayure|raye|eraflure|efle|scratche", FLAGS), "Scratched"),
    # Good
    (re.compile(r"comme\s+neuf|etat\s+neuf|irreprochable|parfait\s+etat", FLAGS), "Good"),
]
def _normalize_text(text: str) -> str:
    """Removes accents to make regex matching better"""
    import unicodedata
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("ascii")

target_device = 0 if torch.cuda.is_available() else -1
classifier = pipeline(
    "zero-shot-classification",
    model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
    device=target_device,
    dtype=torch.float16
)
_ETIQUETTES = list(CATEGORY_LABELS.values())
_INVERSE_MAP = {v: k for k, v in CATEGORY_LABELS.items()}


NEGATION_REGEX = re.compile(r"(pas\s+de|aucune?|sans|ni)\s+\w*", FLAGS)

def check_regex(text: str) -> str | None:
    """Checks the description against regex rules, ignoring negations"""
    normalised = _normalize_text(text)
    
    normalised_sans_NEGATION_REGEX = NEGATION_REGEX.sub("", normalised)
    for pattern, etat in REGEX_RULES:
        if pattern.search(normalised_sans_NEGATION_REGEX):
            return etat
    return None

def guess_state(text: str) -> str:
    """
    Predicts the physical condition of a phone from its raw description.
    Returns : 'Good' | 'Normal' | 'Scratched' | 'Cracked' | 'Pieces'
    """
    if not text or not text.strip():
        return "Normal"
    if len(text.strip()) < 20:
        return "Normal"
    
    cleaned_text = text.lower().strip()

    empty_words = r'(iphone|apple|air|pro|max|mini|se|go|to|gb|tb|bleu|noir|blanc|titane|or|argent|rose|chassis|facture|boite|scelle|neuf|occasion)'
    filtered_text = re.sub(empty_words, '', cleaned_text)
    filtered_text = re.sub(r'[\d\.,\?\!\|"\'\(\)\-–‼️]', '', filtered_text).strip()

    if len(filtered_text.split()) < 3:
        return "Normal"
    
    regex_state=check_regex(cleaned_text)
    if regex_state:
        return regex_state
    
    try:
        result = classifier(text, candidate_labels=_ETIQUETTES, multi_label=False)
        best_label = result["labels"][0]
        best_score = result["scores"][0]
        if best_score < CONFIDENCE_THRESHOLD:
            return "Normal" 

        return _INVERSE_MAP[best_label]
    except Exception as e:
        print(f"Erreur in nlp :{e}")
    finally:
        if target_device == 0:
            torch.cuda.empty_cache()



# --- Test ---
if __name__ == "__main__":
    cas_tests = [
        "L'écran a une grosse fissure en haut, mais sinon il marche bien.",
        "Téléphone en parfait état, jamais tombé, comme neuf.",
        "Quelques micro-rayures au dos, rien de grave.",
        "Ne s'allume plus, vendu pour pièces.",
        "Bon état général, légère usure sur les bords.",
        # Cas limites supplémentaires
        "Vitre cassée mais tout fonctionne.",
        "Rayé sur les côtés, écran nickel.",
        "Bloqué sur le logo, je sais pas pourquoi.",
        "Pas de fissure, écran nickel.",        # doit donner Good/Normal, pas Cracked
        "Aucune rayure, comme neuf.",           # doit donner Good, pas Scratched
        "Fonctionne très bien, sans problème.",
        "Téléphone fonctionnel, pas de fissure",
        "Iphone 16 pro.",
        "Iphone 16 pro max 256 go iphone 16 pro max 256 go iphone 16"
        "Iphone 15 pro max 256 giga , ne s’allume pas ecran en tres bon etat et vitre arriere aussi , peut etre bloque par un identifiant apple , a vendre pour pieces"
    ]
    for texte in cas_tests:
        print(f"  [{guess_state(texte):10}] {texte}")



