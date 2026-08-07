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

## Mode web (terminal dans le navigateur)

Pour accéder à examshell depuis une page web plutôt que de lancer le
script à la main :

```sh
pip3 install -r requirements.txt
python3 -m examshell.web        # ou: ./bin/examshell-web
```

Puis ouvre `http://localhost:8000`. C'est un vrai terminal dans la page
(via [xterm.js](https://xtermjs.org/)), connecté par WebSocket à une
session `python3 -m examshell` tournant dans un pty côté serveur — donc
tout fonctionne comme en local, y compris l'ouverture de `nano`/`vim` en
plein écran pour éditer tes fichiers.

Options :

```sh
python3 -m examshell.web --http-port 8000 --ws-port 8765
```

⚠️ **Usage local/de confiance uniquement.** Quiconque atteint ce serveur
peut exécuter examshell (et l'éditeur qu'il lance) avec les droits du
processus serveur. Ne l'expose pas sur un réseau non fiable ou sur
Internet sans authentification devant.

## Déploiement sur GitHub Pages (100% dans le navigateur)

Il existe une troisième version, sous `pages/`, pensée pour être hébergée
gratuitement sur **GitHub Pages** — donc sans aucun serveur, ce qui exclut
le mode web ci-dessus (il a besoin de `gcc` et d'un processus Python côté
serveur). À la place, cette version compile et exécute le C **directement
dans le navigateur**, en WebAssembly :

- Le moteur (exercices, minuteur, score, détection de fonctions interdites)
  est réécrit en JavaScript pur dans `pages/js/` (`exercises.js`,
  `session.js`, `forbidden.js`), en portage fidèle de
  `examshell/exercises.py`, `session.py` et `compiler.py`.
- La compilation stricte (`-Wall -Wextra -Werror -std=gnu99`) et
  l'exécution des tests utilisent le vrai compilateur **clang**, lancé en
  WebAssembly via le [Wasmer JS SDK](https://github.com/wasmerio/wasmer-js)
  (paquet `clang/clang` du registre Wasmer, chargé depuis un CDN — voir
  `pages/js/compiler.js`).
- `pages/coi-serviceworker.js` (vendored depuis
  [wasmer-js/examples/cdn-coi-serviceworker](https://github.com/wasmerio/wasmer-js/tree/main/examples/cdn-coi-serviceworker),
  lui-même basé sur [coi-serviceworker](https://github.com/gzuidhof/coi-serviceworker))
  ajoute les en-têtes `Cross-Origin-Opener-Policy` / `Cross-Origin-Embedder-Policy`
  requis par le SDK (`SharedArrayBuffer`), que GitHub Pages ne permet pas de
  configurer côté serveur.

### Activer le déploiement

1. Dans les paramètres du repo GitHub : **Settings → Pages → Build and
   deployment → Source : "GitHub Actions"**.
2. Un push sur `main` qui touche `pages/`, `data/` ou
   `scripts/build_web_data.py` déclenche `.github/workflows/deploy-pages.yml`,
   qui régénère `pages/data/` (via `scripts/build_web_data.py`, pour que les
   exercices servis correspondent toujours à `data/exercises/`) puis publie
   `pages/` tel quel. Déclenchement manuel possible via l'onglet *Actions*
   (`workflow_dispatch`).

### Limites connues

- **Dépendance externe au runtime** : la page va chercher `clang/clang`
  sur le registre public de Wasmer au premier lancement (mis en cache par
  le navigateur ensuite). Si ce service est indisponible, la compilation
  échoue avec un message d'erreur explicite dans l'interface — ce n'est pas
  un bug de la page elle-même.
- **Pas de "kill" dur sur boucle infinie** : contrairement au mode CLI/web
  (qui tue le process `gcc`/binaire via `subprocess.run(timeout=...)`), le
  SDK Wasmer n'expose pas de méthode pour interrompre de force une instance
  WASI en cours d'exécution. Un test qui dépasse son timeout est bien
  signalé comme tel côté élève, mais le calcul sous-jacent peut continuer
  en arrière-plan dans le pool de workers du SDK.
- Cette intégration s'appuie sur l'exemple officiel
  `wasmerio/wasmer-js/examples/clang-cdn` et sur le paquet `@wasmer/sdk`
  publié sur npm (API vérifiée dans le code source du paquet), mais n'a pas
  pu être testée de bout en bout avec un vrai appel réseau vers le CDN/le
  registre Wasmer depuis l'environnement où elle a été écrite (accès
  sortant restreint). Tout le reste (chargement des exercices, minuteur,
  scoring, détection de fonctions interdites, UI) a été vérifié avec des
  tests Node et un test Playwright. Si la compilation ne fonctionne pas une
  fois déployé, ouvre la console du navigateur : le message d'erreur
  affiché dans l'interface vient directement de `Wasmer.fromRegistry` /
  `clang.entrypoint.run` et devrait indiquer la cause.

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
- Pour le mode web uniquement : `pip3 install -r requirements.txt` (paquet
  `websockets`) ; le CLI de base n'a aucune dépendance externe.
