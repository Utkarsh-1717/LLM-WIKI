# Create Master-Data-1min Dataset on Kaggle

This plan outlines the creation of a Kaggle notebook to systematically fetch and store 1-minute historical data for all NSE 500 stocks over the last 120 trading days using the Fyers API.

## User Review Required

> [!IMPORTANT]
> **Kaggle Dataset vs Notebook Output:**
> The most robust way to create a dataset purely on Kaggle is to use the native Notebook Output feature. The notebook will generate the `Master-Data-1min.sqlite` file in its output directory. On Kaggle, this output is automatically treated as a dataset that can be directly imported into any future backtesting notebooks (via "Add Data -> Notebook Output"). 
> 
> *Is this acceptable, or do you explicitly need the notebook to run the `kaggle datasets create` command internally to publish a standalone dataset?* (Notebook output is highly recommended to avoid complex API credential injection within the notebook).

> [!WARNING]
> **Credential Handling:**
> To strictly obey the rule "Never write token to any file" and "Credentials always from ~/.quant_env", the local script will first push a copy of your `~/.quant_env` as a strictly **PRIVATE** Kaggle dataset (`fyers-credentials`). The Kaggle notebook will attach this private dataset to read the credentials and perform the Fyers authentication itself. This ensures maximum security.

## Proposed Changes

### 1. Credentials Push
- **Action**: Create a temporary folder locally, copy `~/.quant_env` to it, and push it as a private Kaggle dataset named `fyers-credentials`.
- **Reason**: Allows the Kaggle Notebook to securely authenticate with Fyers without hardcoding any keys or tokens.

### 2. Notebook Generation
- **Action**: Generate `Master-Data-1min-NB.ipynb` locally using a python builder script. The notebook will strictly adhere to the `kaggle-notebook-run` skill cell structure.
- **Stages in Notebook**:
  - **Stage 1 (Auth)**: Install `fyers-apiv3`, load `~/.quant_env` from the private dataset, and execute the 5-step TOTP authentication.
  - **Stage 2 (NSE 500 List)**: Fetch the official Nifty 500 list from NSE via HTTP request and format symbols (e.g., `NSE:RELIANCE-EQ`).
  - **Stage 3 (Database Setup)**: Initialize `/kaggle/working/Master-Data-1min.sqlite`.
  - **Stage 4 (Fetch Data)**: Loop through the 500 symbols. For each, fetch the last 180 calendar days (which covers ~125 trading days) in two 100-day chunks (Fyers 1-minute API limit). Enforce a strict 0.5s sleep between calls. Append to SQLite using pandas.
  - **Stage 5 (Verification)**: Query the final SQLite database to count symbols processed, date ranges, and total row counts.

### 3. Execution
- **Action**: Use `kaggle kernels push` to send the notebook to Kaggle for execution.
- **Action**: Provide you with the URL to monitor the notebook.

## Verification Plan

### Automated Checks
- The notebook itself will run a SQL query at the end to verify:
  1. The exact number of unique equities successfully downloaded.
  2. The exact number of trading days captured per equity.
  3. The total database row count and file size.
- Errors during downloading (e.g., delisted stocks or API timeouts) will be systematically caught, printed, and logged in a final error summary within the notebook.

### Manual Verification
- Review the Kaggle notebook output logs and verify the presence of `Master-Data-1min.sqlite`.
