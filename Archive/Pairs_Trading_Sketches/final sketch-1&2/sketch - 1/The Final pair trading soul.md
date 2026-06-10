> [!WARNING]
> **ARCHIVED & OBSOLETE**
> This file is part of the trial-and-error "Sketch" phase. 
> The mathematics and code herein may contain deprecated Expectation-Maximization loops or failed concepts.
> The final, verified truth is located in the `Soul/` directory.
> Tags: #archived-sketch #pairs-trading-prototype

- First go through all the available context in the directory about pair trading all the files needs to have loaded for all the agents.. make sure all kagglr run time error when running parallel processing is also loaded.. all maximum context .
- Mainly you will get context from the plan folder .md files, and make sure you locally save all those successful run individually kaggle Note books for each plan stage , save those notebook code file into directory locally for quick access..need to download latest version and robust version of those file from the kaggle...
- make sure that entire QC points as well as Soul/QC_Rebuttals_and_Context.md is fully loaded in context and ready for final multi agent work...

Stage 1: 500 ranked pairs CSV with Pearson correlation coefficient. Values . Only one file 

Stage 2: on entire 500 stage 1 ranked pairs, stage 1 rank, Pearson correlation coefficient, Q values, R values, noice to signal ratio (for beta and alpha), kalman ou half life in minutes, adf p value standard, adf p value  with kalman, em convergent (true, false), em total iteration (?!), previous original stage 2 had em not converged for maximum number of pairs, this time make sure that em is converted for almost all pairs 500 list.., hurst component,

Does this much details are sufficient for stage 2 or do we need all the original stage 2 parameters as well????? There were many??? If required please expand the list..

Stage 3A: pure optimization run for all 500 pairs, for maximum profit and max total number of trades.., need to fetch all required parameters from the stage 1 and stage 2 CSV, .. here we will try to find the best possible configuration for each pairs..here we will only use gross or raw price variation profit..no fees or tax consideration..two profit exit criteria seperately, HL based or Z=0 based.., entry trigger will be 2,2.5,3,3.5,4,4.5,........15,  Stop loss can be (Half life time gross/raw negative, or Zsl=  2.5,3,3.5........16....or no stop loss (exit at the market end session), three seperate conditions ..make sure that here we only trade intrday only and only. Here need to find best as well not overfiited values of configs..only one CSV containing all the 500 pairs best config that gives max number of trade while maintaining the maximum profits..

Here when entry is triggered , then when SL is hit, we will wait Z vallue to get inside the entr_trigger_z/2 rannge, only then we start looking for next possible entry trigger so we will freeze the pair to take next trade suddenly after it has already lost..at Z> trigger area. As this will help to stop cascade of structure break stop loss money wipe outs.

Here always only one sided lagger trades only..

Along with best config parameters, make sure to save gross win rate, sessions end exit, half life exits, mean reversion exits, stop loss exists, take profit exits, number of trades, ....... Here win rate is only considering the total gross profit trade / total trade . . Avg points profit avg points loss, meaning if asset price was from 1500.00 to 1530.00, then delta 30. Either positive or negative.?!

Stage 3B:

Based on the stage  3A, CSV file best configuration, with total 500 pairs, need to run a full backtest on non training dataset, from getting all values from the stage 1 to 3A, CSV outputs., total money=10,000 only with lagger pair only with mis x5, so total 50,000 per one sided lagger. Same criteria of running backtest logic as of state 1A....with all combined from stage 1 to 3B parameters achieved with CSV file... One output only..
