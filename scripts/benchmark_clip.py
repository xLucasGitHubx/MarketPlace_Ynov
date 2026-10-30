"""Benchmark CLIP zero-shot sur le jeu de test (décision du LLM Council du 30/10).

CLIP compare l'image à des descriptions textuelles. Chaque catégorie d'annonce
est décrite par une liste d'objets typiques (inspirée des sous-catégories d'une
marketplace, écrite AVANT de regarder les erreurs du jeu de test). Les scores
des objets sont cumulés par catégorie : exactement la même logique métier que
pour ResNet (business.suggest), seul le vocabulaire change.

Ce script reste un benchmark : CLIP ne remplace ResNet en production que si la
mesure le justifie (accuracy ≥ 80 % et p95 < 500 ms).

Usage : python scripts/benchmark_clip.py [--vocab detaille|generique] [--model openai/clip-vit-base-patch32] [--mlflow]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from app.business import CategoryMap, ClassInfo, suggest  # noqa: E402
from scripts.evaluate import TEST_DIR, evaluate_predictor, log_to_mlflow  # noqa: E402

# Catégorie -> [(objet en anglais pour CLIP, titre suggéré en français)]
VOCABULARY: dict[str, list[tuple[str, str]]] = {
    "Électronique": [
        ("smartphone", "Smartphone"), ("laptop computer", "Ordinateur portable"),
        ("desktop computer", "Ordinateur de bureau"), ("computer monitor", "Écran d'ordinateur"),
        ("computer keyboard", "Clavier"), ("computer mouse", "Souris"), ("tablet", "Tablette"),
        ("television", "Télévision"), ("headphones", "Casque audio"), ("speaker", "Enceinte"),
        ("digital camera", "Appareil photo"), ("video game console", "Console de jeux"),
        ("game controller", "Manette"), ("printer", "Imprimante"), ("mp3 player", "Baladeur MP3"),
        ("video projector", "Vidéoprojecteur"), ("calculator", "Calculatrice"),
    ],
    "Maison et meubles": [
        ("sofa", "Canapé"), ("armchair", "Fauteuil"), ("chair", "Chaise"), ("table", "Table"),
        ("desk", "Bureau"), ("bed", "Lit"), ("mattress", "Matelas"), ("wardrobe", "Armoire"),
        ("cabinet", "Meuble de rangement"), ("bookshelf", "Bibliothèque"), ("lamp", "Lampe"),
        ("chandelier", "Lustre"), ("rug", "Tapis"), ("mirror", "Miroir"), ("vase", "Vase"),
        ("plates and dishes", "Vaisselle"), ("mug", "Mug"), ("teapot", "Théière"),
        ("cooking pot", "Casserole"), ("frying pan", "Poêle"), ("kitchen utensils", "Ustensiles de cuisine"),
    ],
    "Électroménager": [
        ("refrigerator", "Réfrigérateur"), ("washing machine", "Lave-linge"), ("dishwasher", "Lave-vaisselle"),
        ("microwave oven", "Micro-ondes"), ("oven", "Four"), ("coffee machine", "Machine à café"),
        ("electric kettle", "Bouilloire électrique"), ("toaster", "Grille-pain"), ("bread maker", "Machine à pain"),
        ("vacuum cleaner", "Aspirateur"), ("blender", "Mixeur"), ("hair dryer", "Sèche-cheveux"),
        ("clothes iron", "Fer à repasser"), ("electric fan", "Ventilateur"), ("space heater", "Chauffage d'appoint"),
    ],
    "Vêtements et accessoires": [
        ("t-shirt", "T-shirt"), ("shirt", "Chemise"), ("dress", "Robe"), ("jeans", "Jean"),
        ("jacket", "Veste"), ("coat", "Manteau"), ("sweater", "Pull"), ("shoes", "Chaussures"),
        ("sneakers", "Baskets"), ("boots", "Bottes"), ("hat", "Chapeau"), ("cap", "Casquette"),
        ("handbag", "Sac à main"), ("backpack", "Sac à dos"), ("wristwatch", "Montre"),
        ("glasses", "Lunettes"), ("jewelry", "Bijou"), ("necktie", "Cravate"), ("socks", "Chaussettes"),
        ("scarf", "Écharpe"),
    ],
    "Sport et loisirs": [
        ("bicycle", "Vélo"), ("tennis racket", "Raquette de tennis"), ("soccer ball", "Ballon de football"),
        ("basketball", "Ballon de basket"), ("golf ball", "Balle de golf"), ("golf club", "Club de golf"),
        ("skis", "Skis"), ("surfboard", "Planche de surf"), ("skateboard", "Skateboard"),
        ("dumbbell", "Haltère"), ("fitness equipment", "Appareil de fitness"), ("camping tent", "Tente"),
        ("fishing rod", "Canne à pêche"), ("kayak", "Kayak"), ("boxing gloves", "Gants de boxe"),
        ("baseball bat", "Batte de baseball"), ("baseball glove", "Gant de baseball"), ("bowling ball", "Boule de bowling"),
    ],
    "Jeux et jouets": [
        ("teddy bear", "Peluche"), ("doll", "Poupée"), ("toy car", "Petite voiture"), ("lego bricks", "Lego"),
        ("board game", "Jeu de société"), ("jigsaw puzzle", "Puzzle"), ("playing cards", "Jeu de cartes"),
        ("dice", "Dés"), ("chess board", "Jeu d'échecs"), ("children's toy", "Jouet"), ("yo-yo", "Yo-yo"),
        ("toy figure", "Figurine"),
    ],
    "Véhicules et pièces": [
        ("car", "Voiture"), ("motorcycle", "Moto"), ("scooter", "Scooter"), ("truck", "Camion"),
        ("van", "Utilitaire"), ("bus", "Bus"), ("boat", "Bateau"), ("car tire", "Pneu"), ("car wheel", "Jante"),
        ("car part", "Pièce auto"), ("steering wheel", "Volant"), ("motorcycle helmet", "Casque moto"),
        ("snowmobile", "Motoneige"), ("fire truck", "Camion de pompiers"),
    ],
    "Bricolage et jardin": [
        ("hammer", "Marteau"), ("screwdriver", "Tournevis"), ("power drill", "Perceuse"), ("saw", "Scie"),
        ("wrench", "Clé"), ("toolbox", "Boîte à outils"), ("ladder", "Échelle"), ("lawn mower", "Tondeuse"),
        ("wheelbarrow", "Brouette"), ("garden tools", "Outils de jardin"), ("flashlight", "Lampe torche"),
        ("paint brush", "Pinceau"), ("garden furniture", "Salon de jardin"), ("flower pot", "Pot de fleurs"),
        ("mailbox", "Boîte aux lettres"), ("bird bath", "Bain d'oiseaux"), ("welding mask", "Masque de soudure"),
    ],
    "Livres et musique": [
        ("book", "Livre"), ("comic book", "Bande dessinée"), ("magazine", "Magazine"), ("guitar", "Guitare"),
        ("electric guitar", "Guitare électrique"), ("piano", "Piano"), ("violin", "Violon"),
        ("drum kit", "Batterie"), ("trumpet", "Trompette"), ("saxophone", "Saxophone"),
        ("harmonica", "Harmonica"), ("harp", "Harpe"), ("mandolin", "Mandoline"), ("tambourine", "Tambourin"),
        ("xylophone", "Xylophone"), ("french horn", "Cor"), ("vinyl record", "Vinyle"), ("CD", "CD"),
        ("sheet music", "Partition"),
    ],
    "Autre": [
        ("dog", "Chien"), ("cat", "Chat"), ("horse", "Cheval"), ("wild animal", "Animal"), ("bird", "Oiseau"),
        ("insect", "Insecte"), ("landscape", "Paysage"), ("food", "Nourriture"), ("plant", "Plante"),
        ("person", "Personne"), ("building", "Bâtiment"), ("monument", "Monument"),
    ],
}
# Variante « aveugle » : uniquement des descriptions de niveau catégorie, sans aucun
# objet précis. Sert de contrôle : le vocabulaire détaillé ci-dessus a été écrit en
# connaissant les classes sources du jeu de test (cf. scripts/build_test_set.py),
# ce qui peut l'avantager. Si la variante générique tient aussi, le gain est robuste.
VOCABULARY_GENERIC: dict[str, list[tuple[str, str]]] = {
    "Électronique": [("electronic device", "Appareil électronique"), ("consumer electronics", "Électronique")],
    "Maison et meubles": [("piece of furniture", "Meuble"), ("home decoration", "Décoration"),
                          ("kitchenware", "Ustensile de cuisine")],
    "Électroménager": [("household appliance", "Électroménager"), ("kitchen appliance", "Appareil de cuisine")],
    "Vêtements et accessoires": [("piece of clothing", "Vêtement"), ("fashion accessory", "Accessoire de mode"),
                                 ("pair of shoes", "Chaussures")],
    "Sport et loisirs": [("sports equipment", "Article de sport"), ("bicycle", "Vélo")],
    "Jeux et jouets": [("toy", "Jouet"), ("game", "Jeu")],
    "Véhicules et pièces": [("vehicle", "Véhicule"), ("car part", "Pièce auto")],
    "Bricolage et jardin": [("tool", "Outil"), ("gardening equipment", "Matériel de jardin")],
    "Livres et musique": [("book", "Livre"), ("musical instrument", "Instrument de musique")],
    "Autre": [("animal", "Animal"), ("food", "Nourriture"), ("landscape", "Paysage"), ("person", "Personne")],
}
TEMPLATES = ["a photo of a {}.", "a photo of a {} for sale.", "a close-up photo of a {}."]


def build_category_map(vocabulary: dict[str, list[tuple[str, str]]] = VOCABULARY) -> CategoryMap:
    classes = tuple(ClassInfo(en, cat, fr) for cat, items in vocabulary.items() for en, fr in items)
    return CategoryMap(categories=tuple(vocabulary), classes=classes)


class ClipZeroShotPredictor:
    """Encodeur image CLIP + embeddings texte pré-calculés une fois au démarrage."""

    def __init__(self, model_id: str, cache_dir: str | None, cmap: CategoryMap):
        import torch
        from transformers import CLIPModel, CLIPProcessor

        self._torch = torch
        self.model = CLIPModel.from_pretrained(model_id, cache_dir=cache_dir).eval()
        self.processor = CLIPProcessor.from_pretrained(model_id, cache_dir=cache_dir)
        with torch.inference_mode():
            embeds = []
            for c in cmap.classes:  # moyenne des gabarits de phrase (« prompt ensembling »)
                tok = self.processor(text=[t.format(c.label) for t in TEMPLATES], return_tensors="pt", padding=True)
                e = self.model.get_text_features(**tok)
                e = e / e.norm(dim=-1, keepdim=True)
                e = e.mean(dim=0)
                embeds.append(e / e.norm())
            self.text_embeds = torch.stack(embeds)  # (n_classes, d)
        self.scale = self.model.logit_scale.exp().item()
        self.name = model_id.split("/")[-1] + "-zeroshot-pytorch-fp32"
        if len(cmap.classes) < 40:
            self.name += "-generique"

    def predict_proba(self, image) -> np.ndarray:
        torch = self._torch
        with torch.inference_mode():
            pix = self.processor(images=image, return_tensors="pt")["pixel_values"]
            img = self.model.get_image_features(pixel_values=pix)
            img = img / img.norm(dim=-1, keepdim=True)
            logits = (self.scale * img @ self.text_embeds.T)[0]
            return torch.softmax(logits, dim=-1).numpy().astype(np.float64)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="openai/clip-vit-base-patch32")
    ap.add_argument("--cache-dir", default=os.getenv("MODEL_CACHE_DIR", "models/hf"))
    ap.add_argument("--vocab", choices=["detaille", "generique"], default="detaille")
    ap.add_argument("--threshold", type=float, default=0.6)
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--mlflow", action="store_true")
    ap.add_argument("--tracking-uri", default=os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db"))
    args = ap.parse_args()

    cmap = build_category_map(VOCABULARY if args.vocab == "detaille" else VOCABULARY_GENERIC)
    predictor = ClipZeroShotPredictor(args.model, args.cache_dir, cmap)
    res = evaluate_predictor(
        predictor, lambda p, t: suggest(p, threshold=t, top_k=args.top_k, cmap=cmap), args.threshold, TEST_DIR
    )
    model_dir = f"*{args.model.split('/')[-1]}*/**/"
    weights = [w for pat in ("model.safetensors", "pytorch_model.bin")
               for w in sorted(Path(args.cache_dir).rglob(model_dir + pat))
               if ".no_exist" not in w.parts and w.resolve().stat().st_size > 0]
    size = round(weights[0].resolve().stat().st_size / 1_048_576, 1) if weights else None
    res.update({"backend": "clip-pytorch", "top_k": args.top_k, "taille_modele_mo": size,
                "n_descriptions": len(cmap.classes)})

    print(json.dumps({k: v for k, v in res.items() if k != "erreurs"}, ensure_ascii=False, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.mlflow:
        run_id = log_to_mlflow(res, args.tracking_uri, {"n_descriptions": len(cmap.classes),
                                                        "gabarits": len(TEMPLATES), "vocabulaire": args.vocab})
        print(f"Run MLflow {run_id} -> {args.tracking_uri}")


if __name__ == "__main__":
    main()
