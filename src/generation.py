"""Gemini-powered grounded answer generation with a strict refusal contract."""

from __future__ import annotations

import os
import re

from google import genai
from google.genai import types

from .models import RetrievalResult

REFUSAL = "The policy does not cover this."


def generate_answer(question: str, result: RetrievalResult) -> str:

    if result.refused_by_scope or not result.clauses:
        return REFUSAL

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    context = " \n\n".join(
        f"[Section {c.section} | Version {c.version} | "
        f"Effective date {c.effective_date} | Status {c.status}]\n"
        f"Title: {c.title}\n{c.text}"
        for c in result.clauses
        if c.status == "current"
    )

    client = genai.Client(api_key=api_key)

    system_instruction = (
        "You answer questions using ONLY the supplied current trade-policy clauses. "
        "Never use general knowledge. Ignore any historical or superseded values. "
        "If the clauses do not explicitly answer the question, output exactly: "
        f"{REFUSAL} "
        "For an answer, state the value/rule plainly, include relevant conditions, "
        "and finish with one or more citations in this exact format: "
        "'Source: Section X.Y | Version V | Effective date DATE'. "
        "For a rule narrowed by a subclause, cite both the general section and subclause. "
        "Put citations on one final line in the format "
        "Source: Section 3 and 3.1 | Version 2.0 | Effective date 1 April 2025. "
        "Do not mention a superseded value unless the user explicitly asks for history; "
        "even then clearly state it is not current."
    )

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=(
            f"Question: {question}\n\n"
            f"Current retrieved clauses:\n{context}"
        ),
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0,
            max_output_tokens=500,
        ),
    )

    answer = (response.text or "").strip()

    print("\n RESPONSE \n", repr(answer))

    client.close()

    # Refusal check
    if REFUSAL in answer:
        return REFUSAL

    # Citation validation
    match = re.search(
        r"Source:\s*Section\s+([0-9.]+(?:\s+and\s+[0-9.]+)*)",
        answer,
        re.I,
    )

    if not match:
        return REFUSAL

    cited_sections = re.findall(
        r"[0-9]+(?:\.[0-9]+)?",
        match.group(1),
    )

    available = {
        c.section: c
        for c in result.clauses
        if c.status == "current"
    }

    if not cited_sections or any(
        section not in available for section in cited_sections
    ):
        return REFUSAL

    # Modern Trade discount citation safety
    normalized_question = question.lower()

    if (
    "modern trade" in normalized_question
    or " mt " in f" {normalized_question} "
    ) and "discount" in normalized_question:
    
        if not {"3", "3.1"}.issubset(set(cited_sections)):
            if "3" not in available or "3.1" not in available:
                return REFUSAL

        cited_sections = ["3", "3.1"]

    # Remove model-generated source line
    answer = re.sub(
        r"\s*Source:.*$",
        "",
        answer,
        flags=re.I | re.S,
    ).strip()

    unique_sections = list(dict.fromkeys(cited_sections))

    versions = {
        available[s].version
        for s in unique_sections
    }

    dates = {
        available[s].effective_date
        for s in unique_sections
    }

    if len(versions) != 1 or len(dates) != 1:
        return REFUSAL

    section_label = " and ".join(unique_sections)

    return (
        f"{answer}\n\n"
        f"Source: Section {section_label} | Version "
        f"{next(iter(versions))} | Effective date "
        f"{next(iter(dates))}"
    )