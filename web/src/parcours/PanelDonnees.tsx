import type { JSX } from "react";
import jeuRaw from "./jeu.json?raw";
import styles from "./PanelDonnees.module.css";

type CategoryCount = {
  label: string;
  count: number;
};

type SourceCount = {
  id: string;
  count: number;
};

type Jeu = {
  manifestPath: string;
  total: number;
  categories: CategoryCount[];
  sources: SourceCount[];
};

function isCategory(value: unknown): value is CategoryCount {
  if (typeof value !== "object" || value === null) return false;
  const row = value as Record<string, unknown>;
  return typeof row.label === "string" && typeof row.count === "number";
}

function isSource(value: unknown): value is SourceCount {
  if (typeof value !== "object" || value === null) return false;
  const row = value as Record<string, unknown>;
  return typeof row.id === "string" && typeof row.count === "number";
}

function isJeu(value: unknown): value is Jeu {
  if (typeof value !== "object" || value === null) return false;
  const row = value as Record<string, unknown>;
  return (
    typeof row.manifestPath === "string" &&
    typeof row.total === "number" &&
    Array.isArray(row.categories) &&
    row.categories.every(isCategory) &&
    Array.isArray(row.sources) &&
    row.sources.every(isSource)
  );
}

function readJeu(raw: string): Jeu {
  const parsed: unknown = JSON.parse(raw);
  if (!isJeu(parsed)) {
    throw new Error("jeu.json does not match the expected counts shape.");
  }
  return parsed;
}

const jeu = readJeu(jeuRaw);

const BAR_SCALE = 100;

/** Dataset pages for the two URLs hardcoded in scripts/build_test_set.py. */
const DATASETS = [
  {
    id: "sop",
    label: "Stanford Online Products",
    href: "https://huggingface.co/datasets/pawlo2013/StanfordOnlineProducts",
    detail:
      "Photos de produits eBay. Le script en retient meubles, électroménager et vélos.",
  },
  {
    id: "caltech",
    label: "Caltech-256",
    href: "https://huggingface.co/datasets/ilee0022/Caltech-256",
    detail: "Split de test. Il couvre les catégories absentes du jeu eBay.",
  },
] as const;

export function PanelDonnees(): JSX.Element {
  const firstCount = jeu.categories[0]?.count;
  const sharedCount =
    firstCount !== undefined &&
    jeu.categories.every((category) => category.count === firstCount)
      ? firstCount
      : undefined;
  const maxCount = Math.max(
    1,
    ...jeu.categories.map((category) => category.count),
  );

  return (
    <section className={styles.panel} aria-labelledby="panel-donnees-title">
      <h2 id="panel-donnees-title" className={styles.title}>
        Données
      </h2>
      <p className={styles.lead}>
        Ce jeu est un proxy de laboratoire : 10 catégories d’annonce, pas des
        photos réelles de Leboncoin.
      </p>
      <p className={styles.choice}>
        On ne génère pas d’images synthétiques : des photos fabriquées ne
        rapprocheraient pas ce proxy de vraies annonces, et le jeu reste celui
        du manifeste.
      </p>
      <p className={styles.meta}>
        {sharedCount !== undefined
          ? `${jeu.total}\u00a0images au total, ${sharedCount}\u00a0par catégorie.`
          : `${jeu.total}\u00a0images au total, sur ${jeu.categories.length}\u00a0catégories.`}
      </p>

      <figure className={styles.figure}>
        <figcaption className={styles.caption}>
          Effectifs par catégorie
        </figcaption>
        <ul className={styles.chart}>
          {jeu.categories.map((category) => (
            <li key={category.label} className={styles.row}>
              <span className={styles.label}>{category.label}</span>
              <svg
                className={styles.bar}
                viewBox={`0 0 ${BAR_SCALE} 10`}
                preserveAspectRatio="none"
                aria-hidden="true"
              >
                <rect
                  className={styles.track}
                  x={0}
                  y={0}
                  width={BAR_SCALE}
                  height={10}
                />
                <rect
                  className={styles.fill}
                  x={0}
                  y={0}
                  width={(category.count / maxCount) * BAR_SCALE}
                  height={10}
                />
              </svg>
              <span className={styles.count}>{category.count}</span>
            </li>
          ))}
        </ul>
      </figure>

      <h3 className={styles.sourcesTitle}>Sources</h3>
      <ul className={styles.sources}>
        {DATASETS.map((dataset) => {
          const count = jeu.sources.find((source) => source.id === dataset.id)
            ?.count;
          return (
            <li key={dataset.id} className={styles.source}>
              <a
                className={styles.link}
                href={dataset.href}
                target="_blank"
                rel="noopener noreferrer"
              >
                {dataset.label}
                <span className={styles.srOnly}> (nouvel onglet)</span>
              </a>
              <p className={styles.detail}>
                {count !== undefined ? `${count}\u00a0images. ` : null}
                {dataset.detail}
              </p>
            </li>
          );
        })}
        <li className={styles.source}>
          <span className={styles.localLabel}>Manifeste du jeu</span>
          <p className={styles.detail}>
            Décompte versionné de ces barres :{" "}
            <code className={styles.path} translate="no">
              {jeu.manifestPath}
            </code>
          </p>
        </li>
      </ul>
    </section>
  );
}
