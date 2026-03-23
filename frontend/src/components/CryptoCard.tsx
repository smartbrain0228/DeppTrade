import { CryptoSymbol } from "../types/trading";

interface CryptoCardProps {
  symbol: CryptoSymbol;
  isSelected: boolean;
  isDisabled?: boolean;
  setupCount?: number;
  setupLabels?: string[];
  onSelect: () => void;
}

const CryptoCard = ({
  symbol,
  isSelected,
  isDisabled = false,
  setupCount = 0,
  setupLabels = [],
  onSelect
}: CryptoCardProps) => {
  return (
    <button
      className={`card crypto-card text-start ${isSelected ? "selected" : ""}`}
      type="button"
      onClick={onSelect}
      disabled={isDisabled}
    >
      <div className="card-body crypto-card__body">
        <div className="crypto-card__topline">
          <div>
            <h6 className="mb-1 crypto-card__symbol">{symbol}</h6>
            <small className="text-muted crypto-card__caption">
              Top market
            </small>
          </div>
          <span className="badge crypto-card__badge">{setupCount > 0 ? "Setup" : "Watch"}</span>
        </div>
        <div className="crypto-card__content">
          <small className="text-muted crypto-card__status">
            {setupCount > 0 ? `${setupCount} setup(s) actif(s)` : "Aucun setup"}
          </small>
          {setupLabels.length > 0 && (
            <div className="crypto-card__meta">
              {setupLabels.slice(0, 2).map((label) => (
                <span key={label} className="crypto-card__pill">
                  {label}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </button>
  );
};

export default CryptoCard;
