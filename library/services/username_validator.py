import re
import unicodedata
from typing import Optional

BLOCKED_CATEGORIES = {
    "Cc",  # control characters
    "Cf",  # format characters (zero-width tricks, bidi overrides, ...)
    "Cs",  # surrogate halves - never valid in real text
    "Co",  # private-use characters - not renderable across systems
    "Cn",  # unassigned code points
    "Zl",  # line separator
    "Zp",  # paragraph separator
    "Zs",  # space separator - no spaces, to keep usernames a single token
}

# Zero-width joiner (U+200D) and emoji variation selectors (U+FE0E/U+FE0F) are
# format characters too, but blocking them would break legitimate multi-part
# emoji sequences (e.g. family or flag emoji).
ALLOWED_FORMAT_CHARACTERS = {"‍", "︎", "️"}

# A literal slash would break the /users/<username> route.
BLOCKED_LITERAL_CHARACTERS = {"/"}


class UsernameValidator:
    """
    Validates usernames very permissively on character content - letters,
    digits, punctuation, and emoji from any language or script are all
    allowed - while blocking invisible/control characters and a couple of
    characters that would break routing or rendering, and enforcing sane
    length limits.
    """

    MIN_LENGTH = 3
    MAX_LENGTH = 24

    def normalize(self, username: str) -> str:
        """
        Normalize a username to a canonical Unicode form for storage and comparison.

        param username: The raw, user-submitted username.

        :return: The NFC-normalized, whitespace-trimmed username.
        """
        return unicodedata.normalize("NFC", username.strip())

    def validate(self, username: str) -> Optional[str]:
        """
        Check an already-normalized username against the length and character rules.

        param username: The normalized username to validate.

        :return: A translation key describing the problem, or None if the username is valid.
        """
        if len(username) < self.MIN_LENGTH:
            return "auth.error.username_too_short"
        if len(username) > self.MAX_LENGTH:
            return "auth.error.username_too_long"

        for character in username:
            if character in ALLOWED_FORMAT_CHARACTERS:
                continue
            if character in BLOCKED_LITERAL_CHARACTERS:
                return "auth.error.username_invalid_characters"
            if unicodedata.category(character) in BLOCKED_CATEGORIES:
                return "auth.error.username_invalid_characters"

        return None

    def derive_from_display_name(self, display_name: str, fallback: str) -> str:
        """
        Turn a free-form display name (e.g. a Google account's real name) into
        a valid username candidate, falling back to another string if the
        display name can't be turned into anything valid.

        param display_name: The free-form name to derive a username from.
        param fallback: A string to fall back to if the display name yields nothing valid.

        :return: A username that passes `validate()`.
        """
        candidate = re.sub(r"\s+", "_", self.normalize(display_name or "")).strip("_")
        candidate = candidate[: self.MAX_LENGTH]
        if len(candidate) >= self.MIN_LENGTH and self.validate(candidate) is None:
            return candidate

        candidate = re.sub(r"\s+", "_", self.normalize(fallback)).strip("_")[: self.MAX_LENGTH]
        if len(candidate) >= self.MIN_LENGTH and self.validate(candidate) is None:
            return candidate

        return f"player{abs(hash(fallback)) % 100000}"
