import { useId } from "react";
import type { JSX } from "react";

import styles from "./SchemaRequete.module.css";

const STEPS: readonly { id: string; label: string; mono?: boolean }[] = [
  { id: "reception", label: "Réception" },
  { id: "jeton", label: "Jeton" },
  { id: "format", label: "Format" },
  { id: "resize", label: "224×224", mono: true },
  { id: "modele", label: "Modèle" },
  { id: "categorie", label: "Catégorie" },
  { id: "phrase", label: "Phrase" },
  { id: "oubli", label: "Oubli de la photo" },
];

type StepState = "pending" | "done" | "current";

const STATE_LABEL: Record<StepState, string> = {
  pending: "à venir",
  done: "terminée",
  current: "en cours",
};

function stepState(index: number, etapeActive: number): StepState {
  const active = Number.isInteger(etapeActive) ? etapeActive : -1;
  if (index === active) return "current";
  if (active >= 0 && active >= index) return "done";
  return "pending";
}

export function SchemaRequete({
  etapeActive,
}: {
  etapeActive: number;
}): JSX.Element {
  const titleId = useId();
  const active = Number.isInteger(etapeActive) ? etapeActive : -1;
  const running = active >= 0 && active < STEPS.length;
  const finished = active >= STEPS.length;

  let live = "En attente d’une photo.";
  if (running) {
    live = `Étape ${active + 1} sur ${STEPS.length} — ${STEPS[active].label}`;
  } else if (finished) {
    live = "Les huit étapes sont terminées.";
  }

  return (
    <section className={styles.root} aria-labelledby={titleId}>
      <h2 id={titleId} className={styles.title}>
        Chaîne d’une requête
      </h2>
      <p
        className={styles.live}
        aria-live="polite"
        aria-atomic="true"
        data-mode={running ? "running" : finished ? "done" : "idle"}
      >
        {live}
      </p>
      <ol className={styles.pipeline}>
        {STEPS.map((step, index) => {
          const state = stepState(index, etapeActive);
          return (
            <li
              key={step.id}
              className={styles.step}
              data-state={state}
              aria-current={state === "current" ? "step" : undefined}
            >
              <span className={styles.index}>
                {String(index + 1).padStart(2, "0")}
              </span>
              <span
                className={
                  step.mono ? `${styles.label} ${styles.labelMono}` : styles.label
                }
              >
                {step.label}
              </span>
              <span className={styles.markSlot}>
                {state === "done" ? (
                  <svg viewBox="0 0 16 16" aria-hidden="true">
                    <path
                      d="M3.5 8.2 6.4 11.2 12.5 4.8"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.6"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                ) : null}
              </span>
              <svg
                className={styles.arrow}
                viewBox="0 0 16 16"
                aria-hidden="true"
              >
                <path
                  d="M2 8h11M9 4l4 4-4 4"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <span className={styles.srOnly}>{STATE_LABEL[state]}</span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
