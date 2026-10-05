"""Ticket analysis: LLM (Claude) if configured, otherwise a rule-based fallback."""
import json
import os

CATEGORIES = ["billing", "technical", "account", "outage", "feature_request", "general"]
PRIORITIES = ["low", "medium", "high", "critical"]
TEAMS = {
    "billing": "Finance Support",
    "technical": "Tech Support",
    "account": "Account Services",
    "outage": "Site Reliability",
    "feature_request": "Product",
    "general": "Customer Care",
}

KEYWORDS = {
    "outage": ["outage", "down", "unavailable", "not loading", "500 error", "crash"],
    "billing": ["invoice", "charge", "refund", "payment", "billing", "subscription"],
    "account": ["password", "login", "log in", "locked", "account", "2fa", "sign in"],
    "technical": ["error", "bug", "broken", "not working", "fails", "exception", "slow"],
    "feature_request": ["feature", "would be nice", "suggest", "request", "wish"],
}
NEGATIVE = ["angry", "terrible", "worst", "unacceptable", "furious", "frustrated",
            "disappointed", "useless", "again", "still not"]
POSITIVE = ["thanks", "thank you", "great", "love", "awesome", "appreciate"]
URGENT = ["urgent", "asap", "immediately", "critical", "production", "emergency", "now"]

REPLIES = {
    "billing": "Thanks for reaching out about billing. We're reviewing your account and will confirm the details shortly.",
    "technical": "Sorry about the trouble. Our support engineers are looking into this. Could you share any error messages or screenshots?",
    "account": "We can help with your account access. For security, we'll verify your identity and then restore access.",
    "outage": "We're sorry for the disruption. Our reliability team has been alerted and is investigating as a priority.",
    "feature_request": "Thank you for the suggestion! We've passed it to our product team for consideration.",
    "general": "Thanks for contacting us. A member of our team will get back to you shortly.",
}


def _rule_based(message: str) -> dict:
    text = message.lower()
    scores = {c: sum(k in text for k in kws) for c, kws in KEYWORDS.items()}
    category = max(scores, key=scores.get) if any(scores.values()) else "general"

    neg = sum(w in text for w in NEGATIVE)
    pos = sum(w in text for w in POSITIVE)
    sentiment = "negative" if neg > pos else "positive" if pos > neg else "neutral"

    urgent = sum(w in text for w in URGENT)
    level = urgent + (1 if sentiment == "negative" else 0) + (2 if category == "outage" else 0)
    priority = "critical" if level >= 3 else "high" if level == 2 else "medium" if level == 1 else "low"

    summary = message.strip().replace("\n", " ")
    summary = summary[:117] + "..." if len(summary) > 120 else summary
    return {
        "category": category, "priority": priority, "sentiment": sentiment,
        "summary": summary, "suggested_reply": REPLIES[category], "source": "rules",
    }


def _llm(message: str) -> dict:
    import anthropic

    client = anthropic.Anthropic()
    prompt = (
        "You are a service-operations triage assistant. Analyze the customer message and "
        "return ONLY a JSON object with keys: category (one of "
        f"{CATEGORIES}), priority (one of {PRIORITIES}), sentiment "
        "(positive|neutral|negative), summary (max 20 words), suggested_reply "
        f"(2-3 polite sentences).\n\nMessage:\n{message}"
    )
    resp = client.messages.create(
        model=os.getenv("AI_MODEL", "claude-sonnet-4-6"),
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip().strip("`")
    if text.startswith("json"):
        text = text[4:]
    data = json.loads(text)
    if data["category"] not in CATEGORIES or data["priority"] not in PRIORITIES:
        raise ValueError("invalid LLM output")
    data["source"] = "llm"
    return data


def analyze(message: str) -> dict:
    result = None
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            result = _llm(message)
        except Exception as exc:  # fall back on any LLM/parse failure
            print(f"LLM analysis failed, using rules: {exc}")
    if result is None:
        result = _rule_based(message)
    result["team"] = TEAMS[result["category"]]
    return result
