/*
 * ALG26 graph algorithms note in C++.
 *
 * This file mirrors the TXT, DOCX, and C samples. It is useful for testing
 * whether the knowledge-base assistant treats C++ source as code while still
 * extracting the same graph-algorithm knowledge.
 *
 * Core facts:
 * - BFS and DFS: Theta(V + E)
 * - Dijkstra: single-source shortest path, non-negative weights only
 * - Bellman-Ford: supports negative edges and detects negative cycles
 * - Floyd-Warshall: all-pairs shortest paths, Theta(V^3)
 * - Edmonds-Karp: max flow, O(VE^2)
 * - Dinic: max flow, O(V^2E)
 */

#include <iostream>
#include <string>
#include <vector>

struct AlgorithmFact {
    std::string name;
    std::string task;
    std::string complexity;
    std::string condition;
};

int main() {
    const std::vector<AlgorithmFact> facts = {
        {"BFS", "unweighted shortest path", "Theta(V + E)", "unweighted graph"},
        {"DFS", "graph traversal", "Theta(V + E)", "directed or undirected graph"},
        {"Dijkstra", "single-source shortest path", "O(E log V)", "non-negative weights"},
        {"Bellman-Ford", "single-source shortest path", "Theta(VE)", "negative edges allowed"},
        {"Floyd-Warshall", "all-pairs shortest path", "Theta(V^3)", "no negative cycles"},
        {"Edmonds-Karp", "maximum flow", "O(VE^2)", "flow network"},
        {"Dinic", "maximum flow", "O(V^2E)", "flow network"}
    };

    for (const auto& fact : facts) {
        std::cout << fact.name << ": "
                  << fact.task << ", "
                  << fact.complexity << ", "
                  << fact.condition << '\n';
    }
}
