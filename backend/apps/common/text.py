def _mojibake_score(text):
    markers = ("Р", "С", "Ð", "Ñ", "вЂ", "в„", "в–", "в—", "Â")
    return sum(text.count(marker) for marker in markers)


def repair_mojibake(text):
    if not text:
        return text

    original_score = _mojibake_score(text)
    if original_score == 0:
        return text

    candidates = [text]
    for encoding in ("cp1251", "latin-1"):
        try:
            candidates.append(text.encode(encoding).decode("utf-8"))
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue

    return min(candidates, key=_mojibake_score)
