import type { JSX } from "react";
import { Link } from "react-router-dom";
import styles from "./PanelModele.module.css";

type ExternalSource = {
  label: string;
  href: string;
  repoId?: string;
};

type CatalogSource = {
  catalogId: string;
  note?: string;
  links: readonly ExternalSource[];
};

/** Hugging Face repo ids copied from the code, not guessed.
 *  Prod: app/model.py HF_MODEL_ID and scripts/export_onnx.py MODEL_ID.
 *  EfficientNet, MobileNet, CLIP: hf_model_id on CATALOG in app/registry.py.
 *  Student: no hf_model_id; scripts/distill_student.py STUDENT_ID and TEACHER_ID.
 */
const CATALOG_SOURCES: readonly CatalogSource[] = [
  {
    catalogId: "resnet50-onnx-int8",
    note: "Choix de production : inférence directe, convertie en ONNX int8.",
    links: [
      {
        label: "ResNet-50 sur Hugging Face",
        href: "https://huggingface.co/microsoft/resnet-50",
        repoId: "microsoft/resnet-50",
      },
    ],
  },
  {
    catalogId: "efficientnet-b0-onnx-int8",
    links: [
      {
        label: "EfficientNet-B0 sur Hugging Face",
        href: "https://huggingface.co/google/efficientnet-b0",
        repoId: "google/efficientnet-b0",
      },
    ],
  },
  {
    catalogId: "mobilenet-v3-small-onnx-int8",
    links: [
      {
        label: "MobileNetV3-Small sur Hugging Face",
        href: "https://huggingface.co/facebook/mobilenet_v3_small",
        repoId: "facebook/mobilenet_v3_small",
      },
    ],
  },
  {
    catalogId: "student-kd-mobilenet-int8",
    note: "Pas de dépôt propre dans le registre. La distillation part de ces deux identifiants.",
    links: [
      {
        label: "Architecture de l’élève sur Hugging Face",
        href: "https://huggingface.co/facebook/mobilenet_v3_small",
        repoId: "facebook/mobilenet_v3_small",
      },
      {
        label: "Enseignant ResNet-50 sur Hugging Face",
        href: "https://huggingface.co/microsoft/resnet-50",
        repoId: "microsoft/resnet-50",
      },
    ],
  },
  {
    catalogId: "clip-vit-b32",
    note: "Comparaison CLIP / ViT. Environ 577 Mo : trop lourd pour l’image Azure.",
    links: [
      {
        label: "CLIP ViT-B/32 sur Hugging Face",
        href: "https://huggingface.co/openai/clip-vit-base-patch32",
        repoId: "openai/clip-vit-base-patch32",
      },
    ],
  },
];

const RUNTIME_SOURCE: ExternalSource = {
  label: "ONNX Runtime",
  href: "https://onnxruntime.ai/",
};

function ExternalAnchor({ href, label }: ExternalSource): JSX.Element {
  return (
    <a className={styles.link} href={href} target="_blank" rel="noopener noreferrer">
      {label}
      <span className={styles.srOnly}> (nouvel onglet)</span>
    </a>
  );
}

export function PanelModele(): JSX.Element {
  return (
    <section className={styles.panel} aria-labelledby="panel-modele-titre">
      <h2 id="panel-modele-titre" className={styles.title}>
        Choix du modèle
      </h2>
      <div className={styles.prose}>
        <p>
          Le choix retenu est l’inférence directe de{" "}
          <ExternalAnchor
            href="https://huggingface.co/microsoft/resnet-50"
            label="ResNet-50"
          />{" "}
          <code className={styles.repo} translate="no">
            microsoft/resnet-50
          </code>
          , déjà entraîné, converti en ONNX int8. L’identifiant de production est{" "}
          <code className={styles.repo} translate="no">
            resnet50-onnx-int8
          </code>
          . On ne ré-entraîne pas&nbsp;: on industrialise un modèle pré-entraîné.
        </p>
        <p>
          L’image Azure reste autour de 551&nbsp;Mo, sans PyTorch. L’inférence passe par{" "}
          <ExternalAnchor href={RUNTIME_SOURCE.href} label={RUNTIME_SOURCE.label} />.
        </p>
        <p>
          CLIP et ViT restent des comparaisons. CLIP ViT-B/32 pèse environ 577&nbsp;Mo dans
          le catalogue&nbsp;: trop lourd pour cette image. Les mesures des autres modèles
          sont dans le comparateur.
        </p>
        <p className={styles.action}>
          <Link className={styles.internalLink} to="/comparateur">
            Voir le comparateur
          </Link>
        </p>
      </div>

      <div className={styles.sources}>
        <h3 className={styles.sourcesTitle}>Sources</h3>
        <ul className={styles.list}>
          {CATALOG_SOURCES.map((source) => (
            <li key={source.catalogId} className={styles.item}>
              <code className={styles.catalogId} translate="no">
                {source.catalogId}
              </code>
              {source.note ? <p className={styles.note}>{source.note}</p> : null}
              <ul className={styles.linkList}>
                {source.links.map((link) => (
                  <li key={`${source.catalogId}-${link.repoId ?? link.href}`} className={styles.linkRow}>
                    <ExternalAnchor href={link.href} label={link.label} />
                    {link.repoId ? (
                      <code className={styles.repo} translate="no">
                        {link.repoId}
                      </code>
                    ) : null}
                  </li>
                ))}
              </ul>
            </li>
          ))}
          <li className={styles.item}>
            <span className={styles.catalogId}>Moteur d’inférence</span>
            <ul className={styles.linkList}>
              <li className={styles.linkRow}>
                <ExternalAnchor href={RUNTIME_SOURCE.href} label={RUNTIME_SOURCE.label} />
              </li>
            </ul>
          </li>
        </ul>
      </div>
    </section>
  );
}
