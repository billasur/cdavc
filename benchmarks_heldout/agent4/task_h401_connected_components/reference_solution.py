"""Count the connected components of an undirected graph."""


def connected_components(graph: dict[str, list[str]]) -> int:
    nodes = set(graph)
    for neighbours in graph.values():
        nodes.update(neighbours)
    seen: set[str] = set()
    count = 0
    for node in nodes:
        if node in seen:
            continue
        count += 1
        seen.add(node)
        stack = [node]
        while stack:
            current = stack.pop()
            for neighbour in graph.get(current, ()):
                if neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)
    return count
