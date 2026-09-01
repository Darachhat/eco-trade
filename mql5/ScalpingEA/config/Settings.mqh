//+------------------------------------------------------------------+
//|                                                     Settings.mqh |
//|                                  Copyright 2026, EcoTrade Quant  |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, EcoTrade Quant"
#property link      "https://ecotrade.ai"

//--- Risk Parameters
input group "=== Risk Management ==="
input double   InpRiskPerTradePct       = 0.50;    // Risk % per trade (e.g. 0.50%)
input double   InpMaxDailyLossPct       = 3.00;    // Max daily loss % (e.g. 3.00%)
input double   InpMaxDrawdownPct        = 10.00;   // Max drawdown % (e.g. 10.00%)
input int      InpMaxConsecutiveLosses  = 4;       // Max consecutive losses
input int      InpConsecutiveCooldownM  = 30;      // Cooldown after max losses (minutes)
input int      InpMaxConcurrentPositions= 1;       // Max open positions
input double   InpMinMarginLevelPct     = 200.0;   // Min margin level % required

//--- Dynamic Lot Sizing
input group "=== Position Sizing ==="
input double   InpMinLot                = 0.01;    // Min lot size
input double   InpMaxLot                = 2.00;    // Max lot size

//--- ATR-Based TP & SL
input group "=== ATR Target Configuration ==="
input int      InpATRPeriod             = 14;      // ATR period
input double   InpTP_ATR_Multiplier     = 1.20;    // Take Profit ATR multiplier
input double   InpSL_ATR_Multiplier     = 1.00;    // Stop Loss ATR multiplier

//--- Market Filters
input group "=== Market Filters ==="
input double   InpMaxSpreadPoints       = 35.0;    // Max allowed spread (points)
input double   InpMinTPToSpreadRatio    = 3.50;    // Min TP / Spread ratio
input double   InpMinATRPoints          = 50.0;    // Min ATR points (slow market filter)
input double   InpMaxATRPoints          = 600.0;   // Max ATR points (high volatility filter)
input int      InpSessionStartHour      = 1;       // Session start hour (UTC)
input int      InpSessionEndHour        = 23;      // Session end hour (UTC)
input int      InpCooldownSeconds       = 30;      // Cooldown after trade close (sec)

//--- Active Trade Management
input group "=== Trade Management ==="
input bool     InpBreakEvenEnabled      = true;    // Enable dynamic Break-Even
input double   InpBreakEvenTriggerATR   = 0.60;    // BE trigger (ATR multiplier)
input double   InpBEProfitBufferPts     = 5.0;     // BE buffer in points
input bool     InpTrailingEnabled       = true;    // Enable trailing stop
input double   InpTrailingTriggerATR    = 0.80;    // Trailing trigger (ATR multiplier)
input double   InpTrailingDistATR       = 0.50;    // Trailing distance (ATR multiplier)
input int      InpMaxTradeSeconds       = 300;     // Time-based exit timeout (seconds)
input ulong    InpMagicNumber           = 234000;  // EA Magic Number
