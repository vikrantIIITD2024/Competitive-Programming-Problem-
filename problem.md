# The Archmage's Layered Spellbook

## Problem Description

Deep in the Tower of Mirrors, the Archmage maintains a magic array of energy crystals `a[1..n]`, each with an initial energy value. Over time, the Archmage performs `q` spells on these crystals.

## Spell Types

### 1. Energy Spell
l r k p x

where:
- `[l, r]` - range of crystals affected
- `k` - layer ID of the spell
- `p` - parity mode (0 for even, 1 for odd)
- `x` - energy magnitude to add or subtract

### 2. Undo Spell
t

Rewinds the entire spellbook back to the exact state after spell `t` was cast, erasing all later spells.

## Spell Mechanics

- Each spell activates a new magical layer labeled `k` on crystals `l..r`
- Crystals may have multiple active layers stacked upon them
- The **topmost layer** (largest `k`) controls the final behavior

For a crystal with top layer `(k, p, x)`:
- If the number of active layers covering that crystal is **even** and `p = 0`, it gains energy `+x`
- If the number of active layers covering that crystal is **odd** and `p = 1`, it gains energy `+x`
- Otherwise, it loses energy `-x`

## Input Format
n q

a1 a2 ... an

Followed by `q` lines of operations, each either:
- `+ l r k p x`
- `- t`

## Output Format
After each operation, print the sum of all crystals' current energies.

## Example

**Input:**

4 5
2 3 5 1

1 3 1 0 2

2 4 2 1 1

1

1 4 3 0 3

0


**Output:**

15
18
15
24
11


## Note

1. "UNDO 0" means reverting to the initial state (no spells active)
2. Multiple layers can overlap; only the highest k layer on each crystal determines its visible effect
3. The parity check (even vs odd) depends on all currently active layers, not just the top one
4. Time rewinds may cause new histories to branch

