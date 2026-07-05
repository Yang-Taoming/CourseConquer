# ALG26 算法基础测试问题与理论正确答案

本文档用于测试 `test_data` 中算法基础资料的解析、检索、问答和跨文件一致性能力。问题覆盖 TXT、DOCX、PDF、CSV、代码文件和 OCR 图片中的核心知识点。

## 一、基础检索

### 1. BFS 和 DFS 的时间复杂度是多少？

理论正确答案：BFS 和 DFS 的时间复杂度都是 `Theta(V + E)`，其中 `V` 是顶点数，`E` 是边数。

### 2. Dijkstra 适用于什么类型的边权？

理论正确答案：Dijkstra 适用于所有边权非负的图，通常用于单源最短路径问题。如果存在负权边，不应使用普通 Dijkstra。

### 3. Bellman-Ford 和 Dijkstra 的主要区别是什么？

理论正确答案：Dijkstra 要求边权非负，通常配合堆可达到 `O(E log V)`；Bellman-Ford 可以处理负权边，并且可以检测负权环，时间复杂度通常是 `Theta(VE)`。

### 4. Floyd-Warshall 是解决什么问题的？复杂度是多少？

理论正确答案：Floyd-Warshall 用于求所有点对之间的最短路径，时间复杂度是 `Theta(V^3)`。它通常适合较小或较稠密的图。

### 5. Edmonds-Karp 和 Dinic 分别用于什么问题？复杂度是多少？

理论正确答案：Edmonds-Karp 和 Dinic 都用于最大流问题。Edmonds-Karp 的复杂度是 `O(VE^2)`，Dinic 在一般图上的复杂度是 `O(V^2E)`。

### 6. 哪些算法可以用于最短路径问题？

理论正确答案：BFS 可用于无权图最短路径；Dijkstra 用于非负权图的单源最短路径；Bellman-Ford 用于允许负权边的单源最短路径，并可检测负权环；Floyd-Warshall 用于所有点对最短路径。

### 7. 哪些算法可以用于最大流问题？

理论正确答案：Edmonds-Karp 和 Dinic 都是最大流算法。

### 8. 图算法里哪些算法的复杂度是 `Theta(V + E)`？

理论正确答案：BFS 和 DFS 的复杂度是 `Theta(V + E)`。

## 二、代码理解

### 9. `kmp_prefix_function.py` 里的 `compute_pi` 函数是做什么的？

理论正确答案：`compute_pi` 用于计算 KMP 算法中的前缀函数数组 `pi`。`pi[i]` 表示模式串 `pattern[0..i]` 的最长相等真前缀和真后缀长度。

### 10. KMP 为什么在失配时不用回退文本指针？

理论正确答案：KMP 在失配时利用前缀函数让模式串指针 `j` 回退到 `pi[j - 1]`，保留已经匹配的信息，因此文本指针不需要回退，整体匹配可以在线性时间内完成。

### 11. `kmp_search` 找到一次匹配后，为什么要执行 `j = pi[j - 1]`？

理论正确答案：这样可以继续寻找可能重叠的下一次匹配。匹配完成后，模式串指针回退到最长可复用前后缀的位置，而不是从头开始。

### 12. `dijkstra_vs_bellman_ford.py` 里为什么 Dijkstra 要检查 `weight < 0`？

理论正确答案：因为 Dijkstra 的正确性依赖边权非负。如果存在负权边，已经确定的最短距离可能之后又被更短路径更新，破坏算法假设，所以代码遇到负权边会抛出异常。

### 13. Bellman-Ford 是如何检测负权环的？

理论正确答案：Bellman-Ford 先进行 `|V| - 1` 轮松弛。如果之后仍然存在某条边 `(u, v, weight)` 可以继续松弛，即 `dist[u] + weight < dist[v]`，说明存在从源点可达的负权环。

### 14. C++ 文件用什么数据结构保存算法信息？

理论正确答案：C++ 文件使用 `std::vector<AlgorithmFact>` 保存算法信息，每个 `AlgorithmFact` 记录算法名称、任务、复杂度和适用条件。

### 15. C 文件里的 `AlgorithmFact` 结构体包含哪些字段？

理论正确答案：`AlgorithmFact` 结构体包含 `name`、`task`、`complexity` 和 `condition` 四类信息，用于描述算法名称、问题任务、复杂度和适用条件。

### 16. C++ 文件中哪些算法的任务是 `maximum flow`？

理论正确答案：Edmonds-Karp 和 Dinic 的任务是 `maximum flow`。

## 三、算法对比

### 17. Dijkstra 和 Bellman-Ford 应该分别在什么情况下使用？

理论正确答案：当所有边权非负时，可以使用 Dijkstra；当图中可能存在负权边时，应使用 Bellman-Ford。如果需要检测负权环，也应使用 Bellman-Ford。

### 18. Bellman-Ford 和 Floyd-Warshall 都能处理哪些最短路径问题？区别是什么？

理论正确答案：Bellman-Ford 解决单源最短路径问题，可以处理负权边并检测负权环，复杂度为 `Theta(VE)`；Floyd-Warshall 解决所有点对最短路径问题，复杂度为 `Theta(V^3)`，通常要求不存在会使最短路径无定义的负权环。

### 19. Edmonds-Karp 和 Dinic 的复杂度有什么不同？

理论正确答案：Edmonds-Karp 的复杂度是 `O(VE^2)`；Dinic 在一般图上的复杂度是 `O(V^2E)`。二者都用于最大流，但 Dinic 使用层次图和阻塞流思想。

### 20. Merge Sort 和 Heap Sort 的复杂度相同吗？稳定性和原地性有什么区别？

理论正确答案：二者的主要时间复杂度都可以达到 `O(n log n)`。Merge Sort 是稳定排序，但通常不是原地排序；Heap Sort 是原地排序，但不是稳定排序。

### 21. Counting Sort 和比较排序有什么不同？

理论正确答案：Counting Sort 是非比较排序，适用于键值范围较小的整数排序，复杂度为 `O(n + k)`。比较排序通过元素之间的比较确定顺序，通用比较排序的下界通常是 `Omega(n log n)`。

### 22. KMP 相比普通字符串匹配的优势是什么？

理论正确答案：KMP 使用前缀函数避免文本指针回退，匹配过程可以达到 `Theta(m + n)`，其中 `m` 是模式串长度，`n` 是文本长度。

### 23. 0-1 Knapsack 为什么是 pseudo-polynomial time？

理论正确答案：0-1 背包的动态规划复杂度通常是 `Theta(nW)`，其中 `W` 是容量数值。复杂度依赖数值大小而不是输入编码长度的多项式，因此称为伪多项式时间。

### 24. BFS 为什么可以用于无权图最短路径？

理论正确答案：在无权图中，每条边的代价都可视为 1。BFS 按层次从源点向外扩展，第一次访问到某个顶点时经过的边数最少，因此可求无权图最短路径。

## 四、CSV 表格检索

### 25. CSV 里有哪些算法属于 `graph` 类别？

理论正确答案：CSV 中属于 `graph` 类别的算法包括 BFS、DFS、Kruskal、Dijkstra、Bellman-Ford、Floyd-Warshall、Edmonds-Karp 和 Dinic。

### 26. CSV 里哪些算法属于 `sorting` 类别？

理论正确答案：CSV 中属于 `sorting` 类别的算法包括 Insertion Sort、Merge Sort、Heap Sort 和 Counting Sort。

### 27. CSV 中 Counting Sort 的适用条件是什么？

理论正确答案：Counting Sort 适用于键值处于较小整数范围内的情况，即 `keys in a small integer range`。

### 28. CSV 中 KMP 的 `key_note` 是什么？

理论正确答案：KMP 的关键说明是前缀函数可以防止文本指针回退，即 `prefix function prevents text pointer rollback`。

### 29. CSV 中复杂度为 `Theta(n log n)` 的算法是哪一个？

理论正确答案：Merge Sort 的复杂度是 `Theta(n log n)`。

### 30. CSV 中问题为 `single-source shortest path` 的算法有哪些？

理论正确答案：Dijkstra 和 Bellman-Ford 的问题类型是 `single-source shortest path`。

### 31. CSV 中适用条件包含 `negative edges allowed` 的算法是什么？

理论正确答案：Bellman-Ford 的适用条件是 `negative edges allowed`。

### 32. CSV 中 0-1 Knapsack 的复杂度是多少？

理论正确答案：0-1 Knapsack 的复杂度是 `Theta(nW)`。

## 五、红黑树

### 33. 红黑树有哪五条性质？

理论正确答案：每个节点是红色或黑色；根节点是黑色；NIL 叶子是黑色；红色节点的孩子都是黑色；从任一节点到其后代 NIL 叶子的所有路径包含相同数量的黑色节点。

### 34. 红黑树插入修复中，叔父节点是红色时怎么处理？

理论正确答案：将父节点和叔父节点变为黑色，将祖父节点变为红色，然后从祖父节点继续向上修复。

### 35. 叔父节点是黑色且新节点是 inner child shape 时怎么处理？

理论正确答案：先进行一次旋转，将 inner child 形态转换为 outer child 形态，然后进入 outer child 的处理情况。

### 36. 叔父节点是黑色且新节点是 outer child shape 时怎么处理？

理论正确答案：将父节点变为黑色，将祖父节点变为红色，然后在祖父节点处进行旋转，以恢复红黑树性质。

### 37. 这份红黑树资料有没有提供完整代码？

理论正确答案：没有。资料只提供红黑树性质和插入修复情况概要，没有提供完整实现或完整伪代码。

### 38. 为什么红黑树需要旋转和变色？

理论正确答案：插入新节点可能破坏“红色节点不能有红色孩子”和黑高一致性等性质。变色用于调整局部颜色关系，旋转用于改变局部结构，二者共同恢复红黑树平衡约束。

## 六、OCR 图片测试

### 39. 图片里 BFS 和 DFS 的复杂度是多少？

理论正确答案：图片中 BFS 和 DFS 的复杂度是 `Theta(V + E)`。

### 40. 图片里哪个算法只能用于非负权边？

理论正确答案：图片中 Dijkstra 被标注为只适用于非负权边，即 `non-negative weights only`。

### 41. 图片里哪个算法可以检测负权环？

理论正确答案：图片中 Bellman-Ford 可以检测负权环，并且支持负权边。

### 42. 图片里 Floyd-Warshall 的用途是什么？

理论正确答案：图片中 Floyd-Warshall 用于所有点对最短路径，即 `all-pairs shortest paths`。

### 43. 图片里 Edmonds-Karp 和 Dinic 的复杂度分别是多少？

理论正确答案：图片中 Edmonds-Karp 的复杂度是 `O(VE^2)`，Dinic 的复杂度是 `O(V^2E)`。

### 44. OCR 是否应该正确识别 `Theta(V + E)`、`Theta(V^3)`、`O(VE^2)` 和 `O(V^2E)`？

理论正确答案：是。该图片测试的关键之一就是 OCR 是否能正确识别复杂度表达式中的希腊字母含义、括号、加号和指数。

## 七、跨文件一致性

### 45. TXT、DOCX、C、C++ 文件中对 BFS/DFS 复杂度的描述是否一致？

理论正确答案：一致。它们都表达 BFS 和 DFS 的复杂度为 `Theta(V + E)`。

### 46. 图片、TXT 和 CSV 中都提到了哪些图算法？

理论正确答案：它们共同提到了 BFS、DFS、Dijkstra、Bellman-Ford、Floyd-Warshall、Edmonds-Karp 和 Dinic。

### 47. Dijkstra 的适用条件在 Python、CSV、TXT 和图片中是否一致？

理论正确答案：一致。它们都说明 Dijkstra 要求非负权边。

### 48. Bellman-Ford 的负权环检测能力在哪些文件中出现过？

理论正确答案：该能力出现在 Python 代码、TXT/DOCX 图算法笔记、OCR 图片以及期望抽取结果中。CSV 中强调 Bellman-Ford 允许负权边，关键说明也包含检测负权环。

### 49. 最大流算法在 TXT、CSV、C++ 和图片中分别是怎么写的？

理论正确答案：这些文件都将 Edmonds-Karp 和 Dinic 归为最大流算法。Edmonds-Karp 的复杂度为 `O(VE^2)`，Dinic 的复杂度为 `O(V^2E)`。

### 50. 同一个图算法知识点在代码文件和课程笔记文件中表达有什么区别？

理论正确答案：课程笔记通常用自然语言总结算法用途、条件和复杂度；代码文件可能通过注释、结构体、数组、`vector` 或函数实现来表达同样知识。问答系统应能从不同文件格式中抽取一致的算法事实。

## 八、综合应用

### 51. 如果图中存在负权边但没有负权环，应该选择哪个最短路径算法？

理论正确答案：应选择 Bellman-Ford，因为它允许负权边，并能检测负权环。

### 52. 如果要解决所有点对之间的最短路径，应该用哪个算法？

理论正确答案：应该使用 Floyd-Warshall，特别是在图较小或较稠密时。

### 53. 如果图是无权图，要求单源最短路径，可以用哪个算法？

理论正确答案：可以使用 BFS，因为无权图中 BFS 按层扩展，第一次到达节点时对应最短边数。

### 54. 如果要做字符串模式匹配，并避免文本指针回退，可以用哪个算法？

理论正确答案：可以使用 KMP。KMP 通过前缀函数避免文本指针回退，匹配复杂度为 `Theta(m + n)`。

### 55. 如果要对小范围整数排序，应该考虑哪个排序算法？

理论正确答案：应该考虑 Counting Sort，因为它适用于键值范围较小的整数排序，复杂度为 `O(n + k)`。

### 56. 如果要解决容量约束选择问题，CSV 中对应的是哪个算法？

理论正确答案：CSV 中对应的是 0-1 Knapsack，复杂度为 `Theta(nW)`。

### 57. 如果要复习算法基础期末考试，哪些材料最适合作为复习提纲？

理论正确答案：`ALG26_Exam_Review.pdf` 最适合作为总体复习提纲，因为它覆盖算法基础、递归、排序、分治、数据结构、动态规划、贪心、图算法、字符串匹配和复杂度对比等主题。图算法 TXT/DOCX、CSV 和代码文件可作为补充材料。

### 58. 请按“排序、图算法、动态规划、字符串匹配”整理 test_data 中出现的算法。

理论正确答案：

- 排序：Insertion Sort、Merge Sort、Heap Sort、Counting Sort。
- 图算法：BFS、DFS、Kruskal、Dijkstra、Bellman-Ford、Floyd-Warshall、Edmonds-Karp、Dinic。
- 动态规划：LCS、0-1 Knapsack、Floyd-Warshall。
- 字符串匹配：KMP。

### 59. 如果一个查询问“哪个算法能检测 negative cycle”，理论答案是什么？

理论正确答案：Bellman-Ford 可以检测负权环。检测方式是在 `|V| - 1` 轮松弛后继续检查是否仍有边可以被松弛。

### 60. 如果一个查询问“哪些资料能证明 Dijkstra 不支持负权边”，理论答案是什么？

理论正确答案：Python 代码中 `dijkstra_nonnegative` 遇到 `weight < 0` 会抛出异常；TXT/DOCX 和 OCR 图片说明 Dijkstra 只适用于非负权边；CSV 中 Dijkstra 的适用条件也是 `non-negative edge weights`。
