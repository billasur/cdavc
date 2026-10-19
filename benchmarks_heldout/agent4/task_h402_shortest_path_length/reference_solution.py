"""Fewest edges between two nodes of an unweighted undirected graph."""

from collections import deque


def shortest_path_length(graph: dict[str, list[str]], start: str, goal: str) -> int:
    if start == goal:
        return 0
    visited = {start}
    queue = deque([(start, 0)])
    while queue:
        node, distance = queue.popleft()
        for neighbour in graph.get(node, ()):
            if neighbour == goal:
                return distance + 1
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append((neighbour, distance + 1))
    return -1
