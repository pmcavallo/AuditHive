"""OpenAI-compatible chat completions endpoint — the core product."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audithive.api.middleware.auth import AuthenticatedCustomer, get_current_customer
from audithive.alerts.dispatcher import dispatch_alert
from audithive.audit.logger import log_interaction
from audithive.db.database import get_db
from audithive.db.models import PolicyConfig
from audithive.policy.engine import run_policy_checks
from audithive.proxy.llm_proxy import proxy_request
from audithive.schemas.chat import ChatCompletionRequest

router = APIRouter()


@router.post("/v1/chat/completions")
async def chat_completions(
    body: ChatCompletionRequest,
    request: Request,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """OpenAI-compatible chat completions with governance."""
    # 1. Extract customer's LLM key
    llm_key = request.headers.get("X-LLM-Key")
    if not llm_key:
        return JSONResponse(
            status_code=400,
            content={"error": "missing_llm_key", "message": "X-LLM-Key header is required. Provide your LLM provider API key."},
        )

    messages_dicts = [m.model_dump() for m in body.messages]
    request_params = body.to_openai_dict()
    del request_params["messages"]
    del request_params["model"]

    # 2. Load customer's policy config
    result = await db.execute(
        select(PolicyConfig).where(
            PolicyConfig.customer_id == customer.customer_id,
            PolicyConfig.is_active.is_(True),
        ).order_by(PolicyConfig.created_at.desc()).limit(1)
    )
    policy_row = result.scalar_one_or_none()
    policy_config = policy_row.config if policy_row else None

    # 3. Run pre-call policy checks
    engine_result = run_policy_checks(messages_dicts, policy_config)

    checks_dicts = [asdict(c) for c in engine_result.checks]
    violations_dicts = [asdict(v) for v in engine_result.violations]

    # 4. If blocked, log and return 403
    if not engine_result.allowed:
        log_id = await log_interaction(
            db=db,
            customer_id=customer.customer_id,
            api_key_id=customer.api_key_id,
            request_model=body.model,
            request_messages=messages_dicts,
            request_params=request_params,
            response_content=None,
            response_tokens_in=None,
            response_tokens_out=None,
            response_latency_ms=None,
            policies_applied=checks_dicts,
            policies_violated=violations_dicts,
            action_taken=engine_result.action,
            status="blocked",
        )
        # Dispatch alert
        await dispatch_alert(
            db=db,
            customer_id=customer.customer_id,
            trigger_type="policy_block",
            trigger_details={"audit_log_id": str(log_id), "action_taken": "block"},
        )

        return JSONResponse(
            status_code=403,
            content={
                "error": "policy_violation",
                "message": "Request blocked by policy.",
                "action": engine_result.action,
                "violations": violations_dicts,
                "audit_log_id": str(log_id),
            },
            headers={"X-AuditHive-Log-Id": str(log_id)},
        )

    # 5. Forward to LLM provider
    proxy_resp = await proxy_request(
        provider="openai",
        llm_api_key=llm_key,
        request_body=body.to_openai_dict(),
    )

    # 6. Extract token usage from successful responses
    tokens_in = None
    tokens_out = None
    if proxy_resp.status_code == 200:
        usage = proxy_resp.body.get("usage", {})
        tokens_in = usage.get("prompt_tokens")
        tokens_out = usage.get("completion_tokens")

    # 7. Determine final status
    if proxy_resp.error:
        status = "error"
    elif engine_result.action == "flag":
        status = "flagged"
    else:
        status = "completed"

    # 8. Log the interaction
    log_id = await log_interaction(
        db=db,
        customer_id=customer.customer_id,
        api_key_id=customer.api_key_id,
        request_model=body.model,
        request_messages=messages_dicts,
        request_params=request_params,
        response_content=proxy_resp.body,
        response_tokens_in=tokens_in,
        response_tokens_out=tokens_out,
        response_latency_ms=proxy_resp.latency_ms,
        policies_applied=checks_dicts,
        policies_violated=violations_dicts,
        action_taken=engine_result.action,
        status=status,
        error_message=proxy_resp.error,
    )

    # 9. Dispatch alerts
    if engine_result.action in ("block", "flag"):
        await dispatch_alert(
            db=db,
            customer_id=customer.customer_id,
            trigger_type=f"policy_{engine_result.action}",
            trigger_details={"audit_log_id": str(log_id), "action_taken": engine_result.action},
        )

    # 10. Return the provider response (pass-through)
    return JSONResponse(
        status_code=proxy_resp.status_code,
        content=proxy_resp.body,
        headers={"X-AuditHive-Log-Id": str(log_id)},
    )
