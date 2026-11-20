import type { JSX } from "react";
import styles from "./PanelMesure.module.css";

const HF_RESNET_URL = "https://huggingface.co/microsoft/resnet-50";

export function PanelMesure(): JSX.Element {
  return (
    <section className={styles.panel} aria-labelledby="panel-mesure-titre">
      <h2 id="panel-mesure-titre" className={styles.title}>
        Mesure
      </h2>

      <div className={styles.text}>
        <p>Une photo, une catégorie. On mesure l’accuracy. Pas la mAP.</p>
        <p>
          Seuil 0,6. En dessous, le statut est{" "}
          <code className={styles.code} translate="no">
            a_confirmer
          </code>
          .
        </p>
        <p>
          ONNX, it.&nbsp;4 : 68,5&nbsp;% sur 200 photos. Inférence p50
          21,5&nbsp;ms, p95 28,6&nbsp;ms.
        </p>
        <p>
          Charge, it.&nbsp;5 : la requête complète, 1&nbsp;vCPU, ~68&nbsp;ms
          p50. C’est le chiffre de la facture.
        </p>
      </div>

      <dl className={styles.metrics}>
        <div className={styles.metric}>
          <dt>Accuracy</dt>
          <dd>68,5&nbsp;%</dd>
        </div>
        <div className={styles.metric}>
          <dt>Seuil</dt>
          <dd>0,6</dd>
        </div>
        <div className={styles.metric}>
          <dt>p50</dt>
          <dd>21,5&nbsp;ms</dd>
        </div>
        <div className={styles.metric}>
          <dt>p95</dt>
          <dd>28,6&nbsp;ms</dd>
        </div>
      </dl>
      <p className={styles.caption}>
        Production{" "}
        <code className={styles.code} translate="no">
          resnet50-onnx-int8
        </code>
        , jeu proxy de 200 photos.
      </p>

      <h3 className={styles.sourcesTitle}>Sources</h3>
      <ul className={styles.sources}>
        <li>
          <a
            className={styles.link}
            href={HF_RESNET_URL}
            target="_blank"
            rel="noopener noreferrer"
          >
            ResNet-50 sur Hugging Face
            <span className={styles.srOnly}> (nouvel onglet)</span>
          </a>
        </li>
        <li>
          Preuve d’optimisation :{" "}
          <code className={styles.code} translate="no">
            docs/preuves/it4-optimisation.md
          </code>
          . ONNX int8 statique, accuracy 68,5&nbsp;%, p50 21,5&nbsp;ms, p95
          28,6&nbsp;ms.
        </li>
        <li>
          Même mesure dans{" "}
          <code className={styles.code} translate="no">
            docs/preuves/eval/catalog_metrics.json
          </code>
          , entrée{" "}
          <code className={styles.code} translate="no">
            resnet50-onnx-int8
          </code>{" "}
          (
          <code className={styles.code} translate="no">
            accuracy
          </code>{" "}
          0,685,{" "}
          <code className={styles.code} translate="no">
            p50_ms
          </code>{" "}
          21,5,{" "}
          <code className={styles.code} translate="no">
            p95_ms
          </code>{" "}
          28,6,{" "}
          <code className={styles.code} translate="no">
            metric_source
          </code>{" "}
          measured).
        </li>
        <li>
          Promesse « moins d’une seconde » :{" "}
          <code className={styles.code} translate="no">
            docs/SPECIFICATIONS.md
          </code>
          .
        </li>
      </ul>
    </section>
  );
}
