import re
from typing import Dict, Any, List, Tuple

def parse_search_query(query: str) -> Dict[str, Any]:
    """
    Parses an advanced search query string into a structured dictionary.
    Supports:
      - AND (default, space-separated terms)
      - OR (`OR` or `|`)
      - Phrase search with double quotes
      - Exclusion (NOT, -, !)
      - Property search (prop:value, e.g. color:red)
    Returns a dict with:
      {
        "and": [ ... terms/phrases ... ],
        "or": [ ... terms/phrases ... ],
        "not": [ ... terms/phrases ... ],
        "properties": { key: value, ... }
      }
    """
    # normalize spacing
    query = query.strip()
    # regex patterns
    phrase_pat = r'"([^"]+)"'
    prop_pat = r'(\b\w+):("[^"]+"|\S+)'
    or_split_pat = re.compile(r'\s+\bOR\b\s+|\s+\|\s+', re.IGNORECASE)

    # 1. Extract phrases
    phrases = re.findall(phrase_pat, query)
    query_no_phrases = re.sub(phrase_pat, '', query)

    # 2. Extract properties (prop:value)
    properties = {}
    for match in re.finditer(prop_pat, query_no_phrases):
        k, v = match.group(1), match.group(2)
        properties[k.lower()] = v.strip('"')
    query_no_phrases_props = re.sub(prop_pat, '', query_no_phrases)

    # 3. Tokenize using OR
    or_sections = or_split_pat.split(query_no_phrases_props)
    or_terms = []
    and_terms = []
    not_terms = []

    for section in or_sections:
        tokens = section.split()
        for tok in tokens:
            if not tok:
                continue
            # Exclusion: -term, !term, NOT term
            if tok.startswith('-'):
                not_terms.append(tok[1:])
            elif tok.startswith('!'):
                not_terms.append(tok[1:])
            elif tok.upper() == 'NOT':
                continue  # handled below
            else:
                and_terms.append(tok)

    # Also handle NOT keyword exclusion (e.g. "foo NOT bar")
    tokens = query_no_phrases_props.split()
    for i, tok in enumerate(tokens):
        if tok.upper() == 'NOT' and i + 1 < len(tokens):
            not_terms.append(tokens[i + 1])

    # Add quoted phrases to AND (unless specifically excluded)
    and_terms.extend(phrases)

    # If original query contained OR, collect all tokens in or_sections (except not-terms)
    if len(or_sections) > 1:
        for section in or_sections:
            tokens = section.split()
            for tok in tokens:
                t = tok.lstrip('-!')
                if tok.startswith('-') or tok.startswith('!') or tok.upper() == 'NOT':
                    continue
                # Skip property tokens
                if ':' in t:
                    continue
                or_terms.append(t)
        # remove duplicates and remove overlap with not_terms
        or_terms = [t for t in set(or_terms) if t not in not_terms]

    # Remove not_terms from and_terms
    and_terms = [t for t in and_terms if t not in not_terms and ':' not in t]

    # Remove property tokens from and_terms and or_terms
    and_terms = [t for t in and_terms if ':' not in t]
    or_terms = [t for t in or_terms if ':' not in t and t not in not_terms]

    # Remove empty
    and_terms = [t for t in and_terms if t]
    or_terms = [t for t in or_terms if t]
    not_terms = [t for t in not_terms if t]

    return {
        "and": and_terms,
        "or": or_terms,
        "not": not_terms,
        "properties": properties
    }