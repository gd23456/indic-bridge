"""
langs.py - one table of language codes, so no script hard-codes them.

Different datasets use different codes for the same language. Getting
these wrong is the most common early mistake, so everything reads here.
"""

LANGS = {
    #            FLEURS     Whisper token  Unicode block of the script
    "hindi":   {"fleurs": "hi_in", "whisper": "hindi",   "script": (0x0900, 0x097F), "family": "Indo-Aryan"},
    "marathi": {"fleurs": "mr_in", "whisper": "marathi", "script": (0x0900, 0x097F), "family": "Indo-Aryan"},
    "kannada": {"fleurs": "kn_in", "whisper": "kannada", "script": (0x0C80, 0x0CFF), "family": "Dravidian"},
    # Whisper has no <|or|> token. The token used is chosen per run.
    "odia":    {"fleurs": "or_in", "whisper": None,      "script": (0x0B00, 0x0B7F), "family": "Indo-Aryan"},
    "english": {"fleurs": "en_us", "whisper": "english", "script": None,             "family": "Germanic"},
}

# Borrowed tokens for Odia, in order of genealogical closeness
# (Eastern Indo-Aryan first). RQ2 compares all three.
ODIA_TOKENS = ["bengali", "assamese", "hindi"]

# Fixed in advance for every Odia run in the main grid: Odia's closest
# relative, and a token neither pivot is trained with. Choosing <|hi|> would
# hand the Hindi pivot a decoder prompt it already learned and the English
# pivot never saw. The other two tokens are compared in the T-odia runs.
ODIA_MAIN_TOKEN = "bengali"

TARGETS = ["marathi", "kannada", "odia"]

# Whisper tokens per second of speech, highest rate seen in FLEURS test
# references (measured 2 Nov). Odia needs ~3 tokens per letter, Hindi ~1.3.
# Decoding stops at 1.5x this rate, so a looping model cannot run to
# 440 tokens on every clip, and no real transcript is ever cut short.
MAX_TOKENS_PER_SEC = {"hindi": 19.0, "marathi": 18.8, "kannada": 26.0, "odia": 43.7,
                      "english": 19.0}
