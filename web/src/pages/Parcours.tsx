import { useState, type JSX } from "react";
import { PanelBesoin } from "@/parcours/PanelBesoin";
import { PanelDonnees } from "@/parcours/PanelDonnees";
import { PanelFiche } from "@/parcours/PanelFiche";
import { PanelMesure } from "@/parcours/PanelMesure";
import { PanelModele } from "@/parcours/PanelModele";
import { PanelPreparation } from "@/parcours/PanelPreparation";
import { PanelProduction } from "@/parcours/PanelProduction";
import { PanelSurveillance } from "@/parcours/PanelSurveillance";
import { SchemaCycle } from "@/parcours/SchemaCycle";

const PANELS: Record<string, () => JSX.Element> = {
  besoin: PanelBesoin,
  donnees: PanelDonnees,
  preparation: PanelPreparation,
  modele: PanelModele,
  mesure: PanelMesure,
  fiche: PanelFiche,
  production: PanelProduction,
  surveillance: PanelSurveillance,
};

export function ParcoursPage() {
  const [actif, setActif] = useState("besoin");
  const Panel = PANELS[actif] ?? PanelBesoin;

  return (
    <section className="fade-in" aria-labelledby="parcours-title">
      <h1 id="parcours-title" className="page-title">
        Parcours
      </h1>
      <p className="page-lead">
        Le cycle MLOps du marketplace, du besoin jusqu’à la surveillance. Un clic ouvre
        l’étape.
      </p>
      <SchemaCycle actif={actif} onChoisir={setActif} />
      <div style={{ marginTop: 20 }}>
        <Panel />
      </div>
    </section>
  );
}
