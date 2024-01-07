def is_contain_keyword(text: str, keywords: list):
    for keyword in keywords:
        compare_keyword = keyword.lower().strip()
        if compare_keyword in text.lower():
            return True

    return False
