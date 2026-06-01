---
Title: "Higher Level Data Extraction for Trading"
Author: "User"
Reference: "Higher Level Data Extraction for Trading.md"
ContentType:
  - "markdown"
Created: 2026-05-30
Processed: true
tags:
  - "source"
---


2. Bank Nifty Futures (Current Month Expiry).

With help of available Fyers based api.

I need to collect very high level data for above assets,.

Code should automatically start.. 5 min early as to very as compared to starting windows of trading.. and ending at exactly trading window ends 

Handles Hollidays or no trading days etc..

I need a system that runs automatically everyday see if this is no trading day or not, if is no trading day then ends , if it is trading day it starts authentication 5 Mins early, fetches tick by tick data automatically till session end. It should also automatically handle current month expiry future symbol and update accordingly the ticket.. as to fetch always the current month expiry futures data..all the data max data that api provides everything..

It should store this data as one file only that gets updated automatically each day only one file very effective file format easy to handle data without any data loss or corruption of data. I will later going to use this tich by tich high level data for alpha exploitation.

This automatically downloaded and fetching data should happen on cloud without running anything on local.. automatically saves files on cloud only.