import type { JSX } from "react";
import { Link } from "react-router-dom";
import styles from "./PanelSurveillance.module.css";

const PHOTO_SHIFTS = [
  { id: "light", name: "Lumière", detail: "nuit, contre-jour, pièce sombre" },
  { id: "blur", name: "Flou", detail: "bougé ou mise au point ratée" },
  { id: "background", name: "Fond", detail: "autre pièce, autre décor" },
  { id: "camera", name: "Appareil", detail: "autre téléphone, autre cadrage" },
] as const;

const WATCHED_SIGNALS = [
  { id: "latency", name: "Latence", detail: "le temps de réponse qui s’allonge" },
  { id: "errors", name: "Erreurs", detail: "refus et échecs d’analyse" },
  {
    id: "confidence",
    name: "Confiance",
    detail: "scores plus bas sur des objets connus",
  },
] as const;

export function PanelSurveillance(): JSX.Element {
  return (
    <article className={styles.panel} aria-labelledby="surveillance-title">
      <p className={styles.kicker}>Surveillance</p>
      <h2 id="surveillance-title" className={styles.title}>
        Les photos changent, le modèle peut devenir moins fiable
      </h2>
      <p className={styles.prose}>
        Une annonce réelle n’est pas la photo du labo. La nuit change la
        lumière, le flou gomme les détails, le fond et l’appareil ne sont plus
        les mêmes. Le modèle, lui, n’a pas bougé&nbsp;: il peut alors se tromper
        plus souvent.
      </p>
      <p className={styles.choice}>
        Choix retenu&nbsp;: surveiller la latence, les erreurs et la confiance,
        sans garder les photos. Si ces signaux se dégradent, on revient aux
        données et on mesure à nouveau.
      </p>

      <h3 className={styles.groupTitle}>Ce qui change sur la photo</h3>
      <ul className={styles.shiftList}>
        {PHOTO_SHIFTS.map((shift) => (
          <li key={shift.id} className={styles.shift}>
            <span className={styles.shiftName}>{shift.name}</span>
            <span className={styles.shiftDetail}>{shift.detail}</span>
          </li>
        ))}
      </ul>

      <h3 className={styles.groupTitle}>Ce que l’on regarde</h3>
      <dl className={styles.signalList}>
        {WATCHED_SIGNALS.map((signal) => (
          <div key={signal.id} className={styles.signal}>
            <dt className={styles.signalName}>{signal.name}</dt>
            <dd className={styles.signalDetail}>{signal.detail}</dd>
          </div>
        ))}
      </dl>

      <p className={styles.prose}>
        L’image est lue en mémoire le temps de l’analyse, puis oubliée. Aucune
        photo n’est écrite sur le disque (RGPD).
      </p>

      <p className={styles.linkRow}>
        <Link className={styles.link} to="/garde-fous">
          Voir les garde-fous
        </Link>
      </p>

      <footer className={styles.sources}>
        <h3 className={styles.sourcesTitle}>Sources</h3>
        <p className={styles.sourcesLine}>
          Règle «&nbsp;aucune image sur disque&nbsp;»&nbsp;:{" "}
          <code className={styles.sourcePath}>docs/preuves/it6-securite.md</code>
        </p>
      </footer>
    </article>
  );
}
