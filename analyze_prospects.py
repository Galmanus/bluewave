
import json
import math

def compute_U(A, F, k, S, w, alpha=0.5, beta=0.5, gamma=0.5, delta=0.3, epsilon=0.3):
    Fk = F * (1 - k)
    Sigma = 0.5
    tau = 0.3
    kappa = 0.3
    Phi = 0.5
    U = (alpha * A * (1 - Fk)
         - beta * Fk * (1 - S)
         + gamma * S * (1 - w) * Sigma
         + delta * tau * kappa
         - epsilon * Phi)
    return round(max(-1.0, min(2.0, U)), 4)

def compute_FP(A, F, k, S, w, R=0.5):
    U = compute_U(A, F, k, S, w)
    U_crit = 0.3
    kappa = 0.3
    tau = 0.3
    Phi = 0.5
    eps = 1e-3
    denominator = max(U_crit - U + eps, eps)
    return round(((1 - R) * (kappa + tau + Phi)) / denominator, 4)

prospects = [
    {"id": "yard_nyc", "name": "Jenny Koo (Yard NYC)", "A": 0.6, "F": 0.7, "k": 0.3, "S": 0.6, "w": 0.8},
    {"id": "langdock", "name": "Tobias Kemkes (Langdock)", "A": 0.7, "F": 0.8, "k": 0.2, "S": 0.5, "w": 0.9},
    {"id": "codedesign", "name": "Bruno Gavino (Codedesign)", "A": 0.8, "F": 0.4, "k": 0.4, "S": 0.7, "w": 0.3},
    {"id": "meta_creative", "name": "Irina Freitas (Meta Creative)", "A": 0.7, "F": 0.5, "k": 0.3, "S": 0.6, "w": 0.4},
    {"id": "gimlet", "name": "Natalie Serrino (Gimlet)", "A": 0.8, "F": 0.3, "k": 0.2, "S": 0.6, "w": 0.2}
]

results = []
for p in prospects:
    u = compute_U(p["A"], p["F"], p["k"], p["S"], p["w"])
    fp = compute_FP(p["A"], p["F"], p["k"], p["S"], p["w"])
    results.append({"name": p["name"], "U": u, "FP": fp})

results.sort(key=lambda x: x["FP"], reverse=True)

print("PTM ANALYSIS - PROSPECT FRACTURE POTENTIAL")
print("-" * 50)
for r in results:
    print(f"{r['name']:<25} | U: {r['U']:>7.4f} | FP: {r['FP']:>7.4f}")
