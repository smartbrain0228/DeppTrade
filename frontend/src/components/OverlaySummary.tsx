import { AssignmentOverlayResponse } from "../types/trading";
import { formatDateTime, formatPrice } from "../utils/format";

interface OverlaySummaryProps {
  overlay: AssignmentOverlayResponse | null;
  isLoading: boolean;
  error: string | null;
}

const OverlaySummary = ({ overlay, isLoading, error }: OverlaySummaryProps) => {
  const latestOverlay = overlay?.latest;

  return (
    <div className="overlay-summary mt-3">
      <div className="d-flex flex-wrap gap-2 mb-3">
        <span className="overlay-pill">Evenements: {overlay?.count ?? 0}</span>
        <span className="overlay-pill">Statut: {latestOverlay?.signal_status ?? "Aucun"}</span>
        <span className="overlay-pill">Bias: {latestOverlay?.htf_bias ?? "n/a"}</span>
        <span className="overlay-pill">Strategie: {latestOverlay?.strategy_name ?? "n/a"}</span>
      </div>
      {!latestOverlay && !error && !isLoading && (
        <div className="text-muted small">Aucun snapshot de signal pour cet assignment pour le moment.</div>
      )}
      {latestOverlay && (
        <div className="row g-3">
          <div className="col-md-4">
            <div className="overlay-card">
              <div className="overlay-label">Niveaux</div>
              <div>Entry: {latestOverlay.levels.entry_price ? formatPrice(latestOverlay.levels.entry_price) : "-"}</div>
              <div>SL: {latestOverlay.levels.stop_loss ? formatPrice(latestOverlay.levels.stop_loss) : "-"}</div>
              <div>TP: {latestOverlay.levels.take_profit ? formatPrice(latestOverlay.levels.take_profit) : "-"}</div>
            </div>
          </div>
          <div className="col-md-4">
            <div className="overlay-card">
              <div className="overlay-label">Timeline</div>
              <div>Sweep: {formatDateTime(latestOverlay.timeline.sweep_time)}</div>
              <div>MSS: {formatDateTime(latestOverlay.timeline.mss_time)}</div>
              <div>FVG: {formatDateTime(latestOverlay.timeline.fvg_time)}</div>
            </div>
          </div>
          <div className="col-md-4">
            <div className="overlay-card">
              <div className="overlay-label">Dernier signal</div>
              <div>{latestOverlay.signal_reason}</div>
              <div className="text-muted small mt-2">Trigger: {latestOverlay.trigger}</div>
              <div className="text-muted small">Snapshot: {formatDateTime(latestOverlay.created_at)}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OverlaySummary;
