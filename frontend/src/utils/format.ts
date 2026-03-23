import { Candle } from "../types/trading";

export const formatPrice = (value: number) => {
  if (value >= 1000) {
    return value.toLocaleString("en-US", { maximumFractionDigits: 2 });
  }
  if (value >= 1) {
    return value.toFixed(2);
  }
  return value.toFixed(6);
};

export const formatPercent = (value: number) => {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
};

export const formatDateTime = (value: number | string | null | undefined) => {
  if (value == null) {
    return "Jamais";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Jamais";
  }

  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(date);
};

export const generateCandles = (count: number, startPrice = 42000): Candle[] => {
  const candles: Candle[] = [];
  let current = startPrice;
  let time = Math.floor(Date.now() / 1000) - count * 60;

  for (let i = 0; i < count; i += 1) {
    const open = current;
    const delta = (Math.random() - 0.5) * 200;
    const close = Math.max(100, open + delta);
    const high = Math.max(open, close) + Math.random() * 120;
    const low = Math.min(open, close) - Math.random() * 120;
    const volume = Math.random() * 500 + 200;

    candles.push({
      time,
      open: Number(open.toFixed(2)),
      high: Number(high.toFixed(2)),
      low: Number(low.toFixed(2)),
      close: Number(close.toFixed(2)),
      volume: Number(volume.toFixed(2))
    });

    current = close;
    time += 60;
  }

  return candles;
};
