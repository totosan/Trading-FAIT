"""
Trading-FAIT Technical Indicators Service
Wrapper around pandas-ta for common trading indicators
"""

from dataclasses import dataclass
from typing import Literal

import pandas as pd
import pandas_ta as ta

from ..core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class IndicatorResult:
    """Result from indicator calculation"""
    name: str
    value: float | None
    signal: Literal["bullish", "bearish", "neutral"] | None = None
    description: str | None = None


@dataclass
class TechnicalAnalysis:
    """Complete technical analysis result"""
    symbol: str
    timeframe: str
    trend: Literal["bullish", "bearish", "neutral"] = "neutral"
    trend_strength: Literal["weak", "moderate", "strong"] = "moderate"
    
    # Price levels
    support: float | None = None
    resistance: float | None = None
    current_price: float | None = None
    
    # Indicators
    rsi: IndicatorResult | None = None
    macd: dict | None = None
    moving_averages: dict | None = None
    bollinger: dict | None = None
    atr: IndicatorResult | None = None
    
    # Summary
    summary: str = ""
    recommendation: Literal["strong_buy", "buy", "hold", "sell", "strong_sell"] = "hold"


class IndicatorService:
    """
    Technical indicator calculations using pandas-ta.
    
    Provides common indicators for trading analysis:
    - RSI, MACD, Stochastic
    - Moving Averages (SMA, EMA)
    - Bollinger Bands
    - ATR, ADX
    - Support/Resistance detection
    """
    
    def __init__(self):
        pass
    
    def calculate_rsi(
        self, 
        df: pd.DataFrame, 
        length: int = 14,
        column: str = "Close"
    ) -> IndicatorResult:
        """Calculate RSI indicator"""
        try:
            rsi = ta.rsi(df[column], length=length)
            current_rsi = rsi.iloc[-1] if not rsi.empty else None
            
            # Determine signal
            if current_rsi is None:
                signal = None
                desc = "Keine Daten"
            elif current_rsi > 70:
                signal = "bearish"
                desc = f"Überkauft ({current_rsi:.1f})"
            elif current_rsi < 30:
                signal = "bullish"
                desc = f"Überverkauft ({current_rsi:.1f})"
            else:
                signal = "neutral"
                desc = f"Neutral ({current_rsi:.1f})"
            
            return IndicatorResult(
                name="RSI",
                value=round(current_rsi, 2) if current_rsi else None,
                signal=signal,
                description=desc,
            )
        except Exception as e:
            logger.error(f"RSI calculation error: {e}")
            return IndicatorResult(name="RSI", value=None, description=str(e))
    
    def calculate_macd(
        self,
        df: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        column: str = "Close"
    ) -> dict:
        """Calculate MACD indicator"""
        try:
            macd = ta.macd(df[column], fast=fast, slow=slow, signal=signal)
            
            if macd is None or macd.empty:
                return {"error": "Keine MACD-Daten"}
            
            # Get latest values
            macd_line = macd.iloc[-1, 0]  # MACD line
            signal_line = macd.iloc[-1, 1]  # Signal line
            histogram = macd.iloc[-1, 2]  # Histogram
            
            # Determine signal
            if macd_line > signal_line:
                trend = "bullish"
                desc = "MACD über Signal-Linie"
            else:
                trend = "bearish"
                desc = "MACD unter Signal-Linie"
            
            return {
                "macd": round(macd_line, 4) if pd.notna(macd_line) else None,
                "signal": round(signal_line, 4) if pd.notna(signal_line) else None,
                "histogram": round(histogram, 4) if pd.notna(histogram) else None,
                "trend": trend,
                "description": desc,
            }
        except Exception as e:
            logger.error(f"MACD calculation error: {e}")
            return {"error": str(e)}
    
    def calculate_moving_averages(
        self,
        df: pd.DataFrame,
        periods: list[int] = [20, 50, 200],
        column: str = "Close"
    ) -> dict:
        """Calculate multiple moving averages"""
        try:
            result = {}
            current_price = df[column].iloc[-1]
            
            for period in periods:
                if len(df) >= period:
                    sma = ta.sma(df[column], length=period)
                    ema = ta.ema(df[column], length=period)
                    
                    sma_val = sma.iloc[-1] if not sma.empty else None
                    ema_val = ema.iloc[-1] if not ema.empty else None
                    
                    result[f"SMA_{period}"] = round(sma_val, 2) if pd.notna(sma_val) else None
                    result[f"EMA_{period}"] = round(ema_val, 2) if pd.notna(ema_val) else None
            
            # Trend analysis based on MAs
            if "SMA_20" in result and "SMA_50" in result:
                if result["SMA_20"] and result["SMA_50"]:
                    if result["SMA_20"] > result["SMA_50"]:
                        result["trend"] = "bullish"
                        result["description"] = "Kurzfristiger MA über langfristigem"
                    else:
                        result["trend"] = "bearish"
                        result["description"] = "Kurzfristiger MA unter langfristigem"
            
            result["current_price"] = round(current_price, 2) if pd.notna(current_price) else None
            
            return result
        except Exception as e:
            logger.error(f"Moving averages calculation error: {e}")
            return {"error": str(e)}
    
    def calculate_bollinger_bands(
        self,
        df: pd.DataFrame,
        length: int = 20,
        std: float = 2.0,
        column: str = "Close"
    ) -> dict:
        """Calculate Bollinger Bands"""
        try:
            bb = ta.bbands(df[column], length=length, std=std)
            
            if bb is None or bb.empty:
                return {"error": "Keine Bollinger-Daten"}
            
            current_price = df[column].iloc[-1]
            lower = bb.iloc[-1, 0]  # Lower band
            mid = bb.iloc[-1, 1]    # Middle (SMA)
            upper = bb.iloc[-1, 2]  # Upper band
            
            # Position within bands
            if pd.notna(lower) and pd.notna(upper):
                band_width = upper - lower
                position = (current_price - lower) / band_width if band_width > 0 else 0.5
                
                if position > 0.8:
                    signal = "bearish"
                    desc = "Preis nahe oberem Band (überkauft)"
                elif position < 0.2:
                    signal = "bullish"
                    desc = "Preis nahe unterem Band (überverkauft)"
                else:
                    signal = "neutral"
                    desc = "Preis im mittleren Bereich"
            else:
                signal = "neutral"
                desc = "Keine Positionsbestimmung möglich"
                position = None
            
            return {
                "upper": round(upper, 2) if pd.notna(upper) else None,
                "middle": round(mid, 2) if pd.notna(mid) else None,
                "lower": round(lower, 2) if pd.notna(lower) else None,
                "position": round(position, 2) if position else None,
                "signal": signal,
                "description": desc,
            }
        except Exception as e:
            logger.error(f"Bollinger Bands calculation error: {e}")
            return {"error": str(e)}
    
    def calculate_atr(
        self,
        df: pd.DataFrame,
        length: int = 14,
    ) -> IndicatorResult:
        """Calculate Average True Range (volatility)"""
        try:
            atr = ta.atr(df['High'], df['Low'], df['Close'], length=length)
            current_atr = atr.iloc[-1] if not atr.empty else None
            current_price = df['Close'].iloc[-1]
            
            # ATR as percentage of price
            atr_pct = (current_atr / current_price * 100) if current_atr and current_price else None
            
            if atr_pct:
                if atr_pct > 5:
                    desc = f"Hohe Volatilität ({atr_pct:.1f}%)"
                elif atr_pct > 2:
                    desc = f"Moderate Volatilität ({atr_pct:.1f}%)"
                else:
                    desc = f"Niedrige Volatilität ({atr_pct:.1f}%)"
            else:
                desc = "Keine ATR-Daten"
            
            return IndicatorResult(
                name="ATR",
                value=round(current_atr, 2) if current_atr else None,
                signal="neutral",
                description=desc,
            )
        except Exception as e:
            logger.error(f"ATR calculation error: {e}")
            return IndicatorResult(name="ATR", value=None, description=str(e))
    
    def find_support_resistance(
        self,
        df: pd.DataFrame,
        window: int = 10,
    ) -> dict:
        """Find basic support and resistance levels"""
        try:
            highs = df['High'].rolling(window=window, center=True).max()
            lows = df['Low'].rolling(window=window, center=True).min()
            
            # Recent support: lowest low in last N candles
            support = df['Low'].tail(window).min()
            
            # Recent resistance: highest high in last N candles
            resistance = df['High'].tail(window).max()
            
            current = df['Close'].iloc[-1]
            
            return {
                "support": round(support, 2) if pd.notna(support) else None,
                "resistance": round(resistance, 2) if pd.notna(resistance) else None,
                "current": round(current, 2) if pd.notna(current) else None,
                "distance_to_support": round(((current - support) / current) * 100, 2) if support else None,
                "distance_to_resistance": round(((resistance - current) / current) * 100, 2) if resistance else None,
            }
        except Exception as e:
            logger.error(f"Support/Resistance calculation error: {e}")
            return {"error": str(e)}
    
    def full_analysis(
        self,
        df: pd.DataFrame,
        symbol: str = "UNKNOWN",
        timeframe: str = "1D",
    ) -> TechnicalAnalysis:
        """Perform complete technical analysis"""
        
        if df is None or df.empty:
            return TechnicalAnalysis(
                symbol=symbol,
                timeframe=timeframe,
                summary="Keine Daten für Analyse verfügbar",
            )
        
        # Calculate all indicators
        rsi = self.calculate_rsi(df)
        macd = self.calculate_macd(df)
        mas = self.calculate_moving_averages(df)
        bb = self.calculate_bollinger_bands(df)
        atr = self.calculate_atr(df)
        levels = self.find_support_resistance(df)
        
        # Determine overall trend
        bullish_signals = 0
        bearish_signals = 0
        
        if rsi.signal == "bullish":
            bullish_signals += 1
        elif rsi.signal == "bearish":
            bearish_signals += 1
        
        if macd.get("trend") == "bullish":
            bullish_signals += 1
        elif macd.get("trend") == "bearish":
            bearish_signals += 1
        
        if mas.get("trend") == "bullish":
            bullish_signals += 1
        elif mas.get("trend") == "bearish":
            bearish_signals += 1
        
        if bb.get("signal") == "bullish":
            bullish_signals += 1
        elif bb.get("signal") == "bearish":
            bearish_signals += 1
        
        # Overall trend and recommendation
        if bullish_signals >= 3:
            trend = "bullish"
            strength = "strong" if bullish_signals == 4 else "moderate"
            recommendation = "strong_buy" if bullish_signals == 4 else "buy"
        elif bearish_signals >= 3:
            trend = "bearish"
            strength = "strong" if bearish_signals == 4 else "moderate"
            recommendation = "strong_sell" if bearish_signals == 4 else "sell"
        else:
            trend = "neutral"
            strength = "weak"
            recommendation = "hold"
        
        # Build summary
        summary_parts = []
        summary_parts.append(f"Trend: {trend.upper()} ({strength})")
        if rsi.value:
            summary_parts.append(f"RSI: {rsi.value}")
        if macd.get("histogram"):
            summary_parts.append(f"MACD Histogramm: {macd['histogram']}")
        if levels.get("support") and levels.get("resistance"):
            summary_parts.append(f"Support: {levels['support']}, Resistance: {levels['resistance']}")
        
        return TechnicalAnalysis(
            symbol=symbol,
            timeframe=timeframe,
            trend=trend,
            trend_strength=strength,
            support=levels.get("support"),
            resistance=levels.get("resistance"),
            current_price=mas.get("current_price"),
            rsi=rsi,
            macd=macd,
            moving_averages=mas,
            bollinger=bb,
            atr=atr,
            summary=" | ".join(summary_parts),
            recommendation=recommendation,
        )


# Global service instance
_indicator_service: IndicatorService | None = None


def get_indicator_service() -> IndicatorService:
    """Get or create indicator service"""
    global _indicator_service
    if _indicator_service is None:
        _indicator_service = IndicatorService()
    return _indicator_service
