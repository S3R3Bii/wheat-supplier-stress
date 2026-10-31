"""Exact finite-network allocation; capacities are caller-supplied scenario assumptions."""

from collections import deque
from fractions import Fraction


def maximum_flow(supplies, routes, demands):
    """Return a feasible maximum flow using rational residual augmentation."""
    origins = sorted(supplies, key=int)
    importers = sorted(demands, key=int)
    graph = {"source": {}, "sink": {}}
    original = {}

    def edge(start, end, value):
        capacity = Fraction(value)
        if capacity < 0:
            raise ValueError("Negative capacity")
        graph.setdefault(start, {})[end] = capacity
        graph.setdefault(end, {})[start] = Fraction()
        original[start, end] = capacity

    for origin in origins:
        edge("source", "origin:" + str(origin), supplies[origin])
    for origin in origins:
        for importer in importers:
            edge(
                "origin:" + str(origin),
                "importer:" + str(importer),
                routes.get((origin, importer), 0),
            )
    for importer in importers:
        edge("importer:" + str(importer), "sink", demands[importer])
    total = Fraction()
    augmentations = 0
    while True:
        previous = {"source": None}
        queue = deque(["source"])
        while queue and "sink" not in previous:
            current = queue.popleft()
            for neighbor, remaining in graph[current].items():
                if remaining > 0 and neighbor not in previous:
                    previous[neighbor] = current
                    queue.append(neighbor)
        if "sink" not in previous:
            break
        path = []
        current = "sink"
        while previous[current] is not None:
            path.append((previous[current], current))
            current = previous[current]
        amount = min(graph[a][b] for a, b in path)
        for a, b in path:
            graph[a][b] -= amount
            graph[b][a] += amount
        total += amount
        augmentations += 1
    flows = {
        key: capacity - graph[key[0]][key[1]] for key, capacity in original.items()
    }
    return total, flows, augmentations


def separate_country_claims(supplies, routes, demands):
    """Each country independently uses the same supplies; the sum need not be jointly feasible."""
    return {
        importer: min(
            Fraction(demand),
            sum(
                (
                    min(Fraction(supply), Fraction(routes.get((origin, importer), 0)))
                    for origin, supply in supplies.items()
                ),
                Fraction(),
            ),
        )
        for importer, demand in demands.items()
    }
