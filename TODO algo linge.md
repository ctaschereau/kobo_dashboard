# TODO : algorithme d'habillement (« algo linge »)

Idées pour améliorer les icônes de vêtements du panneau. **Rien de tout ça n'est codé** : c'est
une liste de pistes à trier avant de toucher à `clothes()` et `draw_weather()` dans
`server/dashboard.py`.

## Le problème

S'il fait 0° au départ mais 14° plus tard, afficher « manteau chaud, bottes, tuque, mitaines »
pour toute la journée est sous-optimal. La règle actuelle regarde **un seul chiffre**, alors que
ce qui compte, c'est la température **pendant les sorties** des enfants.

## Comment ça marche aujourd'hui

**Température de référence** (une seule valeur pour tout l'affichage) :

- avant midi : la température **ressentie maintenant** ;
- à partir de midi (`now.hour >= 12`) : la **moyenne de la min et de la max de demain**.

**Règles** (`clothes()`), appliquées à cette température de référence :

| Vêtement | Condition |
|---|---|
| T-shirt | 20° ou plus |
| Manteau | moins de 20° (« Manteau chaud » sous 5°) |
| Pantalon de neige | moins de -10° |
| Bottes | moins de 5°, ou neige |
| Bottes de pluie | pluie, orage, ou 50 % et plus de probabilité de pluie (si les bottes d'hiver ne sont pas déjà affichées) |
| Tuque | moins de 5° |
| Mitaines | moins de 0° |
| Parapluie | pluie ou orage, ou 50 % et plus de probabilité de pluie (pas en cas de neige) |
| Chapeau | max de 25° ou plus, et ciel dégagé ou partiellement nuageux |

Au plus 6 icônes sont affichées.

**Défauts concrets**

- 0° puis 14° : manteau chaud, bottes, tuque et mitaines toute la journée.
- Le basculement à midi est arbitraire : à 11 h 59, on s'habille pour la température de l'instant,
  à 12 h 00 pour demain.
- Une moyenne (min + max) / 2 cache un matin glacial : -4° puis 12° donne 4°, donc aucune mitaine
  alors que le départ est à -4°.
- Les bottes dépendent de la température, pas de l'état du sol (neige, bouette, flaques).
- Aucune notion de ce qu'on peut enlever ou mettre dans le sac.

## Idées

### 1. Raisonner par fenêtres de sortie, pas par température instantanée

Définir deux sorties dans la config (par exemple départ 8 h à 9 h, retour 15 h 30 à 17 h) et
utiliser les prévisions **heure par heure**. Pour chaque fenêtre, calculer la température
ressentie minimale et maximale, les précipitations, etc.

On afficherait la **prochaine sortie** plutôt que le basculement à midi : avant 9 h le départ du
jour, entre 9 h et 15 h le retour, après le retour le départ de demain.

### 2. Séparer « à porter » et « dans le sac »

Habiller pour le moment le plus froid de la sortie, mais marquer ce qui devient inutile plus tard.
Exemple 0° puis 14° : manteau, tuque et mitaines au départ ; au retour, tuque et mitaines « dans
le sac » et un chandail léger.

Si l'écart dans la journée dépasse environ 8 à 10°, afficher **deux rangées** : Départ et Retour.

### 3. Les bottes selon le sol, pas selon la température

- bottes d'hiver : neige au sol ou en prévision, ou bouette (température autour de 0° avec
  précipitations) ;
- bottes de pluie : pluie en prévision, ou pluie récente (flaques) ;
- sinon : espadrilles (aucune icône).

Dans l'exemple 0° puis 14°, sec et sans neige : pas de bottes.

### 4. Une règle par vêtement, avec ses propres seuils

- tuque et mitaines : température **ressentie** (le vent compte), pas la température brute ;
- manteau : ressenti au départ ;
- imperméable ou parapluie : probabilité **et** quantité de pluie sur la fenêtre ;
- chapeau et lunettes : indice UV et ensoleillement.

Sortir les seuils du code vers un petit tableau réglable dans `config.ini`.

### 5. Un réglage « frileux »

Un décalage en degrés (par exemple -2°) pour habiller un peu plus chaud au départ, quand les
jeunes enfants bougent peu, et moins au retour, quand ils ont bougé.

### 6. Des niveaux plutôt que des seuils durs (facultatif)

Au lieu d'un seuil à 5°, trois niveaux qui se chevauchent : manteau d'hiver, manteau mi-saison,
coupe-vent. On pourrait aussi regrouper en « ensembles » (par exemple « ensemble de neige » =
manteau + pantalon + bottes) pour rester à 6 icônes ou moins.

## Données à ajouter (Open-Meteo)

À vérifier dans la documentation d'Open-Meteo avant de coder : les variables **horaires**
`apparent_temperature`, `precipitation`, `precipitation_probability`, `snowfall`, `snow_depth`,
`uv_index`, `wind_speed_10m`, `weather_code`, et la possibilité de demander les dernières heures
(pluie récente) avec `past_hours`.

## Exemple de configuration (à discuter)

```ini
[outings]
# Sorties des enfants (heure début-fin)
depart = 08:00-09:00
retour = 15:30-17:00

[clothing]
# Décalage en degrés : positif = habiller moins chaud, négatif = plus chaud
frileux = -2
```

## Contrainte d'espace

La zone des habits fait environ 300 × 350 px. Deux rangées (Départ / Retour) de 3 icônes à
environ 64 px tiennent, avec une petite étiquette ou une pastille « sac ». Maximum 6 icônes en
tout, comme aujourd'hui.

## Cas de test à écrire

| Situation | Résultat attendu |
|---|---|
| 0° au départ, 14° au retour, sec, sans neige | Départ : manteau, tuque, mitaines. Retour : chandail léger, tuque et mitaines dans le sac. Pas de bottes |
| -15° toute la journée, neige au sol | Manteau chaud, pantalon de neige, bottes, tuque, mitaines |
| 3°, pluie | Manteau, bottes de pluie, parapluie |
| 12° au départ, 22° au retour | Manteau léger, t-shirt dans le sac |
| 27°, ensoleillé | T-shirt, chapeau |
| 1° puis 6°, neige fondante | Bottes (bouette) |
| Week-end | À décider : une seule fenêtre, ou pas de rangée « Départ » |

## Questions ouvertes

- Quelles sont les heures de sortie réelles, en semaine et en fin de semaine ?
- Y a-t-il toujours un sac pour les vêtements en trop ?
- Quels manteaux ont les enfants (hiver, mi-saison, coupe-vent) ?
- Faut-il gérer plusieurs enfants d'âges différents (donc plusieurs réglages « frileux ») ?

## Ordre de réalisation suggéré

1. Récupérer les données horaires et calculer les fenêtres, **sans changer l'affichage**.
2. Bottes selon l'état du sol.
3. « À porter » et « dans le sac » (deux rangées si l'écart est grand).
4. Seuils et réglage « frileux » dans `config.ini`.
