interface DashboardHeaderProps {
  username: string;
  headerLabel: string;
  authError: string | null;
  onLogout: () => void;
}

const DashboardHeader = ({ username, headerLabel, authError, onLogout }: DashboardHeaderProps) => {
  return (
    <>
      <div className="dashboard-hero mb-4">
        <div className="dashboard-hero__content">
          <div className="dashboard-hero__eyebrow">Trading cockpit</div>
          <h1 className="dashboard-hero__title">Market Operations Console</h1>
          <p className="dashboard-hero__subtitle">{headerLabel}</p>
        </div>
        <div className="dashboard-hero__actions">
          <div className="dashboard-user-chip">
            <span className="dashboard-user-chip__label">Session</span>
            <strong>{username}</strong>
          </div>
          <button type="button" className="btn btn-outline-light btn-sm dashboard-ghost-button" onClick={onLogout}>
            Deconnexion
          </button>
        </div>
      </div>

      {authError && <div className="alert alert-warning dashboard-alert">{authError}</div>}
    </>
  );
};

export default DashboardHeader;
