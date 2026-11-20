/** Itérations du sujet, dans l’ordre de numérotation des preuves. */
export const ITERATIONS = [
  { id: "squelette", label: "Squelette", it: "1", step: "besoin" },
  { id: "cerveau", label: "Cerveau", it: "2", step: "modele" },
  { id: "docker", label: "Docker", it: "3", step: "production" },
  { id: "onnx", label: "ONNX", it: "4", step: "mesure" },
  { id: "charge", label: "Charge", it: "5", step: "mesure" },
  { id: "securite", label: "Sécurité", it: "6", step: "surveillance" },
  { id: "azure", label: "Azure", it: "7", step: "production" },
  { id: "mlflow", label: "MLflow", it: "8", step: "fiche" },
  { id: "facture", label: "Facture", it: "9", step: "production" },
] as const;

export type IterationId = (typeof ITERATIONS)[number]["id"];

export const ORAL_STEPS = [
  { id: "besoin", serves: null },
  {
    id: "donnees",
    serves: "Jeu du cerveau et de l’ONNX. Pas une itération à part.",
  },
  {
    id: "preparation",
    serves: "La photo que le ResNet sait lire. Pas une itération à part.",
  },
  { id: "modele", serves: null },
  { id: "mesure", serves: null },
  { id: "fiche", serves: null },
  { id: "production", serves: null },
  { id: "surveillance", serves: null },
] as const;

export function iterationsForStep(stepId: string) {
  return ITERATIONS.filter((item) => item.step === stepId);
}
