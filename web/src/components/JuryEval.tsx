import { useEffect } from "react";
import { formatAccuracy, formatConfidence, formatMb } from "@/lib/format";
import {
  juryView,
  type JuryBanc,
  type JuryGroup,
  type JuryModel,
  type JuryProtocol,
  type JuryVignetteSource,
} from "@/data/juryEval";

const RAISONS: Record<string, string> = {
  int8_ecarte: "Int8 écarté à l’export : il ne prédit pas.",
  student_absent: "Pas d’ONNX entraîné.",
  onnx_absent: "Fichier ONNX absent sur ce jeu.",
};

const MECANISMES: Record<string, string> = {
  accord: "Accord des deux modèles",
  classe_absente: "Classe absente d’ImageNet",
  puits_autre: "Puits Autre",
  confusion_voisine: "Confusion de catégories voisines",
  erreur_confiante: "Erreur confiante",
  desaccord_modeles: "Désaccord des deux modèles",
};

const ms = new Intl.NumberFormat("fr-FR", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

function formatJuryMs(value: number | null): string {
  if (value == null) return "—";
  return `${ms.format(value)}\u00a0ms`;
}

function bancLabel(banc: JuryBanc | null): string | null {
  if (banc === "it4") return "it. 4, autre machine";
  if (banc === "ce_run") return "ce run, CPU local";
  if (banc === "ce_run_clip") return "ce run, zero-shot";
  return null;
}

function proofKind(model: JuryModel): { className: string; label: string } {
  if (model.metricSource === "measured" && model.role === "comparable") {
    return { className: "provenance-measured", label: "mesuré" };
  }
  if (model.metricSource === "estimated") {
    return { className: "provenance-estimated", label: "estimé" };
  }
  if (model.metricSource === "unmeasured" || model.role === "absent") {
    return { className: "provenance-unmeasured", label: "non mesuré" };
  }
  return { className: "provenance-excluded", label: "écarté" };
}

function defendedAccuracy(model: JuryModel): string {
  if (model.role !== "comparable" || model.metricSource !== "measured") return "—";
  return formatAccuracy(model.accuracy);
}

function defendedScore(model: JuryModel, label: string): string {
  if (model.role !== "comparable" || model.metricSource !== "measured") return "—";
  const score = model.scores[label];
  if (typeof score !== "number") return "—";
  return formatAccuracy(score);
}

function scoreOf(protocol: JuryProtocol, modelId: string, label: string): number | null {
  const model = protocol.models.find((item) => item.id === modelId);
  const score = model?.scores[label];
  return typeof score === "number" ? score : null;
}

function Proof({ model }: { model: JuryModel }) {
  const proof = proofKind(model);
  return (
    <span className="provenance-cell">
      <span className={`provenance ${proof.className}`}>{proof.label}</span>
      <span className="provenance-sub">{model.qualifier}</span>
    </span>
  );
}

function ProtocolTable({ protocol }: { protocol: JuryProtocol }) {
  const showCategories = protocol.headline;
  return (
    <div className="table-wrap">
      <table className="compare-table" data-protocol={protocol.id}>
        <caption className="jury-caption">
          {protocol.headline
            ? `Jeu focal seulement. Accuracy globale sur les ${protocol.n} photos de ce manifeste. Chaque catégorie est à son n.`
            : `Jeu proxy seulement, ${protocol.n} photos, 20 × 10. Ces accuracies ne se mélangent pas avec le jeu focal.`}
        </caption>
        <thead>
          <tr>
            <th scope="col">Modèle</th>
            <th scope="col">Preuve</th>
            <th scope="col">n</th>
            <th scope="col">Accuracy</th>
            {showCategories
              ? protocol.categories.map((category) => (
                  <th key={category.label} scope="col">
                    {category.label}
                    <span className="provenance-sub">n = {category.n}</span>
                  </th>
                ))
              : null}
            <th scope="col">p50</th>
          </tr>
        </thead>
        <tbody>
          {protocol.models.map((model) => {
            const context = bancLabel(model.banc);
            const reason = model.raisonId ? RAISONS[model.raisonId] : null;
            return (
              <tr key={model.id} data-model={model.id} data-role={model.role}>
                <th scope="row">
                  <strong>{model.label}</strong>
                  <span className="model-id" translate="no">
                    {model.id}
                  </span>
                  {reason ? <span className="jury-reason">{reason}</span> : null}
                </th>
                <td>
                  <Proof model={model} />
                </td>
                <td className="num">{model.n == null ? "—" : `n = ${model.n}`}</td>
                <td className="num">{defendedAccuracy(model)}</td>
                {showCategories
                  ? protocol.categories.map((category) => (
                      <td key={category.label} className="num">
                        {defendedScore(model, category.label)}
                      </td>
                    ))
                  : null}
                <td className="num">
                  {model.metricSource === "measured" ? formatJuryMs(model.p50Ms) : "—"}
                  {context ? <span className="provenance-sub">{context}</span> : null}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function AccordTable({ protocol }: { protocol: JuryProtocol }) {
  return (
    <div className="table-wrap">
      <table className="compare-table">
        <caption className="jury-caption">
          {protocol.id === "focal"
            ? `Accord sur le jeu focal, n = ${protocol.n}. ResNet n’entre pas dans cette paire.`
            : `Accord sur le jeu proxy, n = ${protocol.n}.`}
        </caption>
        <thead>
          <tr>
            <th scope="col">Paire</th>
            <th scope="col">Même catégorie</th>
            <th scope="col">Désaccords</th>
            <th scope="col">n</th>
          </tr>
        </thead>
        <tbody>
          {protocol.accord.map((row) => (
            <tr key={`${protocol.id}-${row.modeleA}-${row.modeleB}`}>
              <th scope="row">
                {row.labelA} / {row.labelB}
              </th>
              <td className="num">{formatAccuracy(row.partMemeCategorie)}</td>
              <td className="num">{row.desaccord}</td>
              <td className="num">n = {row.n}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Vignettes({
  groupes,
  source,
}: {
  groupes: JuryGroup[];
  source: JuryVignetteSource;
}) {
  const cards = groupes.reduce((sum, group) => sum + group.items.length, 0);
  if (cards === 0) {
    return (
      <p className="empty-state" data-jury-vignettes="empty">
        Aucune ligne par image : la grille de désaccords reste vide.
      </p>
    );
  }
  const focus = source === "focus" || source === "predictions";
  const sourceText = focus
    ? "Photos réelles du jeu focal, préfixe focus_caltech_. EfficientNet et CLIP, avec la confiance de chacun."
    : "Cas commentés du proxy, n = 20. Ils restent en archive : ce n’est pas la mesure du jeu focal.";
  return (
    <>
      <p className="jury-note">{sourceText}</p>
      {groupes.map((group) =>
        group.items.length === 0 ? null : (
          <div key={group.attendu} className="jury-group">
            <h3 className="jury-group-title">
              {group.attendu}
              {group.n != null ? <span className="jury-n">n = {group.n}</span> : null}
            </h3>
            <p className="jury-note">
              {focus
                ? `${group.items.length} photos de cette catégorie, n = ${group.n ?? "—"}.`
                : `${group.items.length} cas du proxy. Catégorie lue sur n = ${group.n ?? "—"}.`}
            </p>
            <ul className="jury-grid">
              {group.items.map((card) => (
                <li key={card.src} className="jury-card">
                  <img src={card.src} alt={`${card.attendu}, ${card.fichier}`} />
                  <p className="jury-card-kicker">
                    {card.mecanisme ? `${MECANISMES[card.mecanisme] ?? card.mecanisme} · ` : ""}
                    Attendu · {card.attendu}
                    {card.n != null ? ` · n = ${card.n}` : ""}
                  </p>
                  {card.commentaire ? <p className="jury-comment">{card.commentaire}</p> : null}
                  <ul className="jury-preds">
                    {card.predictions.map((pred) => (
                      <li key={pred.id} data-hit={pred.correct ? "ok" : "miss"}>
                        <span className="jury-pred-name">{pred.label}</span>
                        <span>{pred.predit}</span>
                        {pred.confiance != null ? (
                          <span className="num">{formatConfidence(pred.confiance)}</span>
                        ) : (
                          <span className="provenance-sub">confiance non archivée</span>
                        )}
                        {pred.top1 ? (
                          <span className="model-id" translate="no">
                            {pred.top1}
                          </span>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          </div>
        ),
      )}
    </>
  );
}

export function JuryEval() {
  useEffect(() => {
    if (window.location.hash !== "#jury-eval") return;
    document.getElementById("jury-eval")?.scrollIntoView({ block: "start" });
  }, []);

  const view = juryView;
  if (!view) {
    return (
      <section id="jury-eval" className="jury-block" aria-label="Lecture jury">
        <h2 className="jury-title">Lecture jury indisponible.</h2>
        <p className="empty-state">
          Le fichier de preuve n’a pas le format attendu. Le tableau chiffré et la
          grille restent vides.
        </p>
      </section>
    );
  }

  const focal = view.protocoles.find((protocol) => protocol.id === "focal");
  const proxy = view.protocoles.find((protocol) => protocol.id === "proxy");
  if (!focal || !proxy) {
    return (
      <section id="jury-eval" className="jury-block" aria-label="Lecture jury">
        <h2 className="jury-title">Lecture jury indisponible.</h2>
        <p className="empty-state">Les deux protocoles ne sont pas dans le fichier.</p>
      </section>
    );
  }

  const effVeh = scoreOf(focal, "efficientnet-b0-onnx-int8", "Véhicules et pièces");
  const effJeux = scoreOf(focal, "efficientnet-b0-onnx-int8", "Jeux et jouets");
  const clipVeh = scoreOf(focal, "clip-vit-b32", "Véhicules et pièces");
  const clipJeux = scoreOf(focal, "clip-vit-b32", "Jeux et jouets");
  const eff = focal.models.find((model) => model.id === "efficientnet-b0-onnx-int8");
  const clip = focal.models.find((model) => model.id === "clip-vit-b32");
  const resnetProxy = proxy.models.find((model) => model.id === "resnet50-onnx-int8");
  const effProxy = proxy.models.find((model) => model.id === "efficientnet-b0-onnx-int8");
  const clipProxy = proxy.models.find((model) => model.id === "clip-vit-b32");
  const accord = focal.accord[0];
  const warning = view.avertissement;

  return (
    <section id="jury-eval" className="jury-block" aria-label="Lecture jury">
      <h2 className="jury-title">
        Jeu focal, n = {warning.nFocal}. EfficientNet : Véhicules {formatAccuracy(effVeh)}, Jeux{" "}
        {formatAccuracy(effJeux)}. CLIP : Véhicules {formatAccuracy(clipVeh)}, Jeux{" "}
        {formatAccuracy(clipJeux)}.
      </h2>
      <p className="jury-note">
        {focal.detail} Sur les {focal.n} photos de ce manifeste, EfficientNet int8 est à{" "}
        {formatAccuracy(eff?.accuracy)} (p50 {formatJuryMs(eff?.p50Ms ?? null)}, ce run) et CLIP
        générique à {formatAccuracy(clip?.accuracy)} (p50 {formatJuryMs(clip?.p50Ms ?? null)}).
        Accord entre eux : {formatAccuracy(accord?.partMemeCategorie)}. ResNet n’a pas été mesuré
        sur ce jeu : le fichier ONNX est absent.
      </p>

      <ProtocolTable protocol={focal} />
      <AccordTable protocol={focal} />

      <aside className="clip-caveat" role="note" aria-label="Avertissement n = 20">
        <p className="clip-caveat-title">Le n = {warning.nProxy} ne se reporte pas.</p>
        <p>
          Sur le jeu proxy, {warning.modele}, {warning.categorie}, n = {warning.nProxy} :{" "}
          {formatAccuracy(warning.accuracyProxy)}. Ce score ne tient pas à n = {warning.nFocal} :
          le jeu focal donne {formatAccuracy(warning.accuracyFocal)}.
        </p>
      </aside>

      <h3 className="jury-group-title">
        {proxy.titre}, {proxy.n} photos
      </h3>
      <p className="jury-note">
        {proxy.detail} ResNet int8 {formatAccuracy(resnetProxy?.accuracy)}, historique, p50{" "}
        {formatJuryMs(resnetProxy?.p50Ms ?? null)}, autre machine. EfficientNet int8{" "}
        {formatAccuracy(effProxy?.accuracy)}, p50 {formatJuryMs(effProxy?.p50Ms ?? null)}, ce CPU.
        CLIP vocab générique {formatAccuracy(clipProxy?.accuracy)}, p50{" "}
        {formatJuryMs(clipProxy?.p50Ms ?? null)}.
      </p>
      <ProtocolTable protocol={proxy} />
      <p className="jury-note">
        Deux bancs sur le proxy : it. 4 pour le p50 ResNet, ce run sur CPU Windows pour
        EfficientNet et CLIP. Le p50 EfficientNet du jeu focal est une autre mesure.
      </p>
      <AccordTable protocol={proxy} />

      <aside className="clip-caveat" role="note" aria-label="Ce qui n’est pas le chiffre de tête">
        <p className="clip-caveat-title">Le vocabulaire détaillé n’est pas le chiffre de tête.</p>
        <p>
          {`CLIP générique, ${formatAccuracy(clipProxy?.accuracy)} sur le proxy, est le zero-shot à mettre à côté du ResNet : texte contre classement ImageNet puis mapping.`}
          {view.clipDetaille.tailleMo != null
            ? ` Hors Azure, environ ${formatMb(view.clipDetaille.tailleMo)}.`
            : " Hors Azure."}{" "}
          Le statut <span translate="no">space_only</span> veut dire garé : l’inférence
          Space ne fonctionne pas encore.
        </p>
        <p>
          Vocabulaire détaillé : {formatAccuracy(view.clipDetaille.accuracy)} sur n ={" "}
          {view.clipDetaille.n}. Autre protocole, hors du tableau.
        </p>
        <p>MobileNet int8 et le student KD restent écartés, sans accuracy défendue.</p>
      </aside>

      <h3 className="jury-group-title">Photos du jeu focal</h3>
      <Vignettes groupes={view.groupes} source={view.vignettesSource} />

      {view.archive && view.archive.groupes.some((group) => group.items.length > 0) ? (
        <details className="jury-archive">
          <summary>Archive du proxy, n = 20. Ce n’est pas la mesure du jeu focal.</summary>
          <Vignettes groupes={view.archive.groupes} source={view.archive.vignettesSource} />
        </details>
      ) : null}
    </section>
  );
}
