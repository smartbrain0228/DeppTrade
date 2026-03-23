import { useEffect, useMemo, useState } from "react";
import CryptoCard from "./CryptoCard";
import { CryptoSymbol } from "../types/trading";
import { useTradingStore } from "../store/useTradingStore";
import { fetchPopularCryptos } from "../services/api";

const fallbackCryptos: CryptoSymbol[] = [
  "BTC",
  "ETH",
  "SOL",
  "BNB",
  "XRP",
  "ADA",
  "DOGE",
  "DOT",
  "AVAX",
  "MATIC"
];

const CryptoList = () => {
  const { assignments, selectedCrypto, selectedAssignmentId, setSelectedAssignmentId } = useTradingStore();
  const [items, setItems] = useState<CryptoSymbol[]>(fallbackCryptos);

  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    const loadCryptos = async () => {
      try {
        const data = await fetchPopularCryptos(controller.signal);
        if (isMounted && data.length > 0) {
          setItems(data);
        }
      } catch {
        if (!controller.signal.aborted && isMounted) {
          setItems(fallbackCryptos);
        }
      }
    };

    loadCryptos();

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, []);

  const list = useMemo(() => items, [items]);

  return (
    <div className="crypto-watchlist">
      {list.map((symbol) => {
        const matchingAssignments = assignments.filter((item) => item.symbol.startsWith(symbol));
        const matchedAssignment = matchingAssignments[0];
        const setupLabels = matchingAssignments.map((item) => `${item.htf}/${item.ltf}`);
        return (
          <div className="crypto-watchlist__item" key={symbol}>
            <CryptoCard
              symbol={symbol}
              isSelected={matchingAssignments.some((item) => item.id === selectedAssignmentId) || symbol === selectedCrypto}
              isDisabled={matchedAssignment == null}
              setupCount={matchingAssignments.length}
              setupLabels={setupLabels}
              onSelect={() => {
                if (matchedAssignment) {
                  setSelectedAssignmentId(matchedAssignment.id);
                }
              }}
            />
          </div>
        );
      })}
    </div>
  );
};

export default CryptoList;
