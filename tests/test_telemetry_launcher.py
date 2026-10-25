import sys

import httpx
import pytest
from opentelemetry.sdk.trace import TracerProvider

from mesh import launcher, telemetry


class RecordingProvider:
    def __init__(self, resource):
        self.resource = resource
        self.exporters = []

    def add_span_processor(self, processor):
        self.exporters.append(processor)


def install(monkeypatch) -> list:
    installed: list = []
    monkeypatch.setattr(telemetry, "TracerProvider", RecordingProvider)
    monkeypatch.setattr(telemetry, "BatchSpanProcessor", lambda exporter: exporter)
    monkeypatch.setattr(telemetry.trace, "set_tracer_provider", installed.append)
    return installed


def test_console_tracing_names_the_service(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setenv("MESH_TRACE_CONSOLE", "1")
    installed = install(monkeypatch)

    telemetry.setup_tracing("flights_agent")

    provider = installed[0]
    assert provider.resource.attributes["service.name"] == "flights_agent"
    assert [type(e).__name__ for e in provider.exporters] == ["ConsoleSpanExporter"]


def test_otlp_exporter_is_added_when_an_endpoint_is_configured(monkeypatch):
    pytest.importorskip("opentelemetry.exporter.otlp.proto.http.trace_exporter")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    monkeypatch.delenv("MESH_TRACE_CONSOLE", raising=False)
    installed = install(monkeypatch)

    telemetry.setup_tracing("hotels_agent")

    assert [type(e).__name__ for e in installed[0].exporters] == ["OTLPSpanExporter"]


async def test_outbound_requests_carry_the_current_trace():
    tracer = TracerProvider().get_tracer("test")
    request = httpx.Request("POST", "http://127.0.0.1:8001/")
    with tracer.start_as_current_span("planner-turn") as span:
        await telemetry.inject_traceparent(request)
    trace_id = format(span.get_span_context().trace_id, "032x")
    assert request.headers["traceparent"].split("-")[1] == trace_id


def test_launcher_starts_every_specialist_and_stops_them_on_ctrl_c(monkeypatch):
    started = []

    class FakeProcess:
        def __init__(self, cmd):
            self.cmd, self.terminated = cmd, False
            started.append(self)

        def wait(self):
            raise KeyboardInterrupt  # the user hits Ctrl+C while agents run

        def terminate(self):
            self.terminated = True

    monkeypatch.setattr(launcher.subprocess, "Popen", FakeProcess)

    launcher.main()

    assert [p.cmd for p in started] == [[sys.executable, "-m", m] for m in launcher.AGENTS]
    assert all(p.terminated for p in started)
