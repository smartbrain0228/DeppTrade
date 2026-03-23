import { FormEvent, useState } from "react";
import { DashboardActionLogEntry } from "../hooks/tradingDashboard/useTradingDashboardData";
import { SignalAnalysisResponse, TradeResponse } from "../types/trading";
import { formatDateTime, formatPrice } from "../utils/format";

interface SignalActionPanelProps {
  isBusy: boolean;
  error: string | null;
  successMessage?: string | null;
  hasActiveAssignment?: boolean;
  actionLog?: DashboardActionLogEntry[];
  lastScan: SignalAnalysisResponse | null;
  lastTrade: TradeResponse | null;
  lastScanAt?: number | null;
  lastExecuteAt?: number | null;
  onScan: () => Promise<void>;
  onExecute: (quantity: number) => Promise<void>;
}

const getSignalStatusTone = (status: string | null) => {
  if (status === "READY") {
    return "success";
  }
  if (status === "NO_BIAS") {
    return "secondary";
  }
  if (status?.startsWith("WAITING_")) {
    return "warning";
  }
  return "light";
};

const getSignalStatusSummary = (analysis: SignalAnalysisResponse | null) => {
  const status = analysis?.signal.status ?? null;

  switch (status) {
    case "READY":
      return "Le setup est executable selon l'analyse backend actuelle.";
    case "NO_BIAS":
      return "Le contexte HTF est neutre. Aucun trade ne doit etre envoye tant que le bias n'est pas clarifie.";
    case "WAITING_SWEEP":
      return "Le bias existe, mais la liquidite n'a pas encore ete balayee sur le LTF.";
    case "WAITING_MSS":
      return "Le sweep est detecte, mais la cassure de structure n'est pas encore confirmee.";
    case "WAITING_FVG":
      return "La structure progresse, mais la zone d'entree exploitable n'est pas encore validee.";
    default:
      return "Lance un scan pour obtenir l'etat backend le plus recent sur cet assignment.";
  }
};

const getExecutionChecklist = (status: string | null) => [
  {
    label: "Bias HTF exploitable",
    done: status !== null && status !== "NO_BIAS"
  },
  {
    label: "Sweep confirme",
    done: status === "WAITING_MSS" || status === "WAITING_FVG" || status === "READY"
  },
  {
    label: "MSS confirme",
    done: status === "WAITING_FVG" || status === "READY"
  },
  {
    label: "Zone FVG validee",
    done: status === "READY"
  }
];

const getSignalBlockers = (analysis: SignalAnalysisResponse | null) => {
  const status = analysis?.signal.status ?? null;
  const reason = analysis?.signal.reason ?? null;

  switch (status) {
    case "READY":
      return ["Aucun blocage detecte. Le setup est pret selon la derniere analyse backend."];
    case "NO_BIAS":
      return [
        "Le contexte HTF ne donne pas encore de direction exploitable.",
        reason ?? "Le backend attend un bias plus clair avant toute execution."
      ];
    case "WAITING_SWEEP":
      return [
        "Le setup a un bias, mais la prise de liquidite n'est pas encore confirmee sur le LTF.",
        reason ?? "Aucun sweep valide n'a encore ete enregistre."
      ];
    case "WAITING_MSS":
      return [
        "Le sweep est present, mais la cassure de structure manque encore pour confirmer l'entree.",
        reason ?? "Le backend attend une MSS valide."
      ];
    case "WAITING_FVG":
      return [
        "La structure a progresse, mais il manque encore une zone FVG exploitable.",
        reason ?? "Le backend attend une FVG conforme au plan de trade."
      ];
    default:
      return [reason ?? "Lance un scan pour connaitre le prochain blocage operatoire."];
  }
};

const SignalActionPanel = ({
  isBusy,
  error,
  successMessage,
  hasActiveAssignment = true,
  actionLog = [],
  lastScan,
  lastTrade,
  lastScanAt,
  lastExecuteAt,
  onScan,
  onExecute
}: SignalActionPanelProps) => {
  const [quantity, setQuantity] = useState("1");
  const signalStatus = lastScan?.signal.status ?? null;
  const tradePlan = lastScan?.signal.trade_plan;
  const parsedQuantity = Number(quantity);
  const hasValidQuantity = Number.isFinite(parsedQuantity) && parsedQuantity > 0;
  const canExecute = hasActiveAssignment && signalStatus === "READY" && tradePlan != null;
  const statusTone = getSignalStatusTone(signalStatus);
  const signalSummary = getSignalStatusSummary(lastScan);
  const executionChecklist = getExecutionChecklist(signalStatus);
  const signalBlockers = getSignalBlockers(lastScan);
  const assignmentConfig = lastScan?.assignment;

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!hasValidQuantity || !tradePlan) {
      return;
    }

    const confirmationMessage = [
      "Confirmer l'execution du trade ?",
      `Quantite: ${parsedQuantity}`,
      `Side: ${tradePlan.side ?? "-"}`,
      `Entry: ${tradePlan.entry_price != null ? formatPrice(tradePlan.entry_price) : "-"}`,
      `SL: ${tradePlan.stop_loss != null ? formatPrice(tradePlan.stop_loss) : "-"}`,
      `TP: ${tradePlan.take_profit != null ? formatPrice(tradePlan.take_profit) : "-"}`
    ].join("\n");

    if (!window.confirm(confirmationMessage)) {
      return;
    }

    await onExecute(parsedQuantity);
  };

  return (
    <div className="signal-panel mt-3">
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
        <div className="panel-heading">
          <span className="panel-heading__eyebrow">Signal engine</span>
          <h3 className="h6 fw-bold mb-1">Signal operationnel</h3>
          <p className="text-muted mb-0">Scan le setup, puis execute si le signal est pret.</p>
        </div>
        <button className="btn btn-outline-primary trade-refresh" type="button" onClick={() => void onScan()} disabled={isBusy || !hasActiveAssignment}>
          {isBusy ? "Traitement..." : "Scanner le signal"}
        </button>
      </div>

      {!hasActiveAssignment && (
        <div className="alert alert-secondary py-2 dashboard-alert">
          Selectionne d'abord un assignment actif pour lancer un scan ou preparer une execution.
        </div>
      )}

      {error && <div className="alert alert-warning py-2 dashboard-alert">{error}</div>}
      {successMessage && <div className="alert alert-success py-2 dashboard-alert">{successMessage}</div>}

      <div className="row g-3">
        <div className="col-md-6">
          <div className="overlay-card h-100">
            <div className="overlay-label">Dernier scan</div>
            <div className="text-muted small mb-2">Mis a jour: {formatDateTime(lastScanAt)}</div>
            <div className="mb-2 d-flex align-items-center gap-2 flex-wrap">
              <span>Statut:</span>
              <span className={`badge text-bg-${statusTone}`}>{signalStatus ?? "Aucun"}</span>
            </div>
            <div className="small mb-2">{signalSummary}</div>
            <div className="text-muted small mb-3">{lastScan?.signal.reason ?? "Aucun scan lance pour le moment."}</div>
            <div className="small mb-3">
              <div className="fw-semibold mb-2">Blocages actuels</div>
              <div className="d-grid gap-1">
                {signalBlockers.map((item) => (
                  <div key={item} className={signalStatus === "READY" ? "text-success" : "text-muted"}>
                    {signalStatus === "READY" ? "OK" : "A surveiller"} | {item}
                  </div>
                ))}
              </div>
            </div>
            {tradePlan && (
              <div className="small">
                <div>Side: {tradePlan.side ?? "-"}</div>
                <div>Entry: {tradePlan.entry_price != null ? formatPrice(tradePlan.entry_price) : "-"}</div>
                <div>SL: {tradePlan.stop_loss != null ? formatPrice(tradePlan.stop_loss) : "-"}</div>
                <div>TP: {tradePlan.take_profit != null ? formatPrice(tradePlan.take_profit) : "-"}</div>
                <div>RR: {tradePlan.reward_risk_ratio != null ? tradePlan.reward_risk_ratio.toFixed(2) : "-"}</div>
              </div>
            )}
            <div className="small mt-3 pt-3 border-top">
              <div className="fw-semibold mb-2">Checklist d'execution</div>
              <div className="d-grid gap-1">
                {executionChecklist.map((item) => (
                  <div key={item.label} className={item.done ? "text-success" : "text-muted"}>
                    {item.done ? "OK" : "En attente"} | {item.label}
                  </div>
                ))}
              </div>
            </div>
            {assignmentConfig && (
              <div className="small mt-3 pt-3 border-top">
                <div className="fw-semibold mb-1">Cadre assignment</div>
                <div>Risque configure: {assignmentConfig.risk_pct.toFixed(2)}%</div>
                <div>Max trades / jour: {assignmentConfig.max_trades_per_day}</div>
              </div>
            )}
          </div>
        </div>
        <div className="col-md-6">
          <div className="overlay-card h-100">
            <div className="overlay-label">Execution</div>
            <div className="text-muted small mb-2">Derniere execution: {formatDateTime(lastExecuteAt)}</div>
            <form onSubmit={handleSubmit}>
              <label className="form-label small">Quantite</label>
              <input
                className="form-control mb-3 auth-input"
                type="number"
                min="0.00000001"
                step="0.00000001"
                value={quantity}
                onChange={(event) => setQuantity(event.target.value)}
              />
              <button className="btn btn-primary w-100 auth-submit" type="submit" disabled={isBusy || !canExecute || !hasValidQuantity}>
                Executer le trade
              </button>
            </form>
            {!hasValidQuantity && <div className="text-warning small mt-2">Entre une quantite strictement positive.</div>}
            {canExecute && (
              <div className="text-muted small mt-2">Une confirmation affiche les niveaux du plan avant envoi au backend.</div>
            )}
            {signalStatus === "READY" && (
              <div className="text-success small mt-2">
                Le backend considere le setup executable sur la base du dernier scan disponible.
              </div>
            )}
            {!canExecute && hasActiveAssignment && (
              <div className="text-muted small mt-2">L'execution est disponible uniquement quand le signal est `READY`.</div>
            )}
            {lastTrade && (
              <div className="small mt-3 pt-3 border-top">
                <div className="fw-semibold mb-1">Dernier trade cree</div>
                <div>#{lastTrade.id} | {lastTrade.side} | {lastTrade.status}</div>
                <div>{lastTrade.symbol} | Qty {lastTrade.quantity}</div>
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="overlay-card mt-3">
        <div className="overlay-label mb-2">Journal d'action</div>
        {actionLog.length === 0 && <div className="text-muted small">Aucune action recente sur cet assignment pour le moment.</div>}
        {actionLog.length > 0 && (
          <div className="d-grid gap-2">
            {actionLog.map((entry) => (
              <div key={entry.id} className="action-log-entry">
                <div className="d-flex flex-wrap align-items-center justify-content-between gap-2">
                  <div className="d-flex align-items-center gap-2">
                    <span className={`badge text-bg-${entry.tone}`}>{entry.type}</span>
                    <span className="fw-semibold small">{entry.title}</span>
                  </div>
                  <span className="text-muted small">{formatDateTime(entry.createdAt)}</span>
                </div>
                <div className="text-muted small mt-1">{entry.message}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SignalActionPanel;
