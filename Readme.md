# Background
The first commit for the Meta Query Project was made on November 6, 2023. This project aimed to trade proprietary trading accounts using MetaTrader, leveraging the MetaTrader API for transactions. This includes risk management, dynamic risk allocation, entry and exit plan and also data collection to analyse the PNL and risk reward ratios including Power BI dashboard.

Throughout the journey, I experimented with various strategies, but ultimately realized the unpredictable nature of the stock market. Regardless of the approach, finding an edge proved to be extremely difficult. One key lesson I learned is to avoid relying on a single stock or symbol. Instead, trading with a diversified selection of stocks or symbols can help manage risk—if one moves in an unfavorable direction, others may balance out the loss.

However, this strategy also fell short. Even when the entire position briefly showed profit, fluctuations between positive and negative were inevitable, reflecting the volatile dynamics of the market. Furthermore, trading trade proprietary specifically presented additional challenges due to the substantial spread, which made trading conditions far from ideal.

Given these insights, I’ve decided to archive this project and accept the reality that trading in the forex market is not viable for me. For anyone interested in pursuing this, the simplest way would be to use the MetaTrader main.py, which includes predefined strategies accessible via a bot script

# Learnings
I recommend automating trading instead of doing it manually. While it's possible for individuals to trade manually, emotions can negatively impact their decisions. For instance, a trader might gain confidence from a series of winning trades, not realizing that the market was simply favorable at that time. This confidence can lead to increased risk due to greed. If the market then reverses, the trader may not adapt, resulting in significant losses. Over time, this cycle can erode their confidence.

Emotions like greed and fear greatly influence this process. The best way to eliminate these emotions is by using a trading bot that makes decisions based on set rules, such as:

1. When to make a trade
2. Which symbol to trade
3. The risk level for each trade
4. Entry and exit plans

In trading, there's no single right or wrong approach. If a method works for you and brings in profit, that's what matters.

From my experience, I’ve learned that the market doesn’t always move in one direction. Some trading experts suggest holding your position until the market closes if you’re day trading. It’s also important to focus on tight stops with very high profit targets. I’ve been trading with a 1-hour timeframe, but the problem is that the stop is large, and hence the target must be large as well. This makes it challenging to achieve a high risk-to-reward ratio because entry opportunities are always a 50-50 chance. The only way to be profitable in the market is to have a very high risk-to-reward ratio to beat the odds of 50/50. Therefore, it’s best to focus on shorter timeframes, such as 15 minutes, because 5 minutes is very noisy. Trading based on reversal points is advisable since the market occasionally trends but mostly reverses, even on trend days.

# Mindset of trading
| **Win Rate (%)** | **Risk-Reward Ratio 1:1** | **Risk-Reward Ratio 1:2** | **Risk-Reward Ratio 1:3** | **Risk-Reward Ratio 1:4** | **Risk-Reward Ratio 1:5** |
|------------------|---------------------------|---------------------------|---------------------------|---------------------------|---------------------------|
| 90%              | 0.8                        | 1.7                        | 2.6                        | 3.5                        | 4.4                        |
| 80%              | 0.6                        | 1.4                        | 2.2                        | 3.0                        | 3.8                        |
| 70%              | 0.4                        | 1.1                        | 1.8                        | 2.5                        | 3.2                        |
| 60%              | 0.2                        | 0.8                        | 1.4                        | 2.0                        | 2.6                        |
| 55%              | 0.1                        | 0.65                       | 1.2                        | 1.75                       | 2.3                        |
| 50%              | 0.0                        | 0.5                        | 1.0                        | 1.5                        | 2.0                        |
| 45%              | -0.1                       | 0.35                       | 0.8                        | 1.25                       | 1.7                        |
| 40%              | -0.2                       | 0.2                        | 0.6                        | 1.0                        | 1.4                        |
| 35%              | -0.3                       | 0.05                       | 0.4                        | 0.75                       | 1.1                        |
| 30%              | -0.4                       | -0.1                       | 0.2                        | 0.5                        | 0.8                        |
| 25%              | -0.5                       | -0.25                      | 0.0                        | 0.25                       | 0.5                        |


# Configuration