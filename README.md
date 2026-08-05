# examshell

Un simulateur d'examen C en ligne de commande, inspiré de l'examshell de
42 : tu tires des exercices, tu codes ta solution dans ton éditeur, et le
programme te compile en mode strict (`-Wall -Wextra -Werror`), vérifie que
tu n'utilises pas de fonction interdite, puis fait tourner une batterie de
tests sur ta fonction/ton programme — le tout avec un minuteur si tu choisis
le mode examen.

## Lancer

```sh
python3 -m examshell        # ou: ./bin/examshell
```

Menu principal :

- **Examen chronométré** : choisis un rank (1, 2 ou 3), le programme tire
  aléatoirement une poignée d'exercices de ce rank et démarre le minuteur
  (60/90/120 min selon le rank). À la fin du temps, ou quand tu quittes,
  un score final est affiché et sauvegardé (`report.json`).
- **Mode entraînement** : aucun minuteur, tous les exercices sont
  disponibles, tentatives illimitées, et tu peux révéler la solution de
  référence avec `sol <n>`.

Dans les deux modes : tape le numéro d'un exercice pour ouvrir ton
`$EDITOR` (nano/vim en secours) sur le fichier à compléter. Dès que tu
fermes l'éditeur, la compilation et les tests tournent automatiquement.

Commandes disponibles pendant un examen :

```
<n>       éditer l'exercice n
t <n>     relancer les tests sans rouvrir l'éditeur
s <n>     réafficher l'énoncé
r         voir le détail des résultats de tous les exercices
q         terminer l'examen (avec confirmation)
```

## Usage non-interactif

Utile pour scripter ou tester rapidement un fichier :

```sh
python3 -m examshell list                       # lister les exercices
python3 -m examshell show ft_swap                # afficher un énoncé
python3 -m examshell test ft_swap mon_fichier.c  # compiler + tester un fichier précis
```

`test` renvoie un code de sortie 0 si tous les tests passent, 1 sinon.

## Comment ça corrige

Pour chaque exercice, le moteur :

1. Grep le fichier de l'étudiant (hors commentaires/chaînes) à la
   recherche de fonctions interdites (tout sauf celles listées dans
   `allowed_functions`, typiquement seulement `write`).
2. Compile avec `gcc -Wall -Wextra -Werror -std=gnu99`. Le moindre warning
   fait échouer la compilation, comme à l'examen.
3. Pour les exercices "fonction", compile le fichier étudiant avec un
   harnais de test (`main()` fourni) qui appelle la fonction avec les
   arguments donnés en `argv`. Pour les exercices "programme", le fichier
   étudiant doit fournir son propre `main()`.
4. Exécute le binaire pour chaque cas de test et compare la sortie
   standard exacte à la sortie attendue (avec timeout pour détecter les
   boucles infinies).

## Ajouter un exercice

Chaque exercice est un fichier JSON dans `data/exercises/`, avec un
solution de référence correspondante dans `data/solutions/<id>.c` (utilisée
par la suite de tests et par la commande `sol` du mode entraînement).
Voir les fichiers existants pour le schéma exact (`id`, `rank`,
`time_minutes`, `type` ("function" ou "program"), `prototype`, `statement`,
`allowed_functions`, `harness`, `tests`).

## Exercices disponibles

- **Rank 1** (~1h) : `ft_putchar`, `ft_putstr`, `ft_strlen`
- **Rank 2** (~1h30) : `ft_putnbr`, `ft_swap`, `ft_div_mod`, `ft_min_max`,
  `ft_rev_int_tab`, `ft_sort_int_tab`
- **Rank 3** (~2h) : `ft_is_prime`, `ft_find_next_prime`, `ft_sqrt`,
  `ft_recursive_power`, `ft_iterative_power`, `ft_print_comb`,
  `ft_print_comb2`

## Tests

```sh
python3 -m unittest tests.test_examshell -v
```

Vérifie que chaque solution de référence passe tous ses tests et qu'une
implémentation vide échoue, pour chacun des 16 exercices.

## Prérequis

- Python 3.10+
- `gcc`
