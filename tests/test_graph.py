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


if __name__ == "__main__":
    unittest.main()
