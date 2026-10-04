import pytest
from pydantic import ValidationError

from app.config import Settings
from app.schemas import (
    AssistantMessageRequest,
    BrandCampaignBrief,
    BrandRequirement,
    CampaignBriefSaveRequest,
    ContentMode,
    CreatorStyleProfileContent,
    ProposalChange,
    ScriptContent,
    ScriptGenerationRequest,
    ScriptHook,
    ScriptSection,
    SignatureInclusionPolicy,
    SignatureLine,
    SignaturePlacement,
)


def script_content() -> ScriptContent:
    return ScriptContent(
        hooks=[ScriptHook(id="hook_1", text="Start with this simple change")],
        selected_hook_id="hook_1",
        sections=[
            ScriptSection(
                id="section_1",
                position=1,
                heading="Opening",
                text="Show the result before explaining it.",
            )
        ],
        title="A practical creator script",
        description="A short script with an actionable opening.",
        call_to_action="Save this for your next reel.",
    )


def test_script_content_requires_selected_hook_and_consecutive_sections() -> None:
    assert script_content().selected_hook_id == "hook_1"

    with pytest.raises(ValidationError, match="selected_hook_id"):
        ScriptContent(
            hooks=[ScriptHook(id="hook_1", text="A hook")],
            selected_hook_id="missing_hook",
            sections=[ScriptSection(id="section_1", position=1, heading="One", text="Text")],
            title="Title",
            description="Description",
            call_to_action="CTA",
        )

    with pytest.raises(ValidationError, match="consecutive positions"):
        ScriptContent(
            hooks=[ScriptHook(id="hook_1", text="A hook")],
            selected_hook_id="hook_1",
            sections=[ScriptSection(id="section_1", position=2, heading="One", text="Text")],
            title="Title",
            description="Description",
            call_to_action="CTA",
        )


def test_brand_mode_requires_a_brand_brief_and_literal_text() -> None:
    with pytest.raises(ValidationError, match="brand mode requires brand_brief"):
        CampaignBriefSaveRequest(content_mode=ContentMode.BRAND)

    with pytest.raises(ValidationError, match="literal requirements need literal_text"):
        BrandRequirement(id="req_1", kind="literal", description="Use the discount code")

    brand_brief = BrandCampaignBrief(
        brand_name="CreatorAI",
        product_name="Creator Workspace",
        product_description="A workspace for building short-form content.",
        campaign_goal="Awareness",
        campaign_audience="New creators",
        publishing_destination="creator_account",
    )
    assert (
        CampaignBriefSaveRequest(
            content_mode=ContentMode.BRAND, brand_brief=brand_brief
        ).brand_brief
        == brand_brief
    )


def test_style_profile_keeps_signature_line_ids_unique() -> None:
    signature = SignatureLine(
        id="signoff_1",
        text="See you in the next one.",
        inclusion_policy=SignatureInclusionPolicy.ALWAYS,
        placement=SignaturePlacement.CLOSING,
    )
    with pytest.raises(ValidationError, match="unique IDs"):
        CreatorStyleProfileContent(signature_lines=[signature, signature])


def test_generation_requires_an_explicit_style_revision() -> None:
    with pytest.raises(ValidationError, match="use_style_profile requires"):
        ScriptGenerationRequest(use_style_profile=True)

    with pytest.raises(ValidationError, match="requires use_style_profile"):
        ScriptGenerationRequest(style_profile_revision=1)

    assert (
        ScriptGenerationRequest(use_style_profile=True, style_profile_revision=2).language
        == "english"
    )


def test_assistant_targets_only_accept_relevant_ids() -> None:
    with pytest.raises(ValidationError, match="require target_id"):
        AssistantMessageRequest(base_version=1, message="Make it shorter", target_scope="section")

    with pytest.raises(ValidationError, match="cannot include target_id"):
        AssistantMessageRequest(
            base_version=1,
            message="Make this shorter",
            target_scope="script",
            target_id="section_1",
        )

    assert (
        AssistantMessageRequest(
            base_version=1,
            message="Make this more casual",
            target_scope="section",
            target_id="section_1",
        ).target_id
        == "section_1"
    )


def test_full_script_proposals_use_a_complete_replacement() -> None:
    replacement = script_content().model_copy(update={"title": "A refreshed creator script"})
    change = ProposalChange(target_scope="script", content_after=replacement)

    assert change.content_after == replacement
    with pytest.raises(ValidationError, match="content_after only"):
        ProposalChange(
            target_scope="script",
            before="Old script",
            after="New script",
        )


def test_openrouter_configuration_deduplicates_and_bounds_fallbacks() -> None:
    settings = Settings(
        _env_file=None,
        openrouter_fallback_models="model-a, model-b, model-a, model-c",
        openrouter_max_fallback_models=2,
    )

    assert settings.openrouter_free_only is False
    assert settings.openrouter_default_model == "google/gemini-3.8-flash"
    assert settings.openrouter_reasoning_effort == "low"
    assert settings.configured_openrouter_models == ("model-a", "model-b")
