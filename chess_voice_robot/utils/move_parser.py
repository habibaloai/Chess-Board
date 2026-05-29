"""
Convert natural speech text into UCI move strings (e.g. e2e4, e7e8q).

Supported examples:
  - "e two e four"
  - "move e2 to e4"
  - "e2 e4"
  - "knight f3"  (when unambiguous — best-effort)
"""

import re
from typing import Optional

# Spoken numbers → digit
WORD_TO_DIGIT = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8",
    "won": "1", "to": "", "too": "2", "for": "4", "fore": "4",
}

# Promotion piece names → UCI suffix letter
PROMOTION_MAP = {
    "queen": "q", "rook": "r", "bishop": "b", "knight": "n", "horse": "n",
    "q": "q", "r": "r", "b": "b", "n": "n",
}

# Words stripped before parsing
FILLER_WORDS = {
    "move", "moves", "from", "to", "the", "a", "an", "please",
    "piece", "play", "plays", "pawn", "takes", "take", "capture",
    "castle", "castles", "king", "side", "queenside", "kingside",
    "promote", "promotion", "promotes", "into", "as",
}


def _normalize(text: str) -> str:
    """Lowercase, remove punctuation, expand spoken numbers."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = text.split()
    expanded = []
    for token in tokens:
        if token in FILLER_WORDS:
            continue
        if token in WORD_TO_DIGIT:
            digit = WORD_TO_DIGIT[token]
            if digit:
                expanded.append(digit)
        else:
            expanded.append(token)
    return " ".join(expanded)


def _extract_promotion(tokens: list[str]) -> tuple[list[str], Optional[str]]:
    """Pull promotion suffix from token list if present."""
    promo = None
    remaining = []
    for t in tokens:
        if t in PROMOTION_MAP:
            promo = PROMOTION_MAP[t]
        else:
            remaining.append(t)
    return remaining, promo


def parse_speech_to_uci(text: str) -> Optional[str]:
    """
    Parse spoken move text into UCI format (e.g. e2e4, e7e8q).
    Returns None if the text cannot be parsed.
    """
    if not text or not text.strip():
        return None

    normalized = _normalize(text)
    tokens = normalized.split()
    tokens, promo_suffix = _extract_promotion(tokens)
    joined = "".join(tokens)

    # Direct UCI glued: e2e4 or e7e8q
    m = re.match(r"^([a-h][1-8])([a-h][1-8])([qrbn])?$", joined)
    if m:
        uci = m.group(1) + m.group(2)
        suffix = m.group(3) or promo_suffix
        if suffix:
            uci += suffix
        return uci

    # Spaced or separate tokens: e 2 e 4  OR  e2 e4
    square_pattern = re.compile(r"^([a-h])([1-8])$")
    squares = []

    for token in tokens:
        # e2 style
        m2 = re.match(r"^([a-h])([1-8])$", token)
        if m2:
            squares.append(m2.group(1) + m2.group(2))
            continue
        # e 2 as separate tokens — collect file/rank chars
        if re.match(r"^[a-h]$", token):
            squares.append(token)  # partial; handled below
        elif re.match(r"^[1-8]$", token):
            if squares and len(squares[-1]) == 1:
                squares[-1] = squares[-1] + token
            else:
                squares.append(token)

    # Re-scan joined string for four-char square pairs
    clean = re.sub(r"\s+", "", normalized)
    m = re.findall(r"[a-h][1-8]", clean)
    if len(m) >= 2:
        uci = m[0] + m[1]
        if promo_suffix:
            uci += promo_suffix
        return uci

    if len(squares) >= 2:
        # squares may be ['e2','e4'] or built from parts
        s0, s1 = squares[0], squares[1]
        if len(s0) == 1 and len(s1) == 2:
            pass  # incomplete
        elif len(s0) == 2 and len(s1) == 2:
            uci = s0 + s1
            if promo_suffix:
                uci += promo_suffix
            return uci

    # Castling spoken informally
    if "o-o-o" in text or "queenside" in text.lower() or "long" in tokens:
        return None  # caller must use legal move context; skip for now
    if "o-o" in text or "kingside" in text.lower() or "short" in tokens:
        return None

    return None
