/*
 * ALG26 graph algorithms note in C.
 *
 * This file intentionally contains the same facts as the TXT, DOCX, and C++
 * samples, but encoded as C comments and simple data structures. It tests
 * whether the knowledge-base assistant can summarize C source files.
 *
 * Core facts:
 * - BFS and DFS: Theta(V + E)
 * - Dijkstra: single-source shortest path, non-negative weights only
 * - Bellman-Ford: supports negative edges and detects negative cycles
 * - Floyd-Warshall: all-pairs shortest paths, Theta(V^3)
 * - Edmonds-Karp: max flow, O(VE^2)
 * - Dinic: max flow, O(V^2E)
 */

#include <stdio.h>

typedef struct {
    const char *name;
    const char *task;
    const char *complexity;
    const char *condition;
} AlgorithmFact;

static const AlgorithmFact FACTS[] = {
    {"BFS", "unweighted shortest path", "Theta(V + E)", "unweighted graph"},
    {"DFS", "graph traversal", "Theta(V + E)", "directed or undirected graph"},
    {"Dijkstra", "single-source shortest path", "O(E log V)", "non-negative weights"},
    {"Bellman-Ford", "single-source shortest path", "Theta(VE)", "negative edges allowed"},
    {"Floyd-Warshall", "all-pairs shortest path", "Theta(V^3)", "no negative cycles"},
    {"Edmonds-Karp", "maximum flow", "O(VE^2)", "flow network"},
    {"Dinic", "maximum flow", "O(V^2E)", "flow network"}
};

int main(void) {
    int count = (int)(sizeof(FACTS) / sizeof(FACTS[0]));
    for (int i = 0; i < count; ++i) {
        printf("%s: %s, %s, %s\n",
               FACTS[i].name,
               FACTS[i].task,
               FACTS[i].complexity,
               FACTS[i].condition);
    }
    return 0;
}
