- Two stage process.

Stage 1 : A 4 week / monthly re-roll engine
- Run only by monthly only.
- It main purpose is to find the top most profitable pairs {Top 50 most profitable pairs ranked from most profit to least..here we will only consider the pair if the physics is validating as per criteria achieved with as below...
  (If we were to trade tomorrow, we would
  simply run the matrix and filter for  ADF <
  0.005 ,  Half-Life < 1,000 ,  Spread Vol >
  0.045 , and  Kalman Q > 3e-06 . Any pair
  that
  passes those 4 bounds is mathematically
  destined to mirror the Top 50 Elite!
  })

 Context :- files...
  (- build_continuous_ols_pipeline_nb.py
  1. The Production Code: The Kaggle
  generation notebook script (                     build_continuous_ols_pipeline_nb.py )
  already contains the final successful
  OpenBLAS/NumPy Thread-Locking injection
  inside  Soul/pairs-trading/Code/ .
  2. The Analysis Script: The pure-Python Walk-
  Forward decile-clustering script has been        saved permanently as
analyze_walkforward_matrix.py .
  3. The Deep Analysis Report: I wrote the         formal conclusions comparing the Elite 50
  parameters against the Bottom 50 into
  walkforward-physics-analysis.md .                4. The Final Matrix Data: I created a
  Results/  folder and moved the massive 124,      750-pair sweep dataset to
continuous_ols_production_results.csv .
  4. The Knowledge Graph: I linked the new
  walkforward-physics-analysis.md  document
  directly into  catalog.jsonl  so it will be
  globally searchable by all future agents.)


Stage 1 will run on weekends with most optimised code structure in kaggle by Months..for following..

Step1: from api here  or most optimal and correct way fetch the NSE 500 list live and current as per that date.. so this automatically updates any year .. and don't need human touch..so it can be any year in 2070 pr in 2030 it never fails.. nse only. 500.

Step 2: connect to api (https://myapi.fyers.in/) 
The code it self will have a hard coded.. authentication no secret as the api is temporary.. and it is no risk api for my use cases not primary trading api it is free and used for exactly only to download historical or live data.. so no security risk with this api.. 

Now once it authenticates.. it then needs to download exactly the 120 latest trading days worth 1 min candle data.. fully..here i need full 120 days worth of trading data..when session was active for those day con 375x120 total candle data points all 1 min time frame only close of 1 min bar with date and time step are required..(date, timestemp, close_price) we can take help of api to only get the details of whether the day was trading or not we only neeed to focus on the active 120 days of the trades .. i don't want any arbitrary implementation to get 120 days like 160 days of data will give 120 active day etc. i strictly need exactly 120 trading day you can here take help of api or other any related calanders like nse bse calendar etc something like it...

From all the nse500 stock filter out the stock that had <70% coverage in 120x375(new ipo etc..etc...) ignore them and add save such a stocks with le_70_coverage_06-13-26.csv (all files will be saved with date ..in last actual live date of code run.. month-day-year..)

Once we have this data we will treat treat this data as continues only for further all analysis..of pair trading...continue only** ignoring all sessions end gaps and all the weekend etc we will only consider continues previous day close 1 min, the. After next day 9:15 open .. but make sure for each individual pair thire exist actual data drop any data points if for a given individual pair the individual stock data might be missing for a minute or something like api based error handling.. skip that data point for that perticular pair..

Etc..

Then the main logic...

Take initiative 20 days as buffer.. data points 20x375.. it will be used to find the lagger stock from a pair..with logic found in the build_continuous_ols_pipeline_nb.py, keep that stock as stock a the lagger one as stock a and other as stock b for further all analysis..

Here we need to be very careful with trading we will only going to trade the larger side only one side only as to save money on fees and to get benefits of lagger - leader relationship..as there is more alpha harvesting can be done with laggger side as compared to more solved leader side.. so only trade stock A of pair with full capital..make sure to correctly implement the trading logic as previously manu ai agent had failed..

Take rolling 20x375 actual datapoints as main thing. (20 trading days..) To reflect all the spread Z score and all other logic...

Now at each new minute close you need to update the ols calculation for beta, alpha as per code .. so basically it updates every minute..our ols engine updates every minute and keeps context of rolling 20x375 data points.. similarly to code ..trade execution and all other are provided as per the code ..Z>= 2 trigger with Z~0 exit or session end exits.. also Z<1 area re entry for further trigger logic keep this in mind as well..

Final files..
NSE-500_06-13-26.csv only 500 list of stocks.
le_70_coverage_06-13-26.csv (generally this will be empty..)
Ranked_Profit_All_06-13-26.csv (all possible pairs ranked from most profit to least.(Stock-A-lagger, Stock-B-leader, all other CSV filed all as per original code .all fileds.. without missing any))

Top_50_Pure_06-13-26.csv (top profit 50 pairs with filtering out pairs with physical metrics did not match as per our deep analysis criteria.....(unreliable pairs ..))

Only 4 CSV will be output nothing else ... 

Now how will this work is that at 4 week interval, at exactly 3:AM ist Gihub will run the notebook.. notebook will run and send the results back to safe place currently this safe place is not difined..but the it will be starting point for stage 2 live execution engine.

Can you add safe place best option as per your understanding it will only beused to write new files delete older files.. read those files for free and easy..

Need to save methodology final .md file  along with final code file into Advanced-Soul/ pair trading/ stage 1 (alredy existing folder)

Only create a final pair-trading_stage-1_methodology.md file that explains full methodology, code logic reasoning code math all in md file it explains everything chunk by chunk and also explain entire pair-trading_stage-1.py code structure and logic behind it ..let it be a in depth blueprint.. of actual code and reasoning..

Please also correctly impliment gihub actions-kagglenotbookrun-safe-place update... 

Gihut action trigger, first is 3 am ist 06-14-26, them every 4 week intervals and on Sunday 3am...



