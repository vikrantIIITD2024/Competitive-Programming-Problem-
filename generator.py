#!/usr/bin/env python3
# generator.py
#
# Generates test cases for "The Archmage’s Layered Spellbook".
# Creates .in and .out files under ./test_cases using an embedded brute-force solver.
#
# Usage examples:
#   python3 generator.py                          # default: 6 cases
#   python3 generator.py --cases 10 --seed 42
#   python3 generator.py --nmin 1 --nmax 12 --qmin 6 --qmax 20
#
# The .out is computed with the same timeline semantics as the official statement:
#   - Build version tree from UNDOs
#   - For each operation i, answer = total energy at node i
#   - Print answers in input order

import os
import random
import argparse
from typing import List, Tuple

# ----------------------------
# Brute-force evaluator (same semantics as solution_bf.py)
# ----------------------------

def build_version_tree_from_ops(q_ops: List[Tuple]) -> Tuple[List, List[List[int]]]:
    """
    Input q_ops: list of parsed ops for i = 1..q, each:
        ('add', l, r, k, p, x)  or  ('undo', t)
    Returns:
        ops: 1-indexed list with ops[i]
        children: adjacency list for nodes 0..q
    """
    q = len(q_ops)
    ops = [None] * (q + 1)
    parent = [0] * (q + 1)
    children = [[] for _ in range(q + 1)]

    cur = 0
    for i in range(1, q + 1):
        op = q_ops[i - 1]
        ops[i] = op
        if op[0] == 'add':
            parent[i] = cur
            children[parent[i]].append(i)
            cur = i
        else:
            # undo to t
            t = op[1]
            parent[i] = t
            children[parent[i]].append(i)
            cur = i
    return ops, children

def brute_force_answers(n: int, a: List[int], q_ops: List[Tuple]) -> List[int]:
    """
    Returns answers for operations 1..q in input order using a DFS over the version tree.
    """
    base_sum = sum(a[1:])
    ops, children = build_version_tree_from_ops(q_ops)
    stacks = [[] for _ in range(n + 1)]  # per-index active layers: list of (k,p,x)
    ans = [0] * (len(q_ops) + 1)

    def apply_range(l, r, k, p, x):
        for i in range(l, r + 1):
            stacks[i].append((k, p, x))

    def revert_range(l, r):
        for i in range(l, r + 1):
            stacks[i].pop()

    def recompute_total():
        total = base_sum
        for i in range(1, n + 1):
            if not stacks[i]:
                continue
            mk = -1
            mp = 0
            mx = 0
            for (kk, pp, xx) in stacks[i]:
                if kk > mk:
                    mk = kk
                    mp = pp
                    mx = xx
            cover = len(stacks[i])
            if (cover & 1) == mp:
                total += mx
            else:
                total -= mx
        return total

    def dfs(u: int):
        tag = None
        if u != 0:
            op = ops[u]
            if op[0] == 'add':
                _, l, r, k, p, x = op
                apply_range(l, r, k, p, x)
                tag = ('add', l, r)
            # 'undo' node applies no direct change here
            ans[u] = recompute_total()

        for v in children[u]:
            dfs(v)

        if tag and tag[0] == 'add':
            _, l, r = tag
            revert_range(l, r)

    dfs(0)
    return ans[1:]  # answers for i=1..q

# ----------------------------
# Random & adversarial builders
# ----------------------------

def rand_range(n):
    l = random.randint(1, n)
    r = random.randint(1, n)
    if l > r:
        l, r = r, l
    return l, r

def make_case_random(n: int, q: int, k_base: int = 1) -> Tuple[List[int], List[Tuple]]:
    """
    Mixed random case with ~25-35% undo, overlapping ranges,
    varied k with occasional collisions.
    """
    a = [0] + [random.randint(0, 15) for _ in range(n)]
    ops = []
    current_idx = 0
    next_k = k_base
    for i in range(1, q + 1):
        choose_undo = (i > 1) and (random.random() < 0.3)
        if choose_undo:
            t = random.randint(0, i - 1)
            ops.append(('undo', t))
            current_idx = i
            continue

        l, r = rand_range(n)

        # Occasionally make very large k to overshadow others
        if random.random() < 0.2:
            k = next_k + random.randint(50, 200)
        else:
            # sometimes repeat k to create equal-k test
            if random.random() < 0.15 and next_k > k_base:
                k = random.randint(k_base, next_k)
            else:
                k = next_k
        next_k = max(next_k + 1, k + 1)

        p = random.randint(0, 1)
        x = random.randint(1, 10)

        ops.append(('add', l, r, k, p, x))
        current_idx = i
    return a, ops

def make_case_nested(n: int, q: int, deep: int = 6, width: int = 2) -> Tuple[List[int], List[Tuple]]:
    """
    Builds nested intervals with frequent undos to stress parity flips and top layer dominance.
    """
    a = [0] + [random.randint(0, 5) for _ in range(n)]
    ops = []
    k = 1
    # Build a tower of nested layers
    for d in range(deep):
        l = 1 + d * max(1, n // (2 * deep))
        r = n - d * max(1, n // (2 * deep))
        if l > r:
            l, r = 1, n
        p = d & 1
        x = 1 + (d % 5)
        ops.append(('add', l, r, k, p, x))
        k += 1

        # small local layers
        for _ in range(width):
            ll, rr = rand_range(n)
            ops.append(('add', ll, rr, k, random.randint(0, 1), random.randint(1, 6)))
            k += 1

    # Add undos bouncing around the build steps
    extra = max(0, q - len(ops))
    for i in range(extra):
        t = random.randint(0, min(len(ops), deep * (1 + width)) - 1)
        ops.append(('undo', t))

    # Trim or pad
    ops = ops[:q]
    while len(ops) < q:
        l, r = rand_range(n)
        ops.append(('add', l, r, k, random.randint(0, 1), random.randint(1, 6)))
        k += 1

    return a, ops

def make_case_edge(n: int, q: int) -> Tuple[List[int], List[Tuple]]:
    """
    Edgey case:
      - many identical ranges
      - many equal k clashes
      - alternating parity
      - undos to 0 and to recent nodes
    """
    a = [0] + [0]*n
    ops = []
    k = 5
    # first few ops with same (l,r)
    for i in range(min(q, 10)):
        if i % 3 == 2:
            ops.append(('undo', random.randint(0, i)))
            continue
        l, r = 1, n
        ops.append(('add', l, r, k if i % 2 == 0 else 5, i & 1, 1 + (i % 3)))
        k += 1
    while len(ops) < q:
        if random.random() < 0.35:
            ops.append(('undo', random.randint(0, len(ops))))
        else:
            l, r = rand_range(n)
            kk = random.randint(1, 12)
            ops.append(('add', l, r, kk, random.randint(0, 1), random.randint(1, 4)))
    return a, ops[:q]

# ----------------------------
# Formatting & IO
# ----------------------------

def format_input(n: int, a: List[int], ops: List[Tuple]) -> str:
    lines = []
    lines.append(f"{n} {len(ops)}")
    lines.append(" ".join(map(str, a[1:])))
    for op in ops:
        if op[0] == 'add':
            _, l, r, k, p, x = op
            lines.append(f"+ {l} {r} {k} {p} {x}")
        else:
            _, t = op
            lines.append(f"- {t}")
    return "\n".join(lines) + "\n"

def generate_case(kind: str, n: int, q: int, kbase: int = 1) -> Tuple[str, str]:
    if kind == 'random':
        a, ops = make_case_random(n, q, kbase)
    elif kind == 'nested':
        a, ops = make_case_nested(n, q)
    elif kind == 'edge':
        a, ops = make_case_edge(n, q)
    else:
        a, ops = make_case_random(n, q, kbase)

    answers = brute_force_answers(n, a, ops)
    inp = format_input(n, a, ops)
    out = "\n".join(map(str, answers)) + "\n"
    return inp, out

def main():
    parser = argparse.ArgumentParser(description="Test case generator for The Archmage’s Layered Spellbook")
    parser.add_argument("--cases", type=int, default=6, help="number of cases to generate")
    parser.add_argument("--seed", type=int, default=20251022, help="random seed")
    parser.add_argument("--nmin", type=int, default=1)
    parser.add_argument("--nmax", type=int, default=20)
    parser.add_argument("--qmin", type=int, default=5)
    parser.add_argument("--qmax", type=int, default=30)
    parser.add_argument("--outdir", type=str, default="test_cases")
    args = parser.parse_args()

    random.seed(args.seed)
    os.makedirs(args.outdir, exist_ok=True)

    # Distribute kinds across cases
    kinds = []
    base = ['random', 'nested', 'edge']
    while len(kinds) < args.cases:
        kinds.extend(base)
    kinds = kinds[:args.cases]

    for idx in range(1, args.cases + 1):
        n = random.randint(args.nmin, args.nmax)
        q = random.randint(args.qmin, args.qmax)
        kind = kinds[idx - 1]
        inp, out = generate_case(kind, n, q, kbase=1 + idx * 10)

        in_path = os.path.join(args.outdir, f"{idx}.in")
        out_path = os.path.join(args.outdir, f"{idx}.out")
        with open(in_path, "w") as f:
            f.write(inp)
        with open(out_path, "w") as f:
            f.write(out)

    print(f"Generated {args.cases} cases in ./{args.outdir}")

if __name__ == "__main__":
    main()
