//+------------------------------------------------------------------+
//|                                                   ScalpingEA.mq5 |
//|                                  Copyright 2026, EcoTrade Quant  |
//|                                           https://ecotrade.ai    |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, EcoTrade Quant"
#property link      "https://ecotrade.ai"
#property version   "1.00"
#property description "EcoTrade Institutional High-Frequency Scalping EA with ATR Dynamic Sizing & Risk Controls"

#include <Trade\Trade.mqh>
#include "config\Settings.mqh"
#include "core\PositionSizer.mqh"
#include "core\TradeManager.mqh"

//--- Global Handles & Objects
CTrade            ExtTrade;
CTradeManager     ExtTradeManager;
int               ExtHandleATR;
int               ExtHandleEMA9;
int               ExtHandleEMA21;
int               ExtHandleEMA50;
int               ExtHandleRSI;

datetime          ExtLastTradeCloseTime = 0;
int               ExtConsecutiveLosses  = 0;
double            ExtStartingDailyEquity= 0.0;
double            ExtPeakEquity         = 0.0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   ExtTrade.SetExpertMagicNumber(InpMagicNumber);
   ExtStartingDailyEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   ExtPeakEquity = ExtStartingDailyEquity;

   // Initialize Indicators
   ExtHandleATR   = iATR(_Symbol, PERIOD_M1, InpATRPeriod);
   ExtHandleEMA9  = iMA(_Symbol, PERIOD_M1, 9, 0, MODE_EMA, PRICE_CLOSE);
   ExtHandleEMA21 = iMA(_Symbol, PERIOD_M1, 21, 0, MODE_EMA, PRICE_CLOSE);
   ExtHandleEMA50 = iMA(_Symbol, PERIOD_M1, 50, 0, MODE_EMA, PRICE_CLOSE);
   ExtHandleRSI   = iRSI(_Symbol, PERIOD_M1, 14, PRICE_CLOSE);

   if(ExtHandleATR == INVALID_HANDLE || ExtHandleEMA9 == INVALID_HANDLE)
   {
      Print("Error creating indicator handles");
      return INIT_FAILED;
   }

   Print("EcoTrade Scalping EA Initialized on ", _Symbol);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   IndicatorRelease(ExtHandleATR);
   IndicatorRelease(ExtHandleEMA9);
   IndicatorRelease(ExtHandleEMA21);
   IndicatorRelease(ExtHandleEMA50);
   IndicatorRelease(ExtHandleRSI);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick)) return;

   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int digits   = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   // 1. Read Indicators
   double atr_buf[1], ema9_buf[1], ema21_buf[1], ema50_buf[1], rsi_buf[1];
   if(CopyBuffer(ExtHandleATR, 0, 0, 1, atr_buf) <= 0) return;
   if(CopyBuffer(ExtHandleEMA9, 0, 0, 1, ema9_buf) <= 0) return;
   if(CopyBuffer(ExtHandleEMA21, 0, 0, 1, ema21_buf) <= 0) return;
   if(CopyBuffer(ExtHandleEMA50, 0, 0, 1, ema50_buf) <= 0) return;
   if(CopyBuffer(ExtHandleRSI, 0, 0, 1, rsi_buf) <= 0) return;

   double atr_val = atr_buf[0];
   double atr_points = atr_val / point;
   double spread_points = (tick.ask - tick.bid) / point;

   // 2. Active Trade Management (Trailing & Break-Even & Time Exit)
   ExtTradeManager.ManagePositions(_Symbol, atr_points, tick.bid, tick.ask);

   // 3. Risk & Circuit Breakers Check
   double cur_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   ExtPeakEquity = MathMax(ExtPeakEquity, cur_equity);

   // Max Daily Loss
   double daily_loss_pct = ((ExtStartingDailyEquity - cur_equity) / ExtStartingDailyEquity) * 100.0;
   if(daily_loss_pct >= InpMaxDailyLossPct)
      return; // Lockout for the day

   // Max Drawdown
   double dd_pct = ((ExtPeakEquity - cur_equity) / ExtPeakEquity) * 100.0;
   if(dd_pct >= InpMaxDrawdownPct)
      return; // Lockout

   // Max Positions
   int open_pos = 0;
   for(int i = 0; i < PositionsTotal(); i++)
   {
      if(PositionGetTicket(i) > 0 && PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
         open_pos++;
   }
   if(open_pos >= InpMaxConcurrentPositions)
      return;

   // 4. Market Filters
   // Cooldown
   if(TimeCurrent() - ExtLastTradeCloseTime < InpCooldownSeconds)
      return;

   // Spread & TP/Spread ratio
   if(spread_points > InpMaxSpreadPoints)
      return;

   double est_tp_points = atr_points * InpTP_ATR_Multiplier;
   if((est_tp_points / MathMax(1.0, spread_points)) < InpMinTPToSpreadRatio)
      return;

   // Volatility ATR bounds
   if(atr_points < InpMinATRPoints || atr_points > InpMaxATRPoints)
      return;

   // 5. Signal Evaluation
   bool is_buy  = (ema9_buf[0] > ema21_buf[0]) && (tick.close > ema50_buf[0]) && (rsi_buf[0] >= 52.0 && rsi_buf[0] <= 72.0);
   bool is_sell = (ema9_buf[0] < ema21_buf[0]) && (tick.close < ema50_buf[0]) && (rsi_buf[0] >= 28.0 && rsi_buf[0] <= 48.0);

   if(!is_buy && !is_sell)
      return;

   // 6. Dynamic Sizing & SL/TP
   double sl_points = atr_points * InpSL_ATR_Multiplier;
   double tp_points = atr_points * InpTP_ATR_Multiplier;
   double lot_size  = CPositionSizer::CalculateLot(_Symbol, sl_points);

   // 7. Execution
   if(is_buy)
   {
      double sl = NormalizeDouble(tick.ask - (sl_points * point), digits);
      double tp = NormalizeDouble(tick.ask + (tp_points * point), digits);
      ExtTrade.Buy(lot_size, _Symbol, tick.ask, sl, tp, "EcoTrade Scalper Buy");
   }
   else if(is_sell)
   {
      double sl = NormalizeDouble(tick.bid + (sl_points * point), digits);
      double tp = NormalizeDouble(tick.bid - (tp_points * point), digits);
      ExtTrade.Sell(lot_size, _Symbol, tick.bid, sl, tp, "EcoTrade Scalper Sell");
   }
}
