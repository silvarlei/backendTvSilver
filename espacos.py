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
    "\U00002300-\U000023FF"  # Misc Technical, Arrows like U+23E9 (⏩)
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE
)

_VARIATION_SELECTOR = re.compile(r"[\uFE0E\uFE0F]")
_CONTROL_CHARS = re.compile(r"[\u0000-\u001F\u007F-\u009F]")

# remove símbolos/pontuações excessivas no começo/fim (ex: >>>, ⏩⏩, ---, ___)
_EDGE_SYMBOLS = re.compile(r"^[\W_]+|[\W_]+$")

_WHITESPACE_RE = re.compile(r"\s+")

def _remove_diacritics(s: str) -> str:
    """
    Remove acentos/diacríticos usando NFKD e filtrando marcas combinantes.
    """
    nkfd = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in nkfd if not unicodedata.combining(ch))

def _clean_single(text: object, remove_non_ascii: bool = False) -> str:
    """
    Limpa uma única string:
    - remove emojis e símbolos definidos
    - remove variation selectors e caracteres de controle
    - remove símbolos excessivos nas bordas
    - normaliza múltiplos espaços para um único espaço
    - remove acentos (diacríticos)
    - opcional: remove todos caracteres não-ASCII se remove_non_ascii=True
    """
    if text is None:
        return ""
    s = str(text)

    # normaliza composição unicode
    s = unicodedata.normalize("NFKC", s)

    # remove emojis, setas e símbolos definidos nas faixas
    s = _EMOJI_SYMBOL_PATTERN.sub("", s)

    # remove variation selectors
    s = _VARIATION_SELECTOR.sub("", s)

    # remove control/invisible chars
    s = _CONTROL_CHARS.sub("", s)

    # remove símbolos/pontuações excessivas nas bordas
    s = _EDGE_SYMBOLS.sub("", s)

    # normaliza espaços: tabs/newlines/múltiplos -> único espaço
    s = _WHITESPACE_RE.sub("", s)

    s = s.replace("–", "").replace("—", "").replace("―", "").replace("-","").replace("-","")
    # trim
    s = s.strip()

    if not s:
        return ""

    # remove acentos/diacríticos
    s = _remove_diacritics(s)

    # opcional: remover caracteres não ASCII (descomente se quiser)
    if remove_non_ascii:
        s = s.encode("ascii", errors="ignore").decode("ascii")

    return s

def limpar_emoticons_e_espacos(
    value: Union[str, List[object], None],
    remove_non_ascii: bool = False
) -> Union[str, List[str]]:
    """
    Limpa texto aceitando str, list ou None.

    - Se receber str -> retorna str limpa.
    - Se receber list -> retorna lista de strings limpas (mantém ordem).
    - Se receber None -> retorna "".
    - Parâmetro remove_non_ascii: se True remove todos caracteres não-ASCII no resultado final.
    """
    if value is None:
        return ""
    if isinstance(value, list):
        return [_clean_single(item, remove_non_ascii=remove_non_ascii) for item in value]
    return _clean_single(value, remove_non_ascii=remove_non_ascii)

# Exemplos:
# limpar_emoticons_e_espacos("⏩FILMESESÉRIES") -> "FILMESESERIES"
# limpar_emoticons_e_espacos("  Olá\tMundo! ⏩👍  ") -> "Ola Mundo!"
# limpar_emoticons_e_espacos([" ⏩HBO", "Coração ❤️"]) -> ["HBO", "Coracao"]
