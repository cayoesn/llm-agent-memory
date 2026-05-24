import logging
import sys
import structlog
from opentelemetry import trace

def setup_logging():
    """Configures structured logging with OpenTelemetry integration."""
    
    # Processors for structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        # Add trace context to logs
        add_otel_trace_id,
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

def add_otel_trace_id(_, __, event_dict):
    """Adds OpenTelemetry trace and span IDs to the log event."""
    span = trace.get_current_span()
    if span.is_recording():
        ctx = span.get_span_context()
        event_dict["trace_id"] = f"{ctx.trace_id:032x}"
        event_dict["span_id"] = f"{ctx.span_id:016x}"
    return event_dict

# Initialize logging on module load
setup_logging()
logger = structlog.get_logger()
