"""Hidden checks for task_e08_case_convert (dev2 set, written without reading any held-out test)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(argv):
    name = argv[0] if argv else "reference_solution.py"
    path = Path(__file__).resolve().parent / name
    spec = importlib.util.spec_from_file_location(f"task_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _eq(actual, expected):
    assert actual == expected, f"expected {expected!r}, got {actual!r}"


def _raises(error, function, *args, **kwargs):
    try:
        function(*args, **kwargs)
    except error:
        return
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(f"expected {error.__name__}, got {type(exc).__name__}: {exc}")
    raise AssertionError(f"expected {error.__name__}")


def _checks(m):
    c2s, s2c = m.camel_to_snake, m.snake_to_camel
    _eq(c2s("fooBar"), "foo_bar")
    _eq(c2s("HTTPServer"), "http_server")
    _eq(c2s("parseXMLFile"), "parse_xml_file")
    _eq(c2s("getHTTPResponseCode"), "get_http_response_code")
    _eq(c2s("base64Encode"), "base64_encode")
    _eq(c2s("v2Beta"), "v2_beta")
    _eq(c2s("ipV4"), "ip_v4")
    _eq(c2s("HTTP2Server"), "http2_server")
    _eq(c2s("foo_Bar"), "foo_bar")
    _eq(c2s("already_snake"), "already_snake")
    _eq(c2s("ABC"), "abc")
    _eq(c2s("A"), "a")
    _eq(c2s("aB"), "a_b")
    _eq(c2s(""), "")
    _eq(s2c("http_server"), "httpServer")
    _eq(s2c("http_server", upper_first=True), "HttpServer")
    _eq(s2c("HTTP_SERVER"), "httpServer")
    _eq(s2c("a_1_b"), "a1B")
    _eq(s2c("__x__y_"), "xY")
    _eq(s2c("single"), "single")
    _eq(s2c("single", True), "Single")
    _eq(s2c(""), "")
    _raises(TypeError, c2s, None)
    _raises(TypeError, s2c, 5)


def main(argv=None):
    try:
        _checks(_load(argv or sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - evaluator output is the retry signal
        print(f"hidden test failed for task_e08_case_convert: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
