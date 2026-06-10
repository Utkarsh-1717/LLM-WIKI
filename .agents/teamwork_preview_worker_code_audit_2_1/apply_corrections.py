import json
import os

notebook_path = "/storage/emulated/0/Quant/LLM-WIKI/Soul/Master_Pairs_Trading_Soul.ipynb"

# Load notebook
with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Find cells by ID
cells_by_id = {cell.get("id"): cell for cell in nb.get("cells", []) if cell.get("id")}

print("=== Starting Notebook Modifications ===")

# 1. Cell e9cf67b2: Pass 2 alignment
cell1 = cells_by_id.get("e9cf67b2")
if cell1:
    source_str = "".join(cell1["source"])
    target = (
        "# Pass 2: Inner join on survivors (drop timestamps missing ANY survivor)\n"
        "price_matrix_close = price_matrix_close.dropna(how='any', axis=0)\n"
        "common_idx = price_matrix_close.index\n"
        "price_matrix_open = price_matrix_open.loc[common_idx]\n"
    )
    replacement = (
        "# Pass 2: Inner join on survivors (drop timestamps missing ANY survivor)\n"
        "price_matrix_close = price_matrix_close.dropna(how='any', axis=0)\n"
        "price_matrix_open = price_matrix_open.dropna(how='any', axis=0)\n"
        "common_idx = price_matrix_close.index.intersection(price_matrix_open.index)\n"
        "price_matrix_close = price_matrix_close.loc[common_idx]\n"
        "price_matrix_open = price_matrix_open.loc[common_idx]\n"
    )
    if target in source_str:
        source_str = source_str.replace(target, replacement)
        cell1["source"] = source_str.splitlines(keepends=True)
        print("✅ Cell e9cf67b2: Pass 2 alignment successfully replaced.")
    else:
        print("❌ Cell e9cf67b2: Target string not found!")
else:
    print("❌ Cell e9cf67b2 not found!")

# 2. Cell ca17c2f1: OLS P0 init, phi stability check, duplicate em_kalman_scaled removal
cell2 = cells_by_id.get("ca17c2f1")
if cell2:
    source_str = "".join(cell2["source"])
    
    # a. Change OLS P0 initialization
    target_p0 = "    P0 = np.eye(2) * 1e-3\n"
    replace_p0 = "    P0 = sigma2 * XtX_inv * 10.0\n"
    
    p0_replaced = False
    if target_p0 in source_str:
        source_str = source_str.replace(target_p0, replace_p0)
        p0_replaced = True
        print("✅ Cell ca17c2f1: OLS P0 initialization successfully replaced.")
    else:
        print("❌ Cell ca17c2f1: OLS P0 target string not found!")
        
    # b. Change stability check for phi
    target_phi = "if not (0.0 < phi < 1.0) or not np.isfinite(phi):"
    replace_phi = "if not (1e-5 < phi < 1.0 - 1e-5) or not np.isfinite(phi):"
    
    phi_replaced = False
    if target_phi in source_str:
        source_str = source_str.replace(target_phi, replace_phi)
        phi_replaced = True
        print("✅ Cell ca17c2f1: phi stability check successfully replaced.")
    else:
        print("❌ Cell ca17c2f1: phi stability check target string not found!")
        
    # Convert back to list of lines to handle duplicate removal
    cell2["source"] = source_str.splitlines(keepends=True)
    
    # c. Remove duplicate definition of em_kalman_scaled
    lines = cell2["source"]
    def_indices = [i for i, line in enumerate(lines) if line.strip() == "def em_kalman_scaled(ya, yb, is_new_day):"]
    wrapper_indices = [i for i, line in enumerate(lines) if line.strip() == "def em_kalman_scaled_wrapper(ya, yb, is_new_day):"]
    
    if len(def_indices) == 2 and len(wrapper_indices) == 1:
        idx1 = def_indices[0]
        idx2 = def_indices[1]
        wrapper_idx = wrapper_indices[0]
        
        if idx1 < wrapper_idx < idx2:
            # Remove the first definition
            cell2["source"] = lines[:idx1] + lines[wrapper_idx:]
            print("✅ Cell ca17c2f1: First duplicate definition of em_kalman_scaled successfully removed.")
        else:
            print(f"❌ Cell ca17c2f1: Order of definitions mismatch: idx1={idx1}, wrapper_idx={wrapper_idx}, idx2={idx2}")
    else:
        print(f"❌ Cell ca17c2f1: Cannot remove duplicate definition (found {len(def_indices)} defs and {len(wrapper_indices)} wrappers).")
else:
    print("❌ Cell ca17c2f1 not found!")

# 3. Cell c138afc1: optimized_rows.append block
cell3 = cells_by_id.get("c138afc1")
if cell3:
    lines = cell3["source"]
    start_idx = -1
    for i, line in enumerate(lines):
        if "optimized_rows.append({" in line:
            start_idx = i
            break
            
    if start_idx != -1:
        end_idx = -1
        for i in range(start_idx, len(lines)):
            if lines[i].strip() == "})":
                end_idx = i
                break
                
        if end_idx != -1:
            block_content = "".join(lines[start_idx:end_idx+1])
            if "symbol_a" in block_content and "lagger" in block_content:
                replacement_lines = [
                    "    optimized_rows.append({\n",
                    '        "symbol_a": sym_a,\n',
                    '        "symbol_b": sym_b,\n',
                    '        "best_z_entry": best_config[0],\n',
                    '        "best_z_sl": best_config[1],\n',
                    '        "best_hl_stop": best_config[2],\n',
                    '        "gross_profit": best_profit,\n',
                    '        "trade_count": best_trade_count,\n',
                    '        "win_rate": best_win_rate,\n',
                    '        "exit_mr_count": int(best_stats[0]),\n',
                    '        "exit_sl_count": int(best_stats[1]),\n',
                    '        "exit_hl_count": int(best_stats[2]),\n',
                    '        "exit_session_count": int(best_stats[3]),\n',
                    '        "avg_points_profit": float(best_stats[4]),\n',
                    '        "avg_points_loss": float(best_stats[5]),\n',
                    '        "lagger": lagger,\n',
                    "    })\n"
                ]
                cell3["source"] = lines[:start_idx] + replacement_lines + lines[end_idx+1:]
                print("✅ Cell c138afc1: optimized_rows.append block successfully replaced.")
            else:
                print("❌ Cell c138afc1: Block content verification failed (does not contain expected symbols).")
        else:
            print("❌ Cell c138afc1: Matching end of block not found!")
    else:
        print("❌ Cell c138afc1: optimized_rows.append({ not found!")
else:
    print("❌ Cell c138afc1 not found!")

# Save modified notebook
with open(notebook_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
print("=== Notebook saved successfully ===")
