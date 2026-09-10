---
title: "[알고리즘] 정올 4808 맛집 추천: 트리 DP와 센트로이드 분할로 500ms 도전"
date: 2026-09-10 13:00:00 +0900
categories: [개발, Algorithm]
tags: [jungol, koi, cpp, tree-dp, centroid-decomposition, optimization, mission]
math: true
---

<style>.post-tail-wrapper .license-wrapper { display: none; }</style>

## 1. 미션 개요

이번 미션은 [정올 4808번 맛집 추천](https://jungol.co.kr/problem/4808)을 풀고, 실행 시간을 **500ms 이내**로 줄이는 과정을 정리하는 것이다. 출제자는 **@Pay1oad_김예준(walow)**, 미션 난이도는 별 1개, 예상 기간은 14일이다. 별 개수는 미션에 표시된 값이며 알고리즘 문제 자체의 난이도와는 구분한다.

문제는 **2021 KOI 2차 고등부 4번**이다. 정올 화면의 시간 제한은 3초이므로, 미션 목표는 기본 제한보다 더 엄격하다.

![정올 4808 문제 화면](/assets/img/koi-delivery/01-problem.png)
_로그인 없이 확인한 실제 문제 화면._

이 글은 AI 도구의 도움을 받아 풀이 구현, 테스트, 성능 개선을 수행한 기록이다. **정올 로그인·제출과 미션 완료 등록은 수행하지 않았다.** 따라서 아래 기록은 로컬 검증 결과이며, 정올에서 500ms 이내로 통과했다는 의미는 아니다.

미션에 연결된 [출제자 참고 글](https://yejunkim2000.github.io/posts/koi-delivery/)은 작업 시점에 GitHub Pages 404 화면이 표시되었다. 대신 [KOI 공식 자료 페이지](https://koi.or.kr/koi/2021/2/)에서 공개한 문제, 해설, 테스트 데이터를 확인했다. 풀이의 출발점은 윤창기 님의 공식 해설에 나오는 트리 DP와 센트로이드 분할이며, 아래 코드는 그 아이디어를 바탕으로 별도로 구현하고 검증했다.

---

## 2. 문제를 트리 위의 영역 선택으로 바꾸기

도시가 정점이고 길이 간선인 트리가 주어진다. 맛집 `i`에는 중심 도시 `c_i`, 배달 반경 `d_i`, 선호도 `g_i`가 있다. 배달 구역은 중심에서 거리가 반경 이하인 정점들의 집합이다.

선택한 맛집들의 배달 구역이 서로 겹치면 안 된다. 목표는 선택한 선호도의 합을 최대화하는 것이다.

두 맛집만 비교하면 겹침 조건은 간단하다.

$$\operatorname{dist}(c_i,c_j)\le d_i+d_j$$

하지만 맛집이 최대 10만 개라 모든 쌍을 비교하면 약 50억 쌍이다. 충돌 그래프를 직접 만들기보다 **배달 구역을 지웠을 때 남는 트리 구조**를 이용해야 한다.

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

### 3.1 DP 상태

`dp[v]`를 다음과 같이 정의한다.

> 배달 구역 전체가 `v`의 서브트리 안에 들어가는 맛집들만 선택할 때 얻는 최대 선호도 합.

경우는 두 가지다.

**v를 덮지 않는 경우**에는 각 자식 서브트리를 독립적으로 해결한다.

$$dp[v] = \sum_{u:\ parent[u]=v}dp[u]$$

**v를 어떤 맛집 i가 덮는 경우**에는 `top(i)=v`여야 한다. 이 맛집의 배달 구역을 지우면 남는 부분은 여러 서브트리로 나뉜다. 남은 각 서브트리의 루트 `x`는 다음 조건을 만족한다.

$$\operatorname{dist}(c_i,x)=d_i+1$$

따라서 해당 맛집을 고르는 후보 값은 다음과 같다.

$$g_i + \sum_{\substack{x\in subtree(v)\\\operatorname{dist}(c_i,x)=d_i+1}}dp[x]$$

이 값들과 자식 DP 합 중 최댓값이 `dp[v]`다.

### 3.2 왜 이 점화식이 맞을까?

겹침이 금지되어 있으므로 `v`를 덮는 선택된 맛집은 최대 하나다. 없으면 선택 영역이 서로 다른 자식 서브트리를 가로질러 갈 수 없다. 가로지르는 연결 영역은 반드시 `v`를 지나기 때문이다.

맛집 `i`를 선택했다면 나머지 선택 영역은 `R_i`를 피해야 한다. 트리에서 연결된 영역 `R_i`를 제거한 뒤 남는 연결 성분끼리는 독립적이다. 각 성분은 경계 정점 `x`를 루트로 하는 서브트리이므로 최적값이 `dp[x]`다. 각 경우를 빠짐없이 고려하고, 자식부터 계산하므로 귀납적으로 정답이 된다.

---

## 4. 경계 정점의 합을 빠르게 구하기

단순 구현에서는 맛집마다 경계 정점을 탐색한다. 경계 크기가 클 수 있으므로 전체 비용이 `O(NM)`까지 증가한다.

필요한 연산은 두 개뿐이다.

1. DP가 확정된 정점 `x`에 값 `dp[x]`를 등록한다.
2. 중심 `c`에서 **정확히 거리 r**인 등록된 정점들의 값을 합산한다.

여기서 구하는 것은 반경 이하 누적합이 아니라 **정확히 한 거리의 합**이다. 센트로이드마다 거리별 배열을 두면 배열 원소를 바로 읽고 더할 수 있다. 이 차이 덕분에 Fenwick tree의 추가 로그 비용이 필요 없다.

### 4.1 센트로이드 분할

센트로이드는 제거했을 때 남는 각 연결 성분의 크기가 원래 크기의 절반 이하가 되는 정점이다. 이를 반복해서 분할하면 한 정점이 속하는 분할 단계가 `O(log N)`개다.

센트로이드 `z`마다 다음 정보를 유지한다.

| 배열 | 의미 |
| --- | --- |
| `total[z][t]` | 해당 분할 성분에서 `z`와 거리가 `t`인 등록 정점 값의 합 |
| `subtract[b][t]` | `z`를 제거했을 때 특정 가지 `b`에 들어가는 등록 정점 중 `z`와 거리가 `t`인 값의 합 |

중심 `c`의 센트로이드 조상 `z`에서 `t = r - dist(c,z)`라 놓으면, `total[z][t]`를 더하고 `c`가 들어 있는 가지의 `subtract[b][t]`를 뺀다. 음수 거리나 배열 범위 밖이면 기여도는 0이다.

같은 가지 내부에서는 실제 경로가 `z`를 지나지 않을 수 있으므로 그 부분을 빼야 한다. 두 정점이 처음으로 서로 다른 가지로 분리되는 단계에서는 실제 경로가 센트로이드를 지나고 거리의 합이 정확해진다. 이전 단계에서는 더한 뒤 빠지고 이후에는 상대 정점이 같은 분할 성분에 없으므로, 각 정점이 정확히 한 번 집계된다. `c` 자신이 센트로이드인 단계에는 빼야 할 가지가 없다.

### 4.2 서브트리 조건은 어떻게 지킬까?

거리 합 자료구조에는 이미 확정된 DP만 넣는다. 구현은 루트에서 만든 BFS 순서를 역순으로 처리하므로 자손이 조상보다 먼저 등록된다.

`top(i)=v`이고 `v`가 루트가 아니면 `dist(c_i,v)=d_i`이다. `v`의 서브트리 바깥에서 거리 `d_i+1`에 도달할 수 있는 유일한 정점은 `parent[v]`다. 부모는 아직 처리되지 않았으므로 자료구조에 없다. 그보다 더 바깥 정점은 거리가 최소 `d_i+2`다.

따라서 전역 거리 질의를 해도 서브트리 바깥의 DP가 섞이지 않는다. `v`가 루트라면 애초에 바깥 정점이 없다. 같은 깊이의 다른 서브트리를 먼저 처리했더라도 이 성질은 유지된다.

**등록 시점도 중요하다.** `v`에 묶인 맛집을 전부 계산한 뒤 `dp[v]`를 한 번만 등록한다. 후보 맛집을 계산할 때마다 등록하면 같은 상태가 중복 반영된다.

---

## 5. 첫 구현: 정답은 맞았지만 500ms를 넘었다

첫 구현도 시간복잡도는 `O((N+M) log N)`이었다. 그러나 인접 리스트, 센트로이드 경로, 거리 배열을 여러 `vector`로 관리하면서 작은 메모리 할당과 흩어진 데이터 접근이 많았다.

공식 165개와 무작위 1,200개는 모두 정답이 일치했지만, `084.in.txt`의 최초 실행은 **645.834ms**, 이후 5회 중앙값은 **566.014ms**였다. `082.in.txt`의 반복 중앙값도 **574.938ms**였다. 점근적 복잡도만으로 500ms 목표를 보장할 수 없었다.

![최적화 전 성능 검증 화면](/assets/img/koi-delivery/02-before.png)
_실제 실행 로그로 만든 로컬 보고서. 정올 채점 화면이 아니다._

### 5.1 메모리 배치 개선

알고리즘은 유지하면서 저장 방식을 바꿨다.

- **인접 리스트를 CSR 배열로 구성:** 정점별 이웃을 하나의 연속 배열에 저장하고 시작 위치로 접근한다.
- **센트로이드 경로를 고정 슬롯으로 저장:** 한 정점당 최대 18개 슬롯과 실제 개수를 둬 작은 벡터의 재할당을 없앴다.
- **거리별 합을 하나의 배열에 저장:** 각 버킷은 시작 오프셋과 길이만 가진다.
- **분할 탐색의 임시 배열을 재사용:** 성분별로 탐색용 벡터를 새로 할당하지 않는다.

입력은 첫 구현부터 사용했던 64KiB `fread` 버퍼를 그대로 유지했다.

이 변경들이 시간을 줄이는 데 기여했지만, 각각의 효과를 분리 측정한 것은 아니다. 아래 비교는 전체 변경 전후의 실행 결과다.

### 5.2 깊은 트리와 큰 정수 처리

일자 트리는 깊이가 10만에 가깝다. 일반 DFS를 깊이만큼 재귀 호출하면 스택 문제가 생길 수 있어 원본 트리 탐색과 거리 수집은 반복문으로 처리했다. 재귀 호출은 깊이가 `O(log N)`인 센트로이드 분할에만 남겼다.

정답의 최댓값은 `10^5 × 10^9 = 10^14`까지 가능하므로, `dp`와 거리별 합 및 출력은 `long long`을 사용한다. 중심·거리·선호도 입력 자체는 주어진 범위 내에서 `int`로 읽을 수 있다.

---

## 6. 검증 결과

공식 예제 출력은 `53`으로 일치했다. 공식 테스트 **165/165**, 무작위 완전탐색 비교 **1,200/1,200**도 모두 일치했다. 최대 크기 네 종류를 각각 5회 실행했고, 모두 예상 답 `100000000000000`을 출력했다.

최적화 후 공식 165개 최초 실행 최대는 **305.209ms**였다. 느린 10개 입력을 각 5회 재측정했을 때 최대는 **367.938ms**였다. 이번에 실행한 공식 데이터와 최대 크기 테스트의 로컬 측정값은 모두 500ms 미만이었다.

| 동일 입력 | 개선 전 중앙값(ms) | 개선 후 중앙값(ms) | 감소율 |
| --- | ---: | ---: | ---: |
| `082.in.txt` | 574.938 | 313.331 | 45.5% |
| `083.in.txt` | 542.997 | 311.621 | 42.6% |
| `084.in.txt` | 566.014 | 339.936 | 39.9% |
| `085.in.txt` | 531.028 | 331.552 | 37.6% |

아래는 최대 크기 `N=M=100000`에서 모든 맛집의 반경을 0, 선호도를 10⁹으로 설정한 결과다. 이 입력은 모든 맛집을 선택할 수 있어 답이 10¹⁴임을 독립적으로 알 수 있다. 다양한 반경은 공식 데이터와 무작위 테스트에서 검증했다.

| 트리 모양 | 5회 중앙값(ms) | 5회 최대(ms) |
| --- | ---: | ---: |
| path | 141.807 | 164.649 |
| star | 69.333 | 70.329 |
| binary | 118.067 | 122.476 |
| random | 227.958 | 257.324 |


![최종 공식 데이터 검증 화면](/assets/img/koi-delivery/03-after.png)
_최적화 이후 동일한 검증 절차를 다시 수행한 결과._

![최대 크기 및 64비트 검증 화면](/assets/img/koi-delivery/04-stress.png)
_최대 크기의 네 가지 트리 모양에서 예상 답 10¹⁴를 확인했다._

### 6.1 측정 방법과 한계

| 항목 | 환경 |
| --- | --- |
| CPU | AMD Ryzen 5 4600H |
| 실행 환경 | WSL2, Ubuntu 22.04.5, x86-64 |
| 컴파일러 | GCC 11.4.0 |
| 옵션 | `-std=c++17 -O2 -Wall -Wextra -Wshadow` |
| 측정 | Python `perf_counter`, Linux 자식 프로세스 경과 시간 |

입력 파일을 Python 메모리로 읽은 뒤 타이머를 시작했다. 프로세스 실행, 입력 파이프 전달, 프로그램 계산, 출력 및 종료까지 포함한다. 파일 읽기와 컴파일 시간, WSL 기동 시간은 포함하지 않는다. 공식 전체 데이터는 각 1회 실행하고, 그중 느렸던 10개를 각 5회 추가 측정했다.

로컬 경과 시간은 OS 스케줄링과 다른 프로그램의 부하에 영향을 받는다. 정올의 CPU, 컴파일 옵션, 실행 시간 산정 방식도 다를 수 있다. **로컬 측정은 최적화의 근거이며, 미션의 서버 500ms 조건 확인은 실제 제출 이후에 가능하다.**

### 6.2 재현 방법

[C++17 소스](/assets/files/koi-delivery/solution.cpp) · [검증 스크립트](/assets/files/koi-delivery/verify.py) · [예제 입력](/assets/files/koi-delivery/sample.in) · [최종 원시 측정 기록](/assets/files/koi-delivery/validation.json)

공식 테스트 데이터는 [KOI 배포 ZIP](https://assets.koi.or.kr/koi/2021/2/tests/recommendation.zip)을 내려받아 `tests` 디렉터리에 푼다. 데이터는 이 글에 재배포하지 않는다.

```bash
g++ -std=c++17 -O2 -Wall -Wextra -Wshadow solution.cpp -o solution
./solution < sample.in
# 예상 출력: 53
python3 verify.py ./solution ./tests
```

검증기는 공식 출력과의 비교, seed 4808의 무작위 작은 입력 1,200개 완전탐색 비교, 최대 크기 테스트를 수행한다. 결과는 `validation.json`으로 저장한다. 작은 입력 검증에서는 각 맛집의 배달 구역을 BFS로 직접 구하고 가능한 선택을 탐색하므로, 센트로이드 구현과 별도의 방법으로 답을 계산한다.

---

## 7. 전체 C++17 코드

시간복잡도는 `O((N+M) log N)`, 공간복잡도는 `O(N log N + M)`이다. 센트로이드 한 단계에서 거리 수집과 배열 크기의 합은 그 단계의 정점 수에 비례한다. 각 맛집은 조상 탐색과 거리 질의에 각각 `O(log N)`, 각 정점의 DP 등록도 `O(log N)`이 든다.

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

    // Only centroid recursion remains: its depth is O(log N).
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
        // Shared scratch arrays are reused by the next component.
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
            for (int k = 0; k < 17; ++k) if (steps & (1 << k)) v = up[v][k];
            shops.push_back({c, d, g, head[v]}); head[v] = i;
        }
        decompose(0);
        // Reverse breadth-first order: deeper vertices are finalized first.
        for (int i = n - 1; i >= 0; --i) {
            int v = order[i]; ll best = dp[v];
            for (int j = head[v]; j != -1; j = shops[j].next) {
                const auto &s = shops[j];
                best = max(best, (ll)s.weight + sphere(s.center, s.radius + 1));
            }
            dp[v] = best; insert(v, best);
            if (v != 0) dp[parent[v]] += best;
        }
        printf("%lld\n", dp[0]);
    }
};
int main() { Solver solver; solver.run(); }
```

---

## 8. 마무리 및 남은 제출 단계

이 문제의 핵심은 선택한 배달 구역의 **바로 바깥 경계**를 DP로 합치는 관찰이었다. 거리 질의를 정확한 한 거리의 합으로 바꾼 덕분에 센트로이드 분할과 단순 배열로 처리할 수 있었다. 실제 실행에서는 메모리 배치도 성능에 큰 영향을 주었다.

풀이 코드, 공식 데이터 대조, 무작위 검증, 로컬 성능 기록까지 준비했다. 남은 단계는 정올에 로그인해 C++17 코드를 제출하고, 실제 정답 판정과 실행 시간을 확인하는 것이다. 그 후 이 글에 서버 결과 캡처와 수치를 추가하고 미션 완료를 등록하면 된다. 현재 글에는 수행하지 않은 제출 성공이나 서버 기록을 기재하지 않았다.

### 참고 자료

- [정올 4808 맛집 추천](https://jungol.co.kr/problem/4808)
- [KOI 2021 2차 공식 자료](https://koi.or.kr/koi/2021/2/)
- [맛집 추천 공식 해설 — 윤창기](https://assets.koi.or.kr/koi/2021/2/solutions/recommendation.pdf)
- [공식 테스트 데이터](https://assets.koi.or.kr/koi/2021/2/tests/recommendation.zip)

공식 자료 페이지의 라이선스는 CC BY-NC-SA 4.0이다. 공식 해설을 바탕으로 재구성한 이 글의 풀이 설명도 해당 조건에 따라 공유한다. 문제 원문과 공식 해설 전체는 옮기지 않았으며, 코드는 별도 구현이다.
