"""Semantic search tool for FEMA policy documents.

Searches a local corpus of 11 FEMA policy documents using OpenAI embeddings
and cosine similarity. Requires OPENAI_API_KEY to be set.
"""

from __future__ import annotations

from omniagents_client.tools import tool

_EMBEDDING_CACHE: dict[str, list[float]] = {}
_DOC_EMBEDDINGS: dict[str, list[float]] = {}
_POLICY_DOCUMENTS: dict[str, str] = {}

DOCUMENTS = {
    "evacuation_protocols": (
        "FEMA Evacuation Protocols (ICS-300): All evacuation orders must follow the Incident Command System. "
        "Zone-based evacuation proceeds from highest-risk zones outward. Mandatory evacuation requires "
        "governor authorization. Evacuation routes must be pre-designated and communicated via Wireless "
        "Emergency Alerts (WEA). Special needs populations require dedicated transport. Shelter capacity "
        "must be verified before issuing orders. Pet-friendly shelters must be available per the PETS Act."
    ),
    "disaster_declaration": (
        "FEMA Disaster Declaration Process: Local government requests state assistance. If overwhelmed, "
        "governor requests federal declaration from the President. FEMA conducts Preliminary Damage "
        "Assessment (PDA). Two declaration types: Emergency Declaration (Category B assistance, $5M cap) "
        "and Major Disaster Declaration (all assistance categories, no cap). Individual Assistance (IA) "
        "and Public Assistance (PA) can be authorized separately. Timeline: PDA within 10 days, "
        "presidential decision within 5 days of governor's request."
    ),
    "aid_eligibility": (
        "FEMA Individual Assistance Eligibility: Applicants must be U.S. citizens, non-citizen nationals, "
        "or qualified aliens. Primary residence must be in the declared disaster area. Damage must be "
        "disaster-caused and not covered by insurance. Apply within 60 days of declaration (extensions "
        "possible). Types of assistance: Housing Assistance (rental, repair, replacement up to $42,500), "
        "Other Needs Assistance (medical, dental, funeral, personal property, transportation, childcare). "
        "SBA disaster loans available for amounts exceeding FEMA maximums."
    ),
    "flood_response": (
        "FEMA Flood Response Procedures: Activate National Flood Insurance Program (NFIP) coordination. "
        "Deploy Urban Search and Rescue (US&R) teams within 6 hours. Establish water rescue staging "
        "areas. Issue flash flood warnings via NWS partnership. Coordinate with Army Corps of Engineers "
        "for levee assessments. Post-flood: conduct rapid needs assessment within 72 hours. Distribute "
        "flood cleanup kits. Monitor waterborne disease risks. Begin mold remediation guidance within 48 hours."
    ),
    "wildfire_safety": (
        "FEMA Wildfire Safety Guidelines: Create defensible space of 100 feet around structures. "
        "Zone 1 (0-30 ft): remove all dead vegetation and flammable materials. Zone 2 (30-100 ft): "
        "reduce and space vegetation. Have a go-bag ready with essentials for 72 hours. Know two "
        "evacuation routes from your area. Close all windows and doors before evacuating. Wear "
        "protective clothing: long sleeves, cotton/wool, N95 mask. Monitor air quality index (AQI) daily."
    ),
    "wildfire_management": (
        "FEMA Wildfire Response (NRF ESF-4): Coordinate with USFS and state forestry agencies. Pre-position "
        "resources when Fire Weather Watch is issued. Activate Fire Management Assistance Grants (FMAG) for "
        "state cost-sharing. Evacuation triggers: fire within 2 miles of populated areas with wind >25mph. "
        "Post-fire: activate Burned Area Emergency Response (BAER) teams within 7 days. Debris flow risk "
        "assessment required for all slopes >30% in burn scar areas."
    ),
    "hurricane_preparedness": (
        "FEMA Hurricane Preparedness Guide: Monitor National Hurricane Center (NHC) advisories. "
        "Hurricane Watch: conditions possible within 48 hours, begin preparations. Hurricane Warning: "
        "conditions expected within 36 hours, complete preparations and evacuate if ordered. "
        "Secure property: install storm shutters, reinforce garage doors, trim trees. Stock supplies "
        "for 7 days minimum (water: 1 gallon per person per day). Know your evacuation zone (A through E). "
        "Register with local special needs registry if applicable."
    ),
    "earthquake_response": (
        "FEMA Earthquake Response Protocol: Activate ShakeAlert early warning system. Immediate response: "
        "Drop, Cover, Hold On. Post-quake: expect aftershocks, check for structural damage before re-entry. "
        "Deploy structural engineers for rapid building assessments (ATC-20 inspections). Red/Yellow/Green "
        "tagging system for building safety. Activate Community Emergency Response Teams (CERT). "
        "Coordinate dam safety inspections. Restore utilities following gas-electric-water priority sequence."
    ),
    "tornado_safety": (
        "FEMA Tornado Safety Procedures: Tornado Watch: conditions favorable, stay alert. Tornado Warning: "
        "tornado detected or imminent, take shelter immediately. Safe rooms: interior room on lowest floor, "
        "no windows. Mobile home residents must evacuate to sturdy shelter. FEMA safe room grants available "
        "under Hazard Mitigation Grant Program (HMGP). Post-tornado: avoid downed power lines, watch for "
        "gas leaks, document damage with photos for insurance claims."
    ),
}


def _load_env() -> None:
    """Load .env if OPENAI_API_KEY is not already set."""
    import os
    if os.getenv("OPENAI_API_KEY"):
        return
    from pathlib import Path
    candidates = [
        Path(os.getcwd()) / ".env",
        Path.home() / ".env",
    ]
    for candidate in candidates:
        if candidate.exists():
            with open(candidate) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        value = value.strip().strip('"').strip("'")
                        os.environ.setdefault(key.strip(), value)
            return


def _embed_text(text: str) -> list[float]:
    import hashlib
    import os
    from openai import OpenAI

    _load_env()
    cache_key = hashlib.md5(text.encode()).hexdigest()
    if cache_key in _EMBEDDING_CACHE:
        return _EMBEDDING_CACHE[cache_key]
    embed_model = os.getenv("EMBED_MODEL", "text-embedding-3-small")
    response = OpenAI().embeddings.create(model=embed_model, input=text)
    embedding = response.data[0].embedding
    _EMBEDDING_CACHE[cache_key] = embedding
    return embedding


def _ensure_doc_embeddings() -> None:
    global _POLICY_DOCUMENTS
    if _DOC_EMBEDDINGS:
        return
    _POLICY_DOCUMENTS = DOCUMENTS
    for doc_id, text in _POLICY_DOCUMENTS.items():
        _DOC_EMBEDDINGS[doc_id] = _embed_text(text)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    import numpy as np
    a_arr, b_arr = np.array(a), np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))


@tool
def search_policies(query: str, top_k: int = 3) -> str:
    """
    Search FEMA policy documents for information relevant to the query.

    :param query: Natural language search query about FEMA policies or procedures.
    :param top_k: Number of top results to return (default 3).
    :returns: Matching policy documents with relevance scores.
    """
    _ensure_doc_embeddings()
    query_embedding = _embed_text(query)

    similarities = []
    for doc_id, doc_embedding in _DOC_EMBEDDINGS.items():
        score = _cosine_similarity(query_embedding, doc_embedding)
        similarities.append({"doc_id": doc_id, "score": score, "text": _POLICY_DOCUMENTS[doc_id]})

    similarities.sort(key=lambda x: x["score"], reverse=True)
    results = similarities[:top_k]

    parts = []
    for r in results:
        parts.append(f"[{r['doc_id']}] (relevance: {r['score']:.3f})\n{r['text']}")

    return "\n\n".join(parts)
