#!/usr/bin/env python3
"""Run from Linux/WSL: python3 verify.py EXECUTABLE OFFICIAL_TEST_DIRECTORY."""
import collections
import json
import pathlib
import random
import statistics
import subprocess
import sys
import time

exe, test_dir = sys.argv[1:3]
rng = random.Random(4808)

def run(data):
    start = time.perf_counter()
    p = subprocess.run([exe], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=10)
    return int(p.stdout.strip()), (time.perf_counter() - start) * 1000

official = []
for path in sorted(pathlib.Path(test_dir).glob('*.in.txt')):
    data = path.read_bytes()
    expected = int(path.with_name(path.name.replace('.in.txt', '.out.txt')).read_text())
    actual, ms = run(data)
    assert actual == expected, (path.name, expected, actual)
    n, m = map(int, data.split(b'\n', 1)[0].split())
    official.append(dict(case=path.name, n=n, m=m, ms=round(ms, 3), answer=actual))
print(f'Official: {len(official)}/{len(official)} PASS', flush=True)

for case in range(1200):
    n, m = rng.randint(1, 18), rng.randint(1, 15)
    edges = [(v, rng.randrange(v)) for v in range(1, n)]
    adj = [[] for _ in range(n)]
    for a, b in edges:
        adj[a].append(b); adj[b].append(a)
    shops, masks = [], []
    for _ in range(m):
        c, radius, g = rng.randrange(n), rng.randrange(n), rng.randint(1, 10**9)
        shops.append((c, radius, g))
        dist = [-1] * n; dist[c] = 0; q = collections.deque([c])
        while q:
            v = q.popleft()
            for u in adj[v]:
                if dist[u] == -1: dist[u] = dist[v] + 1; q.append(u)
        masks.append(sum(1 << v for v in range(n) if dist[v] <= radius))
    def brute(i, used):
        if i == m: return 0
        best = brute(i + 1, used)
        if not used & masks[i]: best = max(best, shops[i][2] + brute(i + 1, used | masks[i]))
        return best
    expected = brute(0, 0)
    text = f'{n} {m}\n' + ''.join(f'{a+1} {b+1}\n' for a,b in edges) + ''.join(f'{c+1} {d} {g}\n' for c,d,g in shops)
    actual, _ = run(text.encode())
    assert actual == expected, (case, text, expected, actual)
print('Random exhaustive comparison: 1200/1200 PASS (seed=4808)', flush=True)

stress = []
for shape in ['path', 'star', 'binary', 'random']:
    n = 100000
    parents = [v-1 if shape == 'path' else 0 if shape == 'star' else (v-1)//2 if shape == 'binary' else rng.randrange(v) for v in range(1,n)]
    # Known answer 1e14: every vertex has a radius-zero restaurant.
    data = (f'{n} {n}\n' + ''.join(f'{v+1} {p+1}\n' for v,p in enumerate(parents,1)) + ''.join(f'{v+1} 0 1000000000\n' for v in range(n))).encode()
    times = []
    for _ in range(5):
        answer, ms = run(data); assert answer == 10**14
        times.append(ms)
    stress.append(dict(shape=shape, answer=answer, min_ms=round(min(times),3), median_ms=round(statistics.median(times),3), max_ms=round(max(times),3)))
print('Maximum-size / int64 tests: 4 shapes x 5 runs PASS', flush=True)

repeated = []
for row in sorted(official, key=lambda r:r['ms'], reverse=True)[:10]:
    data = (pathlib.Path(test_dir)/row['case']).read_bytes()
    times = []
    for _ in range(5):
        ans, ms = run(data); assert ans == row['answer']; times.append(ms)
    repeated.append(dict(case=row['case'], min_ms=round(min(times),3), median_ms=round(statistics.median(times),3), max_ms=round(max(times),3)))
report = dict(official_count=len(official), random_count=1200, seed=4808,
              official=official, stress=stress, slowest_repeated=repeated,
              timing='Linux subprocess wall time including launch, input pipe, computation, output and exit. Input bytes preloaded in Python; not judge time.')
pathlib.Path('validation.json').write_text(json.dumps(report, indent=2))
print(json.dumps(dict(slowest_initial=max(official,key=lambda r:r['ms']),stress=stress,slowest_repeated=repeated),indent=2))
