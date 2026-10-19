"""Check whether an undirected graph is bipartite."""


def is_bipartite(graph: dict[str, list[str]]) -> bool:
    nodes = set(graph)
    for neighbours in graph.values():
        nodes.update(neighbours)
    colour: dict[str, int] = {}
    for start in nodes:
        if start in colour:
            continue
        colour[start] = 0
        stack = [start]
        while stack:
            node = stack.pop()
            for neighbour in graph.get(node, ()):
                if neighbour == node:
                    return False
                if neighbour not in colour:
                    colour[neighbour] = 1 - colour[node]
                    stack.append(neighbour)
                elif colour[neighbour] == colour[node]:
                    return False
    return True
