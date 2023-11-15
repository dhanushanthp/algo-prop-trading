//+------------------------------------------------------------------+
//|                                                  pivotPoints.mq5 |
//|                                  Copyright 2023, MetaQuotes Ltd. |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2023, MetaQuotes Ltd."
#property link      "https://www.mql5.com"
#property version   "1.00"
//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
//---
   
//---
   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
//---
   
  }
//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
  {
//---
   double high1 = iHigh(_Symbol,PERIOD_D1,1);
   double low1 = iLow(_Symbol, PERIOD_D1,1);
   double close1 = iClose(_Symbol,PERIOD_D1,1);
   
   double high0 = iHigh(_Symbol,PERIOD_D1,0);
   double low0 = iLow(_Symbol, PERIOD_D1,0);
   
   double whigh1 = iHigh(_Symbol,PERIOD_W1,1);
   double wlow1 = iLow(_Symbol, PERIOD_W1,1);
   
   double whigh0 = iHigh(_Symbol,PERIOD_W1,0);
   double wlow0 = iLow(_Symbol, PERIOD_W1,0);
   
   datetime time1 = iTime(_Symbol,PERIOD_D1,0) ;
   datetime time2 = time1 + PeriodSeconds (PERIOD_D1);
   
   double pivotPoint = (high1 + low1 + close1) / 3;
   
   string objName = "Pivot Point";
   createLine(objName, clrPink, time1, pivotPoint, time2, pivotPoint);
   
   double r1 = pivotPoint * 2 - low1;
   objName = "R1";
   createLine(objName, clrCoral, time1, r1, time2, r1);
   
   double r2 = pivotPoint + high1 - low1;
   objName = "R2";
   createLine(objName, clrCoral, time1, r2, time2, r2);
   
   double r3 = high1 + 2*(pivotPoint - low1);
   objName = "R3";
   createLine(objName, clrPink, time1, r3, time2, r3);
   
   double s1 = pivotPoint * 2 - high1;
   objName = "S1";
   createLine(objName, clrGreen, time1, s1, time2, s1);
   
   double s2 = pivotPoint - high1 - low1;
   objName = "S2";
   createLine(objName, clrGreen, time1, s2, time2, s2);
   
   double s3 = low1 - 2 * (high1 - pivotPoint);
   objName = "S3";
   createLine(objName, clrGreen, time1, s3, time2, s3);
   
   // High of the day
   objName = "HOD";
   createLine(objName, clrRed, time1, high0, time2, high0, 3);
   
   // Low of the day
   objName = "LOD";
   createLine(objName, clrGreen, time1, low0, time2, low0, 3);
   
   
   // Previous Day High
   objName = "PDH";
   createLine(objName, clrRed, time1, high1, time2, high1, 3);
   
   // Previous Day Low
   objName = "PDL";
   createLine(objName, clrGreen, time1, low1, time2, low1, 3);
   
   // Previous Day Close
   objName = "PDC";
   createLine(objName, clrBrown, time1, close1, time2, close1, 3);
   
   
   // Previous Week High
   objName = "PWH";
   createLine(objName, clrRed, time1, whigh1, time2, whigh1, 3);
   
   // Previous WEEK Low
   objName = "PWL";
   createLine(objName, clrGreen, time1, wlow1, time2, wlow1, 3);
   
   // Current Week High
   objName = "HOW";
   createLine(objName, clrRed, time1, whigh0, time2, whigh0, 3);
   
   // Current Week Low
   objName = "LOW";
   createLine(objName, clrGreen, time1, wlow0, time2, wlow0, 3);
   
  }
  
  
 void createLine(string objName, color clr, datetime time1, double price1, datetime time2, double price2, double width=2){
   ObjectDelete(0,objName);
   ObjectCreate(0, objName, OBJ_TREND,0,time1, price1, time2,price2);
   ObjectSetInteger (0,objName,OBJPROP_COLOR,clr);
   ObjectSetInteger (0,objName,OBJPROP_WIDTH,width);
 }
//+------------------------------------------------------------------+
