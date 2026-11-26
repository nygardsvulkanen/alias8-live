# Alias8 – the pages (what the knobs do on each bank). No Live imports, so it can be tested on its own.

SENDS, PAN, MACROS = "sends", "pan", "macros"
PAGE_NAMES = (SENDS, PAN, MACROS)
DEFAULT_ORDER = (SENDS, MACROS)
MAX_BANKS = 15

TITLES = {SENDS: "sends", PAN: "pan / send", MACROS: "rack macros"}


def page_order(order):
    """PAGE_ORDER from settings.py, cleaned up: known page names only (any case), at most 15.
    Returns (pages, problems): problems lists the names that were left out."""
    if isinstance(order, str):
        order = (order,)
    pages, problems = [], []
    for name in order or ():
        key = str(name).strip().lower()
        if key in PAGE_NAMES and len(pages) < MAX_BANKS:
            pages.append(key)
        else:
            problems.append(name)
    if not pages:
        return DEFAULT_ORDER, problems
    return tuple(pages), problems
