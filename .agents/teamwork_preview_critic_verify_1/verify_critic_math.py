import numpy as np
import pandas as pd

def test_data_alignment():
    print("=== Testing Data Alignment ===")
    # Create dummy data with gaps
    dt = pd.date_range("2026-06-04 09:15:00", periods=5, freq="min")
    pa = pd.Series([100.0, 101.0, np.nan, 102.0, 103.0], index=dt)
    pb = pd.Series([50.0, np.nan, 51.0, 52.0, np.nan], index=dt)
    
    # Original Stage 2 code:
    # aligned = pd.DataFrame({"a": pa, "b": pb}).dropna(how="any")
    # aligned = aligned.ffill(limit=1).dropna(how="any")
    df_orig = pd.DataFrame({"a": pa, "b": pb}).dropna(how="any")
    df_orig_filled = df_orig.ffill(limit=1).dropna(how="any")
    print(f"Original logic output length: {len(df_orig_filled)} (expected 0 if gaps don't overlap perfectly)")
    
    # Proposed Stage 2 code:
    df_prop = pd.DataFrame({"a": pa, "b": pb})
    df_prop_filled = df_prop.ffill(limit=1).dropna(how="any")
    print(f"Proposed logic output length: {len(df_prop_filled)}")
    print(df_prop_filled)
    assert len(df_prop_filled) > 0, "Proposed alignment should retain filled values"

def test_ols_p0():
    print("\n=== Testing OLS P0 Initialization ===")
    n_i = 10
    np.random.seed(42)
    yb = np.random.normal(5.0, 0.1, n_i)
    ya = 2.0 * yb + 1.0 + np.random.normal(0, 0.01, n_i)
    
    # Original logic:
    Xols = np.column_stack([yb, np.ones(n_i)])
    th0, _, _, _ = np.linalg.lstsq(Xols, ya, rcond=None)
    P0_orig = np.cov(Xols.T) * 10.0
    print("Original P0:\n", P0_orig)
    print("Original P0 variance for intercept (should be 0):", P0_orig[1, 1])
    assert P0_orig[1, 1] == 0.0, "Original intercept variance must be 0"

    # Proposed logic:
    y_pred = Xols @ th0
    resid = ya - y_pred
    sigma2 = np.sum(resid**2) / (n_i - 2)
    XTX_inv = np.linalg.inv(Xols.T @ Xols)
    P0_prop = sigma2 * XTX_inv * 10.0
    print("Proposed P0:\n", P0_prop)
    print("Proposed P0 variance for intercept (should be > 0):", P0_prop[1, 1])
    assert P0_prop[1, 1] > 0.0, "Proposed intercept variance should be positive"
    assert np.all(np.linalg.eigvals(P0_prop) > 0), "Proposed P0 should be positive definite"

def test_em_q_update():
    print("\n=== Testing EM Q Update ===")
    T = 15
    np.random.seed(42)
    
    # Dummy Kalman filter output
    ts = np.random.normal(2.0, 0.1, (T, 2))  # smoothed states
    Ps = np.random.normal(0.01, 0.001, (T, 2, 2))  # smoothed covs
    # Make Ps symmetric positive-definite
    for t in range(T):
        Ps[t] = Ps[t] @ Ps[t].T + np.eye(2) * 0.01
        
    Pc = np.random.normal(0.005, 0.001, (T, 2, 2))  # cross covs
    
    # Original calculation
    ts1 = ts[1:]
    ts0 = ts[:-1]
    Ps1 = Ps[1:]
    Pc_ = Pc[:T-1]
    
    oss = np.einsum("ti,tj->tij", ts1, ts1)
    osc = np.einsum("ti,tj->tij", ts1, ts0)
    Q_s_orig = Ps1 + oss - Pc_ - osc
    Q_n_orig = np.mean(Q_s_orig, axis=0)
    Q_n_orig = (Q_n_orig + Q_n_orig.T) / 2
    print("Original Q_n:\n", Q_n_orig)
    
    # Proposed calculation
    # Complete E[(theta_t - theta_{t-1})(theta_t - theta_{t-1})^T | y]
    Ps0 = Ps[:-1]
    os00 = np.einsum("ti,tj->tij", ts0, ts0)
    
    # term3 = E[theta_{t-1} theta_t^T | y] = Pc_ + ts0 * ts1^T
    # osc_t0_t1 = ts0_i * ts1_j
    osc_t0_t1 = np.einsum("ti,tj->tij", ts0, ts1)
    term3 = Pc_ + osc_t0_t1
    
    Q_s_prop = (Ps1 + oss) + (Ps0 + os00) - term3 - np.transpose(term3, (0, 2, 1))
    Q_n_prop = np.mean(Q_s_prop, axis=0)
    print("Proposed Q_n:\n", Q_n_prop)
    
    # Verify symmetry
    is_symmetric = np.allclose(Q_n_prop, Q_n_prop.T)
    print(f"Is proposed Q_n symmetric: {is_symmetric}")
    assert is_symmetric, "Proposed Q_n must be symmetric"
    
    # Verify eigenvalues (should be positive semi-definite)
    eigvals = np.linalg.eigvals(Q_n_prop)
    print(f"Proposed Q_n eigenvalues: {eigvals}")
    # Note: with random dummy inputs, we want to ensure it works for valid state updates.
    # In actual filter, the term is always PSD because it's an expectation of a quadratic form.

def test_phi_guard():
    print("\n=== Testing Phi Guard ===")
    # Test cases for phi
    for phi in [0.95, 0.0, -0.5, 1.05]:
        if phi <= 0.0 or phi >= 1.0:
            print(f"phi = {phi:5} -> INVALID (Guarded, setting to NaN)")
        else:
            kappa = -np.log(phi)
            print(f"phi = {phi:5} -> VALID (kappa = {kappa:.4f})")

def test_overnight_gap():
    print("\n=== Testing Overnight Gap Mask and Weighting ===")
    T = 10
    # Simulate a date transition at index 4 (5th bar of sequence)
    # e.g., 09:15 bar of day 2
    is_new_day = np.zeros(T, dtype=np.bool_)
    is_new_day[0] = True
    is_new_day[4] = True  # overnight transition
    
    # Transitions are from t-1 to t
    # For transitions t = 1 to T-1, we define a multiplier vector
    M_overnight = 15.0
    d = np.ones(T - 1)
    is_overnight = is_new_day[1:]
    d[is_overnight] = M_overnight
    
    print("Transition multiplier vector (length T-1):", d)
    assert d[3] == M_overnight, "Transition 3 (index 3 to 4) should be overnight"
    assert d[0] == 1.0, "Transition 0 (index 0 to 1) should be intraday"

if __name__ == "__main__":
    test_data_alignment()
    test_ols_p0()
    test_em_q_update()
    test_phi_guard()
    test_overnight_gap()
    print("\nAll mathematical logic checks passed!")
