"""
First real bridge configuration: X-large scale (leg=red=6.5cm, hypotenuse=purple=9.5cm),
20 bays spanning 130cm exactly, simply supported (pin + roller), 1kg at midspan.

Validates two things at once:
1. Static equilibrium (reactions sum to exactly cancel the applied load) - same check
   used for Tab 3, the only real correctness check available since there's no MASTAN
   file for the bridge the way there was for the cantilever.
2. The actual pedagogical claim Matt made: "one layer is never enough" - compare a
   2-row (1-layer) truss against a 3-row (2-layer) truss of the same span/scale and
   confirm the deeper one really does deflect meaningfully less, using the real solver,
   not just assumed.
"""
import numpy as np

E = 21235.86  # N/cm^2
A = 0.08284   # cm^2
LEG = 6.5     # cm, red rod (X-large scale)
BAYS = 20     # 20 x 6.5cm = 130cm exactly
LOAD_N = -9.81  # 1kg downward


def generate_ground_structure(cols, rows, spacing):
    nodes = []
    index = {}
    for r in range(rows):
        for c in range(cols):
            index[(c, r)] = len(nodes)
            nodes.append([c * spacing, r * spacing])
    elems = []
    for r in range(rows):
        for c in range(cols - 1):
            elems.append((index[(c, r)], index[(c + 1, r)]))
    for r in range(rows - 1):
        for c in range(cols):
            elems.append((index[(c, r)], index[(c, r + 1)]))
    for r in range(rows - 1):
        for c in range(cols - 1):
            elems.append((index[(c, r)], index[(c + 1, r + 1)]))
            elems.append((index[(c + 1, r)], index[(c, r + 1)]))
    return nodes, elems


def analyze(nodes, elems, fixed_dofs_dict, load_node, load_vec):
    """fixed_dofs_dict: {node_index: (fix_x: bool, fix_y: bool)} - lets us model a
    roller (fix_y only) as well as a pin (fix both), unlike the cantilever's all-pin supports."""
    n = len(nodes)
    ndof = 2 * n
    K = np.zeros((ndof, ndof))
    for i, j in elems:
        xi, yi = nodes[i]; xj, yj = nodes[j]
        L = np.hypot(xj - xi, yj - yi)
        c = (xj - xi) / L; s = (yj - yi) / L
        k = E * A / L
        ke = k * np.array([[c*c,c*s,-c*c,-c*s],[c*s,s*s,-c*s,-s*s],
                            [-c*c,-c*s,c*c,c*s],[-c*s,-s*s,c*s,s*s]])
        dofs = [2*i, 2*i+1, 2*j, 2*j+1]
        for a in range(4):
            for b in range(4):
                K[dofs[a], dofs[b]] += ke[a, b]

    fixed_dofs = set()
    for node, (fx, fy) in fixed_dofs_dict.items():
        if fx: fixed_dofs.add(2*node)
        if fy: fixed_dofs.add(2*node+1)
    free = [d for d in range(ndof) if d not in fixed_dofs]

    F = np.zeros(ndof)
    F[2*load_node+1] = load_vec

    Kff = K[np.ix_(free, free)]
    Ff = F[free]
    if np.linalg.matrix_rank(Kff) < len(free):
        return None
    uf = np.linalg.solve(Kff, Ff)
    u = np.zeros(ndof)
    for k_, d in enumerate(free):
        u[d] = uf[k_]

    Ku = K @ u
    reactions = {node: (Ku[2*node], Ku[2*node+1]) for node in fixed_dofs_dict}
    return u, reactions


for rows, label in [(2, "1 layer (2 rows)"), (3, "2 layers (3 rows)")]:
    nodes, elems = generate_ground_structure(cols=BAYS+1, rows=rows, spacing=LEG)
    n_bottom_right = BAYS  # bottom-right corner node index (row 0, last column)
    mid_col = BAYS // 2
    mid_node = mid_col  # bottom row, midspan

    fixed = {0: (True, True), n_bottom_right: (False, True)}  # pin at bottom-left, roller at bottom-right
    result = analyze(nodes, elems, fixed, mid_node, LOAD_N)
    if result is None:
        print(f"{label}: UNSTABLE (mechanism) - shouldn't happen for a full ground structure")
        continue
    u, reactions = result
    dy_mid = u[2*mid_node+1]
    r0 = reactions[0]
    r1 = reactions[n_bottom_right]
    print(f"{label}: {len(nodes)} nodes, {len(elems)} candidate members")
    print(f"  Midspan deflection: {dy_mid:.4f} cm")
    print(f"  Reactions: pin={tuple(round(v,3) for v in r0)}, roller={tuple(round(v,3) for v in r1)}")
    print(f"  Equilibrium check (sum should be (0, {-LOAD_N})): ({r0[0]+r1[0]:.6f}, {r0[1]+r1[1]:.6f})")
    print()
