import { PairStrategyAssignment } from "../types/trading";

interface SymbolStrategyTabsProps {
  assignments: PairStrategyAssignment[];
  selectedAssignmentId: number | null;
  onSelect: (assignmentId: number) => void;
}

const SymbolStrategyTabs = ({ assignments, selectedAssignmentId, onSelect }: SymbolStrategyTabsProps) => {
  if (assignments.length <= 1) {
    return null;
  }

  return (
    <div className="strategy-tabs">
      <div className="strategy-tabs__label">Setups disponibles</div>
      <div className="strategy-tabs__list">
        {assignments.map((assignment) => {
          const isSelected = assignment.id === selectedAssignmentId;
          return (
            <button
              key={assignment.id}
              type="button"
              className={`strategy-tab ${isSelected ? "is-selected" : ""}`}
              onClick={() => onSelect(assignment.id)}
            >
              <span className="strategy-tab__title">{assignment.strategy_name}</span>
              <span className="strategy-tab__meta">
                {assignment.htf}/{assignment.ltf}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default SymbolStrategyTabs;
