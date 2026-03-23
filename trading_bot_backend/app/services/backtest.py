from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Any

from trading_bot_backend.app.models import StrategyNameEnum, TradeSideEnum
from trading_bot_backend.app.services.strategy import analyze_strategy, Candle

@dataclass
class BacktestTrade:
    side: TradeSideEnum
    entry_price: float
    stop_loss: float
    take_profit: float
    quantity: float
    opened_at: int
    is_be_reached: bool = False
    last_swing_sl: float | None = None
    status: str = "OPEN"
    pnl: float | None = None
    closed_at: int | None = None

@dataclass
class BacktestResult:
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    total_profit: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    equity_curve: list[float] = field(default_factory=lambda: [100.0]) # Starting with 100%

class BacktestEngine:
    def __init__(self, strategy_name: StrategyNameEnum, initial_balance: float = 10000.0, risk_pct: float = 0.01):
        self.strategy_name = strategy_name
        self.balance = initial_balance
        self.risk_pct = risk_pct
        self.active_trade: BacktestTrade | None = None
        self.closed_trades: list[BacktestTrade] = []
        self.equity = [initial_balance]

    def run(self, htf_candles: list[dict], ltf_candles: list[dict]) -> BacktestResult:
        """
        Runs backtest. For simplicity in this implementation, we assume LTF candles 
        are the main timeline and we provide the HTF context available at that time.
        In a real production backtester, we would align timestamps precisely.
        """
        # 1. Align candles (basic version: iterate through LTF candles)
        # We need enough candles for analysis
        min_candles = 100 
        
        for i in range(min_candles, len(ltf_candles)):
            current_ltf = ltf_candles[:i+1]
            current_time = current_ltf[-1]["time"]
            
            # Find HTF candles available at this time
            current_htf = [c for c in htf_candles if c["time"] <= current_time]
            # For backtest, we'll assume Futures HTF is similar to Spot HTF for now 
            # or skip divergence check in backtest if not provided.
            
            if len(current_htf) < 20: # Need some HTF context
                continue

            # 2. Manage Active Trade
            if self.active_trade:
                self._manage_trade(self.active_trade, current_ltf[-1])
                if self.active_trade.status != "OPEN":
                    self.closed_trades.append(self.active_trade)
                    self.balance += self.active_trade.pnl or 0
                    self.equity.append(self.balance)
                    self.active_trade = None
                continue

            # 3. Scan for Signal
            analysis = analyze_strategy(
                strategy_name=self.strategy_name,
                htf_candles=current_htf[-100:], # Last 100 HTF
                ltf_candles=current_ltf[-200:], # Last 200 LTF
                futures_htf_candles=current_htf[-100:] # Simplified for BT
            )
            
            signal = analysis.get("signal", {})
            if signal.get("status") == "READY" and signal.get("trade_plan"):
                plan = signal["trade_plan"]
                self._open_trade(plan, current_time)

        return self._calculate_stats()

    def _open_trade(self, plan: dict, timestamp: int):
        entry_price = plan["entry_price"]
        stop_loss = plan["stop_loss"]
        take_profit = plan["take_profit"]
        side = TradeSideEnum(plan["side"])
        
        risk_amount = self.balance * self.risk_pct
        price_risk = abs(entry_price - stop_loss)
        
        if price_risk <= 0:
            return

        quantity = risk_amount / price_risk
        
        self.active_trade = BacktestTrade(
            side=side,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            quantity=quantity,
            opened_at=timestamp
        )

    def _manage_trade(self, trade: BacktestTrade, current_candle: dict):
        price = current_candle["close"]
        high = current_candle["high"]
        low = current_candle["low"]
        
        # Check Exit Conditions
        if trade.side == TradeSideEnum.BUY:
            # SL hit?
            if low <= trade.stop_loss:
                trade.status = "CLOSED"
                trade.pnl = (trade.stop_loss - trade.entry_price) * trade.quantity
                trade.closed_at = current_candle["time"]
                return
            # TP hit?
            if high >= trade.take_profit:
                trade.status = "CLOSED"
                trade.pnl = (trade.take_profit - trade.entry_price) * trade.quantity
                trade.closed_at = current_candle["time"]
                return
            
            # Management: Break-even at 1R
            # In real SMC, it's 1R. For BT, we use the initial risk.
            initial_risk = abs(trade.entry_price - trade.stop_loss)
            
            if not trade.is_be_reached and price >= trade.entry_price + initial_risk:
                 trade.stop_loss = trade.entry_price
                 trade.is_be_reached = True

        elif trade.side == TradeSideEnum.SELL:
            if high >= trade.stop_loss:
                trade.status = "CLOSED"
                trade.pnl = (trade.entry_price - trade.stop_loss) * trade.quantity
                trade.closed_at = current_candle["time"]
                return
            if low <= trade.take_profit:
                trade.status = "CLOSED"
                trade.pnl = (trade.entry_price - trade.take_profit) * trade.quantity
                trade.closed_at = current_candle["time"]
                return

    def _calculate_stats(self) -> BacktestResult:
        res = BacktestResult()
        res.total_trades = len(self.closed_trades)
        if res.total_trades == 0:
            return res
            
        wins = [t for t in self.closed_trades if (t.pnl or 0) > 0]
        losses = [t for t in self.closed_trades if (t.pnl or 0) <= 0]
        
        res.wins = len(wins)
        res.losses = len(losses)
        res.win_rate = (res.wins / res.total_trades) * 100
        res.total_profit = sum(t.pnl or 0 for t in self.closed_trades)
        
        gross_profit = sum(t.pnl or 0 for t in wins)
        gross_loss = abs(sum(t.pnl or 0 for t in losses))
        res.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Drawdown
        max_balance = 0
        max_dd = 0
        curr_balance = self.equity[0]
        for b in self.equity:
            if b > max_balance:
                max_balance = b
            dd = (max_balance - b) / max_balance
            if dd > max_dd:
                max_dd = dd
        res.max_drawdown = max_dd * 100
        
        return res
