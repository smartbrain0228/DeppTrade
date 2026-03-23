import { useEffect, useRef } from "react";
import {
  createChart,
  IChartApi,
  IPriceLine,
  ISeriesApi,
  SeriesMarker,
  Time
} from "lightweight-charts";
import { useTradingStore } from "../store/useTradingStore";
import { OverlayMarker } from "../types/trading";

const markerColorMap: Record<string, string> = {
  SWEEP: "#f59e0b",
  MSS: "#0ea5e9",
  FVG: "#c084fc"
};

const markerShapeMap: Record<string, "circle" | "square" | "arrowUp"> = {
  SWEEP: "circle",
  MSS: "square",
  FVG: "arrowUp"
};

const Chart = () => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const priceLinesRef = useRef<IPriceLine[]>([]);
  const candles = useTradingStore((state) => state.candles);
  const overlay = useTradingStore((state) => state.overlay);

  useEffect(() => {
    if (!containerRef.current || chartRef.current) {
      return;
    }

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: "#101826" },
        textColor: "#d8e1f0"
      },
      grid: {
        vertLines: { color: "rgba(143, 160, 187, 0.12)" },
        horzLines: { color: "rgba(143, 160, 187, 0.12)" }
      },
      width: containerRef.current.clientWidth,
      height: 420,
      timeScale: {
        borderColor: "rgba(143, 160, 187, 0.2)"
      }
    });

    const series = chart.addCandlestickSeries({
      upColor: "#34d399",
      downColor: "#f87171",
      borderVisible: false,
      wickUpColor: "#34d399",
      wickDownColor: "#f87171"
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const handleResize = () => {
      if (!containerRef.current) {
        return;
      }
      chart.applyOptions({ width: containerRef.current.clientWidth });
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      priceLinesRef.current = [];
    };
  }, []);

  useEffect(() => {
    if (!seriesRef.current) {
      return;
    }

    seriesRef.current.setData(
      candles.map((candle) => ({
        time: candle.time as Time,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close
      }))
    );
  }, [candles]);

  useEffect(() => {
    if (!seriesRef.current) {
      return;
    }

    priceLinesRef.current.forEach((line) => {
      seriesRef.current?.removePriceLine(line);
    });
    priceLinesRef.current = [];

    const latest = overlay?.latest;
    const markers = (latest?.markers ?? [])
      .filter((marker): marker is OverlayMarker & { time: number; price: number } => {
        return marker.time !== null && marker.price !== null;
      })
      .map<SeriesMarker<Time>>((marker) => ({
        time: marker.time as Time,
        position: marker.kind === "FVG" ? "belowBar" : "aboveBar",
        color: markerColorMap[marker.kind] ?? "#111827",
        shape: markerShapeMap[marker.kind] ?? "circle",
        text: marker.kind
      }));

    seriesRef.current.setMarkers(markers);

    const priceLevels = [
      { price: latest?.levels.entry_price, color: "#60a5fa", title: "Entry" },
      { price: latest?.levels.stop_loss, color: "#f87171", title: "SL" },
      { price: latest?.levels.take_profit, color: "#34d399", title: "TP" }
    ];

    priceLevels.forEach((level) => {
      if (level.price == null || !seriesRef.current) {
        return;
      }
      const line = seriesRef.current.createPriceLine({
        price: level.price,
        color: level.color,
        lineWidth: 2,
        lineStyle: 2,
        axisLabelVisible: true,
        title: level.title
      });
      priceLinesRef.current.push(line);
    });
  }, [overlay]);

  return <div className="chart-host" ref={containerRef} />;
};

export default Chart;
