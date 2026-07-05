"""Billing integration for WorkoPilot digital employee usage."""

import logging

logger = logging.getLogger(__name__)

# Billing code → points per unit
BILLING_CODES = {
    "report_generate": 5,
    "report_export": 2,
}


async def deduct_billing(
    robot_id: int,
    user_id: str,
    billing_code: str,
    quantity: int = 1,
) -> dict | None:
    """Deduct billing points for a robot operation.

    Calls the WorkoPilot billing deduction API. Failures are logged but
    are non-blocking in development mode — the operation continues even
    if billing deduction fails.

    Args:
        robot_id: The digital employee robot ID.
        user_id: The user account ID.
        billing_code: One of the keys in BILLING_CODES (e.g. "report_generate").
        quantity: Multiplier (default 1). The total deduction is
                  quantity * BILLING_CODES[billing_code].

    Returns:
        The API response dict on success, or None on failure.
    """
    points = quantity * BILLING_CODES.get(billing_code, 1)
    try:
        from backend.workopilot.client import workopilot_client

        result = await workopilot_client._request(
            "POST",
            "/api/billing/deduct",
            json={
                "robotId": robot_id,
                "userId": user_id,
                "billingCode": billing_code,
                "quantity": points,
            },
        )
        logger.info(
            "Billing deducted: robot=%s user=%s code=%s quantity=%s points=%s",
            robot_id,
            user_id,
            billing_code,
            quantity,
            points,
        )
        return result
    except Exception:
        logger.warning(
            "Billing deduction failed (non-blocking): robot=%s user=%s code=%s",
            robot_id,
            user_id,
            billing_code,
        )
        return None
