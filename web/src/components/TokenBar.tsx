import { useAuth } from "@/hooks/useAuth";

export function TokenBar() {
  const { token, setToken, clearToken, isAuthenticated } = useAuth();

  return (
    <div className="token-bar">
      <label htmlFor="api-token">Bearer token</label>
      <input
        id="api-token"
        name="api-token"
        type="password"
        autoComplete="off"
        spellCheck={false}
        placeholder="API_TOKEN…"
        value={token}
        onChange={(e) => setToken(e.target.value)}
        aria-describedby="token-hint"
      />
      {isAuthenticated ? (
        <button type="button" className="btn btn-ghost" onClick={clearToken}>
          Clear Token
        </button>
      ) : null}
      <span id="token-hint" className="live-region">
        Stocké en sessionStorage uniquement.
      </span>
    </div>
  );
}
