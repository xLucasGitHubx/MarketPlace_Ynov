import { formatMs } from "@/lib/format";
import { useSessionConso } from "@/lib/sessionConso";
import styles from "./CompteurSession.module.css";

const countFr = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });

const usdSession = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 8,
});

export function CompteurSession() {
  const { images, latenceTotaleMs, usdEstime } = useSessionConso();

  return (
    <section className={styles.root} aria-label="Consommation de cette session navigateur">
      <p className={styles.title}>Cette session navigateur</p>
      <p className={styles.note}>
        Photos, temps et coût estimé pour cet onglet. Ce total n’est pas la facture Azure.
      </p>
      <dl className={styles.metrics}>
        <div className={styles.metric}>
          <dt>Photos</dt>
          <dd>{countFr.format(images)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>Temps total</dt>
          <dd>{formatMs(latenceTotaleMs)}</dd>
        </div>
        <div className={styles.metric}>
          <dt>Coût estimé</dt>
          <dd>{usdSession.format(usdEstime)}</dd>
        </div>
      </dl>
      <p className={styles.source}>
        FINOPS.md — taux par million utilisé par l’API : 1,8 × (p95 / 28,6)
      </p>
    </section>
  );
}
