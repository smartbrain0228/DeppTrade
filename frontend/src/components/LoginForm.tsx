import { FormEvent, useState } from "react";

interface LoginFormProps {
  isLoading: boolean;
  error: string | null;
  onSubmit: (username: string, password: string) => Promise<void>;
}

const LoginForm = ({ isLoading, error, onSubmit }: LoginFormProps) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await onSubmit(username, password);
  };

  return (
    <div className="auth-shell">
      <div className="auth-stage" />
      <div className="auth-card">
        <div className="auth-card__intro mb-4">
          <div className="auth-card__eyebrow">Bot Trading Copilot</div>
          <h1 className="h3 fw-bold mb-2">Connexion</h1>
          <p className="text-muted mb-0">
            Connecte-toi pour charger tes assignments, tes signaux et les overlays du chart.
          </p>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="mb-3 text-start">
            <label className="form-label">Email ou username</label>
            <input
              className="form-control auth-input"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="admin@example.com"
              required
            />
          </div>
          <div className="mb-3 text-start">
            <label className="form-label">Mot de passe</label>
            <input
              className="form-control auth-input"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="********"
              required
            />
          </div>
          {error && <div className="alert alert-danger py-2 dashboard-alert">{error}</div>}
          <button className="btn btn-primary w-100 auth-submit" type="submit" disabled={isLoading}>
            {isLoading ? "Connexion..." : "Se connecter"}
          </button>
        </form>
      </div>
    </div>
  );
};

export default LoginForm;
