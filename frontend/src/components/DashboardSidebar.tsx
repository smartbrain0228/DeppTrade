import AssignmentSelector from "./AssignmentSelector";
import CryptoList from "./CryptoList";
import OverviewPanel from "./OverviewPanel";
import { UserOverview } from "../types/trading";

interface DashboardSidebarProps {
  overview: UserOverview | null;
  isOverviewLoading: boolean;
  overviewError: string | null;
  lastOverviewUpdatedAt?: number | null;
  overviewWasRefreshedByAction?: boolean;
  onRefreshOverview: () => Promise<void>;
}

const DashboardSidebar = ({
  overview,
  isOverviewLoading,
  overviewError,
  lastOverviewUpdatedAt,
  overviewWasRefreshedByAction,
  onRefreshOverview
}: DashboardSidebarProps) => {
  return (
    <div className="col-lg-4 d-grid gap-4">
      <OverviewPanel
        isLoading={isOverviewLoading}
        error={overviewError}
        overview={overview}
        lastUpdatedAt={lastOverviewUpdatedAt}
        wasRefreshedByAction={overviewWasRefreshedByAction}
        onRefresh={onRefreshOverview}
      />
      <div className="sidebar-panel card">
        <div className="card-body">
          <AssignmentSelector />
        </div>
      </div>
      <div className="sidebar-panel card h-100">
        <div className="card-body">
          <div className="panel-heading mb-3">
            <span className="panel-heading__eyebrow">Watchlist</span>
            <h3 className="h6 fw-bold mb-0">Cryptos populaires</h3>
          </div>
          <CryptoList />
        </div>
      </div>
    </div>
  );
};

export default DashboardSidebar;
