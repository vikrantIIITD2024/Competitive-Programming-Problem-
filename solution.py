import sys
sys.setrecursionlimit(1_000_000)
rd = sys.stdin.buffer.readline

# ----------------------------
# Utilities: Version tree build
# ----------------------------

def build_version_tree(q):
    """
    Build a rooted tree of operations (version tree).
    Node 0 is the initial state.
    For i=1..q:
      - If op is '+ l r k p x': parent[i] = current; current = i
      - If op is '- t': parent[i] = t; current = i
    Returns:
      ops: list of op tuples (None at 0), either ('add', l, r, k, p, x) or ('undo', t)
      ch: adjacency list of children
    """
    ops_raw = [rd().split() for _ in range(q)]
    ops = [None] * (q + 1)
    parent = [0] * (q + 1)
    ch = [[] for _ in range(q + 1)]

    cur = 0
    for i in range(1, q + 1):
        t = ops_raw[i - 1]
        if t[0] == b'+':
            l = int(t[1]); r = int(t[2])
            k = int(t[3]); p = int(t[4]); x = int(t[5])
            ops[i] = ('add', l, r, k, p, x)
            parent[i] = cur
            ch[parent[i]].append(i)
            cur = i
        else:
            # "- t"
            to = int(t[1])
            ops[i] = ('undo', to)
            parent[i] = to
            ch[parent[i]].append(i)
            cur = i
    return ops, ch


# ----------------------------------------
# Core state with rollback (simple version)
# ----------------------------------------

class SpellbookState:
    """
    Maintains:
      - base array a[1..n]
      - per-index stacks of active layers (k, p, x), where top is max-k
      - per-index coverage count
      - current total sum = sum(a) + sum(contribution(i))
    Contribution rule at index i:
      let top layer be (k,p,x) with k = max of active ks at i (if any),
      let c = coverage_count[i],
      if (c % 2) == p: +x else -x
    """
    __slots__ = (
        "n", "a", "base_sum", "cover", "stacks", "top", "total",
        "changes"
    )
    def __init__(self, a):
        self.n = len(a) - 1  # a is 1-indexed
        self.a = a
        self.base_sum = sum(a[1:])
        self.cover = [0] * (self.n + 1)     # coverage count per index
        self.stacks = [[] for _ in range(self.n + 1)]  # stack of (k,p,x); track max-k on top by sorted pushes
        self.top = [None] * (self.n + 1)    # cached top (p, x) or None
        self.total = self.base_sum           # base + contributions
        self.changes = []                    # rollback stack of callables

    # ---- Helpers to compute per-index contribution ----
    @staticmethod
    def contrib_for(cov, top):
        if top is None:
            return 0
        p, x = top
        if (cov & 1) == p:
            return x
        else:
            return -x

    # ---- Internal primitive: set top for one index (with rollback) ----
    def _set_top(self, i, new_top):
        old_top = self.top[i]
        if old_top == new_top:
            # no change, but keep rollback noop for symmetry if desired
            return

        # Adjust total by removing old contrib, adding new contrib
        delta = 0
        if old_top is not None:
            delta -= self.contrib_for(self.cover[i], old_top)
        if new_top is not None:
            delta += self.contrib_for(self.cover[i], new_top)
        self.total += delta

        self.top[i] = new_top

        def undo():
            # revert to old_top
            # reverse delta
            rev_delta = 0
            cur = self.top[i]
            if cur is not None:
                rev_delta -= self.contrib_for(self.cover[i], cur)
            if old_top is not None:
                rev_delta += self.contrib_for(self.cover[i], old_top)
            self.total += rev_delta
            self.top[i] = old_top

        self.changes.append(undo)

    # ---- Internal primitive: bump coverage for one index (with rollback) ----
    def _add_cover(self, i, d):
        # coverage changes parity -> may flip sign of contribution
        # remove old contrib, update cover, add new contrib
        old_cov = self.cover[i]
        old_top = self.top[i]
        delta = 0
        if old_top is not None:
            delta -= self.contrib_for(old_cov, old_top)
        new_cov = old_cov + d
        self.cover[i] = new_cov
        if old_top is not None:
            delta += self.contrib_for(new_cov, old_top)
        self.total += delta

        def undo():
            # revert coverage
            cur_cov = self.cover[i]
            cur_top = self.top[i]
            rev = 0
            if cur_top is not None:
                rev -= self.contrib_for(cur_cov, cur_top)
            self.cover[i] = old_cov
            if cur_top is not None:
                rev += self.contrib_for(old_cov, cur_top)
            self.total += rev

        self.changes.append(undo)

    # ---- Applying a layer to index i ----
    def _apply_layer_at_i(self, i, k, p, x):
        """
        Push a layer (k,p,x) to index i:
          - Increase coverage by +1
          - Insert into stack maintaining 'top' = layer with maximum k
        """
        # 1) coverage +1
        self._add_cover(i, +1)

        # 2) stacks[i] insert by k; we keep all layers but track top by k=max
        # We don’t need full sort; just push and update top if k is new max.
        prev_top = self.top[i]
        # Determine current max-k (implicit):
        # If prev_top is None, any push becomes top.
        # If prev_top exists and this k is bigger than the k behind prev_top, we promote.
        # To know the k behind prev_top we must also store k there.
        # So: keep a parallel "best k" for i. We can recover k from stack by scanning
        #   but that would be O(height). To keep it simple and still correct, we scan.
        self.stacks[i].append((k, p, x))

        # compute new max layer among active
        mk = -1
        mp = 0
        mx = 0
        for (kk, pp, xx) in self.stacks[i]:
            if kk > mk:
                mk = kk; mp = pp; mx = xx
        new_top = (mp, mx)

        # If top changed, update it
        self._set_top(i, new_top)

        def undo():
            # pop from stack and recompute top
            self.stacks[i].pop()
            # recompute new top after pop
            mk2 = -1
            mp2 = 0
            mx2 = 0
            for (kk, pp, xx) in self.stacks[i]:
                if kk > mk2:
                    mk2 = kk; mp2 = pp; mx2 = xx
            new_top2 = None if mk2 < 0 else (mp2, mx2)
            # set_top with rollback-neutral (but we are in an undo function, so do a direct inverse of set_top)
            # We cannot call _set_top here because that would push another undo. So we do manual inverse:
            cur_top = self.top[i]
            # adjust total: remove cur_top contrib, add new_top2 contrib
            delta = 0
            if cur_top is not None:
                delta -= self.contrib_for(self.cover[i], cur_top)
            if new_top2 is not None:
                delta += self.contrib_for(self.cover[i], new_top2)
            self.total += delta
            self.top[i] = new_top2

            # also revert coverage (+1) we did earlier
            # but coverage revert must match the order of our change pushes:
            # Here, we are inside the undo for the second push (stack/top),
            # the coverage undo is a separate callable earlier on the stack and will be called automatically
            # by the main rollback routine; hence DO NOT touch coverage here.

        # Replace the last change (which was _set_top) with a combined undo that also restores stack
        # Actually, we can just append a separate undo for stack pop; order matters:
        self.changes.append(undo)

    # ---- Removing a layer from index i (inverse of apply) ----
    def _remove_layer_at_i(self, i, k, p, x):
        """
        Exact inverse of _apply_layer_at_i for the same (i,k,p,x) in LIFO order at DFS.
        This is handled automatically by the rollback stack, so we don't need a separate public API.
        """

    # ---- Public range APIs used by DFS ----
    def apply_layer_range(self, l, r, k, p, x):
        """
        Apply one layer over [l, r]. We push two changes per i:
          - coverage +1 (with rollback)
          - push layer to stack, recompute top (with rollback)
        """
        for i in range(l, r + 1):
            self._apply_layer_at_i(i, k, p, x)

    def revert_to(self, checkpoint_size):
        """
        Rollback all changes down to checkpoint_size (LIFO).
        """
        while len(self.changes) > checkpoint_size:
            undo = self.changes.pop()
            undo()

    def checkpoint(self):
        return len(self.changes)


# --------------------------
# DFS over the version tree
# --------------------------

def main():
    n, q = map(int, rd().split())
    arr = [0] + list(map(int, rd().split()))  # 1-indexed

    ops, children = build_version_tree(q)

    state = SpellbookState(arr)
    ans = [0] * (q + 1)

    def enter_node(op):
        """
        Apply this node's effect and return a checkpoint for rollback on exit.
        'undo' nodes do not change the state directly (the parent pointer already encoded time jump).
        """
        cp = state.checkpoint()
        if op is None:
            return cp
        if op[0] == 'add':
            _, l, r, k, p, x = op
            state.apply_layer_range(l, r, k, p, x)
        else:
            # 'undo' node: nothing to apply here
            pass
        return cp

    def dfs(u):
        cp = enter_node(ops[u])

        if u != 0:
            ans[u] = state.total

        for v in children[u]:
            dfs(v)

        state.revert_to(cp)

    dfs(0)

    out = []
    for i in range(1, q + 1):
        out.append(str(ans[i]))
    sys.stdout.write("\n".join(out))


if __name__ == "__main__":
    main()
