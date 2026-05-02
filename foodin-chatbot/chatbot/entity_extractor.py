# chatbot/entity_extractor.py
"""
Hybrid entity extractor:
- Uses spaCy (if installed) for noun chunks and POS
- Falls back to regex-based extraction
Provides:
- extract_order_id(text)
- extract_quantity(text)
- extract_items(text, menu=None) -> list of {"name":..., "qty":...}
- extract_booking(text) -> {"people":int or None, "time": "HH:MM" or None, "date": "YYYY-MM-DD" or None, "preference":str}
- normalize_number_word(word) -> int or None
- fuzzy_match_item(name, menu) -> best match
"""

import re
from datetime import datetime, date, time, timedelta
from difflib import get_close_matches

# try spaCy
try:
    import spacy
    _nlp = spacy.load("en_core_web_sm")# en_core_web_sm is a pre-trained model that is good for English that have been trained on a large corpus like Wikipedia 
    # we can load other models like en_core_web_md or en_core_web_lg because they are trained on larger corpora and they are faster and for current senerio this is fast
    # we can use en_core_web_md but is heavier and less fast then sm bcz it  is more accurate and vector dimensions based on word embeddings and is trained on large corpora
    #if you want to replace just put sm into md  and go into the terminal and paste the line : "python -m spacy download en_core_web_md"
except Exception:
    _nlp = None

_NUM_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
}

_time_regex = re.compile(r"\b(at|@)\s*(\d{1,2})([:.]?(\d{2}))?\s*(am|pm)?\b", flags=re.I)  #re.I: ignore case means case insensitive am or AM or Am or aM etc they didnt matter 
_people_regex = re.compile(r"\b(for|table for|reserve for)\s+(\d{1,2})\b", flags=re.I) #re.I bhi likh sakte thai lekin user ko smjhane ke liye flag use karte hai this is like (quantity = 2)
_date_regex = re.compile(r"\b(on|for)\s+([A-Za-z0-9\-/]+)\b", flags=re.I)  # simple fallback
_qty_item_regex = re.compile(r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b\s*(x|pcs|pieces|of)?\s*([A-Za-z &]+?)\b(?:,| and |$|\.)", flags=re.I)

def normalize_number_word(w):
    if w is None:
        return None
    try:
        return int(w)
    except:
        return _NUM_WORDS.get(w.lower())

def extract_order_id(text):
    if not text:
        return None
    m = re.search(r"\b(\d{3,8})\b", text)
    if m:
        try:
            return int(m.group(1))
        except:
            return None
    return None

def extract_quantity(text):
    if not text:
        return None
    m = re.search(r"\b(\d+)\b", text)
    if m:
        try:
            return int(m.group(1))
        except:
            pass
    for word, val in _NUM_WORDS.items():
        if re.search(r"\b" + re.escape(word) + r"\b", text, flags=re.I):
            return val
    return None

def fuzzy_match_item(name, menu=None):
    """
    If menu (list of item names) provided, return best match via difflib.
    Else return normalized name.
    """
    name = name.strip().lower()
    if not menu:
        return name
    choices = [m.lower() for m in menu]
    matches = get_close_matches(name, choices, n=1, cutoff=0.6)
    return matches[0] if matches else name

def _regex_extract_items(text):
    items = []
    # find patterns like "2 x pizza", "two pizzas", "1 burger"
    for m in _qty_item_regex.finditer(text + " "):
        qty_raw = m.group(1)
        qty = normalize_number_word(qty_raw)
        item_raw = m.group(3)
        name = item_raw.strip()
        items.append({"name": name, "qty": qty or 1})
    # fallback: find single nouns (words) after common verbs
    if not items:
        # simple fallback: split by 'and' / ',' and look for nouns
        parts = re.split(r",| and ", text)
        for p in parts:
            p = p.strip()
            # if contains a number
            q = extract_quantity(p)
            # remove number words
            p2 = re.sub(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\b", "", p, flags=re.I).strip()
            # remove verbs
            p2 = re.sub(r"\b(order|add|want|take|get|i would like|i'll take|i want)\b", "", p2, flags=re.I).strip()
            if p2:
                items.append({"name": p2, "qty": q or 1})
    return items

def extract_items(text, menu=None):
    """
    Returns list of {"name":..., "qty":...}
    menu (optional): list of valid menu item names for fuzzy matching
    """
    if not text:
        return []
    # if spaCy available, try noun chunk approach to extract items and numbers
    if _nlp:
        doc = _nlp(text)
        items = []
        # first capture explicit NUM + NOUN patterns
        for ent in doc.ents:
            # spaCy NUM or CARDINAL ent types
            if ent.label_ in ("CARDINAL", "QUANTITY", "NUMBER"):
                # try to find noun right after
                start = ent.end
                if start < len(doc):
                    nxt = doc[start:start+4]  # small window
                    # find noun chunk or noun token
                    noun = None
                    for token in nxt:
                        if token.pos_ in ("NOUN", "PROPN"):
                            noun = token.text
                            break
                    if noun:
                        qty = normalize_number_word(ent.text)
                        items.append({"name": noun, "qty": qty or 1})
        # fallback noun chunks
        if not items:
            for chunk in doc.noun_chunks:
                txt = chunk.text.strip()
                # skip pronouns and generic words
                if len(txt.split()) <= 4 and not re.search(r"\b(table|order|time|people|book)\b", txt, flags=re.I):
                    # try to find preceding number token
                    qty = 1
                    # check token before chunk start
                    i = chunk.start
                    if i-1 >= 0 and doc[i-1].like_num:
                        try:
                            qty = int(doc[i-1].text)
                        except:
                            qty = normalize_number_word(doc[i-1].text) or 1
                    items.append({"name": txt, "qty": qty})
        # normalize names
        cleaned = []
        for it in items:
            nm = it["name"].lower()
            nm = re.sub(r"[^\w\s&-]", "", nm).strip()
            matched = fuzzy_match_item(nm, menu)
            cleaned.append({"name": matched, "qty": int(it.get("qty",1) or 1)})
        return cleaned

    # fallback non-spacy (regex)
    found = _regex_extract_items(text)
    # normalize names and fuzzy match with menu
    cleaned = []
    for it in found:
        nm = it["name"].lower()
        nm = re.sub(r"[^\w\s&-]", "", nm).strip()
        matched = fuzzy_match_item(nm, menu)
        cleaned.append({"name": matched, "qty": int(it.get("qty",1) or 1)})
    return cleaned

def extract_booking(text):
    """
    Extract booking info: people and time
    returns dict {"people":int or None, "time":"HH:MM" or None, "date":"YYYY-MM-DD" or None, "preference":str or None}
    """
    if not text:
        return {}
    people = None
    tm = None
    dt = None
    preference = None

    # people
    m = _people_regex.search(text)
    if m:
        try:
            people = int(m.group(2))
        except:
            people = normalize_number_word(m.group(2))

    # time
    m = _time_regex.search(text)
    if m:
        hh = int(m.group(2))
        mm = 0
        if m.group(4):
            mm = int(m.group(4))
        ampm = (m.group(5) or "").lower()
        if ampm == "pm" and hh < 12:
            hh += 12
        if ampm == "am" and hh == 12:
            hh = 0
        tm = f"{hh:02d}:{mm:02d}"

    # date (simple parse for today/tomorrow or explicit date dd-mm or words)
    if re.search(r"\btomorrow\b", text, flags=re.I):
        dt = (date.today() + timedelta(days=1)).isoformat()
    elif re.search(r"\btoday\b|\btonight\b", text, flags=re.I):
        dt = date.today().isoformat()

    # explicit ISO date like 2023-12-31
    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if m:
        dt = m.group(1)
    
    pref_m = re.search(r"\b(window|near window|outdoor|inside|indoor|corner)\b", text, flags=re.I)
    if pref_m:
        preference = pref_m.group(1).lower()

    return {"people": people, "time": tm, "date": dt, "preference": preference}
