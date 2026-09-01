//+------------------------------------------------------------------+
//|                                                 TradeManager.mqh |
//|                                  Copyright 2026, EcoTrade Quant  |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, EcoTrade Quant"
#include <Trade\Trade.mqh>
#include "..\config\Settings.mqh"

class CTradeManager
{
private:
   CTrade         m_trade;

public:
   CTradeManager()
   {
      m_trade.SetExpertMagicNumber(InpMagicNumber);
   }

   void ManagePositions(string symbol, double atr_points, double current_bid, double current_ask)
   {
      double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
      int digits   = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
      datetime now = TimeCurrent();

      for(int i = PositionsTotal() - 1; i >= 0; i--)
      {
         ulong ticket = PositionGetTicket(i);
         if(ticket <= 0) continue;
         if(PositionGetString(POSITION_SYMBOL) != symbol) continue;
         if(PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;

         ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
         double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
         double cur_sl     = PositionGetDouble(POSITION_SL);
         double cur_tp     = PositionGetDouble(POSITION_TP);
         datetime open_time= (datetime)PositionGetInteger(POSITION_TIME);

         int duration_sec = (int)(now - open_time);

         // 1. Time-based Exit
         if(duration_sec >= InpMaxTradeSeconds)
         {
            PrintFormat("Time-based exit triggered for ticket %d after %d sec", ticket, duration_sec);
            m_trade.PositionClose(ticket);
            continue;
         }

         bool is_buy = (type == POSITION_TYPE_BUY);
         double cur_price = is_buy ? current_bid : current_ask;
         double profit_points = is_buy ? (cur_price - open_price) / point : (open_price - cur_price) / point;

         // 2. Dynamic Break-Even
         if(InpBreakEvenEnabled)
         {
            double be_trigger_pts = atr_points * InpBreakEvenTriggerATR;
            if(profit_points >= be_trigger_pts)
            {
               double be_price = is_buy ? open_price + (InpBEProfitBufferPts * point) : open_price - (InpBEProfitBufferPts * point);
               bool needs_be = (is_buy && cur_sl < be_price) || (!is_buy && (cur_sl > be_price || cur_sl == 0));
               if(needs_be)
               {
                  m_trade.PositionModify(ticket, NormalizeDouble(be_price, digits), cur_tp);
                  PrintFormat("Break-Even locked for ticket %d at %f", ticket, be_price);
               }
            }
         }

         // 3. Dynamic ATR Trailing Stop
         if(InpTrailingEnabled)
         {
            double trail_trigger_pts = atr_points * InpTrailingTriggerATR;
            if(profit_points >= trail_trigger_pts)
            {
               double trail_dist = atr_points * InpTrailingDistATR * point;
               double new_sl = is_buy ? cur_price - trail_dist : cur_price + trail_dist;
               bool needs_trail = (is_buy && new_sl > cur_sl) || (!is_buy && (new_sl < cur_sl || cur_sl == 0));
               if(needs_trail)
               {
                  m_trade.PositionModify(ticket, NormalizeDouble(new_sl, digits), cur_tp);
               }
            }
         }
      }
   }
};
