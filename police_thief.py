"""Police vs thief chase on an undirected graph.

Input
-----
    N T P M
    X Y      (M lines, an undirected edge between buildings X and Y)

Output
------
    "YES" if the police officer can catch the thief, otherwise "NO".

The thief escapes when any of the following holds:
  * there is no path from the police's building to the thief's building;
  * the thief sits on a cycle made of 4 or more buildings;
  * some cycle of 4 or more buildings exists that the thief reaches strictly
    faster than the police (the first case is just this one with distance 0).

Written for Python 3.8.1 (no walrus-free restrictions needed, but nothing
newer than 3.8 is used).
"""

import sys
from collections import deque

MIN_CYCLE = 4


def bfs(source, adj, n):
    """Number of moves from `source` to every building (-1 when unreachable)."""
    dist = [-1] * n
    if not (0 <= source < n):
        return dist
    dist[source] = 0
    queue = deque([source])
    while queue:
        node = queue.popleft()
        for nxt in adj[node]:
            if dist[nxt] == -1:
                dist[nxt] = dist[node] + 1
                queue.append(nxt)
    return dist


def buildings_on_long_cycle(adj, n):
    """Mark every building that belongs to a simple cycle of >= MIN_CYCLE nodes.

    Each cycle is enumerated once, from its smallest-numbered building, so the
    search only walks nodes greater than the start.  N <= 20 keeps this cheap,
    and the search stops as soon as every building is already marked.
    """
    marked = [False] * n
    remaining = [n]  # how many buildings are still unmarked

    def mark(path):
        for node in path:
            if not marked[node]:
                marked[node] = True
                remaining[0] -= 1

    def walk(start, node, path, in_path):
        for nxt in adj[node]:
            if nxt == start:
                if len(path) >= MIN_CYCLE:
                    mark(path)
                    if remaining[0] == 0:
                        return True
            elif nxt > start and not in_path[nxt]:
                in_path[nxt] = True
                path.append(nxt)
                if walk(start, nxt, path, in_path):
                    return True
                path.pop()
                in_path[nxt] = False
        return False

    for start in range(n):
        in_path = [False] * n
        in_path[start] = True
        if walk(start, start, [start], in_path):
            break
    return marked


def can_police_catch(n, thief, police, edges):
    adj = [[] for _ in range(n)]
    for x, y in edges:
        if x == y:
            continue
        if y not in adj[x]:
            adj[x].append(y)
            adj[y].append(x)

    dist_police = bfs(police, adj, n)
    dist_thief = bfs(thief, adj, n)

    # The thief is out of reach entirely.
    if dist_police[thief] == -1:
        return False

    # Any big cycle the thief reaches first is a safe haven forever.
    for node, on_cycle in enumerate(buildings_on_long_cycle(adj, n)):
        if not on_cycle:
            continue
        if dist_thief[node] == -1:
            continue
        if dist_police[node] == -1 or dist_thief[node] < dist_police[node]:
            return False

    return True


def main():
    data = sys.stdin.read().split()
    if not data:
        return
    values = list(map(int, data))
    n, thief, police, m = values[0], values[1], values[2], values[3]
    edges = []
    idx = 4
    for _ in range(m):
        edges.append((values[idx], values[idx + 1]))
        idx += 2
    print("YES" if can_police_catch(n, thief, police, edges) else "NO")


if __name__ == "__main__":
    main()
