"""
Validates a generic (cols, rows, spacing) -> (nodes, elems) ground-structure generator
against the ALREADY-VALIDATED cantilever ground structure (Ground_Structure_3x6.mat),
before trusting it for the new bridge tool's different scale/depth.

The cantilever's 81 members = a regular 6-col x 4-row grid (68 members: horizontal +
vertical + both diagonals per cell) PLUS an irregular 4-node tip extension (13 members)
that's specific to the cantilever's real physical shape, not relevant to the bridge.
So: validate the generator's output against just the regular-grid subset of the real,
already-proven cantilever structure.
"""
import scipy.io as sio
import numpy as np

def generate_ground_structure(cols, rows, spacing):
    """cols x rows nodes on a uniform grid; candidate members = every horizontal edge,
    every vertical edge, and BOTH diagonals of every unit cell (X-brace), matching the
    same pattern already used (and toggled) in the cantilever ground structure and in
    engineering/investigation.html's Tab 2."""
    nodes = []
    index = {}
    for r in range(rows):
        for c in range(cols):
            index[(c, r)] = len(nodes)
            nodes.append([c * spacing, r * spacing])

    elems = []
    # horizontal
    for r in range(rows):
        for c in range(cols - 1):
            elems.append((index[(c, r)], index[(c + 1, r)]))
    # vertical
    for r in range(rows - 1):
        for c in range(cols):
            elems.append((index[(c, r)], index[(c, r + 1)]))
    # both diagonals per cell
    for r in range(rows - 1):
        for c in range(cols - 1):
            elems.append((index[(c, r)], index[(c + 1, r + 1)]))       # bottom-left to top-right
            elems.append((index[(c + 1, r)], index[(c, r + 1)]))       # bottom-right to top-left

    return nodes, elems


# --- Load the real, already-validated cantilever structure ---
m = sio.loadmat('/home/user/epistemic-demo/engineering/prototypes/Ground_Structure_3x6.mat')
real_nodes = m['node_info'][:, :2]
real_elems = (m['elem_info'][:, :2].astype(int) - 1).tolist()

# The regular 6x4 grid is nodes 0-23 (0-based); nodes 24-27 are the irregular tip extension.
REGULAR_NODE_COUNT = 24
regular_elems = [tuple(sorted(e)) for e in real_elems if e[0] < REGULAR_NODE_COUNT and e[1] < REGULAR_NODE_COUNT]
regular_elems_set = set(regular_elems)

print(f"Real cantilever structure: {len(real_nodes)} nodes, {len(real_elems)} members total")
print(f"Regular-grid subset (excluding the irregular tip extension): {len(regular_elems)} members")

# --- Generate with the new generic function, same 6x4 grid, same 4.1875in spacing ---
gen_nodes, gen_elems = generate_ground_structure(cols=6, rows=4, spacing=4.1875)
gen_elems_set = set(tuple(sorted(e)) for e in gen_elems)

print(f"\nGenerated structure: {len(gen_nodes)} nodes, {len(gen_elems)} members")

# Check node positions match exactly (first 24 real nodes vs generated, allowing for
# possible different node ordering - compare as sets of coordinates)
real_coords = set(tuple(np.round(real_nodes[i], 4)) for i in range(REGULAR_NODE_COUNT))
gen_coords = set(tuple(round(x, 4) for x in n) for n in gen_nodes)
print(f"\nNode coordinates match exactly: {real_coords == gen_coords}")

print(f"Member sets match exactly: {regular_elems_set == gen_elems_set}")
if regular_elems_set != gen_elems_set:
    print("  Missing from generated:", regular_elems_set - gen_elems_set)
    print("  Extra in generated:", gen_elems_set - regular_elems_set)
