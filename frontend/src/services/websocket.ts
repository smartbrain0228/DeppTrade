import { Candle, CryptoSymbol, ExchangeId } from "../types/trading";

type CandleCallback = (candles: Candle[]) => void;

class WebsocketService {
  private socket: WebSocket | null = null;

  private getWebsocketUrl(): string {
    if (import.meta.env.VITE_WS_URL) {
      return import.meta.env.VITE_WS_URL;
    }

    if (typeof window !== "undefined") {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      return `${protocol}//${window.location.host}/ws`;
    }

    return "ws://localhost:8000/ws";
  }

  private ensureOpen(): Promise<void> {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      const url = this.getWebsocketUrl();
      console.log("Connecting to WebSocket:", url);
      this.socket = new WebSocket(url);

      this.socket.onopen = () => {
        console.log("WebSocket connection established");
        resolve();
      };
      this.socket.onerror = (err) => {
        console.error("WebSocket connection error:", err);
        reject(new Error("WebSocket connection failed"));
      };
      this.socket.onclose = (event) => {
        console.log("WebSocket connection closed:", event.code, event.reason);
        this.socket = null;
      };
    });
  }

  async subscribeCandles(exchange: ExchangeId, symbol: CryptoSymbol, onData: CandleCallback) {
    await this.ensureOpen();

    if (!this.socket) {
      return;
    }

    this.socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as { candles?: Candle[]; error?: string };
      if (payload.candles) {
        onData(payload.candles);
      } else if (payload.error) {
        console.error("WebSocket payload error:", payload.error);
      }
    };

    const subscribeMessage = {
      type: "subscribe",
      channel: "candles",
      exchange,
      symbol,
      timeframe: "H1", // Ajout du timeframe correct
      limit: 500
    };
    console.log("Sending subscribe message:", subscribeMessage);
    this.socket.send(JSON.stringify(subscribeMessage));
  }

  disconnect() {
    this.socket?.close();
    this.socket = null;
  }
}

export const websocketService = new WebsocketService();
