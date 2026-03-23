import { useTradingStore } from "../store/useTradingStore";
import { ExchangeId } from "../types/trading";

const ExchangeSelector = () => {
  const { exchange, selectedAssignmentId, setExchange } = useTradingStore();
  const isLocked = selectedAssignmentId !== null;

  return (
    <div className="d-flex align-items-center gap-2">
      <span className="text-muted">Plateforme</span>
      <select
        className="form-select w-auto"
        value={exchange}
        onChange={(event) => setExchange(event.target.value as ExchangeId)}
        disabled={isLocked}
      >
        <option value="binance">Binance</option>
        <option value="mexc">MEXC</option>
      </select>
      {isLocked && <span className="text-muted small">Verrouille par l'assignment</span>}
    </div>
  );
};

export default ExchangeSelector;
