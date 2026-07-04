"""
ALG26 test snippet: choose Dijkstra or Bellman-Ford.

Expected knowledge-base summary:
Dijkstra is appropriate only when all edge weights are non-negative.
Bellman-Ford handles negative edges and detects negative cycles by checking
whether a further relaxation is still possible after |V|-1 rounds.

Expected tags:
shortest path, Dijkstra, Bellman-Ford, negative edge, relaxation
"""

from __future__ import annotations


def dijkstra_nonnegative(graph: dict[str, list[tuple[str, int]]], source: str) -> dict[str, float]:
    import heapq

    dist = {node: float("inf") for node in graph}
    dist[source] = 0
    heap = [(0, source)]

    while heap:
        current, u = heapq.heappop(heap)
        if current != dist[u]:
            continue

        for v, weight in graph[u]:
            if weight < 0:
                raise ValueError("Dijkstra requires non-negative edge weights")

            candidate = current + weight
            if candidate < dist[v]:
                dist[v] = candidate
                heapq.heappush(heap, (candidate, v))

    return dist


def bellman_ford(
    vertices: list[str],
    edges: list[tuple[str, str, int]],
    source: str,
) -> tuple[dict[str, float], bool]:
    dist = {node: float("inf") for node in vertices}
    dist[source] = 0

    for _ in range(len(vertices) - 1):
        changed = False
        for u, v, weight in edges:
            if dist[u] + weight < dist[v]:
                dist[v] = dist[u] + weight
                changed = True
        if not changed:
            break

    has_negative_cycle = any(dist[u] + weight < dist[v] for u, v, weight in edges)
    return dist, has_negative_cycle


if __name__ == "__main__":
    vertices = ["s", "a", "b", "c"]
    edges = [("s", "a", 2), ("s", "b", 5), ("a", "b", -4), ("b", "c", 3)]
    print(bellman_ford(vertices, edges, "s"))
