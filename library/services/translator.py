from typing import Optional

from flask import g

from library.i18n.translations import DEFAULT_LOCALE, STRINGS, SUPPORTED_LOCALES


class Translator:
    """Resolves the active locale and looks up UI strings from the central translation table."""

    def __init__(self, strings: dict, default_locale: str, supported_locales: list) -> None:
        self.strings = strings
        self.default_locale = default_locale
        self.supported_locales = supported_locales

    def resolve_locale(self, accept_languages) -> str:
        """
        Pick the best supported locale for a request based on its Accept-Language header.

        param accept_languages: The `werkzeug.datastructures.LanguageAccept` from `request.accept_languages`.

        :return: A locale code from `supported_locales`, falling back to the default.
        """
        return accept_languages.best_match(self.supported_locales) or self.default_locale

    def translate(self, locale: str, key: str, **kwargs) -> str:
        """
        Look up a string for the given locale, falling back to the default locale, then the key itself.

        param locale: The locale to translate into.
        param key: The dotted translation key.
        param kwargs: Optional named values to interpolate into the string.

        :return: The translated (and interpolated) string.
        """
        entry = self.strings.get(key, {})
        text = entry.get(locale) or entry.get(self.default_locale) or key
        return text.format(**kwargs) if kwargs else text


translator = Translator(STRINGS, DEFAULT_LOCALE, SUPPORTED_LOCALES)


def t(key: str, **kwargs) -> str:
    """
    Translate a key into the current request's locale (module-level convenience for templates and views).

    param key: The dotted translation key.
    param kwargs: Optional named values to interpolate into the string.

    :return: The translated (and interpolated) string.
    """
    locale: Optional[str] = getattr(g, "locale", None)
    return translator.translate(locale or translator.default_locale, key, **kwargs)
