from __future__ import annotations


def make_repair_prompt(pdsl: str, diagnostics: list[str]) -> str:
    diagnostic_text = "\n".join(f"- {diagnostic}" for diagnostic in diagnostics)
    return (
        "The following PolyForge program failed compiler validation.\n\n"
        "Program:\n"
        "```pdsl\n"
        f"{pdsl.strip()}\n"
        "```\n\n"
        "Diagnostics:\n"
        f"{diagnostic_text}\n\n"
        "Repair the program so it satisfies the PolyForge v0.1 language rules. "
        "Return only corrected PolyForge source code in one pdsl code block."
    )
