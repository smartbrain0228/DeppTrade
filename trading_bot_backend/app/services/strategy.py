from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from trading_bot_backend.app.models import StrategyNameEnum, TradeSideEnum
from trading_bot_backend.app.services.ta_utils import Candle, Pivot, find_pivots

BiasLiteral = Literal["bullish", "bearish", "neutral"]
SignalStatusLiteral = Literal["NO_BIAS", "WAITING_SWEEP", "WAITING_MSS", "WAITING_FVG", "READY"]


@dataclass(frozen=True)
class SweepEvent:
    direction: Literal["bullish", "bearish"]
    swept_pivot_index: int
    swept_price: float
    candle_index: int
    candle_time: int
    extreme_price: float
    close_price: float


@dataclass(frozen=True)
class MssEvent:
    direction: Literal["bullish", "bearish"]
    pivot_index: int
    pivot_price: float
    candle_index: int
    candle_time: int
    close_price: float


@dataclass(frozen=True)
class FvgEvent:
    direction: Literal["bullish", "bearish"]
    start_index: int
    middle_index: int
    end_index: int
    lower_price: float
    upper_price: float
    midpoint: float
    candle_time: int


@dataclass(frozen=True)
class TradePlan:
    side: TradeSideEnum
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_per_unit: float
    reward_per_unit: float
    reward_risk_ratio: float


@dataclass(frozen=True)
class StrategySpec:
    name: StrategyNameEnum
    htf: str
    ltf: str
    pivot_window: int = 2
    min_reward_risk: float = 1.5
    htf_limit: int = 120
    ltf_limit: int = 240


STRATEGY_SPECS = {
    StrategyNameEnum.INTRADAY: StrategySpec(
        name=StrategyNameEnum.INTRADAY,
        htf="H4",
        ltf="M15",
        pivot_window=2,
        min_reward_risk=1.5,
        htf_limit=120,
        ltf_limit=240,
    ),
    StrategyNameEnum.SCALP: StrategySpec(
        name=StrategyNameEnum.SCALP,
        htf="H1",
        ltf="M5",
        pivot_window=2,
        min_reward_risk=1.5,
        htf_limit=120,
        ltf_limit=240,
    ),
    StrategyNameEnum.SMA_CROSS: StrategySpec(
        name=StrategyNameEnum.SMA_CROSS,
        htf="D1",
        ltf="H1",
        htf_limit=100,
        ltf_limit=200,
    ),
    StrategyNameEnum.SMC_H4_M15: StrategySpec(
        name=StrategyNameEnum.SMC_H4_M15,
        htf="H4",
        ltf="M15",
        pivot_window=2,
        min_reward_risk=2.0,
        htf_limit=120,
        ltf_limit=240,
    ),
    StrategyNameEnum.SMC_H1_M5: StrategySpec(
        name=StrategyNameEnum.SMC_H1_M5,
        htf="H1",
        ltf="M5",
        pivot_window=2,
        min_reward_risk=2.0,
        htf_limit=120,
        ltf_limit=240,
    ),
}


def get_strategy_spec(strategy_name: StrategyNameEnum) -> StrategySpec:
    return STRATEGY_SPECS[strategy_name]


def _calculate_volatility(candles: list[Candle], period: int = 14) -> float:
    """Calculates relative volatility based on average range."""
    if len(candles) < period:
        return 1.0
    ranges = [c.high - c.low for c in candles[-period:]]
    avg_range = sum(ranges) / period
    current_range = candles[-1].high - candles[-1].low
    if avg_range == 0:
        return 1.0
    return current_range / avg_range


def _get_dynamic_sl_multiplier(volatility: float) -> float:
    """
    Case 1: Calm Market (low volatility < 1.0) -> wider SL (multiplier > 1.0)
    Case 2: Fast Market (high volatility > 1.0) -> tighter SL (multiplier < 1.0)
    """
    if volatility < 0.8:
        return 1.5 # Wider
    if volatility > 1.2:
        return 0.8 # Tighter
    return 1.0


def _calculate_range_info(candles: list[Candle]) -> dict:
    if not candles:
        return {}
    high = max(c.high for c in candles)
    low = min(c.low for c in candles)
    midpoint = (high + low) / 2
    return {
        "high": high,
        "low": low,
        "midpoint": midpoint
    }


def _calculate_sma(candles: list[Candle], period: int) -> list[float | None]:
    if len(candles) < period:
        return [None] * len(candles)
    
    smas: list[float | None] = [None] * (period - 1)
    for i in range(period - 1, len(candles)):
        window = candles[i - period + 1 : i + 1]
        sma = sum(c.close for c in window) / period
        smas.append(sma)
    return smas


def _analyze_sma_cross(ltf_candles: list[Candle]) -> tuple[SignalStatusLiteral, str, TradePlan | None]:
    short_period = 20
    long_period = 50
    
    if len(ltf_candles) < long_period + 2:
        return "NO_BIAS", "Not enough candles for SMA calculation.", None
        
    short_sma = _calculate_sma(ltf_candles, short_period)
    long_sma = _calculate_sma(ltf_candles, long_period)
    
    # Check for crossover in the last 2 candles
    prev_short = short_sma[-2]
    prev_long = long_sma[-2]
    curr_short = short_sma[-1]
    curr_long = long_sma[-1]
    
    if prev_short is None or prev_long is None or curr_short is None or curr_long is None:
        return "NO_BIAS", "SMA calculation error.", None

    # Bullish cross: short crosses above long
    if prev_short <= prev_long and curr_short > curr_long:
        entry_price = ltf_candles[-1].close
        stop_loss = entry_price * 0.98 # 2% SL
        take_profit = entry_price * 1.05 # 5% TP
        plan = TradePlan(
            side=TradeSideEnum.BUY,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_per_unit=entry_price - stop_loss,
            reward_per_unit=take_profit - entry_price,
            reward_risk_ratio=(take_profit - entry_price) / (entry_price - stop_loss)
        )
        return "READY", "Bullish SMA Cross (20/50) detected.", plan

    # Bearish cross: short crosses below long
    if prev_short >= prev_long and curr_short < curr_long:
        entry_price = ltf_candles[-1].close
        stop_loss = entry_price * 1.02 # 2% SL
        take_profit = entry_price * 0.95 # 5% TP
        plan = TradePlan(
            side=TradeSideEnum.SELL,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_per_unit=stop_loss - entry_price,
            reward_per_unit=entry_price - take_profit,
            reward_risk_ratio=(entry_price - take_profit) / (stop_loss - entry_price)
        )
        return "READY", "Bearish SMA Cross (20/50) detected.", plan

    return "NO_BIAS", "No SMA crossover detected.", None


def _determine_bias(highs: list[Pivot], lows: list[Pivot]) -> tuple[BiasLiteral, dict]:
    if len(highs) < 2 or len(lows) < 2:
        return "neutral", {"reason": "Not enough confirmed HTF pivots."}

    last_two_highs = highs[-2:]
    last_two_lows = lows[-2:]

    if last_two_highs[1].price > last_two_highs[0].price and last_two_lows[1].price > last_two_lows[0].price:
        return "bullish", {
            "reason": "Higher highs and higher lows confirmed on HTF.",
            "last_highs": [asdict(pivot) for pivot in last_two_highs],
            "last_lows": [asdict(pivot) for pivot in last_two_lows],
        }

    if last_two_highs[1].price < last_two_highs[0].price and last_two_lows[1].price < last_two_lows[0].price:
        return "bearish", {
            "reason": "Lower highs and lower lows confirmed on HTF.",
            "last_highs": [asdict(pivot) for pivot in last_two_highs],
            "last_lows": [asdict(pivot) for pivot in last_two_lows],
        }

    return "neutral", {
        "reason": "HTF structure is mixed.",
        "last_highs": [asdict(pivot) for pivot in last_two_highs],
        "last_lows": [asdict(pivot) for pivot in last_two_lows],
    }


def _find_sweep(
    candles: list[Candle],
    bias: BiasLiteral,
    highs: list[Pivot],
    lows: list[Pivot],
) -> SweepEvent | None:
    if bias == "bullish":
        for pivot in reversed(lows):
            for index in range(pivot.index + 1, len(candles)):
                candle = candles[index]
                if candle.low < pivot.price and candle.close > pivot.price:
                    return SweepEvent(
                        direction="bullish",
                        swept_pivot_index=pivot.index,
                        swept_price=pivot.price,
                        candle_index=index,
                        candle_time=candle.time,
                        extreme_price=candle.low,
                        close_price=candle.close,
                    )
    elif bias == "bearish":
        for pivot in reversed(highs):
            for index in range(pivot.index + 1, len(candles)):
                candle = candles[index]
                if candle.high > pivot.price and candle.close < pivot.price:
                    return SweepEvent(
                        direction="bearish",
                        swept_pivot_index=pivot.index,
                        swept_price=pivot.price,
                        candle_index=index,
                        candle_time=candle.time,
                        extreme_price=candle.high,
                        close_price=candle.close,
                    )
    return None


def _find_mss(
    candles: list[Candle],
    sweep: SweepEvent | None,
    highs: list[Pivot],
    lows: list[Pivot],
) -> MssEvent | None:
    if sweep is None:
        return None

    if sweep.direction == "bullish":
        reference_highs = [pivot for pivot in highs if pivot.index < sweep.candle_index]
        if not reference_highs:
            return None
        pivot = reference_highs[-1]
        for index in range(sweep.candle_index + 1, len(candles)):
            candle = candles[index]
            if candle.close > pivot.price:
                return MssEvent(
                    direction="bullish",
                    pivot_index=pivot.index,
                    pivot_price=pivot.price,
                    candle_index=index,
                    candle_time=candle.time,
                    close_price=candle.close,
                )

    if sweep.direction == "bearish":
        reference_lows = [pivot for pivot in lows if pivot.index < sweep.candle_index]
        if not reference_lows:
            return None
        pivot = reference_lows[-1]
        for index in range(sweep.candle_index + 1, len(candles)):
            candle = candles[index]
            if candle.close < pivot.price:
                return MssEvent(
                    direction="bearish",
                    pivot_index=pivot.index,
                    pivot_price=pivot.price,
                    candle_index=index,
                    candle_time=candle.time,
                    close_price=candle.close,
                )
    return None


def _find_fvg(candles: list[Candle], mss: MssEvent | None) -> FvgEvent | None:
    if mss is None:
        return None

    start_scan = max(mss.candle_index - 1, 1)
    for index in range(start_scan, len(candles) - 1):
        left = candles[index - 1]
        right = candles[index + 1]

        if mss.direction == "bullish" and left.high < right.low:
            return FvgEvent(
                direction="bullish",
                start_index=index - 1,
                middle_index=index,
                end_index=index + 1,
                lower_price=left.high,
                upper_price=right.low,
                midpoint=(left.high + right.low) / 2,
                candle_time=right.time,
            )

        if mss.direction == "bearish" and left.low > right.high:
            return FvgEvent(
                direction="bearish",
                start_index=index - 1,
                middle_index=index,
                end_index=index + 1,
                lower_price=right.high,
                upper_price=left.low,
                midpoint=(right.high + left.low) / 2,
                candle_time=right.time,
            )

    return None


def _build_trade_plan(
    *,
    bias: BiasLiteral,
    sweep: SweepEvent | None,
    fvg: FvgEvent | None,
    htf_highs: list[Pivot],
    htf_lows: list[Pivot],
    min_reward_risk: float,
) -> TradePlan | None:
    if bias == "neutral" or sweep is None or fvg is None:
        return None

    if bias == "bullish":
        entry_price = fvg.midpoint
        stop_loss = min(sweep.extreme_price, fvg.lower_price)
        risk_per_unit = entry_price - stop_loss
        if risk_per_unit <= 0:
            return None

        structure_target = next((pivot.price for pivot in reversed(htf_highs) if pivot.price > entry_price), None)
        rr_target = entry_price + (risk_per_unit * min_reward_risk)
        take_profit = max(structure_target or rr_target, rr_target)
        reward_per_unit = take_profit - entry_price
        return TradePlan(
            side=TradeSideEnum.BUY,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_per_unit=risk_per_unit,
            reward_per_unit=reward_per_unit,
            reward_risk_ratio=reward_per_unit / risk_per_unit,
        )

    entry_price = fvg.midpoint
    stop_loss = max(sweep.extreme_price, fvg.upper_price)
    risk_per_unit = stop_loss - entry_price
    if risk_per_unit <= 0:
        return None

    structure_target = next((pivot.price for pivot in reversed(htf_lows) if pivot.price < entry_price), None)
    rr_target = entry_price - (risk_per_unit * min_reward_risk)
    take_profit = min(structure_target or rr_target, rr_target)
    reward_per_unit = entry_price - take_profit
    return TradePlan(
        side=TradeSideEnum.SELL,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        risk_per_unit=risk_per_unit,
        reward_per_unit=reward_per_unit,
        reward_risk_ratio=reward_per_unit / risk_per_unit,
    )


def analyze_strategy(
    *,
    strategy_name: StrategyNameEnum,
    htf_candles: list[dict], # Spot HTF
    ltf_candles: list[dict], # Futures LTF
    futures_htf_candles: list[dict] | None = None, # Futures HTF (optional)
) -> dict:
    spec = get_strategy_spec(strategy_name)
    htf = [Candle(**candle) for candle in htf_candles]
    ltf = [Candle(**candle) for candle in ltf_candles]
    f_htf = [Candle(**candle) for candle in futures_htf_candles] if futures_htf_candles else []

    if strategy_name in [StrategyNameEnum.SMC_H4_M15, StrategyNameEnum.SMC_H1_M5, StrategyNameEnum.SMC_INTRADAY]:
        # Spot Analysis
        htf_highs, htf_lows = find_pivots(htf, spec.pivot_window)
        spot_bias, spot_bias_details = _determine_bias(htf_highs, htf_lows)
        
        # Futures Analysis
        futures_bias = "neutral"
        if f_htf:
            f_htf_highs, f_htf_lows = find_pivots(f_htf, spec.pivot_window)
            futures_bias, _ = _determine_bias(f_htf_highs, f_htf_lows)
        
        # Divergence Filter
        has_divergence = False
        skip_reason = None
        if futures_bias != "neutral" and spot_bias != "neutral" and spot_bias != futures_bias:
            has_divergence = True
            skip_reason = f"Divergence: Spot {spot_bias} vs Futures {futures_bias}"
        
        # Range Filter (Premium/Discount) - Based on Spot HTF
        htf_range = _calculate_range_info(htf)
        current_price = ltf[-1].close
        is_in_discount = current_price < htf_range["midpoint"]
        is_in_premium = current_price > htf_range["midpoint"]
        
        # Volatility for Dynamic SL
        vol = _calculate_volatility(ltf)
        sl_multiplier = _get_dynamic_sl_multiplier(vol)
        
        ltf_highs, ltf_lows = find_pivots(ltf, spec.pivot_window)
        sweep = _find_sweep(ltf, spot_bias, ltf_highs, ltf_lows)
        mss = _find_mss(ltf, sweep, ltf_highs, ltf_lows)
        fvg = _find_fvg(ltf, mss)
        
        trade_plan = _build_trade_plan(
            bias=spot_bias,
            sweep=sweep,
            fvg=fvg,
            htf_highs=htf_highs,
            htf_lows=htf_lows,
            min_reward_risk=spec.min_reward_risk,
        )

        # Apply Dynamic SL to trade plan
        if trade_plan:
            # Rebuild with multiplier
            risk = abs(trade_plan.entry_price - trade_plan.stop_loss)
            new_sl = trade_plan.entry_price - (risk * sl_multiplier) if trade_plan.side == TradeSideEnum.BUY else trade_plan.entry_price + (risk * sl_multiplier)
            trade_plan = TradePlan(
                side=trade_plan.side,
                entry_price=trade_plan.entry_price,
                stop_loss=new_sl,
                take_profit=trade_plan.take_profit,
                risk_per_unit=abs(trade_plan.entry_price - new_sl),
                reward_per_unit=trade_plan.reward_per_unit,
                reward_risk_ratio=trade_plan.reward_per_unit / abs(trade_plan.entry_price - new_sl)
            )

        # Apply Filters to signal
        signal_status = "NO_BIAS"
        signal_reason = spot_bias_details["reason"]
        
        if has_divergence:
            signal_status = "NO_BIAS"
            signal_reason = skip_reason
        elif spot_bias == "bullish":
            if not is_in_discount:
                signal_status = "NO_BIAS"
                signal_reason = "Spot Bullish but price is in PREMIUM zone (above 50%). Waiting for DISCOUNT."
            elif sweep is None:
                signal_status = "WAITING_SWEEP"
                signal_reason = "Spot Bullish & Discount zone. Waiting for LTF liquidity sweep."
            elif mss is None:
                signal_status = "WAITING_MSS"
                signal_reason = "Sweep detected. Waiting for MSS (Break of last LH)."
            elif fvg is None:
                signal_status = "WAITING_FVG"
                signal_reason = "MSS confirmed. Waiting for FVG formation."
            elif trade_plan:
                signal_status = "READY"
                signal_reason = f"SMC Setup READY ({'Fast' if vol > 1.2 else 'Calm' if vol < 0.8 else 'Normal'} market)."
        
        elif spot_bias == "bearish":
            if not is_in_premium:
                signal_status = "NO_BIAS"
                signal_reason = "Spot Bearish but price is in DISCOUNT zone (below 50%). Waiting for PREMIUM."
            elif sweep is None:
                signal_status = "WAITING_SWEEP"
                signal_reason = "Spot Bearish & Premium zone. Waiting for LTF liquidity sweep."
            elif mss is None:
                signal_status = "WAITING_MSS"
                signal_reason = "Sweep detected. Waiting for MSS (Break of last HL)."
            elif fvg is None:
                signal_status = "WAITING_FVG"
                signal_reason = "MSS confirmed. Waiting for FVG formation."
            elif trade_plan:
                signal_status = "READY"
                signal_reason = f"SMC Setup READY ({'Fast' if vol > 1.2 else 'Calm' if vol < 0.8 else 'Normal'} market)."

        return {
            "strategy": strategy_name.value,
            "timeframes": {"htf": spec.htf, "ltf": spec.ltf},
            "htf_range": htf_range,
            "spot_bias": spot_bias,
            "futures_bias": futures_bias,
            "has_divergence": has_divergence,
            "skip_reason": skip_reason,
            "volatility": vol,
            "htf_bias": {
                "value": spot_bias,
                "details": spot_bias_details,
            },
            "signal": {
                "status": signal_status,
                "reason": signal_reason,
                "side": trade_plan.side.value if trade_plan and signal_status == "READY" else None,
                "trade_plan": asdict(trade_plan) if trade_plan and signal_status == "READY" else None,
            },
            "ltf_events": {
                "sweep": asdict(sweep) if sweep else None,
                "mss": asdict(mss) if mss else None,
                "fvg": asdict(fvg) if fvg else None,
            },
        }

    if strategy_name == StrategyNameEnum.SMA_CROSS:
        signal_status, signal_reason, trade_plan = _analyze_sma_cross(ltf)
        bias = "neutral"
        if trade_plan:
            bias = "bullish" if trade_plan.side == TradeSideEnum.BUY else "bearish"
            
        return {
            "strategy": strategy_name.value,
            "timeframes": {"htf": spec.htf, "ltf": spec.ltf},
            "assumptions": {
                "short_period": 20,
                "long_period": 50,
                "entry_rule": "Market price on crossover.",
                "stop_loss_pct": 2.0,
                "take_profit_pct": 5.0,
            },
            "htf_bias": {
                "value": bias,
                "details": {"reason": signal_reason},
            },
            "htf_pivots": {"highs": [], "lows": []},
            "ltf_pivots": {"highs": [], "lows": []},
            "ltf_events": {"sweep": None, "mss": None, "fvg": None},
            "signal": {
                "status": signal_status,
                "reason": signal_reason,
                "side": trade_plan.side.value if trade_plan else None,
                "trade_plan": asdict(trade_plan) if trade_plan else None,
            },
            "entry_plan": None,
        }

    if len(htf) < spec.pivot_window * 2 + 3:
        raise ValueError("Not enough HTF candles for structure analysis.")
    if len(ltf) < spec.pivot_window * 2 + 5:
        raise ValueError("Not enough LTF candles for setup analysis.")

    htf_highs, htf_lows = find_pivots(htf, spec.pivot_window)
    bias, bias_details = _determine_bias(htf_highs, htf_lows)

    ltf_highs, ltf_lows = find_pivots(ltf, spec.pivot_window)
    sweep = _find_sweep(ltf, bias, ltf_highs, ltf_lows)
    mss = _find_mss(ltf, sweep, ltf_highs, ltf_lows)
    fvg = _find_fvg(ltf, mss)
    trade_plan = _build_trade_plan(
        bias=bias,
        sweep=sweep,
        fvg=fvg,
        htf_highs=htf_highs,
        htf_lows=htf_lows,
        min_reward_risk=spec.min_reward_risk,
    )

    if bias == "neutral":
        signal_status: SignalStatusLiteral = "NO_BIAS"
        signal_reason = "HTF bias is neutral, so no setup is tradable."
    elif sweep is None:
        signal_status = "WAITING_SWEEP"
        signal_reason = "HTF bias is aligned but no liquidity sweep is confirmed on LTF."
    elif mss is None:
        signal_status = "WAITING_MSS"
        signal_reason = "Sweep detected, waiting for market structure shift confirmation."
    elif fvg is None:
        signal_status = "WAITING_FVG"
        signal_reason = "MSS detected, waiting for a valid FVG entry zone."
    elif trade_plan is None:
        signal_status = "WAITING_FVG"
        signal_reason = "Setup detected but no valid executable trade plan could be derived."
    else:
        signal_status = "READY"
        signal_reason = "Sweep, MSS and FVG are aligned with HTF bias."

    return {
        "strategy": strategy_name.value,
        "timeframes": {"htf": spec.htf, "ltf": spec.ltf},
        "assumptions": {
            "pivot_window": spec.pivot_window,
            "mss_rule": "Close through the last opposite pivot after the sweep.",
            "fvg_rule": "Classic 3-candle imbalance between candle 1 and candle 3.",
            "entry_rule": "Entry is the FVG midpoint once HTF bias, sweep and MSS are aligned.",
            "target_rule": "Take profit uses HTF structure, floored by the minimum reward/risk ratio.",
            "minimum_reward_risk": spec.min_reward_risk,
        },
        "htf_bias": {
            "value": bias,
            "details": bias_details,
        },
        "htf_pivots": {
            "highs": [asdict(pivot) for pivot in htf_highs],
            "lows": [asdict(pivot) for pivot in htf_lows],
        },
        "ltf_pivots": {
            "highs": [asdict(pivot) for pivot in ltf_highs],
            "lows": [asdict(pivot) for pivot in ltf_lows],
        },
        "ltf_events": {
            "sweep": asdict(sweep) if sweep else None,
            "mss": asdict(mss) if mss else None,
            "fvg": asdict(fvg) if fvg else None,
        },
        "signal": {
            "status": signal_status,
            "reason": signal_reason,
            "side": trade_plan.side.value if trade_plan else None,
            "trade_plan": asdict(trade_plan) if trade_plan else None,
        },
        "entry_plan": {
            "should_wait_for_fvg_retrace": fvg is not None,
            "entry_zone": {
                "lower_price": fvg.lower_price,
                "upper_price": fvg.upper_price,
                "midpoint": fvg.midpoint,
            }
            if fvg
            else None,
        },
    }

