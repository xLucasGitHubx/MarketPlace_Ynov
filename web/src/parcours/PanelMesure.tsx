import { useEffect, useRef, type JSX, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  BASELINE,
  CPU1_RAMP,
  CPU2_DROP,
  CPU2_PEAK,
  DIAGNOSTIC_PARTS,
  HF_RESNET18,
  HF_RESNET50,
  INT8_DYNAMIC,
  INT8_STATIC,
  PYTORCH_FP32,
  RATE_10,
  SOURCE_CPU1,
  SOURCE_CPU2,
  SOURCE_EVALUATE,
  SOURCE_EXPORT,
  SOURCE_IT4,
  SOURCE_IT5,
  SOURCE_IT8,
  SOURCE_MODEL,
  SOURCE_RATE,
  frMs,
  frPct,
  frReq,
  partIndex,
  rampAt,
  type DiagnosticPartId,
} from "./diagnostic";
import styles from "./PanelMesure.module.css";

function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function Mark({
  kind,
}: {
  kind: "measured" | "unmeasured" | "na";
}): JSX.Element {
  const label =
    kind === "measured"
      ? "mesuré"
      : kind === "unmeasured"
        ? "non mesuré"
        : "non applicable";
  return (
    <span className={styles.mark} data-kind={kind}>
      {label}
    </span>
  );
}

function Sources({ children }: { children: ReactNode }): JSX.Element {
  return (
    <>
      <h4 className={styles.sourcesTitle}>Sources</h4>
      <ul className={styles.sources}>{children}</ul>
    </>
  );
}

function FileSource({ path }: { path: string }): JSX.Element {
  return (
    <li>
      <code className={styles.code} translate="no">
        {path}
      </code>
    </li>
  );
}

function External({
  href,
  children,
}: {
  href: string;
  children: string;
}): JSX.Element {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
      <span className={styles.srOnly}> (nouvel onglet)</span>
    </a>
  );
}

function Glance({
  kicker,
  children,
}: {
  kicker: string;
  children: ReactNode;
}): JSX.Element {
  return (
    <p className={styles.glance}>
      <span className={styles.glanceKicker}>{kicker}</span>
      {children}
    </p>
  );
}

function PartQualite(): JSX.Element {
  return (
    <>
      <div className={styles.text}>
        <p>Une photo, une catégorie. On mesure l’accuracy. Pas la mAP.</p>
        <p>
          Seuil 0,6. En dessous, le statut est{" "}
          <code className={styles.code} translate="no">
            a_confirmer
          </code>
          . Une mauvaise catégorie coûte plus cher qu’une question.
        </p>
        <p>
          ONNX, it.&nbsp;4&nbsp;: {frPct(INT8_STATIC.accuracy)} sur{" "}
          {INT8_STATIC.n}&nbsp;photos. Inférence p50 {frMs(INT8_STATIC.p50)},
          p95 {frMs(INT8_STATIC.p95)}.
        </p>
        <p>
          Charge, it.&nbsp;5&nbsp;: la requête complète, 1&nbsp;vCPU,{" "}
          {frMs(rampAt(1).p50)} p50. Le studio arrondit à ~68&nbsp;ms. C’est
          le chiffre de la facture. Ce n’est pas le p50 d’inférence.
        </p>
      </div>
      <dl className={styles.metrics}>
        <div className={styles.metric}>
          <dt>Accuracy</dt>
          <dd>{frPct(INT8_STATIC.accuracy)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>Seuil</dt>
          <dd>0,6</dd>
        </div>
        <div className={styles.metric}>
          <dt>p50 inférence</dt>
          <dd>{frMs(INT8_STATIC.p50)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>p50 requête</dt>
          <dd>{frMs(rampAt(1).p50)}</dd>
        </div>
      </dl>
      <p className={styles.caption}>
        Production{" "}
        <code className={styles.code} translate="no">
          resnet50-onnx-int8
        </code>
        . Jeu proxy de {INT8_STATIC.n}&nbsp;photos. La suite de cette étape
        applique le notebook de diagnostic à ces mesures.
      </p>
      <Sources>
        <FileSource path={INT8_STATIC.file} />
        <FileSource path={SOURCE_IT4} />
        <FileSource path={SOURCE_CPU1} />
        <li>
          <External href={HF_RESNET50}>ResNet-50 sur Hugging Face</External>
        </li>
      </Sources>
    </>
  );
}

function PartQuestion(): JSX.Element {
  return (
    <>
      <Glance kicker="La question du cours">
        Comment savoir si une optimisation améliore vraiment le système&nbsp;?
      </Glance>
      <div className={styles.text}>
        <p>Sans référence, un gain ne se démontre pas.</p>
        <p>
          Le livrable du cours est une fiche&nbsp;: modèle, matériel, protocole,
          chiffres. Elle est dans ces parties. Le notebook n’est pas collé à
          côté.
        </p>
        <p>
          Le cours charge{" "}
          <External href={HF_RESNET18}>microsoft/resnet-18</External>. Le
          projet le remplace par{" "}
          <External href={HF_RESNET50}>microsoft/resnet-50</External>, puis par
          l’ONNX int8 retenu.
        </p>
      </div>
      <Sources>
        <li>Notebook diagnostiquer_performances, introduction et §12.</li>
        <FileSource path={SOURCE_IT4} />
      </Sources>
    </>
  );
}

function PartModele(): JSX.Element {
  return (
    <>
      <div className={styles.text}>
        <p>
          Le cours installe PyTorch, Transformers, Pillow, Matplotlib et
          Pandas, puis sépare le prétraitement du passage réseau.
        </p>
        <p>
          En production, l’image Azure n’embarque pas PyTorch. Le runtime est
          ONNX Runtime, avec Pillow et numpy pour la photo. Le prétraitement
          numpy suit le même contrat que l’AutoImageProcessor.
        </p>
      </div>
      <dl className={styles.metrics}>
        <div className={styles.metric}>
          <dt>Cours</dt>
          <dd>resnet-18</dd>
        </div>
        <div className={styles.metric}>
          <dt>Projet</dt>
          <dd>resnet-50</dd>
        </div>
        <div className={styles.metric}>
          <dt>Prod</dt>
          <dd>ONNX int8</dd>
        </div>
        <div className={styles.metric}>
          <dt>Matériel</dt>
          <dd>CPU</dd>
        </div>
      </dl>
      <p className={styles.caption}>
        Le cours prend un GPU CUDA s’il existe. Ici, non. Azure Container Apps
        exécute le conteneur sur CPU. La synchro GPU du §5 ne s’applique pas.
      </p>
      <p className={styles.rowLine}>
        <Mark kind="na" /> Pas de nom de GPU. Pas de mesure CUDA.
      </p>
      <Sources>
        <li>Notebook §1, §2, §2.1.</li>
        <FileSource path={SOURCE_MODEL} />
        <FileSource path={SOURCE_IT4} />
        <li>
          <External href={HF_RESNET18}>microsoft/resnet-18</External>
          {" · "}
          <External href={HF_RESNET50}>microsoft/resnet-50</External>
        </li>
      </Sources>
    </>
  );
}

function PartControle(): JSX.Element {
  return (
    <>
      <Glance kicker="Figure du cours">
        Une photo de chat, puis le top&nbsp;5 ImageNet. Cette figure n’est pas
        rejouée.
      </Glance>
      <div className={styles.text}>
        <p>
          L’image COCO du notebook n’est pas dans le jeu. Elle ne dit rien sur
          nos catégories d’annonce.
        </p>
        <p>
          Le contrôle équivalent est le Studio&nbsp;: une photo devient une
          catégorie, un titre, une confiance, un statut{" "}
          <code className={styles.code} translate="no">
            auto
          </code>{" "}
          ou{" "}
          <code className={styles.code} translate="no">
            a_confirmer
          </code>
          .
        </p>
        <p>
          <Link className={styles.link} to="/">
            Ouvrir le Studio
          </Link>
        </p>
      </div>
      <p className={styles.rowLine}>
        <Mark kind="unmeasured" /> Top&nbsp;5 sur la photo du cours.
      </p>
      <Sources>
        <li>Notebook §2, cellule de visualisation.</li>
        <li>Studio, route /.</li>
      </Sources>
    </>
  );
}

function PartEntrees(): JSX.Element {
  return (
    <>
      <div className={styles.text}>
        <p>
          Le cours fabrique des tenseurs aléatoires, forme 1 × 3 × 224 × 224.
          Ils mesurent le coût du réseau. Pas la qualité.
        </p>
        <p>
          Ici, le chrono it.&nbsp;4 passe sur les {INT8_STATIC.n}&nbsp;photos du
          manifeste. Les mêmes images pour chaque variante. La qualité se lit à
          la partie Qualité, et les effectifs à l’étape Données.
        </p>
        <p>
          L’API sert une photo par requête. Le balayage des lots 1, 2, 4, 8 et
          16 du cours n’a pas été refait.
        </p>
      </div>
      <ul className={styles.stack}>
        <li>
          <Mark kind="unmeasured" /> Tenseurs aléatoires.
        </li>
        <li>
          <Mark kind="unmeasured" /> Débit selon la taille de lot du réseau.
        </li>
        <li>
          <Mark kind="measured" /> {INT8_STATIC.n}&nbsp;photos proxy, une à la
          fois.
        </li>
      </ul>
      <Sources>
        <li>Notebook §3 et §6.</li>
        <FileSource path="data/test_set/manifest.csv" />
        <FileSource path={SOURCE_EVALUATE} />
      </Sources>
    </>
  );
}

function PartIndicateurs(): JSX.Element {
  return (
    <>
      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <caption className={styles.caption}>
            Les quatre indicateurs du cours, répondus avec les mesures du
            projet.
          </caption>
          <thead>
            <tr>
              <th scope="col">Indicateur</th>
              <th scope="col">Question</th>
              <th scope="col">Ici</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">Latence</th>
              <td>Combien de temps attend-on&nbsp;?</td>
              <td>
                Requête {frMs(rampAt(1).p50)} p50, 1&nbsp;vCPU. Inférence{" "}
                {frMs(INT8_STATIC.p50)} p50.
              </td>
            </tr>
            <tr>
              <th scope="row">Débit</th>
              <td>Combien d’images par seconde&nbsp;?</td>
              <td>
                {frReq(rampAt(1).rps)} à 1 utilisateur. {frReq(rampAt(16).rps)}{" "}
                à 16, toujours 1&nbsp;vCPU.
              </td>
            </tr>
            <tr>
              <th scope="row">Mémoire</th>
              <td>Est-ce que ça tient&nbsp;?</td>
              <td>Fichier 24,9&nbsp;Mo. Repos 157&nbsp;Mo. Charge 260&nbsp;Mo.</td>
            </tr>
            <tr>
              <th scope="row">Préchauffage</th>
              <td>Le début est-il plus lent&nbsp;?</td>
              <td>
                3 photos hors chrono. L’écart de durée n’est pas publié.{" "}
                <Mark kind="unmeasured" />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <Sources>
        <li>Notebook §4.</li>
        <FileSource path={SOURCE_CPU1} />
        <FileSource path={INT8_STATIC.file} />
        <FileSource path={SOURCE_IT4} />
        <FileSource path={SOURCE_IT5} />
      </Sources>
    </>
  );
}

function PartProtocole(): JSX.Element {
  return (
    <>
      <ol className={styles.steps}>
        <li>
          <code className={styles.code} translate="no">
            model.eval()
          </code>{" "}
          et{" "}
          <code className={styles.code} translate="no">
            inference_mode
          </code>{" "}
          sur la référence PyTorch. L’ONNX n’a pas de gradient&nbsp;:{" "}
          <code className={styles.code} translate="no">
            session.run
          </code>
          .
        </li>
        <li>
          Préchauffage&nbsp;: 3 photos, hors chrono. Défaut de{" "}
          <code className={styles.code} translate="no">
            evaluate.py
          </code>
          .
        </li>
        <li>
          Puis {INT8_STATIC.n}&nbsp;mesures, une par photo, avec{" "}
          <code className={styles.code} translate="no">
            time.perf_counter
          </code>
          .
        </li>
        <li>
          Machine it.&nbsp;4&nbsp;: 2&nbsp;vCPU, CPU seulement. Même jeu pour
          les quatre variantes.
        </li>
      </ol>
      <p className={styles.rowLine}>
        <Mark kind="na" />{" "}
        <code className={styles.code} translate="no">
          torch.cuda.synchronize
        </code>
        . Pas de CUDA&nbsp;: rien à attendre.
      </p>
      <p className={styles.caption}>
        Le chrono entoure{" "}
        <code className={styles.code} translate="no">
          predict_proba
        </code>
        . Côté ONNX, cela inclut le prétraitement numpy, le réseau et le
        softmax. Ce n’est pas le réseau seul du cours.
      </p>
      <Sources>
        <li>Notebook §5.</li>
        <FileSource path={SOURCE_EVALUATE} />
        <FileSource path={SOURCE_MODEL} />
        <FileSource path={SOURCE_IT4} />
      </Sources>
    </>
  );
}

function PartPercentiles(): JSX.Element {
  return (
    <>
      <p className={styles.caption}>
        Inférence it.&nbsp;4, {INT8_STATIC.n}&nbsp;photos, 2&nbsp;vCPU.{" "}
        <Mark kind="measured" />
      </p>
      <dl className={styles.metrics}>
        <div className={styles.metric}>
          <dt>Moyenne</dt>
          <dd>{frMs(INT8_STATIC.mean)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>p50</dt>
          <dd>{frMs(INT8_STATIC.p50)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>p95</dt>
          <dd>{frMs(INT8_STATIC.p95)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>p99</dt>
          <dd>absent</dd>
        </div>
      </dl>
      <p className={styles.rowLine}>
        <Mark kind="unmeasured" /> p99 de l’inférence.{" "}
        <code className={styles.code} translate="no">
          evaluate.py
        </code>{" "}
        n’écrit pas ce percentile, et les échantillons ne sont pas dans le
        JSON.
      </p>
      <Glance kicker="Là où la queue se voit">
        À 10&nbsp;req/s, {RATE_10.n.toLocaleString("fr-FR")}&nbsp;requêtes&nbsp;:
        moyenne {frMs(RATE_10.mean)}, p50 {frMs(RATE_10.p50)}, p99{" "}
        {frMs(RATE_10.p99)}. La moyenne reste proche du p50. Le p99 part plus
        loin. Zéro erreur.
      </Glance>
      <p className={styles.caption}>
        Ce bloc est une latence HTTP, machine du test de charge. Pas le p99 du
        réseau.
      </p>
      <Sources>
        <li>Notebook §5.1.</li>
        <FileSource path={INT8_STATIC.file} />
        <FileSource path={SOURCE_RATE} />
        <FileSource path={SOURCE_IT5} />
      </Sources>
    </>
  );
}

function PartDebit(): JSX.Element {
  return (
    <>
      <p className={styles.formula} translate="no">
        débit = images / temps
      </p>
      <div className={styles.text}>
        <p>
          Un lot plus grand peut monter le débit et allonger l’attente d’une
          requête. Le cours le montre avec les lots 1 à 16. Ce balayage n’est
          pas dans les preuves.
        </p>
        <p>
          Ce qu’on a mesuré, ce sont des requêtes concurrentes. Une requête, une
          photo.
        </p>
      </div>
      <dl className={styles.metrics}>
        <div className={styles.metric}>
          <dt>1 util. · 1 vCPU</dt>
          <dd>{frReq(rampAt(1).rps)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>16 util. · 1 vCPU</dt>
          <dd>{frReq(rampAt(16).rps)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>Pic 2 vCPU</dt>
          <dd>{frReq(CPU2_PEAK.rps)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>10 req/s imposées</dt>
          <dd>{frMs(RATE_10.p95)} p95</dd>
        </div>
      </dl>
      <p className={styles.caption}>
        Le pic 2&nbsp;vCPU est à {CPU2_PEAK.users}&nbsp;utilisateurs. À{" "}
        {CPU2_DROP.users}, le débit redescend à {frReq(CPU2_DROP.rps)}. Les
        2&nbsp;vCPU sont partagés avec le générateur de charge.
      </p>
      <p className={styles.rowLine}>
        <Mark kind="unmeasured" /> Courbe débit / taille de lot du réseau.
      </p>
      <Sources>
        <li>Notebook §6.</li>
        <FileSource path={SOURCE_CPU1} />
        <FileSource path={SOURCE_CPU2} />
        <FileSource path={SOURCE_RATE} />
      </Sources>
    </>
  );
}

function PartCharge(): JSX.Element {
  const maxRps = Math.max(...CPU1_RAMP.map((row) => row.rps));
  const maxP50 = Math.max(...CPU1_RAMP.map((row) => row.p50));

  return (
    <>
      <Glance kicker="Ce que l’œil doit voir">
        À 1&nbsp;vCPU, le débit passe de {frReq(rampAt(1).rps)} à{" "}
        {frReq(rampAt(16).rps)}. Le p50, de {frMs(rampAt(1).p50)} à{" "}
        {frMs(rampAt(16).p50)}. Les photos attendent. Ce n’est pas un lot plus
        grand.
      </Glance>
      <figure className={styles.figure}>
        <figcaption className={styles.caption}>
          Montée HTTP, conteneur limité à 1&nbsp;vCPU. Chaque série est ramenée
          à son propre maximum, pour voir la forme. Les millisecondes et les
          req/s ne partagent pas une échelle.
        </figcaption>
        <div className={styles.legend} aria-hidden="true">
          <span>
            <i className={styles.swatchDebit} /> Débit
          </span>
          <span>
            <i className={styles.swatchLatence} /> Latence p50
          </span>
        </div>
        <ul className={styles.chart} aria-hidden="true">
          {CPU1_RAMP.map((row) => (
            <li key={row.users} className={styles.chartRow}>
              <span className={styles.chartUsers}>{row.users}</span>
              <span className={styles.track} title={`${frReq(row.rps)}`}>
                <span
                  className={styles.fillDebit}
                  style={{ width: `${(row.rps / maxRps) * 100}%` }}
                />
              </span>
              <span className={styles.chartValue}>{frReq(row.rps)}</span>
              <span className={styles.track}>
                <span
                  className={styles.fillLatence}
                  style={{ width: `${(row.p50 / maxP50) * 100}%` }}
                />
              </span>
              <span className={styles.chartValue}>{frMs(row.p50)}</span>
            </li>
          ))}
        </ul>
      </figure>
      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <caption className={styles.srOnly}>
            Débit et latence selon le nombre d’utilisateurs simultanés, 1 vCPU.
          </caption>
          <thead>
            <tr>
              <th scope="col">Utilisateurs</th>
              <th scope="col">Débit</th>
              <th scope="col">p50</th>
              <th scope="col">p95</th>
              <th scope="col">p99</th>
            </tr>
          </thead>
          <tbody>
            {CPU1_RAMP.map((row) => (
              <tr key={row.users}>
                <th scope="row">{row.users}</th>
                <td>{frReq(row.rps)}</td>
                <td>{frMs(row.p50)}</td>
                <td>{frMs(row.p95)}</td>
                <td>{frMs(row.p99)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className={styles.rowLine}>
        <Mark kind="unmeasured" /> Le graphique du cours (lot 1 à 16, temps par
        lot). Remplacé ici par la charge HTTP, étiquetée comme telle.
      </p>
      <Sources>
        <li>Notebook §6.1.</li>
        <FileSource path={SOURCE_CPU1} />
        <FileSource path={SOURCE_IT5} />
      </Sources>
    </>
  );
}

function PartMemoire(): JSX.Element {
  return (
    <>
      <Glance kicker="Décision de lecture">
        Le fichier fait 24,9&nbsp;Mo. Le service au repos occupe 157&nbsp;Mo, et
        260&nbsp;Mo en charge. La taille du fichier ne dit pas si ça tient.
      </Glance>
      <dl className={styles.metrics}>
        <div className={styles.metric}>
          <dt>Fichier int8</dt>
          <dd>24,9&nbsp;Mo</dd>
        </div>
        <div className={styles.metric}>
          <dt>RAM au repos</dt>
          <dd>157&nbsp;Mo</dd>
        </div>
        <div className={styles.metric}>
          <dt>RAM en charge</dt>
          <dd>260&nbsp;Mo</dd>
        </div>
        <div className={styles.metric}>
          <dt>Image Docker</dt>
          <dd>551&nbsp;Mo</dd>
        </div>
      </dl>
      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <caption className={styles.caption}>
            Référence PyTorch à côté, même preuve it.&nbsp;4 et it.&nbsp;5.
          </caption>
          <thead>
            <tr>
              <th scope="col">Repère</th>
              <th scope="col">ONNX int8</th>
              <th scope="col">PyTorch fp32</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">Fichier modèle</th>
              <td>24,9&nbsp;Mo</td>
              <td>{PYTORCH_FP32.fileMb}</td>
            </tr>
            <tr>
              <th scope="row">Image Docker</th>
              <td>551&nbsp;Mo</td>
              <td>2,04&nbsp;Go</td>
            </tr>
            <tr>
              <th scope="row">RAM au repos</th>
              <td>157&nbsp;Mo</td>
              <td>276&nbsp;Mo</td>
            </tr>
            <tr>
              <th scope="row">RAM en charge</th>
              <td>260&nbsp;Mo</td>
              <td>533&nbsp;Mo</td>
            </tr>
            <tr>
              <th scope="row">Démarrage</th>
              <td>1,6&nbsp;s</td>
              <td>~7&nbsp;s</td>
            </tr>
          </tbody>
        </table>
      </div>
      <ul className={styles.stack}>
        <li>
          <Mark kind="na" /> Pic mémoire CUDA (allouée / réservée).
        </li>
        <li>
          <Mark kind="unmeasured" /> Taille des paramètres séparée du fichier,
          et pic d’allocations CPU.
        </li>
      </ul>
      <p className={styles.caption}>
        Le cours le dit&nbsp;: entrées, sorties et activations s’ajoutent aux
        poids, et grossissent avec le lot et la résolution. On n’a pas profilé
        ce pic sur CPU. On publie le fichier, l’image et la RAM du conteneur.
      </p>
      <Sources>
        <li>Notebook §7 et §7.1.</li>
        <FileSource path={SOURCE_IT4} />
        <FileSource path={SOURCE_IT5} />
        <FileSource path={SOURCE_EXPORT} />
      </Sources>
    </>
  );
}

function PartChaine(): JSX.Element {
  return (
    <>
      <p className={styles.formula}>
        T = réception + prétraitement + inférence + post-traitement + réponse
      </p>
      <dl className={styles.metrics}>
        <div className={styles.metric}>
          <dt>predict_proba p50</dt>
          <dd>{frMs(INT8_STATIC.p50)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>Requête 1 vCPU p50</dt>
          <dd>{frMs(rampAt(1).p50)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>Machine inférence</dt>
          <dd>2 vCPU</dd>
        </div>
        <div className={styles.metric}>
          <dt>Machine requête</dt>
          <dd>1 vCPU</dd>
        </div>
      </dl>
      <Glance kicker="On ne soustrait pas">
        {frMs(INT8_STATIC.p50)} inclut déjà le prétraitement numpy.{" "}
        {frMs(rampAt(1).p50)} est une requête HTTP sur un conteneur bridé à
        1&nbsp;vCPU. Deux protocoles. L’écart n’est pas «&nbsp;le coût du
        prétraitement&nbsp;».
      </Glance>
      <ul className={styles.stack}>
        <li>
          <Mark kind="unmeasured" /> Prétraitement seul, comme le benchmark
          Pillow du cours.
        </li>
        <li>
          <Mark kind="unmeasured" /> Transfert réseau hors du labo. Les charges
          sont locales, en Docker.
        </li>
        <li>
          <Mark kind="measured" /> File d’attente&nbsp;: partie Charge.
          Démarrage du conteneur&nbsp;: 1,6&nbsp;s, une fois.
        </li>
      </ul>
      <p className={styles.caption}>
        Le prétraitement de prod est décrit à l’étape Préparation&nbsp;: 224×224,
        normalisation ImageNet, pas d’augmentation.
      </p>
      <Sources>
        <li>Notebook §8 et §8.1.</li>
        <FileSource path={SOURCE_MODEL} />
        <FileSource path="app/preprocessing.py" />
        <FileSource path={INT8_STATIC.file} />
        <FileSource path={SOURCE_CPU1} />
      </Sources>
    </>
  );
}

function PartReference(): JSX.Element {
  const maxP50 = Math.max(...BASELINE.map((row) => row.p50));

  return (
    <>
      <Glance kicker="Ce qui cloche, et ce qu’on garde">
        L’int8 dynamique tombe à {frPct(INT8_DYNAMIC.accuracy)} et{" "}
        {frMs(INT8_DYNAMIC.p50)}. Plus lent que PyTorch. On garde l’int8
        statique&nbsp;: {frPct(INT8_STATIC.accuracy)}, {frMs(INT8_STATIC.p50)}.
      </Glance>
      <figure className={styles.figure}>
        <figcaption className={styles.caption}>
          p50 d’inférence, même échelle, {INT8_STATIC.n}&nbsp;photos, 2&nbsp;vCPU.
          Le trait long est la variante écartée.
        </figcaption>
        <ul className={styles.bars}>
          {BASELINE.map((row) => (
            <li key={row.id} className={styles.barRow} data-tone={row.tone}>
              <span className={styles.barLabel}>{row.label}</span>
              <span className={styles.track} aria-hidden="true">
                <span
                  className={styles.fill}
                  style={{ width: `${(row.p50 / maxP50) * 100}%` }}
                />
              </span>
              <span className={styles.barValue}>{frMs(row.p50)}</span>
            </li>
          ))}
        </ul>
      </figure>
      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <caption className={styles.srOnly}>
            Référence des quatre variantes ResNet-50.
          </caption>
          <thead>
            <tr>
              <th scope="col">Variante</th>
              <th scope="col">Décision</th>
              <th scope="col">Accuracy</th>
              <th scope="col">p50</th>
              <th scope="col">p95</th>
              <th scope="col">Moyenne</th>
              <th scope="col">Fichier</th>
            </tr>
          </thead>
          <tbody>
            {BASELINE.map((row) => (
              <tr key={row.id} data-tone={row.tone}>
                <th scope="row">{row.label}</th>
                <td>{row.decision}</td>
                <td>{frPct(row.accuracy)}</td>
                <td>{frMs(row.p50)}</td>
                <td>{frMs(row.p95)}</td>
                <td>{frMs(row.mean)}</td>
                <td>{row.fileMb}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className={styles.caption}>
        Comparaison valable parce que le protocole est le même&nbsp;: ResNet-50,
        2&nbsp;vCPU, CPU, {INT8_STATIC.n}&nbsp;photos, seuil 0,6. Les tailles
        ONNX viennent du rapport d’export. Les 97,7&nbsp;Mo PyTorch viennent de
        la preuve it.&nbsp;4.
      </p>
      <Sources>
        <li>Notebook §9. Fiche de référence du projet.</li>
        {BASELINE.map((row) => (
          <FileSource key={row.id} path={row.file} />
        ))}
        <FileSource path={SOURCE_EXPORT} />
        <FileSource path={SOURCE_IT4} />
      </Sources>
    </>
  );
}

function PartTrace(): JSX.Element {
  return (
    <>
      <div className={styles.text}>
        <p>
          Le cours écrit{" "}
          <code className={styles.code} translate="no">
            baseline_performance.csv
          </code>{" "}
          et{" "}
          <code className={styles.code} translate="no">
            baseline_throughput.csv
          </code>
          . Ces deux fichiers n’ont pas été produits.
        </p>
        <p>
          Le même rôle est tenu par les JSON d’évaluation et de charge, puis
          par MLflow, expérience{" "}
          <code className={styles.code} translate="no">
            marketplace-evaluation
          </code>
          . L’étape Fiche dit ce que MLflow garde&nbsp;: les mesures, pas les
          photos.
        </p>
        <p>
          <Link className={styles.link} to="/parcours?etape=fiche">
            Ouvrir la fiche
          </Link>
        </p>
      </div>
      <ul className={styles.stack}>
        <li>
          <Mark kind="unmeasured" /> Les deux CSV du notebook.
        </li>
        <li>
          <Mark kind="measured" /> JSON it.&nbsp;4 et it.&nbsp;5, runs MLflow.
        </li>
      </ul>
      <Sources>
        <li>Notebook §9.1.</li>
        <FileSource path={SOURCE_IT8} />
        <FileSource path={SOURCE_IT4} />
        <FileSource path={SOURCE_IT5} />
      </Sources>
    </>
  );
}

function PartRetenir(): JSX.Element {
  return (
    <>
      <ol className={styles.ideas}>
        <li>
          <strong>Mesurer avant.</strong> PyTorch {frMs(PYTORCH_FP32.p50)} p50,
          int8 statique {frMs(INT8_STATIC.p50)}. Le gain est lisible parce que
          la référence existe.
        </li>
        <li>
          <strong>Même protocole.</strong> {INT8_STATIC.n}&nbsp;photos, 2&nbsp;vCPU,
          CPU, quatre variantes.
        </li>
        <li>
          <strong>Latence et débit.</strong> {frMs(INT8_STATIC.p50)} d’inférence
          ne sont pas {frMs(rampAt(1).p50)} de requête, ni{" "}
          {frReq(rampAt(1).rps)}.
        </li>
        <li>
          <strong>Pas que le réseau.</strong> Fichier 24,9&nbsp;Mo, image
          551&nbsp;Mo, RAM 157&nbsp;Mo au repos. Le prétraitement seul reste non
          mesuré.
        </li>
        <li>
          <strong>Le besoin.</strong> Une photo à la fois, réponse interactive,
          seuil 0,6. Pas un traitement par gros lots.
        </li>
      </ol>
      <Sources>
        <li>Notebook §10.</li>
        <FileSource path={SOURCE_IT4} />
        <FileSource path={SOURCE_IT5} />
      </Sources>
    </>
  );
}

function PartQuestions(): JSX.Element {
  return (
    <>
      <ol className={styles.qa}>
        <li>
          <p className={styles.q}>Latence ou débit&nbsp;?</p>
          <p>
            La latence est l’attente d’une requête. Le débit est un compte
            d’images par seconde. Ici&nbsp;: {frMs(INT8_STATIC.p50)} p50
            d’inférence, {frMs(rampAt(1).p50)} p50 de requête à 1&nbsp;vCPU,{" "}
            {frReq(rampAt(1).rps)}.
          </p>
        </li>
        <li>
          <p className={styles.q}>Pourquoi un préchauffage&nbsp;?</p>
          <p>
            Les premiers appels chargent caches et kernels.{" "}
            <code className={styles.code} translate="no">
              evaluate.py
            </code>{" "}
            en fait 3, hors chrono. Leur durée n’est pas dans le JSON.{" "}
            <Mark kind="unmeasured" />
          </p>
        </li>
        <li>
          <p className={styles.q}>Pourquoi synchroniser le GPU&nbsp;?</p>
          <p>
            CUDA rend la main avant la fin du calcul. Sans synchro, le chrono
            ment. Ici il n’y a pas de CUDA. <Mark kind="na" />
          </p>
        </li>
        <li>
          <p className={styles.q}>
            Le débit monte-t-il toujours avec le lot&nbsp;?
          </p>
          <p>
            Non, pas systématiquement. Le balayage des lots 1 à 16 n’est pas
            mesuré. Sur la charge, à 1&nbsp;vCPU, le débit va de{" "}
            {frReq(rampAt(1).rps)} à {frReq(rampAt(16).rps)} pendant que le
            p50 va de {frMs(rampAt(1).p50)} à {frMs(rampAt(16).p50)}. À
            2&nbsp;vCPU, le débit culmine à {frReq(CPU2_PEAK.rps)} puis
            redescend à {frReq(CPU2_DROP.rps)}.
          </p>
        </li>
        <li>
          <p className={styles.q}>
            Le temps moyen par image est-il l’attente de l’utilisateur&nbsp;?
          </p>
          <p>
            Non. Dans un lot, ce temps amortit des coûts fixes. L’utilisateur
            envoie une photo et attend la réponse entière. Cette attente
            mesurée est {frMs(rampAt(1).p50)} p50, pas{" "}
            {frMs(INT8_STATIC.p50)}, et pas sur la même machine.
          </p>
        </li>
        <li>
          <p className={styles.q}>
            La taille des paramètres suffit-elle&nbsp;?
          </p>
          <p>
            Non. Fichier 24,9&nbsp;Mo, image 551&nbsp;Mo, RAM 157&nbsp;Mo au
            repos et 260&nbsp;Mo en charge. Le pic d’activations CPU n’est pas
            profilé. <Mark kind="unmeasured" />
          </p>
        </li>
        <li>
          <p className={styles.q}>
            Si le prétraitement dépasse l’inférence, qu’optimise-t-on&nbsp;?
          </p>
          <p>
            Le prétraitement, en premier. Sa durée seule n’est pas mesurée. On
            sait seulement qu’il est déjà dans les {frMs(INT8_STATIC.p50)}, et
            que PyTorch a été sorti de l’image. La requête à{" "}
            {frMs(rampAt(1).p50)} ajoute HTTP, décodage, file et réponse.
          </p>
        </li>
      </ol>
      <Sources>
        <li>Notebook §11. Réponses bornées aux preuves du projet.</li>
        <FileSource path={SOURCE_EVALUATE} />
        <FileSource path={SOURCE_IT4} />
        <FileSource path={SOURCE_CPU1} />
        <FileSource path={SOURCE_CPU2} />
      </Sources>
    </>
  );
}

const PART_BODY: Record<DiagnosticPartId, () => JSX.Element> = {
  qualite: PartQualite,
  question: PartQuestion,
  modele: PartModele,
  controle: PartControle,
  entrees: PartEntrees,
  indicateurs: PartIndicateurs,
  protocole: PartProtocole,
  percentiles: PartPercentiles,
  debit: PartDebit,
  charge: PartCharge,
  memoire: PartMemoire,
  chaine: PartChaine,
  reference: PartReference,
  trace: PartTrace,
  retenir: PartRetenir,
  questions: PartQuestions,
};

export function PanelMesure(): JSX.Element {
  const [params, setParams] = useSearchParams();
  const index = partIndex(params.get("partie"));
  const part = DIAGNOSTIC_PARTS[index];
  const Body = PART_BODY[part.id];
  const headingRef = useRef<HTMLHeadingElement>(null);
  const mounted = useRef(false);
  const openedOnPart = useRef(params.get("partie"));

  useEffect(() => {
    const behavior = prefersReducedMotion() ? "auto" : "smooth";
    if (!mounted.current) {
      mounted.current = true;
      if (!openedOnPart.current) return;
    }
    headingRef.current?.focus();
    headingRef.current?.scrollIntoView({ block: "start", behavior });
  }, [part.id]);

  function aller(nextIndex: number) {
    const next = new URLSearchParams(params);
    next.set("etape", "mesure");
    next.set("partie", DIAGNOSTIC_PARTS[nextIndex].id);
    setParams(next);
  }

  return (
    <section className={styles.panel} aria-labelledby="panel-mesure-titre">
      <h2 id="panel-mesure-titre" className={styles.title}>
        Mesure
      </h2>
      <p className={styles.caption}>
        D’abord la qualité. Puis le diagnostic du cours, une partie à la fois.
        It.&nbsp;4 et it.&nbsp;5 ouvrent cette étape.
      </p>

      <h3 className={styles.railTitle}>Parties du diagnostic</h3>
      <ul className={styles.rail} aria-label="Parties du diagnostic">
        {DIAGNOSTIC_PARTS.map((item, itemIndex) => {
          const current = item.id === part.id;
          return (
            <li key={item.id}>
              <button
                type="button"
                aria-current={current ? "step" : undefined}
                onClick={() => aller(itemIndex)}
              >
                <span className={styles.railIndex}>
                  {String(itemIndex + 1).padStart(2, "0")}
                </span>
                {item.nav}
              </button>
            </li>
          );
        })}
      </ul>

      <article className={styles.part} data-partie={part.id} aria-labelledby="diagnostic-part-title">
        <p className={styles.course}>{part.course}</p>
        <h3
          id="diagnostic-part-title"
          className={styles.partTitle}
          tabIndex={-1}
          ref={headingRef}
        >
          {part.title}
        </h3>
        <Body />
      </article>

      <div className={styles.partNav}>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => aller(index - 1)}
          disabled={index === 0}
        >
          Partie précédente
        </button>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => aller(index + 1)}
          disabled={index === DIAGNOSTIC_PARTS.length - 1}
        >
          Partie suivante
        </button>
      </div>
      <p className={styles.meta}>
        Partie {index + 1} / {DIAGNOSTIC_PARTS.length}
      </p>
    </section>
  );
}
