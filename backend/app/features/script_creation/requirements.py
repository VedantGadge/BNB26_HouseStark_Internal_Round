"""Deterministic checks for explicit brand and creator-style requirements."""

from app.schemas import RequirementCheck, RequirementStatus, ScriptContent


def evaluate_requirements(
    snapshot: dict,
    content: ScriptContent,
) -> tuple[list[RequirementCheck], list[str]]:
    checks: list[RequirementCheck] = []
    warnings: list[str] = []
    combined_text = _combined_text(content).casefold()
    campaign = snapshot.get("campaign_brief", {}).get("brand_brief") or {}
    for requirement in campaign.get("requirements", []):
        if requirement.get("kind") == "literal":
            literal = requirement.get("literal_text", "").casefold()
            satisfied = bool(literal and literal in combined_text)
            checks.append(
                RequirementCheck(
                    requirement_id=requirement["id"],
                    status=RequirementStatus.SATISFIED if satisfied else RequirementStatus.MISSING,
                    evidence_section_ids=(
                        [section.id for section in content.sections] if satisfied else []
                    ),
                    message=None if satisfied else "Required literal text is missing.",
                )
            )
        else:
            checks.append(
                RequirementCheck(
                    requirement_id=requirement["id"],
                    status=RequirementStatus.NEEDS_REVIEW,
                    message="Semantic requirement needs creator review.",
                )
            )
            warnings.append(requirement["id"])
    for phrase in campaign.get("forbidden_phrases", []):
        if phrase.casefold() in combined_text:
            warnings.append(f"forbidden:{phrase}")
    _evaluate_signature_lines(snapshot, content, checks)
    return checks, warnings


def _evaluate_signature_lines(
    snapshot: dict,
    content: ScriptContent,
    checks: list[RequirementCheck],
) -> None:
    profile = snapshot.get("style_profile", {}).get("profile") or {}
    selected_optional = set(snapshot.get("request", {}).get("optional_signature_line_ids", []))
    for line in profile.get("signature_lines", []):
        required = line.get("inclusion_policy") == "always" or line.get("id") in selected_optional
        if not required:
            continue
        placement_text = _placement_text(line.get("placement"), content).casefold()
        satisfied = line.get("text", "").casefold() in placement_text
        checks.append(
            RequirementCheck(
                requirement_id=f"signature-{line['id']}",
                status=RequirementStatus.SATISFIED if satisfied else RequirementStatus.MISSING,
                evidence_section_ids=(
                    [content.sections[0].id] if satisfied and content.sections else []
                ),
                message=(
                    None if satisfied else "Required signature line is missing from its placement."
                ),
            )
        )


def _placement_text(placement: str | None, content: ScriptContent) -> str:
    if placement == "opening":
        selected_hook = next(hook for hook in content.hooks if hook.id == content.selected_hook_id)
        return f"{selected_hook.text} {content.sections[0].text}"
    if placement == "closing":
        return f"{content.sections[-1].text} {content.call_to_action}"
    return " ".join(section.text for section in content.sections)


def _combined_text(content: ScriptContent) -> str:
    return " ".join(
        [content.title, content.description, content.call_to_action]
        + [hook.text for hook in content.hooks]
        + [section.text for section in content.sections]
    )
