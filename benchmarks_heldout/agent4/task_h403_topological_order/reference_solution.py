"""Lexicographically smallest topological ordering of a directed graph."""

import heapq


def topological_order(graph: dict[str, list[str]]) -> list[str]:
    nodes = set(graph)
    for successors in graph.values():
        nodes.update(successors)
    indegree = {node: 0 for node in nodes}
    for successors in graph.values():
        for successor in successors:
            indegree[successor] += 1
    ready = [node for node in nodes if indegree[node] == 0]
    heapq.heapify(ready)
    order: list[str] = []
    while ready:
        node = heapq.heappop(ready)
        order.append(node)
        for successor in graph.get(node, ()):
            indegree[successor] -= 1
            if indegree[successor] == 0:
                heapq.heappush(ready, successor)
    if len(order) != len(nodes):
        raise ValueError("graph contains a cycle")
    return order
