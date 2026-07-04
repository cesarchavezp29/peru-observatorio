"""Canonical Peru department identity + a normalizer that maps every keying
convention found in the datasets (2-digit code, ccdd int, ASCII name, accented
name) onto one clean ASCII name that also labels the GeoJSON features.

25 departments, Callao (07) kept SEPARATE — the majority convention (ENDES,
panel, indicadores). Tables that fold Callao into Lima (EPEN) simply leave
Callao unshaded on the map.
"""
import unicodedata

# code -> canonical ASCII name
CODE2NAME = {
    "01": "Amazonas", "02": "Ancash", "03": "Apurimac", "04": "Arequipa",
    "05": "Ayacucho", "06": "Cajamarca", "07": "Callao", "08": "Cusco",
    "09": "Huancavelica", "10": "Huanuco", "11": "Ica", "12": "Junin",
    "13": "La Libertad", "14": "Lambayeque", "15": "Lima", "16": "Loreto",
    "17": "Madre de Dios", "18": "Moquegua", "19": "Pasco", "20": "Piura",
    "21": "Puno", "22": "San Martin", "23": "Tacna", "24": "Tumbes",
    "25": "Ucayali",
}
NAMES = list(CODE2NAME.values())


def _strip(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.upper().split())


# normalized name -> canonical, incl. known variants
_NORM2NAME = {_strip(v): v for v in CODE2NAME.values()}
_NORM2NAME.update({
    "PROV CONST DEL CALLAO": "Callao",
    "PROVINCIA CONSTITUCIONAL DEL CALLAO": "Callao",
    "LIMA METROPOLITANA": "Lima",
    "LIMA PROVINCIAS": "Lima",
    "LIMA REGION": "Lima",
})


def canonical(value) -> str | None:
    """Map any department identifier to its canonical ASCII name, or None."""
    if value is None:
        return None
    # numeric / zero-padded code
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        code = f"{int(value):02d}"
        return CODE2NAME.get(code)
    s = str(value).strip()
    if s.isdigit():
        return CODE2NAME.get(f"{int(s):02d}")
    return _NORM2NAME.get(_strip(s))


# dataset column names that plausibly hold a department identifier
DEPT_COLS = ["dep", "ccdd", "departamento", "dpto", "depto", "region", "ubigeo_dep"]


def detect_dept_col(columns) -> str | None:
    low = {c.lower(): c for c in columns}
    for cand in DEPT_COLS:
        if cand in low:
            return low[cand]
    return None
