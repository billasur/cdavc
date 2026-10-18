import unittest

from cdavc.graph import GraphError, TaskGraph


class TaskGraphTests(unittest.TestCase):
    def test_valid_graph_returns_tasks_in_dependency_order(self):
        graph = TaskGraph.from_dict(
            {
                "project_id": "demo",
                "tasks": [
                    {"id": "B", "title": "second", "dependencies": ["A"], "implementation_files": ["src/b.py"], "test_files": ["tests/test_b.py"]},
                    {"id": "A", "title": "first", "dependencies": [], "implementation_files": ["src/a.py"], "test_files": ["tests/test_a.py"]},
                ],
            }
        )

        self.assertEqual([task.id for task in graph.runnable_tasks(set())], ["A"])
        self.assertEqual([task.id for task in graph.runnable_tasks({"A"})], ["B"])

    def test_graph_rejects_unknown_dependency_and_escape_path(self):
        with self.assertRaises(GraphError):
            TaskGraph.from_dict(
                {
                    "project_id": "demo",
                    "tasks": [{"id": "A", "title": "bad", "dependencies": ["missing"], "implementation_files": ["../secret.py"], "test_files": []}],
                }
            )

    def test_graph_rejects_unknown_dependency(self):
        with self.assertRaisesRegex(GraphError, "unknown dependencies"):
            TaskGraph.from_dict(
                {
                    "project_id": "demo",
                    "tasks": [{"id": "A", "title": "bad", "dependencies": ["missing"], "implementation_files": ["src/a.py"], "test_files": ["tests/a.py"]}],
                }
            )

    def test_graph_rejects_dependency_cycles(self):
        with self.assertRaises(GraphError):
            TaskGraph.from_dict(
                {
                    "project_id": "demo",
                    "tasks": [
                        {"id": "A", "title": "a", "dependencies": ["B"], "implementation_files": ["src/a.py"], "test_files": []},
                        {"id": "B", "title": "b", "dependencies": ["A"], "implementation_files": ["src/b.py"], "test_files": []},
                    ],
                }
            )

    def test_graph_rejects_malformed_top_level_payloads(self):
        malformed_payloads = [
            None,
            {},
            {"project_id": 42, "tasks": []},
            {"project_id": "", "tasks": [{"id": "A", "title": "a", "implementation_files": ["src/a.py"]}]},
            {"project_id": "demo", "tasks": []},
            {"project_id": "demo", "tasks": "tasks"},
        ]

        for payload in malformed_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(GraphError):
                    TaskGraph.from_dict(payload)

    def test_graph_rejects_non_object_tasks_and_duplicate_ids(self):
        with self.assertRaises(GraphError):
            TaskGraph.from_dict({"project_id": "demo", "tasks": ["task"]})

        task = {"id": "A", "title": "first", "implementation_files": ["src/a.py"]}
        with self.assertRaises(GraphError):
            TaskGraph.from_dict({"project_id": "demo", "tasks": [task, dict(task)]})

    def test_graph_rejects_invalid_task_fields_commands_and_retries(self):
        cases = [
            {"id": "A", "title": "", "implementation_files": ["src/a.py"]},
            {"id": "A", "title": "a", "implementation_files": ["src/a.py"], "dependencies": "A"},
            {"id": "A", "title": "a", "implementation_files": ["src/a.py"], "test_command": []},
            {"id": "A", "title": "a", "implementation_files": ["src/a.py"], "test_command": ["python", ""]},
            {"id": "A", "title": "a", "implementation_files": ["src/a.py"], "negative_test_command": "python"},
            {"id": "A", "title": "a", "implementation_files": ["src/a.py"], "max_retries": -1},
            {"id": "A", "title": "a", "implementation_files": ["src/a.py"], "max_retries": 6},
            {"id": "A", "title": "a", "implementation_files": ["src/a.py"], "max_retries": True},
        ]

        for task in cases:
            with self.subTest(task=task):
                with self.assertRaises(GraphError):
                    TaskGraph.from_dict({"project_id": "demo", "tasks": [task]})

    def test_graph_rejects_unsafe_implementation_and_test_paths(self):
        unsafe_paths = ["/tmp/model.py", "../secret.py", "src/../../secret.py", "."]
        for path in unsafe_paths:
            with self.subTest(path=path):
                with self.assertRaises(GraphError):
                    TaskGraph.from_dict(
                        {
                            "project_id": "demo",
                            "tasks": [{"id": "A", "title": "a", "implementation_files": [path]}],
                        }
                    )

        with self.assertRaises(GraphError):
            TaskGraph.from_dict(
                {
                    "project_id": "demo",
                    "tasks": [{"id": "A", "title": "a", "implementation_files": ["src/a.py"], "test_files": ["../test_a.py"]}],
                }
            )

    def test_runnable_tasks_follow_dependency_completion_and_declaration_order(self):
        graph = TaskGraph.from_dict(
            {
                "project_id": "demo",
                "tasks": [
                    {"id": "C", "title": "third", "dependencies": ["B"], "implementation_files": ["src/c.py"]},
                    {"id": "A", "title": "first", "implementation_files": ["src/a.py"]},
                    {"id": "B", "title": "second", "dependencies": ["A"], "implementation_files": ["src/b.py"]},
                ],
            }
        )

        self.assertEqual([task.id for task in graph.runnable_tasks(set())], ["A"])
        self.assertEqual([task.id for task in graph.runnable_tasks({"A"})], ["B"])
        self.assertEqual([task.id for task in graph.runnable_tasks({"A", "B"})], ["C"])
        self.assertEqual(graph.task("B").dependencies, ("A",))


if __name__ == "__main__":
    unittest.main()
