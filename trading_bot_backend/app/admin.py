from fastapi import Request
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend

from trading_bot_backend.app.config import settings
from trading_bot_backend.app.db import engine
from trading_bot_backend.app.models import Strategy, Symbol, Trade, User, UserPairStrategy


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        if (
            username == settings.admin_username
            and password == settings.admin_password
        ):
            request.session.update({"admin_authenticated": True})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return request.session.get("admin_authenticated", False)


class UserAdmin(ModelView, model=User):
    name = "User"
    name_plural = "Users"
    column_list = [User.id, User.email, User.username, User.role, User.is_active, User.created_at]
    form_excluded_columns = [User.pair_strategies, User.trades]


class StrategyAdmin(ModelView, model=Strategy):
    name = "Strategy"
    name_plural = "Strategies"
    column_list = [Strategy.id, Strategy.name, Strategy.htf, Strategy.ltf, Strategy.is_active]


class SymbolAdmin(ModelView, model=Symbol):
    name = "Symbol"
    name_plural = "Symbols"
    column_list = [Symbol.id, Symbol.exchange, Symbol.symbol, Symbol.base_asset, Symbol.quote_asset, Symbol.is_active]


class UserPairStrategyAdmin(ModelView, model=UserPairStrategy):
    name = "Pair Mapping"
    name_plural = "Pair Mappings"
    column_list = [
        UserPairStrategy.id,
        UserPairStrategy.user_id,
        UserPairStrategy.symbol_id,
        UserPairStrategy.strategy_id,
        UserPairStrategy.risk_pct,
        UserPairStrategy.max_trades_per_day,
        UserPairStrategy.is_active,
    ]


class TradeAdmin(ModelView, model=Trade):
    name = "Trade"
    name_plural = "Trades"
    column_list = [
        Trade.id,
        Trade.user_id,
        Trade.symbol_id,
        Trade.strategy_id,
        Trade.tag,
        Trade.side,
        Trade.status,
        Trade.entry_price,
        Trade.pnl,
        Trade.opened_at,
        Trade.closed_at,
    ]


def setup_admin(app) -> None:
    admin = Admin(
        app=app,
        engine=engine,
        authentication_backend=AdminAuth(secret_key=settings.admin_session_secret),
        title="Trading Bot Admin",
    )
    admin.add_view(UserAdmin)
    admin.add_view(StrategyAdmin)
    admin.add_view(SymbolAdmin)
    admin.add_view(UserPairStrategyAdmin)
    admin.add_view(TradeAdmin)
