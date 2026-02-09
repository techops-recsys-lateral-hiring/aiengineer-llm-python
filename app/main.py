"""FastAPI application for customer service with LLM integration."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_ollama import OllamaLLM
import logging

from app.config import OLLAMA_BASE_URL, LLM_MODEL, SYSTEM_PROMPT, PHOENIX_ENDPOINT, PHOENIX_ENABLED
from app.guardrails import (
    filter_input,
    detect_prompt_injection,
    detect_policy_violation,
    moderate_output,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Phoenix tracing if enabled
if PHOENIX_ENABLED:
    try:
        from phoenix.otel import register
        from openinference.instrumentation.langchain import LangChainInstrumentor
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        
        # Register Phoenix tracer
        tracer_provider = register(
            project_name="customer-service-ai",
            endpoint=f"{PHOENIX_ENDPOINT}/v1/traces"
        )
        
        # Instrument LangChain
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
        
        # Get tracer for custom spans
        tracer = trace.get_tracer(__name__)
        
        logger.info(f"Phoenix tracing enabled. Endpoint: {PHOENIX_ENDPOINT}")
    except Exception as e:
        logger.warning(f"Failed to initialize Phoenix tracing: {e}")
        PHOENIX_ENABLED = False
        tracer = None
else:
    tracer = None
    logger.info("Phoenix tracing disabled")

# Initialize FastAPI app
app = FastAPI(
    title="Customer Service AI",
    description="E-commerce customer service application with AI assistance",
    version="1.0.0",
)

# Initialize Ollama LLM
llm = OllamaLLM(
    base_url=OLLAMA_BASE_URL,
    model=LLM_MODEL,
    temperature=0.7,
    max_tokens=200,
)


class QueryRequest(BaseModel):
    """Request model for customer queries."""

    question: str


class QueryResponse(BaseModel):
    """Response model for customer queries."""

    answer: str
    blocked: bool = False
    reason: str = ""


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Customer Service AI"}


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    """
    Process customer service queries with guardrails.
    
    Args:
        request: QueryRequest with customer question
        
    Returns:
        QueryResponse with answer or blocking reason
    """
    question = request.question
    logger.info(f"Received query: {question[:200]}...")
    
    # Create parent span if tracing is enabled
    if PHOENIX_ENABLED and tracer:
        with tracer.start_as_current_span("customer_query") as span:
            span.set_attribute("input.value", question)
            span.set_attribute("input.length", len(question))
            return await _process_query(question, span)
    else:
        return await _process_query(question, None)


async def _process_query(question: str, parent_span) -> QueryResponse:
    """Internal function to process query with optional tracing."""
    
    # Step 1: Input filtering
    if PHOENIX_ENABLED and tracer and parent_span:
        with tracer.start_as_current_span("input_filtering") as span:
            is_valid, filtered_or_reason = filter_input(question)
            span.set_attribute("guardrail.passed", is_valid)
            if not is_valid:
                span.set_attribute("guardrail.reason", filtered_or_reason)
    else:
        is_valid, filtered_or_reason = filter_input(question)
        
    if not is_valid:
        logger.warning(f"Input filtering blocked: {filtered_or_reason}")
        if parent_span:
            parent_span.set_attribute("output.blocked", True)
            parent_span.set_attribute("output.block_reason", "input_validation")
        return QueryResponse(
            answer="",
            blocked=True,
            reason=f"Input validation failed: {filtered_or_reason}",
        )
    
    filtered_question = filtered_or_reason
    
    # Step 2: Prompt injection detection
    if PHOENIX_ENABLED and tracer and parent_span:
        with tracer.start_as_current_span("prompt_injection_detection") as span:
            is_injection, injection_reason = detect_prompt_injection(filtered_question)
            span.set_attribute("guardrail.passed", not is_injection)
            if is_injection:
                span.set_attribute("guardrail.reason", injection_reason)
    else:
        is_injection, injection_reason = detect_prompt_injection(filtered_question)
        
    if is_injection:
        logger.warning(f"Prompt injection detected: {injection_reason}")
        if parent_span:
            parent_span.set_attribute("output.blocked", True)
            parent_span.set_attribute("output.block_reason", "prompt_injection")
        return QueryResponse(
            answer="",
            blocked=True,
            reason="I cannot process this request. Reason: Prompt injection attempt detected.",
        )
    
    # Step 3: Policy violation detection
    if PHOENIX_ENABLED and tracer and parent_span:
        with tracer.start_as_current_span("policy_violation_detection") as span:
            is_violation, violation_reason = detect_policy_violation(filtered_question)
            span.set_attribute("guardrail.passed", not is_violation)
            if is_violation:
                span.set_attribute("guardrail.reason", violation_reason)
    else:
        is_violation, violation_reason = detect_policy_violation(filtered_question)
        
    if is_violation:
        logger.warning(f"Policy violation detected: {violation_reason}")
        if parent_span:
            parent_span.set_attribute("output.blocked", True)
            parent_span.set_attribute("output.block_reason", "policy_violation")
        return QueryResponse(
            answer="",
            blocked=True,
            reason=f"I cannot process this request. Reason: {violation_reason}",
        )
    
    # Step 4: Call LLM
    try:
        full_prompt = f"{SYSTEM_PROMPT}\n\nCustomer: {filtered_question}\n\nAssistant:"
        response = llm.invoke(full_prompt)
        logger.info(f"LLM response generated: {response[:200]}...")
        
    except Exception as e:
        logger.error(f"LLM invocation failed: {str(e)}")
        if parent_span:
            parent_span.set_attribute("output.error", str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to generate response. Please try again later.",
        )
    
    # Step 5: Output moderation
    if PHOENIX_ENABLED and tracer and parent_span:
        with tracer.start_as_current_span("output_moderation") as span:
            is_safe, safety_reason = moderate_output(response)
            span.set_attribute("guardrail.passed", is_safe)
            if not is_safe:
                span.set_attribute("guardrail.reason", safety_reason)
    else:
        is_safe, safety_reason = moderate_output(response)
        
    if not is_safe:
        logger.warning(f"Output moderation blocked: {safety_reason}")
        if parent_span:
            parent_span.set_attribute("output.blocked", True)
            parent_span.set_attribute("output.block_reason", "output_moderation")
        return QueryResponse(
            answer="",
            blocked=True,
            reason="I apologize, but I cannot provide this response due to safety concerns.",
        )
    
    # Return successful response
    if parent_span:
        parent_span.set_attribute("output.blocked", False)
        parent_span.set_attribute("output.value", response.strip())
        parent_span.set_attribute("output.length", len(response))
        
    return QueryResponse(answer=response.strip(), blocked=False, reason="")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

