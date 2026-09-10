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
