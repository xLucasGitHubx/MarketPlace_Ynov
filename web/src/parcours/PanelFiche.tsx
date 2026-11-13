import type { JSX } from "react";
import styles from "./PanelFiche.module.css";

function ExternalLink({ href, children }: { href: string; children: string }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  );
}

export function PanelFiche(): JSX.Element {
  return (
    <section className={styles.panel} aria-labelledby="fiche-titre">
      <h2 id="fiche-titre" className={styles.title}>
        Fiche projet
      </h2>
      <dl className={styles.fiche}>
        <div className={styles.row}>
          <dt>Projet</dt>
          <dd>MarketPlace Vision</dd>
        </div>
        <div className={styles.row}>
          <dt>Tâche</dt>
          <dd>Classification : une catégorie par photo.</dd>
        </div>
        <div className={styles.row}>
          <dt>Dataset</dt>
          <dd>
            Proxy de labo <code>data/test_set/manifest.csv</code>, assemblé par{" "}
            <code>scripts/build_test_set.py</code>. Ce ne sont pas des photos
            Leboncoin. Les images viennent de{" "}
            <ExternalLink href="https://huggingface.co/datasets/pawlo2013/StanfordOnlineProducts">
              Stanford Online Products
            </ExternalLink>{" "}
            (meubles, électroménager, vélos) et du split test{" "}
            <ExternalLink href="https://huggingface.co/datasets/ilee0022/Caltech-256">
              Caltech-256
            </ExternalLink>{" "}
            pour le reste des catégories.
          </dd>
        </div>
        <div className={styles.row}>
          <dt>Modèle de départ</dt>
          <dd>
            <ExternalLink href="https://huggingface.co/microsoft/resnet-50">
              microsoft/resnet-50
            </ExternalLink>
            . En production : <code>resnet50-onnx-int8</code>.
          </dd>
        </div>
        <div className={styles.row}>
          <dt>Prétraitements</dt>
          <dd>
            224×224, normalisation{" "}
            <ExternalLink href="https://www.image-net.org/">
              ImageNet
            </ExternalLink>
            . Pas d’augmentation en production.
          </dd>
        </div>
        <div className={styles.row}>
          <dt>Métriques</dt>
          <dd>
            Accuracy de catégorie, confiance, seuil 0,6, latence p95. Sur le
            jeu de 200 photos, <code>resnet50-onnx-int8</code> atteint
            68,5&nbsp;% d’accuracy et 28,6&nbsp;ms en p95 (
            <code>docs/preuves/it4-optimisation.md</code>).
          </dd>
        </div>
        <div className={styles.row}>
          <dt>Environnement</dt>
          <dd>
            Python 3.11,{" "}
            <ExternalLink href="https://onnxruntime.ai/">
              ONNX Runtime
            </ExternalLink>
            ,{" "}
            <ExternalLink href="https://fastapi.tiangolo.com/">
              FastAPI
            </ExternalLink>
            . PyTorch reste hors de l’image Azure.
          </dd>
        </div>
      </dl>
      <p className={styles.roles}>
        <ExternalLink href="https://huggingface.co/models">
          Hugging Face
        </ExternalLink>{" "}
        fournit le modèle,{" "}
        <ExternalLink href="https://mlflow.org/docs/latest/">
          MLflow
        </ExternalLink>{" "}
        garde les mesures (pas les photos), Git garde le code.
      </p>
      <h3 className={styles.sourcesTitle}>Sources</h3>
      <ul className={styles.sources}>
        <li>
          <ExternalLink href="https://huggingface.co/datasets/pawlo2013/StanfordOnlineProducts">
            Stanford Online Products
          </ExternalLink>
        </li>
        <li>
          <ExternalLink href="https://huggingface.co/datasets/ilee0022/Caltech-256">
            Caltech-256
          </ExternalLink>
        </li>
        <li>
          <ExternalLink href="https://huggingface.co/microsoft/resnet-50">
            microsoft/resnet-50
          </ExternalLink>
        </li>
        <li>
          <ExternalLink href="https://www.image-net.org/">ImageNet</ExternalLink>
        </li>
        <li>
          <ExternalLink href="https://onnxruntime.ai/">ONNX Runtime</ExternalLink>
        </li>
        <li>
          <ExternalLink href="https://fastapi.tiangolo.com/">FastAPI</ExternalLink>
        </li>
        <li>
          <ExternalLink href="https://huggingface.co/models">
            Hugging Face
          </ExternalLink>
        </li>
        <li>
          <ExternalLink href="https://mlflow.org/docs/latest/">MLflow</ExternalLink>
        </li>
        <li>
          <code>docs/preuves/it4-optimisation.md</code>
        </li>
      </ul>
    </section>
  );
}
