import { useId, type JSX } from "react";
import styles from "./SchemaCycle.module.css";

const STEPS = [
  { id: "besoin", label: "Besoin", lines: ["Besoin"], col: 0, row: 0 },
  {
    id: "donnees",
    label: "Données citées",
    lines: ["Données citées"],
    col: 1,
    row: 0,
  },
  {
    id: "preparation",
    label: "Photo 224",
    lines: ["Photo 224"],
    col: 2,
    row: 0,
  },
  {
    id: "modele",
    label: "ResNet déjà entraîné",
    lines: ["ResNet déjà", "entraîné"],
    col: 3,
    row: 0,
  },
  {
    id: "mesure",
    label: "Accuracy et seuil",
    lines: ["Accuracy et seuil"],
    col: 3,
    row: 1,
  },
  {
    id: "fiche",
    label: "Fiche et MLflow",
    lines: ["Fiche et MLflow"],
    col: 2,
    row: 1,
  },
  {
    id: "production",
    label: "Docker puis Azure",
    lines: ["Docker puis Azure"],
    col: 1,
    row: 1,
  },
  {
    id: "surveillance",
    label: "Surveillance sans photo",
    lines: ["Surveillance", "sans photo"],
    col: 0,
    row: 1,
  },
] as const;

const NODE_W = 210;
const NODE_H = 78;
const GAP_X = 32;
const GAP_Y = 100;
const PAD_X = 20;
const PAD_Y = 16;
const COLS = 4;
const ROWS = 2;
const ARROW_GAP = 8;

const VIEW_W = PAD_X * 2 + COLS * NODE_W + (COLS - 1) * GAP_X;
const VIEW_H = PAD_Y * 2 + ROWS * NODE_H + (ROWS - 1) * GAP_Y;

type Box = { x: number; y: number; w: number; h: number };

function boxOf(col: number, row: number): Box {
  return {
    x: PAD_X + col * (NODE_W + GAP_X),
    y: PAD_Y + row * (NODE_H + GAP_Y),
    w: NODE_W,
    h: NODE_H,
  };
}

function linkEnds(from: Box, to: Box): [number, number, number, number] {
  const fromCx = from.x + from.w / 2;
  const fromCy = from.y + from.h / 2;
  const toCx = to.x + to.w / 2;
  const toCy = to.y + to.h / 2;
  const dx = toCx - fromCx;
  const dy = toCy - fromCy;

  if (Math.abs(dx) >= Math.abs(dy)) {
    if (dx > 0) {
      return [from.x + from.w + ARROW_GAP, fromCy, to.x - ARROW_GAP, toCy];
    }
    return [from.x - ARROW_GAP, fromCy, to.x + to.w + ARROW_GAP, toCy];
  }

  if (dy > 0) {
    return [fromCx, from.y + from.h + ARROW_GAP, toCx, to.y - ARROW_GAP];
  }
  return [fromCx, from.y - ARROW_GAP, toCx, to.y + to.h + ARROW_GAP];
}

function returnToDonnees(from: Box, to: Box): {
  d: string;
  labelX: number;
  labelY: number;
} {
  const xStart = from.x + from.w / 2;
  const yStart = from.y - 2;
  const xEnd = to.x + to.w / 2;
  const yEnd = to.y + to.h + ARROW_GAP;
  const yRail = (yStart + yEnd) / 2;

  return {
    d: `M ${xStart} ${yStart} V ${yRail} H ${xEnd} V ${yEnd}`,
    labelX: (xStart + xEnd) / 2,
    labelY: yRail - 14,
  };
}

export function SchemaCycle({
  actif,
  onChoisir,
}: {
  actif: string;
  onChoisir: (id: string) => void;
}): JSX.Element {
  const uid = useId().replace(/:/g, "");
  const forwardMarkerId = `schema-cycle-forward-${uid}`;
  const returnMarkerId = `schema-cycle-return-${uid}`;
  const descriptionId = `schema-cycle-desc-${uid}`;

  const boxes = STEPS.map((step) => boxOf(step.col, step.row));
  const loop = returnToDonnees(boxes[7], boxes[1]);

  return (
    <div
      className={styles.wrap}
      role="group"
      aria-label="Schéma du cycle MLOps"
      aria-describedby={descriptionId}
    >
      <p id={descriptionId} className={styles.srOnly}>
        Huit étapes, du besoin à la surveillance. La flèche « photos
        différentes » relie la surveillance aux données citées.
      </p>
      <svg
        className={styles.diagram}
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <marker
            id={forwardMarkerId}
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto"
          >
            <path d="M 0 0.8 L 9 5 L 0 9.2 Z" fill="var(--muted)" />
          </marker>
          <marker
            id={returnMarkerId}
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto"
          >
            <path d="M 0 0.8 L 9 5 L 0 9.2 Z" fill="var(--accent)" />
          </marker>
        </defs>

        <g className={styles.decor} aria-hidden="true">
          {boxes.slice(0, -1).map((from, index) => {
            const [x1, y1, x2, y2] = linkEnds(from, boxes[index + 1]);
            return (
              <path
                key={STEPS[index].id}
                className={styles.arrow}
                d={`M ${x1} ${y1} L ${x2} ${y2}`}
                markerEnd={`url(#${forwardMarkerId})`}
              />
            );
          })}
          <path
            className={styles.returnArrow}
            d={loop.d}
            markerEnd={`url(#${returnMarkerId})`}
          />
          <text
            className={styles.returnLabel}
            x={loop.labelX}
            y={loop.labelY}
            textAnchor="middle"
          >
            photos différentes
          </text>
        </g>

        {STEPS.map((step, index) => {
          const box = boxes[index];
          const isActive = actif === step.id;
          const firstBaseline = box.y + (step.lines.length === 1 ? 58 : 50);

          return (
            <g
              key={step.id}
              className={isActive ? `${styles.node} ${styles.actif}` : styles.node}
              role="button"
              tabIndex={0}
              aria-label={`Étape ${index + 1} : ${step.label}`}
              aria-current={isActive ? "step" : undefined}
              data-actif={isActive ? "true" : undefined}
              onClick={() => onChoisir(step.id)}
              onKeyDown={(event) => {
                if (event.key !== "Enter" && event.key !== " ") return;
                event.preventDefault();
                onChoisir(step.id);
              }}
            >
              <rect
                className={styles.shape}
                x={box.x}
                y={box.y}
                width={box.w}
                height={box.h}
                rx={8}
              />
              <rect
                className={styles.indexChip}
                x={box.x + 12}
                y={box.y + 10}
                width={30}
                height={18}
                rx={4}
              />
              <text
                className={styles.index}
                x={box.x + 27}
                y={box.y + 19}
                textAnchor="middle"
                dominantBaseline="central"
              >
                {String(index + 1).padStart(2, "0")}
              </text>
              <text className={styles.label} x={box.x + 14} y={firstBaseline}>
                {step.lines.map((line, lineIndex) => (
                  <tspan
                    key={`${step.id}-${lineIndex}`}
                    x={box.x + 14}
                    dy={lineIndex === 0 ? 0 : 16}
                  >
                    {line}
                  </tspan>
                ))}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
