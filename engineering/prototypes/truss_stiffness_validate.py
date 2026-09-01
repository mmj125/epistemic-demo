import numpy as np
import scipy.io as sio

m = sio.loadmat('/root/.claude/uploads/a91dfe50-e6e4-5dfa-9b7b-8947cd2511e1/be3c8dbe-Ground_Structure_3x6.mat')
nodes = m['node_info'][:, :2]          # (28,2) x,y in inches
elems = m['elem_info'][:, :2].astype(int) - 1  # 0-based node indices, (81,2)
E = m['mat_info'][0, 0]                # 30800 psi
A = m['sect_info'][0, 0]               # 0.01284 in^2
defl_ref = m['defl']                   # ground truth (28,6): dx,dy,...

n = nodes.shape[0]
ndof = 2 * n
K = np.zeros((ndof, ndof))

for i, j in elems:
    xi, yi = nodes[i]
    xj, yj = nodes[j]
    L = np.hypot(xj - xi, yj - yi)
    c = (xj - xi) / L
    s = (yj - yi) / L
    k = E * A / L
    ke = k * np.array([
        [ c*c,  c*s, -c*c, -c*s],
        [ c*s,  s*s, -c*s, -s*s],
        [-c*c, -c*s,  c*c,  c*s],
        [-c*s, -s*s,  c*s,  s*s],
    ])
    dofs = [2*i, 2*i+1, 2*j, 2*j+1]
    for a in range(4):
        for b in range(4):
            K[dofs[a], dofs[b]] += ke[a, b]

# Supports: nodes 0, 6, 12, 18 (0-based, all 4 left-edge nodes) fixed in x and y
fixed_nodes = [0, 6, 12, 18]
fixed_dofs = sorted([2*i for i in fixed_nodes] + [2*i+1 for i in fixed_nodes])

# Load: node 24 (0-based, node 25 in 1-based) Fy = -1.5 lbf
F = np.zeros(ndof)
F[2*24 + 1] = -1.5

free_dofs = [d for d in range(ndof) if d not in fixed_dofs]

Kff = K[np.ix_(free_dofs, free_dofs)]
Ff = F[free_dofs]
uf = np.linalg.solve(Kff, Ff)

u = np.zeros(ndof)
for idx, d in enumerate(free_dofs):
    u[d] = uf[idx]

dx = u[0::2]
dy = u[1::2]

print("Computed node 25 (0-based idx 24) dx, dy:", dx[24], dy[24])
print("Reference (MASTAN2) node 25 dx, dy:      ", defl_ref[24, 0], defl_ref[24, 1])
print()
err = np.max(np.abs(dy - defl_ref[:, 1]))
print("Max abs error across all nodes (dy):", err)
match = np.allclose(dy, defl_ref[:, 1], atol=1e-4) and np.allclose(dx, defl_ref[:, 0], atol=1e-4)
print("MATCHES MASTAN2 reference:", match)
