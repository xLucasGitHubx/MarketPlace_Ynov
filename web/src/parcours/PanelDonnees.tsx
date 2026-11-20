import type { JSX } from "react";
import { Link } from "react-router-dom";
import jeuRaw from "./jeu.json?raw";
import photosRaw from "./jeuPhotos.json?raw";
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

type PhotoThumb = {
  src: string;
  source: string;
  classe: string;
};

type PhotoGroup = {
  label: string;
  count: number;
  photos: PhotoThumb[];
};

type PhotoPack = {
  total: number;
  present: number;
  missing: number;
  categories: PhotoGroup[];
};

function isPhoto(value: unknown): value is PhotoThumb {
  if (typeof value !== "object" || value === null) return false;
  const row = value as Record<string, unknown>;
  return (
    typeof row.src === "string" &&
    row.src.startsWith("/jeu/") &&
    !row.src.includes("..") &&
    typeof row.source === "string" &&
    typeof row.classe === "string"
  );
}

function isGroup(value: unknown): value is PhotoGroup {
  if (typeof value !== "object" || value === null) return false;
  const row = value as Record<string, unknown>;
  return (
    typeof row.label === "string" &&
    typeof row.count === "number" &&
    Array.isArray(row.photos) &&
    row.photos.every(isPhoto)
  );
}

function readPhotos(raw: string): PhotoPack {
  const parsed: unknown = JSON.parse(raw);
  if (typeof parsed !== "object" || parsed === null) {
    throw new Error("jeuPhotos.json is not an object.");
  }
  const row = parsed as Record<string, unknown>;
  if (
    typeof row.total !== "number" ||
    typeof row.present !== "number" ||
    typeof row.missing !== "number" ||
    !Array.isArray(row.categories) ||
    !row.categories.every(isGroup)
  ) {
    throw new Error("jeuPhotos.json does not match the thumbnail pack shape.");
  }
  return {
    total: row.total,
    present: row.present,
    missing: row.missing,
    categories: row.categories,
  };
}

const jeu = readJeu(jeuRaw);
const photos = readPhotos(photosRaw);

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
        Pas d’images synthétiques. Le jeu reste celui du manifeste. Ces photos
        mesurent l’accuracy. Le cours de diagnostic chronomètre aussi des
        tenseurs aléatoires&nbsp;: ils ne jugent pas la qualité.{" "}
        <Link className={styles.link} to="/parcours?etape=mesure&partie=entrees">
          Voir la partie Entrées
        </Link>
        .
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

      <section className={styles.gallery} aria-labelledby="panel-donnees-photos">
        <h3 id="panel-donnees-photos" className={styles.sourcesTitle}>
          Photos du manifeste
        </h3>
        <p className={styles.detail}>
          {photos.present}&nbsp;vignettes sur {photos.total} lignes. Proxy de
          laboratoire, pas des photos Leboncoin. Les originaux ne sont pas dans
          l’image Azure.
          {photos.missing > 0
            ? ` ${photos.missing} fichier(s) du manifeste absent(s) du pack.`
            : null}
        </p>
        {photos.categories.map((category) => (
          <div key={category.label} className={styles.group}>
            <h4 className={styles.groupTitle}>
              {category.label}
              <span className={styles.count}>{category.photos.length}</span>
            </h4>
            {category.photos.length === 0 ? (
              <p className={styles.detail}>
                Aucune vignette de cette catégorie n’est dans ce dépôt.
              </p>
            ) : (
              <ul
                className={styles.strip}
                tabIndex={0}
                aria-label={`Vignettes ${category.label}`}
              >
                {category.photos.map((photo) => (
                  <li key={photo.src} className={styles.frame}>
                    <img
                      className={styles.thumb}
                      src={photo.src}
                      alt={`${category.label}, ${photo.classe}. Proxy de laboratoire, pas une photo Leboncoin.`}
                      width={160}
                      height={120}
                    />
                    <span className={styles.classe} translate="no">
                      {photo.classe}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </section>

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
