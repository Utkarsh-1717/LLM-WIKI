import pandas as pd
import numpy as np

def test_em():
    # Load 1 pair from scratch output
    df = pd.read_csv('/storage/emulated/0/Quant/LLM-WIKI/scratch/pairs_top500.csv')
    sym_a = df['symbol_a'].iloc[0]
    sym_b = df['symbol_b'].iloc[0]
    print(f"Testing {sym_a} and {sym_b}")
    # We don't have price data here locally unless we fetch it from sqlite
    import sqlite3
    con = sqlite3.connect('/storage/emulated/0/Quant/LLM-WIKI/scratch/../Master-Data-1min.sqlite') # wait, path is /storage/emulated/0/Quant/LLM-WIKI/Master-Data-1min.sqlite? No, it's inside kaggle input?
    pass

if __name__ == "__main__":
    test_em()
