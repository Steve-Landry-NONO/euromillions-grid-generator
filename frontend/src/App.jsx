/**
 * EuroMillions Grid Generator — Frontend React
 * =============================================
 * Stack     : React + hooks (useState, useEffect, useCallback)
 * Style     : Tailwind (classes utilitaires) + CSS-in-JS inline pour les détails fins
 * Aesthetic : Dark luxury / lottery editorial
 *             Fond quasi-noir · Typographie serif · Accent or/ambre · Jetons premium
 *
 * COMPOSANTS :
 *   <App />              — racine, gestion état global
 *   <Header />           — titre + disclaimer bandeau
 *   <ModelCard />        — carte de sélection du modèle
 *   <GenerateControls /> — nombre de grilles + options avancées
 *   <TicketList />       — liste des grilles générées
 *   <TicketCard />       — une grille individuelle (numéros + étoiles + score)
 *   <ExportButtons />    — copier / exporter CSV
 *   <DisclaimerFooter /> — mentions légales
 *
 * API CLIENT :
 *   Toutes les fonctions fetch() sont regroupées dans apiClient
 *   → facile à brancher sur le vrai backend FastAPI
 */

import { useState, useCallback, useEffect, useRef } from "react";

// ─────────────────────────────────────────────────────────────
// CONFIGURATION API
// Pour pointer sur le vrai backend : changer BASE_URL
// ─────────────────────────────────────────────────────────────
const BASE_URL = "http://localhost:8000/api/v1";

// ─────────────────────────────────────────────────────────────
// DONNÉES MOCK — utilisées quand le backend n'est pas disponible
// Reproduisent exactement le format de réponse de l'API FastAPI
// ─────────────────────────────────────────────────────────────
const MOCK_MODELS = [
  {
    model_id: "oraclestats_v1",
    name: "OracleStats",
    type: "Science",
    short_description: "Approche probabiliste basée sur l'historique",
    what_it_does:
      "Analyse les tirages passés pour construire une distribution de probabilités, puis génère des grilles par échantillonnage pondéré.",
    what_it_does_not:
      "Ne prédit pas les numéros gagnants. N'augmente pas la probabilité de gagner.",
    disclaimer:
      "Approche expérimentale — aucune garantie de gain. EuroMillions reste un jeu de hasard indépendant.",
  },
  {
    model_id: "smartgrid_v1",
    name: "SmartGrid",
    type: "Optimiseur",
    short_description: "Anti-partage & diversification",
    what_it_does:
      "Génère des grilles moins « humaines » (anti-dates, anti-motifs) afin de réduire le risque de partager un gain si vous gagnez.",
    what_it_does_not:
      "N'essaie pas de prédire le tirage. N'augmente pas la probabilité de gagner.",
    disclaimer:
      "Optimise la rareté humaine / anti-partage, pas la probabilité de gagner.",
  },
];

function generateMockTicket(modelId, index) {
  const pick = (arr, n) => {
    const shuffled = [...arr].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, n).sort((a, b) => a - b);
  };
  const nums = pick(Array.from({ length: 50 }, (_, i) => i + 1), 5);
  const stars = pick(Array.from({ length: 12 }, (_, i) => i + 1), 2);
  const score = modelId === "smartgrid_v1" ? +(0.75 + Math.random() * 0.2).toFixed(3) : null;
  const reasons = ["Peu de numéros ≤31", "Pas de suite", "Bonne dispersion", "Bien diversifiée"];
  return {
    numbers: nums,
    stars,
    score,
    explanation: modelId === "smartgrid_v1"
      ? reasons.slice(0, 2 + (index % 2)).join(" · ")
      : "Basé sur l'historique + lissage, puis tirage pondéré sans doublons.",
    explain: modelId === "smartgrid_v1" ? {
      penalty_dates: +(Math.random() * 0.1).toFixed(3),
      penalty_sequence: 0,
      bonus_diversity: +(Math.random() * 0.1).toFixed(3),
    } : null,
  };
}

function generateMockResponse(modelId, nTickets) {
  const today = new Date();
  const daysUntilFriday = (5 - today.getDay() + 7) % 7 || 7;
  const nextFriday = new Date(today);
  nextFriday.setDate(today.getDate() + daysUntilFriday);
  const isoDate = nextFriday.toISOString().split("T")[0];
  const label = nextFriday.toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long", year: "numeric" });

  return {
    model_id: modelId,
    model_name: modelId === "oraclestats_v1" ? "OracleStats (Science)" : "SmartGrid (Optimiseur)",
    draw_target: { date: isoDate, mode: "friday_only", label },
    n_tickets: nTickets,
    tickets: Array.from({ length: nTickets }, (_, i) => generateMockTicket(modelId, i)),
    generation_time_ms: 80 + Math.random() * 200,
    disclaimer:
      modelId === "oraclestats_v1"
        ? "OracleStats produit une distribution de probabilités à partir de l'historique. Aucune garantie de gain."
        : "SmartGrid optimise la rareté humaine / anti-partage, pas la probabilité de gagner.",
  };
}

// ─────────────────────────────────────────────────────────────
// API CLIENT
// ─────────────────────────────────────────────────────────────
const apiClient = {
  async getModels() {
    try {
      const res = await fetch(`${BASE_URL}/models`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      return data.models;
    } catch {
      return MOCK_MODELS;
    }
  },

  async getNextDraw() {
    try {
      const res = await fetch(`${BASE_URL}/draws/next?mode=friday_only`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      return data.draw_target;
    } catch {
      const today = new Date();
      const daysUntilFriday = (5 - today.getDay() + 7) % 7 || 7;
      const nextFriday = new Date(today);
      nextFriday.setDate(today.getDate() + daysUntilFriday);
      return {
        date: nextFriday.toISOString().split("T")[0],
        label: nextFriday.toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long", year: "numeric" }),
      };
    }
  },

  async generate(modelId, nTickets, options = {}) {
    try {
      const res = await fetch(`${BASE_URL}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_id: modelId, n_tickets: nTickets, mode: "friday_only", options }),
      });
      if (!res.ok) throw new Error();
      return await res.json();
    } catch {
      await new Promise((r) => setTimeout(r, 600 + Math.random() * 400));
      return generateMockResponse(modelId, nTickets);
    }
  },
};

// ─────────────────────────────────────────────────────────────
// STYLES GLOBAUX (injectés une fois dans <head>)
// ─────────────────────────────────────────────────────────────
const GLOBAL_CSS = `
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400&family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500&display=swap');

  :root {
    --bg:          #0c0c0e;
    --surface:     #131316;
    --surface2:    #1a1a1f;
    --border:      #2a2a32;
    --border-warm: #3a3520;
    --gold:        #c9a84c;
    --gold-light:  #e8c97a;
    --gold-dim:    #8a6e2a;
    --text:        #e8e4dc;
    --text-muted:  #7a7670;
    --text-dim:    #4a4842;
    --star:        #e8b84b;
    --accent-blue: #4a7fa8;
    --danger:      #c25a3a;
    --success:     #4a8c5c;
    --font-serif:  'Playfair Display', Georgia, serif;
    --font-mono:   'DM Mono', 'Courier New', monospace;
    --font-sans:   'DM Sans', system-ui, sans-serif;
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--font-sans);
    font-size: 15px;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }

  /* Grain overlay */
  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
    pointer-events: none;
    z-index: 9999;
    opacity: 0.35;
  }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-track { background: var(--bg); }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

  /* Animations */
  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  @keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
  }
  @keyframes spinOnce {
    from { transform: rotate(0deg); }
    to   { transform: rotate(360deg); }
  }
  @keyframes shimmer {
    0%   { background-position: -200% center; }
    100% { background-position: 200% center; }
  }
  @keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 0 0 rgba(201,168,76,0); }
    50%       { box-shadow: 0 0 18px 4px rgba(201,168,76,0.18); }
  }
  @keyframes ballDrop {
    0%   { opacity: 0; transform: translateY(-12px) scale(0.7); }
    60%  { transform: translateY(2px) scale(1.05); }
    100% { opacity: 1; transform: translateY(0) scale(1); }
  }
  @keyframes scoreBar {
    from { width: 0; }
  }

  .fade-up { animation: fadeUp 0.45s cubic-bezier(.22,1,.36,1) both; }
  .fade-in { animation: fadeIn 0.3s ease both; }

  /* Number ball */
  .ball {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    font-family: var(--font-mono);
    font-size: 13px;
    font-weight: 500;
    letter-spacing: -0.5px;
    transition: transform 0.18s ease, box-shadow 0.18s ease;
    animation: ballDrop 0.35s cubic-bezier(.22,1,.36,1) both;
  }
  .ball:hover {
    transform: scale(1.12);
    box-shadow: 0 4px 18px rgba(201,168,76,0.25);
  }
  .ball-num {
    background: linear-gradient(135deg, #1e1e26, #2a2a36);
    border: 1px solid var(--border);
    color: var(--text);
  }
  .ball-star {
    background: linear-gradient(135deg, #2a2010, #3a3018);
    border: 1px solid var(--border-warm);
    color: var(--star);
  }

  /* Card */
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    transition: border-color 0.2s, box-shadow 0.2s;
  }
  .card:hover { border-color: #3a3a46; }
  .card.selected {
    border-color: var(--gold-dim);
    box-shadow: 0 0 0 1px var(--gold-dim), inset 0 0 40px rgba(201,168,76,0.04);
  }

  /* Button primary */
  .btn-primary {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 12px 28px;
    background: linear-gradient(135deg, #b8922e, #c9a84c, #b8922e);
    background-size: 200% auto;
    color: #0c0c0e;
    font-family: var(--font-sans);
    font-size: 14px;
    font-weight: 500;
    letter-spacing: 0.04em;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: background-position 0.4s ease, transform 0.15s ease, box-shadow 0.2s;
  }
  .btn-primary:hover {
    background-position: right center;
    box-shadow: 0 4px 24px rgba(201,168,76,0.3);
    transform: translateY(-1px);
  }
  .btn-primary:active { transform: translateY(0); }
  .btn-primary:disabled {
    opacity: 0.4;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
  }

  /* Button ghost */
  .btn-ghost {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    background: transparent;
    color: var(--text-muted);
    font-family: var(--font-sans);
    font-size: 13px;
    border: 1px solid var(--border);
    border-radius: 7px;
    cursor: pointer;
    transition: all 0.18s ease;
  }
  .btn-ghost:hover {
    color: var(--gold-light);
    border-color: var(--gold-dim);
    background: rgba(201,168,76,0.06);
  }

  /* Divider */
  .divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--border), transparent);
  }

  /* Tag */
  .tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-family: var(--font-mono);
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .tag-science { background: rgba(74,127,168,0.15); color: var(--accent-blue); border: 1px solid rgba(74,127,168,0.25); }
  .tag-optimizer { background: rgba(201,168,76,0.12); color: var(--gold); border: 1px solid rgba(201,168,76,0.2); }

  /* Score bar */
  .score-bar-track {
    height: 3px;
    background: var(--border);
    border-radius: 2px;
    overflow: hidden;
  }
  .score-bar-fill {
    height: 100%;
    border-radius: 2px;
    animation: scoreBar 0.8s cubic-bezier(.22,1,.36,1) both 0.3s;
  }

  /* Toast */
  .toast {
    position: fixed;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%) translateY(0);
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--text);
    font-size: 13px;
    padding: 10px 20px;
    border-radius: 100px;
    animation: fadeUp 0.3s ease both;
    z-index: 1000;
    white-space: nowrap;
  }

  /* Loading spinner */
  .spinner {
    width: 20px; height: 20px;
    border: 2px solid rgba(201,168,76,0.2);
    border-top-color: var(--gold);
    border-radius: 50%;
    animation: spinOnce 0.7s linear infinite;
    display: inline-block;
  }

  /* Shimmer loading state */
  .shimmer {
    background: linear-gradient(90deg, var(--surface) 25%, var(--surface2) 50%, var(--surface) 75%);
    background-size: 200% auto;
    animation: shimmer 1.4s linear infinite;
    border-radius: 8px;
  }

  /* n-ticket selector */
  .ticket-count-btn {
    padding: 8px 20px;
    background: transparent;
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 15px;
    border: 1px solid var(--border);
    border-radius: 7px;
    cursor: pointer;
    transition: all 0.15s;
  }
  .ticket-count-btn:hover { border-color: var(--gold-dim); color: var(--gold); }
  .ticket-count-btn.active {
    background: rgba(201,168,76,0.1);
    border-color: var(--gold);
    color: var(--gold-light);
  }
`;

function injectStyles() {
  if (document.getElementById("em-styles")) return;
  const el = document.createElement("style");
  el.id = "em-styles";
  el.textContent = GLOBAL_CSS;
  document.head.appendChild(el);
}

// ─────────────────────────────────────────────────────────────
// COMPOSANT : Toast notification
// ─────────────────────────────────────────────────────────────
function Toast({ message, onDone }) {
  useEffect(() => {
    const t = setTimeout(onDone, 2200);
    return () => clearTimeout(t);
  }, [onDone]);
  return <div className="toast">✓ {message}</div>;
}

// ─────────────────────────────────────────────────────────────
// COMPOSANT : Header
// ─────────────────────────────────────────────────────────────
function Header({ drawTarget }) {
  return (
    <header style={{ padding: "48px 0 36px", textAlign: "center" }} className="fade-up">
      {/* Overline */}
      <div style={{
        fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: "0.18em",
        color: "var(--gold-dim)", textTransform: "uppercase", marginBottom: 16,
      }}>
        Générateur de grilles
      </div>

      {/* Main title */}
      <h1 style={{
        fontFamily: "var(--font-serif)", fontSize: "clamp(32px, 5vw, 52px)",
        fontWeight: 700, color: "var(--text)", lineHeight: 1.1, letterSpacing: "-0.5px",
        marginBottom: 12,
      }}>
        Euro<span style={{ color: "var(--gold)" }}>Millions</span>
      </h1>

      {/* Subtitle */}
      <p style={{ color: "var(--text-muted)", fontSize: 14, maxWidth: 420, margin: "0 auto 20px", lineHeight: 1.7 }}>
        Deux approches, zéro promesse. Une science des probabilités,
        une optimisation anti‑partage.
      </p>

      {/* Draw target pill */}
      {drawTarget && (
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 8,
          padding: "6px 16px", background: "rgba(201,168,76,0.08)",
          border: "1px solid var(--border-warm)", borderRadius: 100,
          fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--gold)",
          letterSpacing: "0.04em",
        }}>
          <span style={{ opacity: 0.6 }}>◈</span>
          Prochain tirage — {drawTarget.label}
        </div>
      )}

      {/* Thin gold rule */}
      <div style={{
        width: 60, height: 1, background: "var(--gold-dim)",
        margin: "28px auto 0", opacity: 0.5,
      }} />
    </header>
  );
}

// ─────────────────────────────────────────────────────────────
// COMPOSANT : ModelCard
// ─────────────────────────────────────────────────────────────
function ModelCard({ model, selected, onSelect }) {
  const isOracle = model.model_id === "oraclestats_v1";
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`card ${selected ? "selected" : ""}`}
      style={{ padding: "24px 28px", cursor: "pointer", position: "relative", overflow: "hidden" }}
      onClick={() => onSelect(model.model_id)}
    >
      {/* Selected indicator line */}
      {selected && (
        <div style={{
          position: "absolute", top: 0, left: 0, right: 0,
          height: 2, background: "linear-gradient(90deg, transparent, var(--gold), transparent)",
        }} />
      )}

      {/* Top row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 14 }}>
        <div>
          <span className={`tag ${isOracle ? "tag-science" : "tag-optimizer"}`}>
            {model.type}
          </span>
          <h2 style={{
            fontFamily: "var(--font-serif)", fontSize: 22, fontWeight: 600,
            color: "var(--text)", marginTop: 8, letterSpacing: "-0.3px",
          }}>
            {model.name}
          </h2>
        </div>

        {/* Selection radio */}
        <div style={{
          width: 20, height: 20, borderRadius: "50%", flexShrink: 0, marginTop: 4,
          border: `2px solid ${selected ? "var(--gold)" : "var(--border)"}`,
          background: selected ? "var(--gold)" : "transparent",
          transition: "all 0.2s ease",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          {selected && <div style={{ width: 7, height: 7, borderRadius: "50%", background: "#0c0c0e" }} />}
        </div>
      </div>

      {/* Short description */}
      <p style={{ color: "var(--text-muted)", fontSize: 13.5, lineHeight: 1.65, marginBottom: 14 }}>
        {model.short_description}
      </p>

      {/* Expand toggle */}
      <button
        className="btn-ghost"
        style={{ fontSize: 12, padding: "5px 10px" }}
        onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
      >
        {expanded ? "▲ Réduire" : "▾ Comment ça marche"}
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="fade-in" style={{
          marginTop: 16, paddingTop: 16,
          borderTop: "1px solid var(--border)",
        }}>
          <div style={{ marginBottom: 10 }}>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: "0.12em", color: "var(--gold-dim)", marginBottom: 6, textTransform: "uppercase" }}>Ce que fait ce modèle</div>
            <p style={{ fontSize: 13, color: "var(--text-muted)", lineHeight: 1.65 }}>{model.what_it_does}</p>
          </div>
          <div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: "0.12em", color: "var(--text-dim)", marginBottom: 6, textTransform: "uppercase" }}>Ce qu'il ne fait pas</div>
            <p style={{ fontSize: 13, color: "var(--text-dim)", lineHeight: 1.65 }}>{model.what_it_does_not}</p>
          </div>
        </div>
      )}

      {/* Disclaimer badge */}
      <div style={{
        marginTop: 16, padding: "8px 12px",
        background: "rgba(255,255,255,0.025)", borderRadius: 6,
        borderLeft: "2px solid var(--border)",
        fontSize: 12, color: "var(--text-dim)", lineHeight: 1.55,
        fontStyle: "italic",
      }}>
        {model.disclaimer}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// COMPOSANT : GenerateControls
// ─────────────────────────────────────────────────────────────
function GenerateControls({ selectedModel, onGenerate, loading }) {
  const [nTickets, setNTickets] = useState(5);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [seed, setSeed] = useState("");

  const handleGenerate = () => {
    const options = {};
    if (seed) options.seed = parseInt(seed, 10);
    onGenerate(nTickets, options);
  };

  return (
    <div className="card" style={{ padding: "24px 28px" }}>
      <div style={{ marginBottom: 20 }}>
        <div style={{
          fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: "0.12em",
          color: "var(--text-dim)", textTransform: "uppercase", marginBottom: 12,
        }}>
          Nombre de grilles
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {[1, 5, 10].map((n) => (
            <button
              key={n}
              className={`ticket-count-btn ${nTickets === n ? "active" : ""}`}
              onClick={() => setNTickets(n)}
            >
              {n}
            </button>
          ))}
        </div>
      </div>

      {/* Advanced options toggle */}
      <button
        className="btn-ghost"
        style={{ fontSize: 12, marginBottom: showAdvanced ? 16 : 0 }}
        onClick={() => setShowAdvanced(!showAdvanced)}
      >
        {showAdvanced ? "▲" : "▾"} Options avancées
      </button>

      {showAdvanced && (
        <div className="fade-in" style={{ paddingTop: 16, borderTop: "1px solid var(--border)" }}>
          <label style={{ display: "block", marginBottom: 16 }}>
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 6, fontFamily: "var(--font-mono)", letterSpacing: "0.06em" }}>
              Graine aléatoire (seed)
            </div>
            <input
              type="number"
              value={seed}
              onChange={(e) => setSeed(e.target.value)}
              placeholder="ex: 42 (pour reproductibilité)"
              style={{
                width: "100%", padding: "9px 14px",
                background: "var(--surface2)", border: "1px solid var(--border)",
                borderRadius: 7, color: "var(--text)", fontSize: 13,
                fontFamily: "var(--font-mono)", outline: "none",
              }}
            />
          </label>
        </div>
      )}

      {/* Generate button */}
      <div style={{ marginTop: 20 }}>
        <button
          className="btn-primary"
          style={{ width: "100%", fontSize: 15, padding: "14px 28px" }}
          onClick={handleGenerate}
          disabled={!selectedModel || loading}
        >
          {loading ? (
            <><span className="spinner" style={{ width: 16, height: 16 }} /> Génération en cours…</>
          ) : (
            selectedModel ? `Générer ${nTickets} grille${nTickets > 1 ? "s" : ""}` : "Choisissez un modèle"
          )}
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// COMPOSANT : TicketCard
// ─────────────────────────────────────────────────────────────
function TicketCard({ ticket, index, modelId }) {
  const [showDetails, setShowDetails] = useState(false);
  const isSmartGrid = modelId === "smartgrid_v1";
  const animDelay = `${index * 80}ms`;

  const scoreColor = ticket.score
    ? ticket.score >= 0.9 ? "var(--success)"
    : ticket.score >= 0.7 ? "var(--gold)"
    : "var(--text-muted)"
    : null;

  return (
    <div
      className="card fade-up"
      style={{
        padding: "20px 24px",
        animationDelay: animDelay,
        animationFillMode: "both",
      }}
    >
      {/* Ticket header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div style={{
          fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-dim)",
          letterSpacing: "0.1em", textTransform: "uppercase",
        }}>
          Grille {String(index + 1).padStart(2, "0")}
        </div>

        {/* Score badge (SmartGrid only) */}
        {isSmartGrid && ticket.score != null && (
          <div style={{
            fontFamily: "var(--font-mono)", fontSize: 12,
            color: scoreColor, letterSpacing: "0.04em",
          }}>
            Score anti-partage <span style={{ fontSize: 14, fontWeight: 500 }}>{ticket.score.toFixed(2)}</span>
          </div>
        )}
      </div>

      {/* Score bar (SmartGrid) */}
      {isSmartGrid && ticket.score != null && (
        <div className="score-bar-track" style={{ marginBottom: 16 }}>
          <div
            className="score-bar-fill"
            style={{
              width: `${ticket.score * 100}%`,
              background: `linear-gradient(90deg, var(--gold-dim), ${scoreColor})`,
              animationDelay: `${index * 80 + 200}ms`,
            }}
          />
        </div>
      )}

      {/* Numbers */}
      <div style={{ marginBottom: 12 }}>
        <div style={{
          fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: "0.12em",
          color: "var(--text-dim)", textTransform: "uppercase", marginBottom: 10,
        }}>
          Numéros
        </div>
        <div style={{ display: "flex", gap: 7, flexWrap: "wrap" }}>
          {ticket.numbers.map((n, i) => (
            <div
              key={i}
              className="ball ball-num"
              style={{ animationDelay: `${index * 80 + i * 50}ms` }}
            >
              {String(n).padStart(2, "0")}
            </div>
          ))}
        </div>
      </div>

      {/* Stars */}
      <div style={{ marginBottom: 14 }}>
        <div style={{
          fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: "0.12em",
          color: "var(--text-dim)", textTransform: "uppercase", marginBottom: 10,
        }}>
          Étoiles
        </div>
        <div style={{ display: "flex", gap: 7 }}>
          {ticket.stars.map((s, i) => (
            <div
              key={i}
              className="ball ball-star"
              style={{ animationDelay: `${index * 80 + (5 + i) * 50}ms` }}
            >
              ★ {s}
            </div>
          ))}
        </div>
      </div>

      {/* Explanation */}
      {ticket.explanation && (
        <div style={{ fontSize: 12, color: "var(--text-dim)", lineHeight: 1.6, fontStyle: "italic" }}>
          {ticket.explanation}
        </div>
      )}

      {/* Details toggle (SmartGrid) */}
      {isSmartGrid && ticket.explain && (
        <>
          <button
            className="btn-ghost"
            style={{ fontSize: 11, marginTop: 10, padding: "4px 8px" }}
            onClick={() => setShowDetails(!showDetails)}
          >
            {showDetails ? "▲ Masquer" : "▾ Détails du score"}
          </button>

          {showDetails && (
            <div className="fade-in" style={{
              marginTop: 12, padding: "12px 14px",
              background: "rgba(255,255,255,0.02)", borderRadius: 7,
              border: "1px solid var(--border)",
            }}>
              {Object.entries(ticket.explain).map(([key, val]) => {
                const label = key
                  .replace("penalty_", "Pénalité ")
                  .replace("bonus_", "Bonus ")
                  .replace(/_/g, " ");
                const isBonus = key.startsWith("bonus");
                return (
                  <div key={key} style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, fontSize: 12 }}>
                    <span style={{ color: "var(--text-dim)", textTransform: "capitalize" }}>{label}</span>
                    <span style={{
                      fontFamily: "var(--font-mono)",
                      color: isBonus ? "var(--success)" : val > 0.05 ? "var(--danger)" : "var(--text-muted)",
                    }}>
                      {isBonus ? "+" : ""}{val.toFixed(3)}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// COMPOSANT : ExportButtons
// ─────────────────────────────────────────────────────────────
function ExportButtons({ response, onToast }) {
  const formatTicketText = (t) =>
    `${t.numbers.map((n) => String(n).padStart(2, "0")).join(" ")} + ${t.stars.map((s) => String(s).padStart(2, "0")).join(" ")}`;

  const handleCopy = useCallback(() => {
    const lines = [
      `EuroMillions — ${response.model_name}`,
      `Tirage cible : ${response.draw_target.label}`,
      `Généré le : ${new Date().toLocaleDateString("fr-FR")}`,
      "",
      ...response.tickets.map((t, i) =>
        `Grille ${String(i + 1).padStart(2, "0")} : ${formatTicketText(t)}${t.score != null ? `  [score: ${t.score.toFixed(3)}]` : ""}`
      ),
      "",
      response.disclaimer,
    ];
    navigator.clipboard.writeText(lines.join("\n")).then(() => onToast("Copié dans le presse-papiers"));
  }, [response, onToast]);

  const handleExportCSV = useCallback(() => {
    const headers = ["grille", "n1", "n2", "n3", "n4", "n5", "s1", "s2", "score", "tirage_cible", "modele"];
    const rows = response.tickets.map((t, i) => [
      i + 1,
      ...t.numbers,
      ...t.stars,
      t.score ?? "",
      response.draw_target.date,
      response.model_id,
    ]);
    const csv = [headers, ...rows].map((r) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `euromillions_${response.model_id}_${response.draw_target.date}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    onToast("CSV téléchargé");
  }, [response, onToast]);

  return (
    <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
      <button className="btn-ghost" onClick={handleCopy} style={{ flex: 1, justifyContent: "center" }}>
        <span>⎘</span> Copier
      </button>
      <button className="btn-ghost" onClick={handleExportCSV} style={{ flex: 1, justifyContent: "center" }}>
        <span>↓</span> Exporter CSV
      </button>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// COMPOSANT : TicketList
// ─────────────────────────────────────────────────────────────
function TicketList({ response, onToast, onRegenerate, loading }) {
  if (!response) return null;

  return (
    <section className="fade-up" style={{ marginTop: 40 }}>
      {/* Section header */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        marginBottom: 20,
      }}>
        <div>
          <div style={{
            fontFamily: "var(--font-mono)", fontSize: 10,
            color: "var(--text-dim)", letterSpacing: "0.12em",
            textTransform: "uppercase", marginBottom: 4,
          }}>
            {response.model_name} · {response.draw_target.label}
          </div>
          <h2 style={{
            fontFamily: "var(--font-serif)", fontSize: 20, fontWeight: 600,
            color: "var(--text)",
          }}>
            {response.n_tickets} grille{response.n_tickets > 1 ? "s" : ""} générée{response.n_tickets > 1 ? "s" : ""}
            <span style={{
              fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-dim)",
              marginLeft: 10, fontWeight: 400,
            }}>
              ({response.generation_time_ms.toFixed(0)} ms)
            </span>
          </h2>
        </div>

        <button className="btn-ghost" onClick={onRegenerate} disabled={loading} style={{ flexShrink: 0 }}>
          {loading ? <span className="spinner" style={{ width: 14, height: 14 }} /> : "↺"} Regénérer
        </button>
      </div>

      {/* Ticket grid */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
        gap: 14,
        marginBottom: 20,
      }}>
        {response.tickets.map((ticket, i) => (
          <TicketCard
            key={i}
            ticket={ticket}
            index={i}
            modelId={response.model_id}
          />
        ))}
      </div>

      {/* Export row */}
      <ExportButtons response={response} onToast={onToast} />

      {/* Disclaimer */}
      <div style={{
        marginTop: 20, padding: "14px 18px",
        background: "rgba(255,255,255,0.02)",
        border: "1px solid var(--border)",
        borderRadius: 8, fontSize: 12,
        color: "var(--text-dim)", lineHeight: 1.65, fontStyle: "italic",
      }}>
        ⚠ {response.disclaimer}
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────
// COMPOSANT : LoadingSkeletons
// ─────────────────────────────────────────────────────────────
function LoadingSkeletons({ count }) {
  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
      gap: 14, marginTop: 40,
    }}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card" style={{ padding: 24 }}>
          <div className="shimmer" style={{ height: 12, width: "40%", marginBottom: 20 }} />
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            {Array.from({ length: 5 }).map((_, j) => (
              <div key={j} className="shimmer" style={{ width: 40, height: 40, borderRadius: "50%" }} />
            ))}
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {Array.from({ length: 2 }).map((_, j) => (
              <div key={j} className="shimmer" style={{ width: 40, height: 40, borderRadius: "50%" }} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// COMPOSANT : DisclaimerFooter
// ─────────────────────────────────────────────────────────────
function DisclaimerFooter() {
  return (
    <footer style={{
      marginTop: 80, paddingTop: 28, paddingBottom: 40,
      borderTop: "1px solid var(--border)",
      textAlign: "center",
    }}>
      <div style={{ display: "flex", justifyContent: "center", gap: 24, marginBottom: 12, flexWrap: "wrap" }}>
        {["À propos & limites", "Jeu responsable", "Confidentialité"].map((label) => (
          <a key={label} href="#" style={{
            fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: "0.06em",
            color: "var(--text-dim)", textDecoration: "none",
            transition: "color 0.15s",
          }}
          onMouseEnter={(e) => e.target.style.color = "var(--gold)"}
          onMouseLeave={(e) => e.target.style.color = "var(--text-dim)"}
          >
            {label}
          </a>
        ))}
      </div>
      <p style={{ fontSize: 12, color: "var(--text-dim)", lineHeight: 1.7, maxWidth: 500, margin: "0 auto" }}>
        EuroMillions est un jeu de hasard. Les résultats sont aléatoires et indépendants.
        Cette application génère des grilles à titre informatif/pédagogique
        et n'offre <strong style={{ fontWeight: 500 }}>aucune garantie de gain</strong>.
        Jouez avec modération.
      </p>
      <div style={{
        marginTop: 20, fontFamily: "var(--font-mono)", fontSize: 10,
        color: "var(--text-dim)", letterSpacing: "0.08em", opacity: 0.5,
      }}>
        MVP v1.0 · OracleStats & SmartGrid
      </div>
    </footer>
  );
}

// ─────────────────────────────────────────────────────────────
// COMPOSANT RACINE : App
// ─────────────────────────────────────────────────────────────
export default function App() {
  injectStyles();

  const [models, setModels] = useState([]);
  const [selectedModelId, setSelectedModelId] = useState(null);
  const [drawTarget, setDrawTarget] = useState(null);
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);
  const [lastRequest, setLastRequest] = useState(null);
  const [pendingCount, setPendingCount] = useState(5);
  const resultsRef = useRef(null);

  // Chargement initial des modèles + date
  useEffect(() => {
    Promise.all([apiClient.getModels(), apiClient.getNextDraw()]).then(([m, d]) => {
      setModels(m);
      setDrawTarget(d);
    });
  }, []);

  const handleGenerate = useCallback(async (nTickets, options) => {
    if (!selectedModelId) return;
    setPendingCount(nTickets);
    setLoading(true);
    const req = { modelId: selectedModelId, nTickets, options };
    setLastRequest(req);

    try {
      const res = await apiClient.generate(selectedModelId, nTickets, options);
      setResponse(res);
      setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 100);
    } finally {
      setLoading(false);
    }
  }, [selectedModelId]);

  const handleRegenerate = useCallback(() => {
    if (!lastRequest) return;
    handleGenerate(lastRequest.nTickets, lastRequest.options);
  }, [lastRequest, handleGenerate]);

  const showToast = useCallback((msg) => setToast(msg), []);

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)" }}>
      <div style={{ maxWidth: 860, margin: "0 auto", padding: "0 20px" }}>

        <Header drawTarget={drawTarget} />

        {/* Model selection */}
        <section style={{ marginBottom: 28 }}>
          <div style={{
            fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: "0.16em",
            color: "var(--text-dim)", textTransform: "uppercase", marginBottom: 14,
          }}>
            01 — Choisissez un modèle
          </div>
          {models.length === 0 ? (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
              {[0, 1].map((i) => (
                <div key={i} className="card shimmer" style={{ height: 160 }} />
              ))}
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 14 }}>
              {models.map((m) => (
                <ModelCard
                  key={m.model_id}
                  model={m}
                  selected={selectedModelId === m.model_id}
                  onSelect={setSelectedModelId}
                />
              ))}
            </div>
          )}
        </section>

        <div className="divider" style={{ marginBottom: 28 }} />

        {/* Generate controls */}
        <section style={{ marginBottom: 8 }}>
          <div style={{
            fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: "0.16em",
            color: "var(--text-dim)", textTransform: "uppercase", marginBottom: 14,
          }}>
            02 — Générez vos grilles
          </div>
          <GenerateControls
            selectedModel={selectedModelId}
            onGenerate={handleGenerate}
            loading={loading}
          />
        </section>

        {/* Results */}
        <div ref={resultsRef}>
          {loading && !response && <LoadingSkeletons count={pendingCount} />}
          {loading && response && <LoadingSkeletons count={pendingCount} />}
          {!loading && response && (
            <TicketList
              response={response}
              onToast={showToast}
              onRegenerate={handleRegenerate}
              loading={loading}
            />
          )}
        </div>

        <DisclaimerFooter />
      </div>

      {/* Toast */}
      {toast && <Toast message={toast} onDone={() => setToast(null)} />}
    </div>
  );
}
