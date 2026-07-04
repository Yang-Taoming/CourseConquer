"""
ALG26 test snippet: KMP prefix function.

Expected knowledge-base summary:
Compute the KMP prefix table in linear time. On mismatch, the pattern index
falls back by using the previous prefix value, so the text pointer never needs
to move backward during search.

Expected tags:
KMP, string matching, prefix function, linear time
"""


def compute_pi(pattern: str) -> list[int]:
    pi = [0] * len(pattern)
    j = 0

    for i in range(1, len(pattern)):
        while j > 0 and pattern[i] != pattern[j]:
            j = pi[j - 1]

        if pattern[i] == pattern[j]:
            j += 1
            pi[i] = j

    return pi


def kmp_search(text: str, pattern: str) -> list[int]:
    if not pattern:
        return list(range(len(text) + 1))

    pi = compute_pi(pattern)
    matches = []
    j = 0

    for i, char in enumerate(text):
        while j > 0 and char != pattern[j]:
            j = pi[j - 1]

        if char == pattern[j]:
            j += 1

        if j == len(pattern):
            matches.append(i - len(pattern) + 1)
            j = pi[j - 1]

    return matches


if __name__ == "__main__":
    print(compute_pi("ababaca"))
    print(kmp_search("bacbababadababacambabacaddababacasdsd", "ababaca"))
