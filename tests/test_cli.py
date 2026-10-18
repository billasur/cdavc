import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from cdavc.cli import main


class CliTests(unittest.TestCase):
    def test_missing_graph_reports_location_without_traceback(self):
        missing = Path(tempfile.gettempdir()) / "cdavc-missing-task-graph.json"
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            status = main([str(missing), "--mock-response", str(missing)])

        output = stderr.getvalue()
        self.assertNotEqual(status, 0)
        self.assertIn(str(missing), output)
        self.assertIn("No such file", output)
        self.assertNotIn("Traceback", output)

    def test_openai_provider_requires_endpoint(self):
        missing = Path(tempfile.gettempdir()) / "cdavc-missing-endpoint-graph.json"
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            status = main([str(missing), "--provider", "openai"])

        self.assertEqual(status, 2)
        self.assertIn("--endpoint", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
