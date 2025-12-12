"""
Trading-FAIT Market Data Service
Unified interface for stocks (yfinance) and crypto (ccxt)
"""

import asyncio
from datetime import datetime, timedelta
from typing import Literal
from dataclasses import dataclass, field

import pandas as pd
import yfinance as yf

from ..core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MarketDataResult:
    """Result from market data query"""
    symbol: str
    asset_type: Literal["stock", "crypto"]
    data: pd.DataFrame | None = None
    current_price: float | None = None
    change_24h: float | None = None
    change_24h_pct: float | None = None
    volume_24h: float | None = None
    high_24h: float | None = None
    low_24h: float | None = None
    market_cap: float | None = None
    error: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def is_valid(self) -> bool:
        return self.error is None and self.data is not None


class MarketDataService:
    """
    Unified market data service supporting both stocks and crypto.
    
    Symbol formats:
    - Stocks: AAPL, MSFT, GOOGL (standard ticker)
    - Crypto: BTC/USDT, ETH/USD (pair format with /)
    """
    
    # Common crypto pairs for detection
    CRYPTO_BASES = {"BTC", "ETH", "XRP", "SOL", "ADA", "DOGE", "DOT", "AVAX", "MATIC", "LINK"}
    CRYPTO_QUOTES = {"USDT", "USD", "USDC", "EUR", "BTC", "ETH"}
    
    def __init__(self):
        self._ccxt_exchange = None
        self._cache: dict[str, MarketDataResult] = {}
        self._cache_ttl = timedelta(minutes=1)
    
    def _is_crypto(self, symbol: str) -> bool:
        """Detect if symbol is crypto based on format"""
        # Contains / -> definitely crypto pair
        if "/" in symbol:
            return True
        
        # Check if it's a known crypto base
        symbol_upper = symbol.upper()
        if symbol_upper in self.CRYPTO_BASES:
            return True
        
        # Check common crypto suffixes
        for quote in self.CRYPTO_QUOTES:
            if symbol_upper.endswith(quote) and len(symbol_upper) > len(quote):
                base = symbol_upper[:-len(quote)]
                if base in self.CRYPTO_BASES:
                    return True
        
        return False
    
    def _normalize_symbol(self, symbol: str) -> tuple[str, Literal["stock", "crypto"]]:
        """Normalize symbol and detect asset type"""
        symbol = symbol.upper().strip()
        
        if self._is_crypto(symbol):
            # Ensure crypto format is BASE/QUOTE
            if "/" not in symbol:
                # Try to split known patterns
                for quote in self.CRYPTO_QUOTES:
                    if symbol.endswith(quote):
                        base = symbol[:-len(quote)]
                        return f"{base}/{quote}", "crypto"
                # Default to USDT
                return f"{symbol}/USDT", "crypto"
            return symbol, "crypto"
        
        return symbol, "stock"
    
    async def _get_ccxt_exchange(self):
        """Lazy load ccxt exchange"""
        if self._ccxt_exchange is None:
            try:
                import ccxt.async_support as ccxt
                self._ccxt_exchange = ccxt.binance({
                    'enableRateLimit': True,
                })
                logger.info("Initialized Binance exchange via ccxt")
            except ImportError:
                logger.warning("ccxt not installed, crypto data unavailable")
                raise ImportError("ccxt is required for crypto data")
        return self._ccxt_exchange
    
    async def get_stock_data(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> MarketDataResult:
        """Fetch stock data via yfinance"""
        try:
            logger.info(f"Fetching stock data for {symbol}")
            
            # Run yfinance in thread pool (it's blocking)
            loop = asyncio.get_event_loop()
            ticker = await loop.run_in_executor(None, yf.Ticker, symbol)
            
            # Get historical data
            hist = await loop.run_in_executor(
                None, 
                lambda: ticker.history(period=period, interval=interval)
            )
            
            if hist.empty:
                return MarketDataResult(
                    symbol=symbol,
                    asset_type="stock",
                    error=f"No data found for {symbol}",
                )
            
            # Get current info
            info = await loop.run_in_executor(None, lambda: ticker.info)
            
            # Calculate 24h change
            if len(hist) >= 2:
                current = hist['Close'].iloc[-1]
                previous = hist['Close'].iloc[-2]
                change = current - previous
                change_pct = (change / previous) * 100
            else:
                current = hist['Close'].iloc[-1] if len(hist) > 0 else None
                change = None
                change_pct = None
            
            return MarketDataResult(
                symbol=symbol,
                asset_type="stock",
                data=hist,
                current_price=current,
                change_24h=change,
                change_24h_pct=change_pct,
                volume_24h=hist['Volume'].iloc[-1] if 'Volume' in hist.columns else None,
                high_24h=hist['High'].iloc[-1] if 'High' in hist.columns else None,
                low_24h=hist['Low'].iloc[-1] if 'Low' in hist.columns else None,
                market_cap=info.get('marketCap'),
            )
            
        except Exception as e:
            logger.error(f"Error fetching stock data for {symbol}: {e}")
            return MarketDataResult(
                symbol=symbol,
                asset_type="stock",
                error=str(e),
            )
    
    async def get_crypto_data(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 30,
    ) -> MarketDataResult:
        """Fetch crypto data via ccxt (Binance)"""
        try:
            logger.info(f"Fetching crypto data for {symbol}")
            
            exchange = await self._get_ccxt_exchange()
            
            # Fetch OHLCV data
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if not ohlcv:
                return MarketDataResult(
                    symbol=symbol,
                    asset_type="crypto",
                    error=f"No data found for {symbol}",
                )
            
            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Get current ticker for 24h stats
            ticker = await exchange.fetch_ticker(symbol)
            
            return MarketDataResult(
                symbol=symbol,
                asset_type="crypto",
                data=df,
                current_price=ticker.get('last'),
                change_24h=ticker.get('change'),
                change_24h_pct=ticker.get('percentage'),
                volume_24h=ticker.get('quoteVolume'),
                high_24h=ticker.get('high'),
                low_24h=ticker.get('low'),
            )
            
        except Exception as e:
            logger.error(f"Error fetching crypto data for {symbol}: {e}")
            return MarketDataResult(
                symbol=symbol,
                asset_type="crypto",
                error=str(e),
            )
    
    async def get_market_data(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> MarketDataResult:
        """
        Unified interface - automatically detects asset type.
        
        Args:
            symbol: Stock ticker (AAPL) or crypto pair (BTC/USDT)
            period: Time period for historical data
            interval: Data interval (1d, 1h, etc.)
        """
        normalized_symbol, asset_type = self._normalize_symbol(symbol)
        
        # Check cache
        cache_key = f"{normalized_symbol}:{period}:{interval}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if datetime.utcnow() - cached.timestamp < self._cache_ttl:
                logger.debug(f"Cache hit for {cache_key}")
                return cached
        
        # Fetch data based on type
        if asset_type == "crypto":
            result = await self.get_crypto_data(
                normalized_symbol,
                timeframe=interval,
                limit=30 if period == "1mo" else 7,
            )
        else:
            result = await self.get_stock_data(
                normalized_symbol,
                period=period,
                interval=interval,
            )
        
        # Update cache
        self._cache[cache_key] = result
        
        return result
    
    async def get_quick_quote(self, symbol: str) -> dict:
        """Get a quick price quote for display"""
        result = await self.get_market_data(symbol, period="5d", interval="1d")
        
        if result.error:
            return {
                "symbol": symbol,
                "error": result.error,
            }
        
        # Convert numpy types to native Python for JSON serialization
        def to_native(val):
            if val is None:
                return None
            try:
                return float(val)
            except (TypeError, ValueError):
                return val
        
        return {
            "symbol": result.symbol,
            "asset_type": result.asset_type,
            "price": to_native(result.current_price),
            "change_24h": to_native(result.change_24h),
            "change_24h_pct": to_native(result.change_24h_pct),
            "high_24h": to_native(result.high_24h),
            "low_24h": to_native(result.low_24h),
            "volume_24h": to_native(result.volume_24h),
        }
    
    async def close(self):
        """Close connections"""
        if self._ccxt_exchange:
            await self._ccxt_exchange.close()
            self._ccxt_exchange = None


# Global service instance
_market_data_service: MarketDataService | None = None


def get_market_data_service() -> MarketDataService:
    """Get or create market data service"""
    global _market_data_service
    if _market_data_service is None:
        _market_data_service = MarketDataService()
    return _market_data_service
