#!/usr/bin/env python3
# solution_bf.py
#
# Brute-force solution for "The Archmage’s Layered Spellbook"
# Strategy:
#   - Build the version tree from the sequence of operations (UNDO creates branches).
#   - DFS the tree. Maintain active layers by naively pushing/popping on [l..r].
#   - After entering each node, recompute the total from scratch:
#       For each index i:
#         cover = number of active layers covering i (stack length)
#         top layer = layer with maximum k among active ones at i (if any)
#         contribution = +x if (cover % 2) == p_top else -x
#   - Print the total after each operation.
#
# Complexity:
#   - Very slow on purpose: O(q * (n + sum over i of stack_i_size)).
#   - Use for small/medium tests and as a correctness oracle.

import sys
sys.setrecursionlimit(1_000_000)
rd = sys.stdin.buffer.readline

def build_version_tree(q):
    """
    Node 0 is the initial state.
    For i=1..q:
      '+ l r k p x'  -> parent[i] = current; current = i
      '- t'          -> parent[i] = t; current = i
    Returns:
      ops[i] = ('add', l,r,k,p,x) or ('undo', t)
      children adjacency list
    """
    ops_raw = [rd().split() for _ in range(q)]
    ops = [None] * (q + 1)
    parent = [0] * (q + 1)
    children = [[] for _ in range(q + 1)]

    cur = 0
    for i in range(1, q + 1):
        t = ops_raw[i - 1]
        if t[0] == b'+':
            l = int(t[1]); r = int(t[2])
            k = int(t[3]); p = int(t[4]); x = int(t[5])
            ops[i] = ('add', l, r, k, p, x)
            parent[i] = cur
            children[parent[i]].append(i)
            cur = i
        else:
            to = int(t[1])
            ops[i] = ('undo', to)
            parent[i] = to
            children[parent[i]].append(i)
            cur = i
    return ops, children

def main():
    n, q = map(int, rd().split())
    a = [0] + list(map(int, rd().split()))  # 1-indexed
    base_sum = sum(a[1:])

    ops, children = build_version_tree(q)

    # Active layers per index: list of (k, p, x)
    stacks = [[] for _ in range(n + 1)]

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
            # Find top layer by maximum k
            mk = -1
            mp = 0
            mx = 0
            for (kk, pp, xx) in stacks[i]:
                if kk > mk:
                    mk = kk; mp = pp; mx = xx
            cover = len(stacks[i])
            if (cover & 1) == mp:
                total += mx
            else:
                total -= mx
        return total

    ans = [0] * (q + 1)

    def dfs(u):
        # Enter: apply op at this node
        tag = None
        if u != 0:
            op = ops[u]
            if op[0] == 'add':
                _, l, r, k, p, x = op
                apply_range(l, r, k, p, x)
                tag = ('add', l, r)  # for revert
            else:
                # 'undo' node has no direct state change here
                tag = None

            # Record answer after applying this operation
            ans[u] = recompute_total()
        # Visit children
        for v in children[u]:
            dfs(v)
        # Exit: revert this node's change
        if tag and tag[0] == 'add':
            _, l, r = tag
            revert_range(l, r)

    dfs(0)

    out = []
    for i in range(1, q + 1):
        out.append(str(ans[i]))
    sys.stdout.write("\n".join(out))

if __name__ == "__main__":
    main()
