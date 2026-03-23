import { useTradingStore } from "../store/useTradingStore";
import SymbolStrategyTabs from "./SymbolStrategyTabs";

const AssignmentSelector = () => {
  const { assignments, selectedAssignmentId, setSelectedAssignmentId } = useTradingStore();
  const hasAssignments = assignments.length > 0;
  const selectedAssignment = assignments.find((assignment) => assignment.id === selectedAssignmentId) ?? null;
  const siblingAssignments = selectedAssignment
    ? assignments.filter((assignment) => assignment.symbol === selectedAssignment.symbol)
    : [];

  return (
    <div className="assignment-selector">
      <div className="d-flex align-items-center justify-content-between gap-2 mb-2 panel-heading">
        <h3 className="h6 fw-bold mb-0">Assignments</h3>
        <span className="text-muted small">{assignments.length} actif(s)</span>
      </div>
      <div className="d-grid gap-2">
        {selectedAssignment && siblingAssignments.length > 1 && (
          <SymbolStrategyTabs
            assignments={siblingAssignments}
            selectedAssignmentId={selectedAssignmentId}
            onSelect={setSelectedAssignmentId}
          />
        )}
        {!hasAssignments && (
          <div className="empty-note text-muted small">
            Aucun assignment actif pour le moment. Un administrateur doit d'abord t'affecter un symbole et une
            strategie avant de pouvoir scanner ou executer un setup.
          </div>
        )}
        {assignments.map((assignment) => (
          <button
            key={assignment.id}
            type="button"
            className={`assignment-card btn text-start ${assignment.id === selectedAssignmentId ? "selected" : ""}`}
            onClick={() => setSelectedAssignmentId(assignment.id)}
          >
            <div className="d-flex align-items-start justify-content-between gap-2">
              <div>
                <div className="fw-semibold">{assignment.symbol}</div>
                <div className="text-muted small">
                  {assignment.exchange.toUpperCase()} | {assignment.strategy_name}
                </div>
              </div>
              <span className="badge assignment-badge">{assignment.htf}/{assignment.ltf}</span>
            </div>
            <div className="assignment-meta mt-2">Risque {assignment.risk_pct}% | Max {assignment.max_trades_per_day}/jour</div>
          </button>
        ))}
      </div>
    </div>
  );
};

export default AssignmentSelector;
