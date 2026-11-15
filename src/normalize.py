"""
normalize.py - shared text cleaner for all languages.

CONTRACT FILE. Owner: M2.
Do NOT edit without telling the whole team. Every number in our
results table depends on this file being identical for all members.

Verify your copy matches:  python src/normalize.py --checksum

v3.0.0 changes from v2.0.0 (manual):
  * strips bracketed annotation tags ([noise], <unk>, {...})
  * maps the Odia/Bengali/Kannada/Devanagari danda variants consistently
  * self-test checks that vowel signs (matras) survive - the bug that
    Whisper's own BasicTextNormalizer has (see evaluate.py)
"""
import re
import sys
import hashlib
import unicodedata

CONTRACT_VERSION = "3.0.0"

# ---------------------------------------------------------------------
# Punctuation set.
#
# Built from explicit \uXXXX escapes on purpose. An earlier version used
# literal curly-quote characters inside a raw triple-quoted string; that
# was ambiguous on screen and did not survive copy-paste. Never put a
# literal quote character in this list.
# ---------------------------------------------------------------------
PUNCT_CHARS = (
    # ASCII punctuation
    "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
    # Devanagari danda and double danda (also used in Odia/Marathi text)
    "।॥"
    # Arabic-Indic comma, semicolon, question mark
    "،؛؟"
    # Hyphens and dashes: hyphen, non-breaking hyphen, figure/en/em/horizontal bar
    "‐‑‒–—―"
    # Single quotation marks: left, right, low-9, reversed-9
    "‘’‚‛"
    # Double quotation marks: left, right, low-9, reversed-9
    "“”„‟"
    # Ellipsis, bullet, guillemets
    "…•«»"
)

PUNCT_RE = re.compile("[" + re.escape(PUNCT_CHARS) + "]")

# Annotation tags used by Indian speech corpora: [noise], <unk>, {laugh}
TAG_RE = re.compile(r"\[[^\]]*\]|<[^>]*>|\{[^}]*\}")

# Invisible joiners that Indic keyboards insert. Visually nothing,
# but they break string comparison.
ZERO_WIDTH_RE = re.compile("[​‌‍﻿]")

WHITESPACE_RE = re.compile(r"\s+")

# Indic digits -> western digits
DIGIT_MAP = {}
for _base in (0x0966,   # Devanagari  (Hindi, Marathi)
              0x09E6,   # Bengali
              0x0B66,   # Odia
              0x0CE6):  # Kannada
    for _i in range(10):
        DIGIT_MAP[chr(_base + _i)] = str(_i)


def normalize_text(text, remove_punct=True):
    """Clean one line of text so two systems can be compared fairly."""
    if text is None:
        return ""

    # 1. Unicode NFC normalisation.
    #    Indic scripts can encode the same visible letter as one character
    #    or as a base plus a combining mark. Without this, identical text
    #    scores as different.
    text = unicodedata.normalize("NFC", text)

    # 2. Annotation tags are never spoken words
    text = TAG_RE.sub(" ", text)

    # 3. Indic digits -> western digits
    text = "".join(DIGIT_MAP.get(ch, ch) for ch in text)

    # 4. Lowercase (affects Latin only; harmless for Indic scripts)
    text = text.lower()

    # 5. Punctuation -> space
    if remove_punct:
        text = PUNCT_RE.sub(" ", text)

    # 6. Strip zero-width characters
    text = ZERO_WIDTH_RE.sub("", text)

    # 7. Collapse whitespace
    text = WHITESPACE_RE.sub(" ", text).strip()

    return text


def file_checksum():
    """SHA-256 of this file, so all members can verify identical copies."""
    with open(__file__, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def _self_test():
    """Fails loudly if the file is corrupt or a rule regresses."""
    cases = [
        ("नमस्ते, आप कैसे हैं?", "hindi"),
        ("ମୁଁ ଭଲ ଅଛି ।",                                     "odia"),
        ("ನಾನು ಚೆನ್ನಾಗಿದ್ದೇನೆ!", "kannada"),
        ("मी ठीक आहे.",                                            "marathi"),
        ("Test “quoted” — and ‘this’…",                                      "curly punctuation"),
        ("२०२४ ೦೧೨",                                                    "indic digits"),
    ]
    for raw, label in cases:
        out = normalize_text(raw)
        assert PUNCT_RE.search(out) is None, f"punct survived in {label}: {out!r}"
        assert "  " not in out, f"double space in {label}: {out!r}"
    # digits must convert
    assert normalize_text("२०२४") == "2024"
    # NFC must make these equal
    a = normalize_text("क़")          # ka + nukta (decomposed)
    b = normalize_text("क़")                # qa (precomposed)
    assert a == b, "NFC normalisation failed"
    # vowel signs and virama must survive: word count is unchanged
    hindi = "नमस्ते आप"
    assert normalize_text(hindi).split() == hindi.split(), "matras were split off"
    # annotation tags are removed
    assert normalize_text("[noise] आप <unk>") == "आप"
    return True


if __name__ == "__main__":
    if "--checksum" in sys.argv:
        print("CONTRACT_VERSION:", CONTRACT_VERSION)
        print("SHA256[:16]     :", file_checksum())
        sys.exit(0)

    _self_test()
    print("Self-test passed. CONTRACT_VERSION =", CONTRACT_VERSION)
    print("Checksum:", file_checksum())
