import type { JSX } from "react";

import styles from "./PanelBesoin.module.css";

export function PanelBesoin(): JSX.Element {
  return (
    <section className={styles.panel} aria-labelledby="panel-besoin-title">
      <h2 id="panel-besoin-title" className={styles.title}>
        Besoin
      </h2>
      <p className={styles.line}>
        Un vendeur envoie la photo de l’objet qu’il veut mettre en vente.
      </p>
      <p className={styles.line}>
        L’API propose une catégorie, un titre et une description d’une phrase.
      </p>
      <p className={styles.line}>
        Confiance haute : le statut est <code>auto</code>.
      </p>
      <p className={styles.line}>
        Confiance basse : le statut est <code>a_confirmer</code>, le vendeur
        choisit parmi 3 propositions.
      </p>
      <p className={styles.line}>
        Une mauvaise catégorie coûte plus qu’une question : on demande alors
        confirmation.
      </p>
      <p className={styles.sources}>
        Sources : <code>docs/SUJET.md</code>
        {" · "}
        <code>docs/SPECIFICATIONS.md</code>
      </p>
    </section>
  );
}
