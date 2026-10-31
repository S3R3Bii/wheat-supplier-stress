"""Sharp finite-network endpoints under an explicitly authored outside-capacity class."""

from fractions import Fraction as F
from flow import maximum_flow, separate_country_claims

OUTSIDE = "999999"


def classify(demand, lower, upper):
    assert 0 <= lower <= upper <= demand
    if demand == 0:
        return "ZERO_MODELED_LOSS"
    if lower == demand:
        return "KNOWN_NETWORK_SUFFICIENT"
    if upper < demand:
        return "CONDITIONAL_SHORTFALL"
    return "UNRESOLVED_WITHOUT_OUTSIDE_CAPACITY"


def completion(supplies, routes, demands, residual, gamma):
    gamma = F(gamma)
    if gamma not in [F(), F(1, 2), F(1)]:
        raise ValueError("outside envelope not in committed grid")
    if OUTSIDE in supplies or set(residual) != set(demands):
        raise ValueError("incomplete or reserved outside identity")
    if any(F(v) < 0 for v in residual.values()):
        raise ValueError("negative accounting residual")
    s = {str(k): F(v) for k, v in supplies.items()}
    r = {k: F(v) for k, v in routes.items()}
    d = {str(k): F(v) for k, v in demands.items()}
    s[OUTSIDE] = sum((gamma * F(v) for v in residual.values()), F())
    for i in d:
        r[OUTSIDE, i] = gamma * F(residual[i])
    return s, r, d


def endpoint(supplies, routes, demands, residual, gamma):
    s, r, d = completion(supplies, routes, demands, residual, gamma)
    total, flows, aug = maximum_flow(s, r, d)
    separate = separate_country_claims(s, r, d)
    return s, r, d, total, flows, aug, separate


def capacities(inputs, basis, alpha, beta, lost):
    s = {
        o: F(alpha) * F(v) if o != lost else F()
        for o, v in inputs["prior_exports"].items()
    }
    routes = {
        tuple(k.split(":")): F(beta) * F(v)
        for k, v in inputs["prior_routes"].items()
        if v is not None and k.split(":")[0] != lost
    }
    amounts = inputs["current_" + basis]
    d = {
        i: F(amounts[lost + ":" + i]) if lost in origins else F()
        for i, origins in inputs["support"].items()
    }
    return s, routes, d, {i: F(v) for i, v in inputs["residual"].items()}
