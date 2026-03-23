import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from trading_bot_backend.app.services.market_data import fetch_candles

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    subscription = None

    try:
        while True:
            # On écoute les messages (non-bloquant avec timeout court ou via un check)
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                payload = json.loads(message)

                if payload.get("type") == "subscribe" and payload.get("channel") == "candles":
                    subscription = {
                        "exchange": payload.get("exchange", "binance"),
                        "symbol": payload.get("symbol", "BTC"),
                        "timeframe": payload.get("timeframe", "H1"), # H1 par défaut
                        "limit": int(payload.get("limit", 500))
                    }
                    print(f"New subscription: {subscription}")
                else:
                    await websocket.send_text(json.dumps({"error": "Invalid subscription message"}))
            except asyncio.TimeoutError:
                pass # Pas de nouveau message, on continue avec l'abonnement actuel

            if subscription:
                try:
                    candles = fetch_candles(
                        exchange=subscription["exchange"],
                        symbol=subscription["symbol"],
                        timeframe=subscription["timeframe"],
                        limit=subscription["limit"]
                    )
                    await websocket.send_text(json.dumps({"candles": candles}))
                except Exception as e:
                    await websocket.send_text(json.dumps({"error": f"Fetch failed: {str(e)}"}))
            
            await asyncio.sleep(2) # Rafraîchissement toutes les 2 secondes

    except WebSocketDisconnect:
        print("WebSocket client disconnected")
        return
    except Exception as exc:
        print(f"WebSocket error: {exc}")
        try:
            await websocket.send_text(json.dumps({"error": str(exc)}))
            await websocket.close()
        except:
            pass
