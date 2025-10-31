import re
import unicodedata
from typing import Union, List

# Faixas ampliadas para emojis, pictogramas, dingbats, setas e símbolos diversos
_EMOJI_SYMBOL_PATTERN = re.compile(
    "[" 
    "\U0001F300-\U0001F5FF"  # pictogramas
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F680-\U0001F6FF"  # transporte e mapas
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U00002700-\U000027BF"  # Dingbats
    "\U00002300-\U000023FF"  # Misc Technical, Arrows like U+23E9
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE
)

_VARIATION_SELECTOR = re.compile(r"[\uFE0E\uFE0F]")
_CONTROL_CHARS = re.compile(r"[\u0000-\u001F\u007F-\u009F]")

# remove caracteres de pontuação/delimitadores repetidos no começo/fim (ex: >>>, ⏩⏩, ---)
_EDGE_SYMBOLS = re.compile(r"^[\W_]+|[\W_]+$")

def _clean_single(text: str) -> str:
    if text is None:
        return ""
    s = str(text)
    s = unicodedata.normalize("NFKC", s)
    # remove emojis e símbolos das faixas definidas
    s = _EMOJI_SYMBOL_PATTERN.sub("", s)
    # remove variation selectors
    s = _VARIATION_SELECTOR.sub("", s)
    # remove control/invisible chars
    s = _CONTROL_CHARS.sub("", s)
    # remove símbolos/pontuações excessivas nas bordas
    s = _EDGE_SYMBOLS.sub("", s)
    # substitui qualquer whitespace por um espaço simples
    s = re.sub(r"\s+", "", s)
    # trim final
    s = s.strip()
    return s

def limpar_emoticons_e_espacos(value: Union[str, List[object], None]) -> Union[str, List[str]]:
    """
    Remove emojis, setas/dingbats e normaliza espaços.
    - str -> str limpa
    - list -> lista de strings limpas
    - None -> ""
    """
    if value is None:
        return ""
    if isinstance(value, list):
        return [_clean_single(item) for item in value]
    return _clean_single(value)
