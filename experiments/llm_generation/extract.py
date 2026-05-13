from __future__ import annotations

import re

FENCED_BLOCK_RE = re.compile(r"```(?:pdsl|polyforge|text)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_pdsl_blocks(text: str) -> list[str]:
    fenced = [_clean_block(match.group(1)) for match in FENCED_BLOCK_RE.finditer(text)]
    pdsl_fenced = [block for block in fenced if block.startswith("polymer ")]
    if pdsl_fenced:
        return pdsl_fenced

    return [_clean_block(block) for block in _extract_raw_polymer_blocks(text)]


def _extract_raw_polymer_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    search_start = 0
    while True:
        match = re.search(r"\bpolymer\s+\w+\s*\{", text[search_start:])
        if match is None:
            return blocks
        start = search_start + match.start()
        opening = search_start + match.end() - 1
        end = _find_matching_brace(text, opening)
        if end is None:
            return blocks
        blocks.append(text[start:end + 1])
        search_start = end + 1


def _find_matching_brace(text: str, opening_index: int) -> int | None:
    depth = 0
    in_string = False
    escaped = False
    for index in range(opening_index, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def _clean_block(block: str) -> str:
    return block.strip()
