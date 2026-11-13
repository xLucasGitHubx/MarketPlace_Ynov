import type { JSX } from "react";
import styles from "./PanelPreparation.module.css";

export function PanelPreparation(): JSX.Element {
  return (
    <section className={styles.panel} aria-labelledby="preparation-title">
      <h2 id="preparation-title" className={styles.title}>
        Préparation
      </h2>

      <div className={styles.text}>
        <p>
          Chaque photo devient un carré de 224×224, puis des nombres
          normalisés à la façon d’ImageNet, avant que le modèle ne la voie.
        </p>
        <p>
          Le petit côté est d’abord porté à 256 pixels, en bicubique. Le centre
          est ensuite recadré en 224×224. C’est le réglage de{" "}
          <code>microsoft/resnet-50</code> : un recadrage de 87,5&nbsp;%.
        </p>
        <p>
          Les pixels, entre 0 et 255, sont divisés par 255. On retire alors la
          moyenne ImageNet et on divise par l’écart-type, couleur par couleur :
          rouge 0,485 et 0,229, vert 0,456 et 0,224, bleu 0,406 et 0,225.
        </p>
        <p>
          Le modèle reçoit un tableau de forme 1 × 3 × 224 × 224 : une image,
          trois couleurs, 224 pixels de haut et de large.
        </p>
        <p>
          L’augmentation (miroir, recadrage au hasard, couleur changée) sert
          seulement à entraîner. On ne réentraîne pas, donc la production
          n’augmente rien : la même photo donne toujours les mêmes nombres.
        </p>
        <p>
          Un seul choix : garder cette recette. Le réseau a appris avec elle.
          Une autre taille ou une autre normalisation lui ferait lire une image
          qu’il ne connaît pas.
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
