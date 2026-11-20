import { useState, type JSX } from "react";
import { PanelBesoin } from "@/parcours/PanelBesoin";
import { PanelDonnees } from "@/parcours/PanelDonnees";
import { PanelFiche } from "@/parcours/PanelFiche";
import { PanelMesure } from "@/parcours/PanelMesure";
import { PanelModele } from "@/parcours/PanelModele";
import { PanelPreparation } from "@/parcours/PanelPreparation";
import { PanelProduction } from "@/parcours/PanelProduction";
import { PanelSurveillance } from "@/parcours/PanelSurveillance";
import { SchemaCycle } from "@/parcours/SchemaCycle";
import { ITERATIONS, ORAL_STEPS, iterationsForStep } from "@/parcours/oral";
import styles from "./Parcours.module.css";

const PANELS: Record<string, () => JSX.Element> = {
  besoin: PanelBesoin,
  donnees: PanelDonnees,
  preparation: PanelPreparation,
  modele: PanelModele,
  mesure: PanelMesure,
  fiche: PanelFiche,
  production: PanelProduction,
  surveillance: PanelSurveillance,
};

export function ParcoursPage() {
  const [actif, setActif] = useState<string>(ORAL_STEPS[0].id);
  const index = Math.max(
    0,
    ORAL_STEPS.findIndex((step) => step.id === actif),
  );
  const step = ORAL_STEPS[index] ?? ORAL_STEPS[0];
  const Panel = PANELS[step.id] ?? PanelBesoin;
  const owned = iterationsForStep(step.id);
  const atStart = index === 0;
  const atEnd = index === ORAL_STEPS.length - 1;

  return (
    <section className="fade-in" aria-labelledby="parcours-title">
      <p className="page-kicker">Parcours</p>
      <h1 id="parcours-title" className="page-title">
        Une idée, puis la suivante.
      </h1>
      <p className={`page-lead ${styles.lead}`}>
        Huit étapes, à voix haute. Les neuf itérations du sujet sont sur la
        ligne du haut.
      </p>

      <h2 className={styles.railTitle}>Itérations du sujet</h2>
      <ul className={styles.rail}>
        {ITERATIONS.map((item) => {
          const pressed = item.step === step.id;
          return (
            <li key={item.id}>
              <button
                type="button"
                aria-pressed={pressed}
                onClick={() => setActif(item.step)}
              >
                <span className={styles.railIndex}>{item.it}</span>
                {item.label}
              </button>
            </li>
          );
        })}
      </ul>

      <SchemaCycle actif={step.id} onChoisir={setActif} />

      <div className={styles.drift}>
        <p className={styles.driftKicker}>Retour du cycle</p>
        <p className={styles.driftWord}>Photos différentes</p>
        <p className={styles.driftWhy}>
          Les annonces réelles ne ressemblent pas au labo. On revient aux
          données.
        </p>
      </div>

      <div className={styles.nav}>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => setActif(ORAL_STEPS[index - 1].id)}
          disabled={atStart}
        >
          Précédent
        </button>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => setActif(ORAL_STEPS[index + 1].id)}
          disabled={atEnd}
        >
          Suivant
        </button>
      </div>

      <p className={styles.meta}>
        <span>
          Étape {index + 1} / {ORAL_STEPS.length}
        </span>
        {owned.length > 0 ? (
          <ul className={styles.chips} aria-label="Itérations de cette étape">
            {owned.map((item) => (
              <li key={item.id} className={styles.chip}>
                {item.label}
                <span className={styles.railIndex}>it. {item.it}</span>
              </li>
            ))}
          </ul>
        ) : null}
      </p>
      {step.serves ? <p className={styles.serves}>{step.serves}</p> : null}

      <Panel />

      <p className="live-region" aria-live="polite">
        Étape {index + 1} sur {ORAL_STEPS.length}.
      </p>
    </section>
  );
}
