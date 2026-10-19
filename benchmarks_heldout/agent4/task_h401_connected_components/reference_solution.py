"""Count the connected components of an undirected graph."""


def connected_components(graph: dict[str, list[str]]) -> int:
    adjacency: dict[str, set[str]] = {}
    for node, neighbours in graph.items():
        adjacency.setdefault(node, set())
        for other in neighbours:
            adjacency[node].add(other)
            adjacency.setdefault(other, set()).add(node)
    seen: set[str] = set()
    count = 0
    for node in adjacency:
        if node in seen:
            continue
        count += 1
        seen.add(node)
        stack = [node]
        while stack:
            current = stack.pop()
            for neighbour in adjacency[current]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)
    return count
