"""ISO 3166-1 alpha-2 country codes with Hungarian/English names and a derived flag emoji."""


def flag_emoji(country_code: str) -> str:
    """
    Build the flag emoji for an ISO 3166-1 alpha-2 country code.

    Each letter maps to a Unicode "regional indicator symbol"; a pair of
    them is what renders as a flag in modern fonts (e.g. "HU" -> the two
    symbols that render as the Hungarian flag).

    param country_code: A two-letter ISO 3166-1 alpha-2 code.

    :return: The corresponding flag emoji.
    """
    return "".join(chr(0x1F1E6 + ord(letter) - ord("A")) for letter in country_code.upper())


_COUNTRY_DATA = [
    ("HU", "Magyarország", "Hungary"),
    ("AT", "Ausztria", "Austria"),
    ("DE", "Németország", "Germany"),
    ("SK", "Szlovákia", "Slovakia"),
    ("RO", "Románia", "Romania"),
    ("HR", "Horvátország", "Croatia"),
    ("SI", "Szlovénia", "Slovenia"),
    ("RS", "Szerbia", "Serbia"),
    ("UA", "Ukrajna", "Ukraine"),
    ("PL", "Lengyelország", "Poland"),
    ("CZ", "Csehország", "Czech Republic"),
    ("IT", "Olaszország", "Italy"),
    ("FR", "Franciaország", "France"),
    ("ES", "Spanyolország", "Spain"),
    ("PT", "Portugália", "Portugal"),
    ("GB", "Egyesült Királyság", "United Kingdom"),
    ("IE", "Írország", "Ireland"),
    ("NL", "Hollandia", "Netherlands"),
    ("BE", "Belgium", "Belgium"),
    ("LU", "Luxemburg", "Luxembourg"),
    ("CH", "Svájc", "Switzerland"),
    ("DK", "Dánia", "Denmark"),
    ("SE", "Svédország", "Sweden"),
    ("NO", "Norvégia", "Norway"),
    ("FI", "Finnország", "Finland"),
    ("IS", "Izland", "Iceland"),
    ("EE", "Észtország", "Estonia"),
    ("LV", "Lettország", "Latvia"),
    ("LT", "Litvánia", "Lithuania"),
    ("BY", "Fehéroroszország", "Belarus"),
    ("MD", "Moldova", "Moldova"),
    ("BG", "Bulgária", "Bulgaria"),
    ("GR", "Görögország", "Greece"),
    ("AL", "Albánia", "Albania"),
    ("MK", "Észak-Macedónia", "North Macedonia"),
    ("BA", "Bosznia-Hercegovina", "Bosnia and Herzegovina"),
    ("ME", "Montenegró", "Montenegro"),
    ("XK", "Koszovó", "Kosovo"),
    ("CY", "Ciprus", "Cyprus"),
    ("MT", "Málta", "Malta"),
    ("RU", "Oroszország", "Russia"),
    ("TR", "Törökország", "Turkey"),
    ("GE", "Grúzia", "Georgia"),
    ("AM", "Örményország", "Armenia"),
    ("AZ", "Azerbajdzsán", "Azerbaijan"),
    ("US", "Amerikai Egyesült Államok", "United States"),
    ("CA", "Kanada", "Canada"),
    ("MX", "Mexikó", "Mexico"),
    ("BR", "Brazília", "Brazil"),
    ("AR", "Argentína", "Argentina"),
    ("CL", "Chile", "Chile"),
    ("CO", "Kolumbia", "Colombia"),
    ("PE", "Peru", "Peru"),
    ("VE", "Venezuela", "Venezuela"),
    ("UY", "Uruguay", "Uruguay"),
    ("CN", "Kína", "China"),
    ("JP", "Japán", "Japan"),
    ("KR", "Dél-Korea", "South Korea"),
    ("KP", "Észak-Korea", "North Korea"),
    ("IN", "India", "India"),
    ("PK", "Pakisztán", "Pakistan"),
    ("BD", "Banglades", "Bangladesh"),
    ("ID", "Indonézia", "Indonesia"),
    ("MY", "Malajzia", "Malaysia"),
    ("TH", "Thaiföld", "Thailand"),
    ("VN", "Vietnám", "Vietnam"),
    ("PH", "Fülöp-szigetek", "Philippines"),
    ("SG", "Szingapúr", "Singapore"),
    ("IL", "Izrael", "Israel"),
    ("SA", "Szaúd-Arábia", "Saudi Arabia"),
    ("AE", "Egyesült Arab Emírségek", "United Arab Emirates"),
    ("IR", "Irán", "Iran"),
    ("IQ", "Irak", "Iraq"),
    ("EG", "Egyiptom", "Egypt"),
    ("ZA", "Dél-afrikai Köztársaság", "South Africa"),
    ("NG", "Nigéria", "Nigeria"),
    ("KE", "Kenya", "Kenya"),
    ("MA", "Marokkó", "Morocco"),
    ("DZ", "Algéria", "Algeria"),
    ("TN", "Tunézia", "Tunisia"),
    ("ET", "Etiópia", "Ethiopia"),
    ("GH", "Ghána", "Ghana"),
    ("AU", "Ausztrália", "Australia"),
    ("NZ", "Új-Zéland", "New Zealand"),
]

COUNTRIES = [
    {"code": code, "hu": name_hu, "en": name_en, "flag": flag_emoji(code)}
    for code, name_hu, name_en in sorted(_COUNTRY_DATA, key=lambda row: row[1])
]

COUNTRY_BY_CODE = {country["code"]: country for country in COUNTRIES}
