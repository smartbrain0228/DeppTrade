from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from trading_bot_backend.app.models import StrategyNameEnum


STRATEGY_LABELS = {
    StrategyNameEnum.INTRADAY: "Intraday H4/M15",
    StrategyNameEnum.SCALP: "Scalping H1/M5",
    StrategyNameEnum.SMC_INTRADAY: "Intraday H4/M15",
    StrategyNameEnum.SMC_H4_M15: "Intraday H4/M15",
    StrategyNameEnum.SMC_H1_M5: "Scalping H1/M5",
    StrategyNameEnum.SMA_CROSS: "SMA Cross",
}


def format_price(price: Any) -> str:
    if price is None:
        return "N/A"
    return f"{float(price):.5f}"


def format_quantity(quantity: Any) -> str:
    if quantity is None:
        return "N/A"
    return f"{float(quantity):.4f}"


def format_pnl(pnl: Any) -> str:
    if pnl is None:
        return "0.00 USDT"
    value = float(pnl)
    return f"{value:+.2f} USDT"


def format_timestamp(value: datetime | None) -> str:
    if value is None:
        return "N/A"
    return value.strftime("%Y-%m-%d %H:%M UTC")


def get_strategy_label(strategy_name: Any) -> str:
    if isinstance(strategy_name, StrategyNameEnum):
        return STRATEGY_LABELS.get(strategy_name, strategy_name.value)

    normalized = str(strategy_name).split(".")[-1].upper()
    for enum_value, label in STRATEGY_LABELS.items():
        if enum_value.value == normalized:
            return label
    return str(strategy_name)


def get_trade_opened_template(
    strategy_name: Any,
    symbol: str,
    side: str,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    balance: float,
    quantity: float | None = None,
    risk_pct: float | None = None,
    mode: str = "Demo",
    opened_at: datetime | None = None,
) -> str:
    lines = [
        "<b>TRADE OUVERT</b>",
        "",
        f"<b>Strategie :</b> {get_strategy_label(strategy_name)}",
        f"<b>Actif :</b> <code>{symbol}</code>",
        f"<b>Direction :</b> <code>{side}</code>",
        f"<b>Mode :</b> {mode}",
        "",
        f"<b>Entree :</b> {format_price(entry_price)}",
        f"<b>Stop Loss :</b> {format_price(stop_loss)}",
        f"<b>Take Profit :</b> {format_price(take_profit)}",
    ]

    if quantity is not None:
        lines.append(f"<b>Quantite :</b> {format_quantity(quantity)}")
    if risk_pct is not None:
        lines.append(f"<b>Risque :</b> {float(risk_pct):.2f}%")

    lines.extend(
        [
            f"<b>Solde strategie :</b> {balance:.2f} USDT",
            f"<b>Ouvert le :</b> {format_timestamp(opened_at)}",
        ]
    )
    return "\n".join(lines)


def get_trade_closed_template(
    symbol: str,
    side: str,
    entry_price: float,
    exit_price: float,
    pnl: float,
    balance: float,
    is_tp: bool = False,
    strategy_name: Any | None = None,
    mode: str = "Demo",
    closed_at: datetime | None = None,
) -> str:
    result = "TP" if is_tp else "SL"
    lines = ["<b>TRADE FERME</b>", ""]

    if strategy_name is not None:
        lines.append(f"<b>Strategie :</b> {get_strategy_label(strategy_name)}")

    lines.extend(
        [
            f"<b>Actif :</b> <code>{symbol}</code>",
            f"<b>Direction :</b> <code>{side}</code>",
            f"<b>Mode :</b> {mode}",
            "",
            f"<b>Entree :</b> {format_price(entry_price)}",
            f"<b>Sortie :</b> {format_price(exit_price)}",
            f"<b>Resultat :</b> {result}",
            f"<b>PnL :</b> {format_pnl(pnl)}",
            f"<b>Nouveau solde :</b> {balance:.2f} USDT",
            f"<b>Ferme le :</b> {format_timestamp(closed_at)}",
        ]
    )
    return "\n".join(lines)


def get_daily_summary_template(
    date_str: str,
    total_trades: int,
    wins: int,
    losses: int,
    win_rate: float,
    profit_today: float,
    balance: float,
) -> str:
    return "\n".join(
        [
            f"<b>RESUME JOURNALIER</b>",
            "",
            f"<b>Date :</b> {date_str}",
            f"<b>Trades :</b> {total_trades}",
            f"<b>Gagnants :</b> {wins}",
            f"<b>Perdants :</b> {losses}",
            f"<b>Win rate :</b> {win_rate:.1f}%",
            "",
            f"<b>PnL du jour :</b> {format_pnl(profit_today)}",
            f"<b>Solde actuel :</b> {balance:.2f} USDT",
        ]
    )


def get_trade_skipped_template(
    strategy_name: Any,
    symbol: str,
    reason: str,
    mode: str = "Demo",
) -> str:
    return "\n".join(
        [
            "<b>TRADE IGNORE</b>",
            "",
            f"<b>Strategie :</b> {get_strategy_label(strategy_name)}",
            f"<b>Actif :</b> <code>{symbol}</code>",
            f"<b>Mode :</b> {mode}",
            f"<b>Raison :</b> {reason}",
        ]
    )


def get_strategy_paused_template(
    strategy_name: Any,
    symbol: str,
    trade_count: int,
    mode: str = "Demo",
) -> str:
    return "\n".join(
        [
            "<b>STRATEGIE EN PAUSE</b>",
            "",
            f"<b>Strategie :</b> {get_strategy_label(strategy_name)}",
            f"<b>Actif :</b> <code>{symbol}</code>",
            f"<b>Mode :</b> {mode}",
            f"<b>Cause :</b> limite de {trade_count} trades atteinte",
        ]
    )


def get_interactive_keyboard(_trade_id: int) -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "Voir graphique", "url": "https://tradingview.com/chart/"},
            ]
        ]
    }
