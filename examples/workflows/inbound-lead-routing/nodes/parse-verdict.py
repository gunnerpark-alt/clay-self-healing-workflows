def handler(context):
    segment = context.get_input("segment") or ""
    confidence = context.get_input("confidence") or "LOW"
    segment = segment.strip().upper().replace(" ", "_")
    if segment not in ("ENTERPRISE", "MID_MARKET", "SMB"):
        segment = "NEEDS_REVIEW"
    return {"segment": segment, "confidence": confidence}
