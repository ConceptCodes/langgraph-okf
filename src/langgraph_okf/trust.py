from datetime import UTC, date, datetime, time

from langgraph_okf.models import Concept, LifecycleStatus, TrustTier


def evaluate_trust_tier(concept: Concept) -> TrustTier:
    """
    Derive the trust tier from frontmatter per OKF v0.2 §5.3.
    - Unverified: No verification record.
    - Machine-confirmed: Verified by an agent or automated process.
    - Human-reviewed: Verified by a human actor (e.g., human:<username>).
    """
    verified = concept.frontmatter.verified
    if not verified:
        return TrustTier.UNVERIFIED

    events = [verified] if isinstance(verified, dict) else verified
    tier = TrustTier.UNVERIFIED
    for event in events:
        actor = event.get("by")
        if not isinstance(actor, str) or not actor.strip():
            continue
        verifier = actor.strip()
        if ":" in verifier and not verifier.split(":", 1)[1].strip():
            continue
        if verifier.startswith("human:"):
            return TrustTier.HUMAN_REVIEWED
        tier = TrustTier.MACHINE_CONFIRMED
    return tier


def evaluate_lifecycle_and_freshness(
    concept: Concept, current_time: datetime | None = None
) -> tuple[bool, list[str]]:
    """
    Check if a concept is stale or superseded, generating advisory signals.
    """
    if current_time is None:
        current_time = datetime.now(UTC)
    elif current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=UTC)

    advisories: list[str] = []
    is_stale = False

    # Check status
    status = concept.frontmatter.status.lower()
    if status == LifecycleStatus.DRAFT:
        advisories.append(f"Concept '{concept.concept_id}' is DRAFT and may be incomplete.")
    if status == LifecycleStatus.DEPRECATED:
        advisories.append(f"Concept '{concept.concept_id}' is DEPRECATED and should not be relied upon.")
        is_stale = True
    elif status == LifecycleStatus.SUPERSEDED:
        advisories.append(f"Concept '{concept.concept_id}' is SUPERSEDED by an amendment or addendum.")
        is_stale = True

    # Check stale_after
    stale_after = concept.frontmatter.stale_after
    if stale_after:
        stale_dt: datetime | None = None
        if isinstance(stale_after, datetime):
            stale_dt = stale_after
        elif isinstance(stale_after, date):
            stale_dt = datetime.combine(stale_after, time.min, tzinfo=UTC)
        elif isinstance(stale_after, str):
            try:
                stale_dt = datetime.fromisoformat(stale_after.replace("Z", "+00:00"))
            except ValueError:
                advisories.append(f"Concept '{concept.concept_id}' has invalid stale_after metadata.")

        if stale_dt:
            if stale_dt.tzinfo is None:
                stale_dt = stale_dt.replace(tzinfo=UTC)
            if current_time >= stale_dt:
                is_stale = True
                advisories.append(
                    f"Concept '{concept.concept_id}' expired on {stale_dt.isoformat()} (exceeded stale_after)."
                )

    return is_stale, advisories


def enrich_concept_trust(concept: Concept, current_time: datetime | None = None) -> Concept:
    """
    Calculates and populates trust tier and advisories on a Concept object.
    """
    tier = evaluate_trust_tier(concept)
    stale, advisories = evaluate_lifecycle_and_freshness(concept, current_time)

    concept.trust_tier = tier
    concept.is_stale = stale
    concept.trust_advisories = advisories
    return concept
