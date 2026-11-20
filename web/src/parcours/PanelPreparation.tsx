import type { JSX } from "react";
import styles from "./PanelPreparation.module.css";

export function PanelPreparation(): JSX.Element {
  return (
    <section className={styles.panel} aria-labelledby="preparation-title">
      <h2 id="preparation-title" className={styles.title}>
        Préparation
      </h2>

      <div className={styles.text}>
        <p>Le petit côté passe à 256. Le centre est recadré en 224×224.</p>
        <p>
          Moyenne et écart-type ImageNet : rouge 0,485 / 0,229, vert 0,456 /
          0,224, bleu 0,406 / 0,225. Forme 1 × 3 × 224 × 224.
        </p>
        <p>
          Pas d’augmentation en production. La même photo donne les mêmes
          nombres : le réseau a appris avec cette recette.
        </p>
      </div>

      <figure
        className={styles.flow}
        aria-label="Photo d’origine, carré 224, puis nombres"
      >
        <div className={styles.step}>
          <svg
            className={styles.original}
            viewBox="0 0 144 96"
            width="144"
            height="96"
            aria-hidden="true"
          >
            <rect className={styles.frame} x="0.75" y="0.75" width="142.5" height="94.5" rx="6" />
            <rect className={styles.side} x="0" y="0" width="24" height="96" />
            <rect className={styles.side} x="120" y="0" width="24" height="96" />
            <rect className={styles.crop} x="24.75" y="0.75" width="94.5" height="94.5" />
            <rect className={styles.object} x="62" y="30" width="20" height="42" rx="3" />
            <rect className={styles.objectCap} x="66" y="22" width="12" height="10" rx="2" />
          </svg>
          <p className={styles.stepLabel}>Photo d’origine</p>
        </div>

        <svg className={styles.arrow} viewBox="0 0 28 16" width="28" height="16" aria-hidden="true">
          <path d="M1 8h20M15 2.5 23.5 8 15 13.5" />
        </svg>

        <div className={styles.step}>
          <svg
            className={styles.square}
            viewBox="0 0 96 96"
            width="96"
            height="96"
            aria-hidden="true"
          >
            <rect className={styles.frame} x="0.75" y="0.75" width="94.5" height="94.5" rx="6" />
            <rect className={styles.object} x="38" y="22" width="20" height="52" rx="3" />
            <rect className={styles.objectCap} x="42" y="12" width="12" height="12" rx="2" />
            <text className={styles.squareMark} x="8" y="16">
              224
            </text>
          </svg>
          <p className={styles.stepLabel}>Carré 224 × 224</p>
        </div>

        <svg className={styles.arrow} viewBox="0 0 28 16" width="28" height="16" aria-hidden="true">
          <path d="M1 8h20M15 2.5 23.5 8 15 13.5" />
        </svg>

        <div className={styles.step}>
          <table className={styles.numbers}>
            <caption className={styles.numbersCaption}>Exemple figé</caption>
            <thead>
              <tr>
                <th scope="col">R</th>
                <th scope="col">G</th>
                <th scope="col">B</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>0,21</td>
                <td>−0,48</td>
                <td>0,73</td>
              </tr>
              <tr>
                <td>−0,90</td>
                <td>1,12</td>
                <td>−0,31</td>
              </tr>
              <tr>
                <td>0,44</td>
                <td>−1,05</td>
                <td>0,18</td>
              </tr>
            </tbody>
          </table>
          <p className={styles.stepLabel}>Nombres</p>
        </div>
      </figure>

      <section className={styles.sources} aria-labelledby="preparation-sources">
        <h3 id="preparation-sources" className={styles.sourcesTitle}>
          Sources
        </h3>
        <ul className={styles.sourceList}>
          <li>
            <a
              href="https://www.image-net.org/"
              target="_blank"
              rel="noopener noreferrer"
            >
              ImageNet
            </a>
          </li>
          <li>
            <a
              className={styles.modelLink}
              href="https://huggingface.co/microsoft/resnet-50"
              target="_blank"
              rel="noopener noreferrer"
            >
              microsoft/resnet-50
            </a>
          </li>
        </ul>
      </section>
    </section>
  );
}
