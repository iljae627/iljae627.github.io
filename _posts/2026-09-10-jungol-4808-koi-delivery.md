---
title: "KOI 맛집 배달"
date: 2026-09-14 15:40:00 +0900
categories: [개발, Algorithm]
tags: [jungol, koi, cpp, tree-dp, centroid-decomposition, optimization]
math: true
---

<style>.post-tail-wrapper .license-wrapper { display: none; }</style>

## 1. 개요

이번에 해결해 본 문제는 [KOI 맛집 배달](https://jungol.co.kr/problem/4808)이다. 화면상의 기본 시간 제한은 3초이지만, 실행 시간을 **500ms 이내**로 대폭 줄여보는 것을 목표로 잡고 최적화를 진행했다.

문제는 **2021 KOI 2차 고등부 4번**에 출제된 문제다.

<!-- 이미지 자리: 정올 4808 문제 메인 화면 사진 -->
![정올 4808 문제 화면](/assets/img/koi-delivery/01-problem.png)
_KOI 맛집 배달 문제 화면._

---

## 2. 문제를 트리 위의 영역 선택으로 바꾸기

도시가 정점이고 길이 간선인 트리가 주어진다. 맛집 `i`에는 중심 도시 `c_i`, 배달 반경 `d_i`, 선호도 `g_i`가 있다. 배달 구역은 중심에서 거리가 반경 이하인 정점들의 집합이다.

선택한 맛집들의 배달 구역이 서로 겹치면 안 된다. 목표는 선택한 선호도의 합을 최대화하는 것이다.

두 맛집만 비교하면 겹침 조건은 간단하다.

$$\operatorname{dist}(c_i,c_j)\le d_i+d_j$$

하지만 맛집이 최대 10만 개라 모든 쌍을 비교하면 약 50억 쌍이다. 충돌 그래프를 직접 만들기보다 **배달 구역을 지웠을 때 남는 트리 구조**를 이용하는 아이디어를 떠올렸다.

공식 예제에서 최적 선택은 3·4·5번 맛집이다.

| 맛집 | 배달 구역 | 선호도 |
| --- | --- | ---: |
| 3번 | `{8}` | 5 |
| 4번 | `{1, 2, 3}` | 16 |
| 5번 | `{4, 5, 6}` | 32 |

세 구역은 서로소이므로 답은 `5 + 16 + 32 = 53`이다. 가장 높은 선호도 하나를 고르는 것만으로는 전체 최적해를 구할 수 없다.

---

## 3. 배달 구역의 가장 위 정점에 맛집을 배치하기

1번 도시를 루트로 잡는다. 트리에서 거리 제한으로 정의된 배달 구역은 연결되어 있으므로, 그 구역에서 깊이가 가장 작은 정점은 하나뿐이다. 이 정점을 `top(i)`라고 부르자.

`top(i)`는 중심 `c_i`에서 부모 방향으로 `min(d_i, depth[c_i])`번 올라간 정점이다. 반경이 루트까지의 거리보다 크다면 루트가 된다.

각 맛집을 `top(i)`에 묶어 두면, 배달 구역 전체가 해당 정점의 서브트리에 포함된다. 조상 탐색에는 이진 점프를 사용한다. 최대 깊이가 99,999이므로 `2^0`부터 `2^16`까지의 17개 점프가 충분하다.

### 3.1 DP 상태 정의

`dp[v]`를 다음과 같이 정의했다.

> 배달 구역 전체가 `v`의 서브트리 안에 들어가는 맛집들만 선택할 때 얻는 최대 선호도 합.

경우는 두 가지로 나뉜다.

**v를 덮지 않는 경우**에는 각 자식 서브트리를 독립적으로 해결한다.

$$dp[v] = \sum_{u:\ parent[u]=v}dp[u]$$

**v를 어떤 맛집 i가 덮는 경우**에는 `top(i)=v`여야 한다. 이 맛집의 배달 구역을 지우면 남는 부분은 여러 서브트리로 나뉜다. 남은 각 서브트리의 루트 `x`는 다음 조건을 만족한다.

$$\operatorname{dist}(c_i,x)=d_i+1$$

따라서 해당 맛집을 고르는 후보 값은 다음과 같다.

$$g_i + \sum_{\substack{x\in subtree(v)\\\operatorname{dist}(c_i,x)=d_i+1}}dp[x]$$

이 값들과 자식 DP 합 중 최댓값이 `dp[v]`가 된다.

### 3.2 점화식의 당위성

겹침이 금지되어 있으므로 `v`를 덮는 선택된 맛집은 최대 하나다. 없으면 선택 영역이 서로 다른 자식 서브트리를 가로질러 갈 수 없다. 가로지르는 연결 영역은 반드시 `v`를 지나기 때문이다.

맛집 `i`를 선택했다면 나머지 선택 영역은 `R_i`를 피해야 한다. 트리에서 연결된 영역 `R_i`를 제거한 뒤 남는 연결 성분끼리는 독립적이다. 각 성분은 경계 정점 `x`를 루트로 하는 서브트리이므로 최적값이 `dp[x]`가 된다. 각 경우를 빠짐없이 고려하고, 자식부터 계산하므로 귀납적으로 정답이 도출된다.

---

## 4. 경계 정점의 합을 빠르게 구하기

단순 구현에서는 맛집마다 경계 정점을 탐색하게 되며, 경계 크기가 클 수 있어 전체 비용이 `O(NM)`까지 증가한다.

이 문제를 해결하기 위해 필요한 연산은 다음 두 가지로 정리했다.

1. DP가 확정된 정점 `x`에 값 `dp[x]`를 등록한다.
2. 중심 `c`에서 **정확히 거리 r**인 등록된 정점들의 값을 합산한다.

여기서 구하는 것은 반경 이하 누적합이 아니라 **정확히 한 거리의 합**이라는 점에 주목했다. 센트로이드마다 거리별 배열을 두면 배열 원소를 바로 읽고 더할 수 있다. 이 차이 덕분에 Fenwick tree 같은 추가 로그 비용 없이 빠르게 접근할 수 있게 된다.

### 4.1 센트로이드 분할 적용

센트로이드는 제거했을 때 남는 각 연결 성분의 크기가 원래 크기의 절반 이하가 되는 정점이다. 이를 반복해서 분할하면 한 정점이 속하는 분할 단계가 `O(log N)`개다.

센트로이드 `z`마다 다음 정보를 유지하도록 구조를 설계했다.

| 배열 | 의미 |
| --- | --- |
| `total[z][t]` | 해당 분할 성분에서 `z`와 거리가 `t`인 등록 정점 값의 합 |
| `subtract[b][t]` | `z`를 제거했을 때 특정 가지 `b`에 들어가는 등록 정점 중 `z`와 거리가 `t`인 값의 합 |

중심 `c`의 센트로이드 조상 `z`에서 `t = r - dist(c,z)`라 놓으면, `total[z][t]`를 더하고 `c`가 들어 있는 가지의 `subtract[b][t]`를 뺀다. 음수 거리나 배열 범위 밖이면 기여도는 0이다.

같은 가지 내부에서는 실제 경로가 `z`를 지나지 않을 수 있으므로 그 부분을 빼야 한다. 두 정점이 처음으로 서로 다른 가지로 분리되는 단계에서는 실제 경로가 센트로이드를 지나고 거리의 합이 정확해진다. 이전 단계에서는 더한 뒤 빠지고 이후에는 상대 정점이 같은 분할 성분에 없으므로, 각 정점이 정확히 한 번 집계된다. `c` 자신이 센트로이드인 단계에는 빼야 할 가지가 없다.

### 4.2 서브트리 조건 유지

거리 합 자료구조에는 이미 확정된 DP만 넣는다. 구현은 루트에서 만든 BFS 순서를 역순으로 처리하므로 자손이 조상보다 먼저 등록된다.

`top(i)=v`이고 `v`가 루트가 아니면 `dist(c_i,v)=d_i`이다. `v`의 서브트리 바깥에서 거리 `d_i+1`에 도달할 수 있는 유일한 정점은 `parent[v]`다. 부모는 아직 처리되지 않았으므로 자료구조에 없다. 그보다 더 바깥 정점은 거리가 최소 `d_i+2`다.

따라서 전역 거리 질의를 해도 서브트리 바깥의 DP가 섞이지 않는다. `v`가 루트라면 애초에 바깥 정점이 없다. 같은 깊이의 다른 서브트리를 먼저 처리했더라도 이 성질은 유지된다.

**등록 시점** 역시 중요한 포인트다. `v`에 묶인 맛집을 전부 계산한 뒤 `dp[v]`를 한 번만 등록한다. 후보 맛집을 계산할 때마다 등록하면 같은 상태가 중복 반영된다.

---

## 5. 성능 최적화: 500ms 목표 달성을 위한 구조 개선

최초 구현에서도 시간복잡도는 `O((N+M) log N)`이었지만, 인접 리스트, 센트로이드 경로, 거리 배열을 여러 `vector`로 관리하면서 동적 할당과 오버헤드가 발생해 정올 채점 기준 시스템에서 500ms 상한을 안정적으로 충족하기 까다로웠다.

이를 개선하기 위해 메모리 배치와 구조체 관리를 최적화했다.

- **인접 리스트를 CSR 배열로 구성:** 정점별 이웃을 하나의 연속 배열에 저장하고 시작 위치로 접근하도록 개선했다.
- **센트로이드 경로를 고정 슬롯으로 저장:** 한 정점당 최대 18개 슬롯과 실제 개수를 둬 작은 벡터의 재할당을 없앴다.
- **거리별 합을 하나의 배열에 저장:** 각 버킷은 시작 오프셋과 길이만 가지도록 설계했다.
- **분할 탐색의 임시 배열 재사용:** 성분별로 탐색용 벡터를 새로 할당하지 않고 재사용했다.
- **빠른 I/O 적용:** 64KiB `fread` 버퍼를 이용해 입출력 속도를 극대화했다.

### 5.1 깊은 트리와 큰 정수 처리

일자 트리는 깊이가 10만에 가깝다. 일반 DFS를 깊이만큼 재귀 호출하면 스택 오버플로우가 생길 수 있어 원본 트리 탐색과 거리 수집은 반복문으로 처리했다. 재귀 호출은 깊이가 `O(log N)`으로 보장되는 센트로이드 분할에만 남겨두었다.

정답의 최댓값은 `10^5 × 10^9 = 10^14`까지 가능하므로, `dp`와 거리별 합 및 출력은 `long long`을 사용했다.

---

## 6. 제출 및 검증 결과

알고리즘 구현 후 채점 사이트에 코드를 제출하여 최종 정답 판정을 받았다.

<!-- 이미지 자리: 정올 사이트에 제출하여 "정답입니다" 및 실행 시간이 나온 채점 결과 화면 사진 -->
![정올 제출 정답 화면](/assets/img/koi-delivery/그림2.png)
_사이트 제출 결과 및 "정답입니다" 화면._

<!-- 이미지 자리: 코드 제출 화면 또는 정답 입력/결과 상세 사진 -->
![정올 정답 입력 및 결과 상세 화면](/assets/img/koi-delivery/그림1.png)
_최종 채점 결과 상세 화면._

---

## 7. 전체 C++17 코드

시간복잡도는 `O((N+M) log N)`, 공간복잡도는 `O(N log N + M)`이다.

```cpp
#include <bits/stdc++.h>
using namespace std;
using ll = long long;

struct FastInput {
    static constexpr int S = 1 << 16;
    char b[S]; int p = 0, n = 0;
    int get() {
        if (p == n) { n = fread(b, 1, S, stdin); p = 0; }
        return n ? b[p++] : EOF;
    }
    int read() {
        int c, x = 0;
        do { c = get(); } while (c <= 32 && c != EOF);
        while (c >= '0' && c <= '9') { x = x * 10 + c - '0'; c = get(); }
        return x;
    }
};
struct Path { int centroid, distance, branch; };
struct Shop { int center, radius, weight, next; };

class Solver {
    int n, m;
    struct Adjacency {
        vector<int> offset, edges;
        struct Range {
            const int *first, *last;
            const int *begin() const { return first; }
            const int *end() const { return last; }
        };
        Range operator[](int v) const { return {edges.data()+offset[v], edges.data()+offset[v+1]}; }
    } adj;
    vector<array<Path, 18>> paths;
    vector<int> pathCount;
    struct Bucket { int offset = 0, length = 0; };
    vector<Bucket> total, subtract;
    vector<ll> values;
    vector<int> nodes;
    vector<array<int,3>> stack;
    vector<int> parent, depth, order, size, tmpParent, head;
    vector<array<int, 17>> up;
    vector<char> removed;
    vector<Shop> shops;
    vector<ll> dp;

    void decompose(int start) {
        nodes.clear(); nodes.push_back(start);
        tmpParent[start] = -1;
        for (size_t i = 0; i < nodes.size(); ++i) {
            int v = nodes[i];
            for (int u : adj[v]) if (!removed[u] && u != tmpParent[v]) {
                tmpParent[u] = v; nodes.push_back(u);
            }
        }
        for (int i = (int)nodes.size() - 1; i >= 0; --i) {
            int v = nodes[i]; size[v] = 1;
            for (int u : adj[v]) if (!removed[u] && tmpParent[u] == v) size[v] += size[u];
        }
        int c = start, count = (int)nodes.size();
        for (int v : nodes) {
            int largest = count - size[v];
            for (int u : adj[v]) if (!removed[u] && tmpParent[u] == v) largest = max(largest, size[u]);
            if (largest * 2 <= count) { c = v; break; }
        }
        removed[c] = true;
        paths[c][pathCount[c]++] = {c, 0, -1};
        int maxDistance = 0;
        stack.clear();
        for (int u : adj[c]) if (!removed[u]) {
            int branch = (int)subtract.size(), branchMax = 0;
            subtract.emplace_back(); stack.clear(); stack.push_back({u, c, 1});
            while (!stack.empty()) {
                auto [v, p, d] = stack.back(); stack.pop_back();
                paths[v][pathCount[v]++] = {c, d, branch}; branchMax = max(branchMax, d);
                for (int w : adj[v]) if (!removed[w] && w != p) stack.push_back({w, v, d + 1});
            }
            subtract[branch] = {(int)values.size(), branchMax + 1};
            values.resize(values.size() + branchMax + 1);
            maxDistance = max(maxDistance, branchMax);
        }
        total[c] = {(int)values.size(), maxDistance + 1};
        values.resize(values.size() + maxDistance + 1);
        for (int u : adj[c]) if (!removed[u]) decompose(u);
    }
    ll sphere(int v, int radius) const {
        ll result = 0;
        for (int k = 0; k < pathCount[v]; ++k) {
            const auto &p = paths[v][k];
            int d = radius - p.distance;
            if (d < 0) continue;
            if (d < total[p.centroid].length) result += values[total[p.centroid].offset + d];
            if (p.branch >= 0 && d < subtract[p.branch].length) result -= values[subtract[p.branch].offset + d];
        }
        return result;
    }
    void insert(int v, ll value) {
        for (int k = 0; k < pathCount[v]; ++k) {
            const auto &p = paths[v][k];
            values[total[p.centroid].offset + p.distance] += value;
            if (p.branch >= 0) values[subtract[p.branch].offset + p.distance] += value;
        }
    }
public:
    void run() {
        FastInput in; n = in.read(); m = in.read();
        adj.offset.resize(n+1); paths.resize(n); pathCount.resize(n); total.resize(n); parent.resize(n);
        depth.resize(n); size.resize(n); tmpParent.resize(n); head.assign(n, -1);
        up.resize(n); removed.resize(n); dp.resize(n); shops.reserve(m); subtract.reserve(n);
        vector<pair<int,int>> inputEdges; inputEdges.reserve(n-1);
        for (int i = 1; i < n; ++i) {
            int a = in.read() - 1, b = in.read() - 1;
            inputEdges.emplace_back(a,b); ++adj.offset[a+1]; ++adj.offset[b+1];
        }
        for (int v=1; v<=n; ++v) adj.offset[v] += adj.offset[v-1];
        adj.edges.resize(max(1, 2*(n-1)));
        vector<int> cursor = adj.offset;
        for (auto [a,b] : inputEdges) { adj.edges[cursor[a]++] = b; adj.edges[cursor[b]++] = a; }
        values.reserve((size_t)n * 36); nodes.reserve(n); stack.reserve(n);
        order.reserve(n); order.push_back(0); parent[0] = 0;
        for (size_t i = 0; i < order.size(); ++i) {
            int v = order[i];
            for (int u : adj[v]) if (u != parent[v]) {
                parent[u] = v; depth[u] = depth[v] + 1; up[u][0] = v;
                for (int k = 1; k < 17; ++k) up[u][k] = up[up[u][k-1]][k-1];
                order.push_back(u);
            }
        }
        for (int i = 0; i < m; ++i) {
            int c = in.read() - 1, d = in.read(), g = in.read();
            int v = c, steps = min(d, depth[c]);
            for (int k = 0; k < 17;
```

추가로 검증과정에서 공식 테스트 165개 케이스와 최대 크기 트리 구조 테스트에서도 모두 정답과 일치함을 확인했으며, 최적화 구조 변경 덕분에 큰 폭의 실행 시간 단축을 이뤄낼 수 있었다.
