//+------------------------------------------------------------------+
//|                                                PositionSizer.mqh |
//|                                  Copyright 2026, EcoTrade Quant  |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, EcoTrade Quant"
#include "..\config\Settings.mqh"

class CPositionSizer
{
public:
   static double CalculateLot(string symbol, double sl_points)
   {
      double equity = AccountInfoDouble(ACCOUNT_EQUITY);
      double risk_money = equity * (InpRiskPerTradePct / 100.0);
      
      double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
      double contract_size = SymbolInfoDouble(symbol, SYMBOL_TRADE_CONTRACT_SIZE);
      double money_per_point = contract_size * point;
      
      if(sl_points <= 0 || money_per_point <= 0)
         return InpMinLot;
         
      double raw_lot = risk_money / (sl_points * money_per_point);
      
      double lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
      double vol_min  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
      double vol_max  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
      
      if(lot_step > 0)
         raw_lot = MathFloor(raw_lot / lot_step) * lot_step;
         
      double final_lot = MathMax(vol_min, MathMin(vol_max, raw_lot));
      final_lot = MathMax(InpMinLot, MathMin(InpMaxLot, final_lot));
      
      return NormalizeDouble(final_lot, 2);
   }
};
