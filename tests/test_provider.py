import json
import socket
import unittest
from urllib.request import Request

from cdavc.providers import (
    MockProvider,
    OpenAICompatibleProvider,
    ProviderUnavailableError,
    SamplingParams,
)


class ProviderTests(unittest.TestCase):
    def test_provider_rejects_non_positive_timeout(self):
        with self.assertRaises(ValueError):
            OpenAICompatibleProvider("https://example.test", timeout=0)

    def test_provider_rejects_empty_endpoint(self):
        with self.assertRaises(ProviderUnavailableError):
            OpenAICompatibleProvider("").complete([])

    def test_provider_supports_non_introspectable_request_opener(self):
        class Opener:
            __signature__ = object()

            def __call__(self, request):
                class Response:
                    def __enter__(self):
                        return self

                    def __exit__(self, *args):
                        return False

                    def read(self):
                        return b'{"choices": [{"message": {"content": "ok"}}]}'

                return Response()

        self.assertEqual(OpenAICompatibleProvider("https://example.test", opener=Opener()).complete([]), "ok")
    def test_mock_provider_returns_scripted_responses_in_order(self):
        provider = MockProvider(["first", "second"])

        self.assertEqual(provider.complete([{"role": "user", "content": "hi"}]), "first")
        self.assertEqual(provider.complete([{"role": "user", "content": "again"}]), "second")

    def test_mock_provider_raises_when_script_is_exhausted(self):
        provider = MockProvider([])

        with self.assertRaises(ProviderUnavailableError):
            provider.complete([])

    def test_unavailable_mock_provider_raises_without_consuming_script(self):
        provider = MockProvider(["later"], available=False)

        with self.assertRaises(ProviderUnavailableError):
            provider.complete([])
        provider.available = True
        self.assertEqual(provider.complete([]), "later")

    def test_openai_compatible_provider_builds_request_and_parses_response(self):
        captured = {}

        def opener(request: Request):
            captured["request"] = request

            class Response:
                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

                def read(self):
                    return json.dumps(
                        {"choices": [{"message": {"content": "hello"}}]}
                    ).encode()

            return Response()

        provider = OpenAICompatibleProvider(
            "https://example.test/v1/chat/completions",
            api_key="secret",
            model="test-model",
            opener=opener,
        )

        self.assertEqual(
            provider.complete([{"role": "user", "content": "hi"}]), "hello"
        )
        request = captured["request"]
        self.assertEqual(request.full_url, "https://example.test/v1/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer secret")
        self.assertEqual(
            json.loads(request.data),
            {
                "model": "test-model",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )

    def test_openai_compatible_provider_rejects_malformed_response(self):
        def opener(request):
            class Response:
                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

                def read(self):
                    return b'{"choices": []}'

            return Response()

        provider = OpenAICompatibleProvider("https://example.test", opener=opener)

        with self.assertRaises(ValueError):
            provider.complete([])

    def test_openai_compatible_provider_rejects_non_string_content(self):
        def opener(request):
            class Response:
                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

                def read(self):
                    return b'{"choices": [{"message": {"content": null}}]}'

            return Response()

        with self.assertRaises(ValueError):
            OpenAICompatibleProvider("https://example.test", opener=opener).complete([])

    def test_openai_compatible_provider_passes_configured_timeout_to_opener(self):
        captured = {}

        def opener(request, *, timeout):
            captured["timeout"] = timeout

            class Response:
                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

                def read(self):
                    return b'{"choices": [{"message": {"content": "ok"}}]}'

            return Response()

        provider = OpenAICompatibleProvider("https://example.test", timeout=2.5, opener=opener)

        self.assertEqual(provider.complete([]), "ok")
        self.assertEqual(captured["timeout"], 2.5)

    def test_openai_compatible_provider_normalizes_timeout_error(self):
        def opener(request, *, timeout):
            raise socket.timeout("timed out")

        provider = OpenAICompatibleProvider("https://example.test", opener=opener)

        with self.assertRaisesRegex(ProviderUnavailableError, "timed out"):
            provider.complete([])

    def test_sampling_parameters_are_sent_and_validated(self):
        captured = {}

        def opener(request: Request):
            captured["request"] = request

            class Response:
                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

                def read(self):
                    return json.dumps(
                        {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}
                    ).encode()

            return Response()

        provider = OpenAICompatibleProvider(
            "https://example.test",
            opener=opener,
            sampling=SamplingParams(temperature=1.0, top_p=0.95, top_k=20, max_tokens=32768),
        )
        completion = provider.complete_with_metadata([])

        self.assertEqual(
            json.loads(captured["request"].data),
            {
                "model": "gpt-4o-mini",
                "messages": [],
                "temperature": 1.0,
                "top_p": 0.95,
                "top_k": 20,
                "max_tokens": 32768,
            },
        )
        self.assertEqual(completion.metadata["finish_reason"], "stop")

        with self.assertRaises(ValueError):
            SamplingParams(temperature=4.0)
        with self.assertRaises(ValueError):
            SamplingParams(top_p=1.5)
        with self.assertRaises(ValueError):
            SamplingParams(top_k=0)
        with self.assertRaises(ValueError):
            SamplingParams(max_tokens=0)
        # None everywhere is the default and serializes to no request fields.
        self.assertEqual(SamplingParams().request_fields(), {})

    def test_truncated_completion_reports_length_finish_reason(self):
        def opener(request: Request):
            class Response:
                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

                def read(self):
                    body = {"choices": [{"message": {"content": '{"files": {"a": '}, "finish_reason": "length"}]}
                    return json.dumps(body).encode()

            return Response()

        provider = OpenAICompatibleProvider("https://example.test", opener=opener)
        completion = provider.complete_with_metadata([])
        self.assertEqual(completion.metadata["finish_reason"], "length")


if __name__ == "__main__":
    unittest.main()
