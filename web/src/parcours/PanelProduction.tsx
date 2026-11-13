import type { JSX } from "react";

import { CompteurSession } from "@/components/CompteurSession";

import styles from "./PanelProduction.module.css";

export function PanelProduction(): JSX.Element {
  return (
    <section className={styles.panel} aria-labelledby="panel-production-title">
      <h2 id="panel-production-title" className={styles.title}>
        Production
      </h2>
      <p className={styles.line}>
        On ne laisse pas le modèle sur la machine du développeur. On l’emballe,
        puis on le met en ligne.
      </p>
      <p className={styles.line}>
        Choix retenu : une image Docker sans PyTorch, sur Azure Container Apps,
        avec une réplique toujours allumée.
      </p>
      <p className={styles.line}>
        PyTorch rend l’image lourde (environ 2 Go) et chaque photo plus lente.
        Sans PyTorch, l’image reste autour de 551 Mo. Une réplique déjà allumée
        répond sans attendre un démarrage.
      </p>
      <p className={styles.line}>
        Deux montants restent côte à côte. On ne les additionne pas.
      </p>

      <div
        className={styles.flow}
        role="list"
        aria-label="Code, image Docker sans PyTorch, Azure Container Apps"
      >
        <div className={styles.box} role="listitem">
          <span className={styles.step}>1</span>
          <span className={styles.boxTitle}>Code</span>
        </div>
        <span className={styles.arrow} aria-hidden="true">
          →
        </span>
        <div className={styles.box} role="listitem">
          <span className={styles.step}>2</span>
          <span className={styles.boxTitle}>Image Docker sans PyTorch</span>
        </div>
        <span className={styles.arrow} aria-hidden="true">
          →
        </span>
        <div className={styles.box} role="listitem">
          <span className={styles.step}>3</span>
          <span className={styles.boxTitle}>Azure Container Apps</span>
        </div>
      </div>

      <div className={styles.costs}>
        <article className={styles.cost} aria-labelledby="cout-estimation">
          <h3 id="cout-estimation" className={styles.costTitle}>
            Estimation
          </h3>
          <p className={styles.amount}>≈ 25 $</p>
          <p className={styles.costLine}>
            pour 1 million d’images par mois, avec une réplique toujours
            allumée.
          </p>
          <p className={styles.disclaimer}>
            Ceci est une estimation. Ce n’est pas la facture Azure.
          </p>
        </article>

        <article className={styles.cost} aria-labelledby="cout-session">
          <h3 id="cout-session" className={styles.costTitle}>
            Cette session
          </h3>
          <p className={styles.costLine}>
            Photos réellement envoyées dans ce navigateur. Ce n’est pas la
            facture Azure.
          </p>
          <CompteurSession />
        </article>
      </div>

      <p className={styles.sources}>
        Sources :{" "}
        <a
          href="https://learn.microsoft.com/azure/container-apps/billing"
          target="_blank"
          rel="noopener noreferrer"
        >
          facturation Azure Container Apps
        </a>
        {" · "}
        <a
          href="https://prices.azure.com/api/retail/prices"
          target="_blank"
          rel="noopener noreferrer"
        >
          prix publics Azure
        </a>
        {" · "}
        chiffre <code>≈ 25 $</code> dans <code>FINOPS.md</code>
      </p>
    </section>
  );
}
