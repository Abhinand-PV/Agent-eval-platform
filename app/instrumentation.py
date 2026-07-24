from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.instrumentation.langchain import LangchainInstrumentor

# Create an in-memory exporter so we can read spans programmatically
_exporter = InMemorySpanExporter()
_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(_exporter))
trace.set_tracer_provider(_provider)

# Instrument all LangChain/LangGraph calls automatically
LangchainInstrumentor().instrument()
def get_exporter() -> InMemorySpanExporter:
    return _exporter


def collect_spans() -> list[dict]:
    """Harvest finished spans and clear the exporter for the next run."""
    spans = _exporter.get_finished_spans()
    collected = []
    for span in spans:
        attrs = dict(span.attributes) if span.attributes else {}
        collected.append({
            "name": span.name,
            "duration_ms": int((span.end_time - span.start_time) / 1_000_000),
            "attributes": attrs,
        })
    _exporter.clear()
    return collected
def extract_metrics(spans: list[dict]) -> dict:
    """Compute token counts, cost, and tool usage from collected spans."""
    total_input_tokens = 0
    total_output_tokens = 0
    tools_called = []

    for span in spans:
        attrs = span.get("attributes", {})
        input_tokens = attrs.get("gen_ai.usage.input_tokens", 0)
        output_tokens = attrs.get("gen_ai.usage.output_tokens", 0)
        total_input_tokens += input_tokens
        total_output_tokens += output_tokens

        tool_name = attrs.get("gen_ai.tool.name")
        if tool_name:
            tools_called.append(tool_name)

    total_tokens = total_input_tokens + total_output_tokens

    # Groq pricing for llama-3.3-70b-versatile: $0.59/1M input, $0.79/1M output
    cost_usd = (total_input_tokens * 0.59 / 1_000_000) + (
        total_output_tokens * 0.79 / 1_000_000
    )

    return {
        "total_tokens": total_tokens,
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "cost_usd": round(cost_usd, 6),
        "tools_called": tools_called,
    }