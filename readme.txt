hubeau.py
---------------------------------------------------------------------------
Licence : BSD 2.0
Copyright, version et historique : voir hubeau.py
---------------------------------------------------------------------------
Script Python permettant d'interroger l'API publique hubeau (hygrométrie)

Permet de suivre les mesures de hauteur des cours d'eau diffusée par l'API HubEau :
	- Télécharge les dernières mesures (API HubEau via json)
	- Stocke les mesures en local (sqlite + sqlalchemy)
	- Permet de faire des graphiques (matplotlib)
	- Génère une page HTML de suivi (ElementTree)
---------------------------------------------------------------------------

-- Modules spécifiques utilisés -------------------------------------------
requests (module à installer : https://requests.readthedocs.io/en/master/)
	permet une interface simple pour interagir avec HTTP ("HTTP for humans")
	Licence Apache2 : https://requests.readthedocs.io/en/master/user/intro/#apache2-license
	Copyright 2019 Kenneth Reitz
matplotlib (module à installer : https://matplotlib.org/)
	permet de créer des graphiques à partir de données (ici mesures de hauteur d'eau)
	Licence PSF, compatible BSD : https://matplotlib.org/users/license.html
	Copyright 2019 Matplotlib Development Team

-- Utilisation ------------------------------------------------------------
Aucune interface GUI, utilisable depuis la ligne de commande (CLI)
Ce logiciel est destinée a être utilisé sous forme de tache de fond système (ex. Cron)
ou lancer manuellement afin de mettre à jour en temps réel les graphiques de hauteurs de 
cours d'eau des stations de mesures surveillées et affichés dans un fichier HTML.

-- interface CLI ----------------------------------------------------------
Sans paramètre, le script prend les données dans le fichier de configuration .INI
C'est la solution a privilégier pour un usage en automatique.

Paramètres de ligne de commande :
	-s permet d'indiquer une station de mesure (on peut le répéter pour interroger plusieurs stations)
		voir la classe Station (plus bas) pour plus de détails sur les stations et leurs identifiants		
	-t permet de préciser les données a afficher dans la graphiques (en jours)
		chaque station propose environ les 30 derniers jours de mesure
		chaque station a sa propre fréquence de mesure (variable de 5 à 60 minutes)
	-g permet d'afficher le graphique de chaque station interrogée (GUI simple)
	-m permet de réunir les données de toutes les stations dans un seul graphique
	-d permet de télécharger les dernières mesures (par défaut)
	-i permet d'afficher les informations des stations interrogées

exemple :
	voir les mesures à Paris des dernières 24 heures
		python hubeau.py -sF700000103 -t24	
	voir mesures à Toulouse des dernièrs 10 jours (240 heures)	
		python hubeau.py -sO200004001 -t240	
	voir et comparer la situation à Bordeaux et Tarascon sur les dernières 48 heures
		python hubeau.py -sO972001001 -sV720001002 -t48

-- Sans paramètres CLI (fichier hubeau.ini) ---------------------------------
Sans paramètres CLI, le script va utiliser la configuration dans le fichier hubeau.ini
C'est l'usage le plus courant pour surveiller les cours d'eau près de chez soi.

Le fichier hubeau.ini par défaut est configuré pour surveiller 4 stations 
sur le fleuve Charente (16) et met en valeur la station de mesure de la ville de Cognac.

Voir le fichier ini avec ses commentaires et le source de la classe COnfig pour les détails.

-- Trouver les identifiants de stations ---------------------------------------
Pour trouver les numéros des stations qui vous intéresse, le plus simple 
est d'utiliser le site internet : https://www.vigicrues.gouv.fr/
D'utiliser son interface graphique pour trouver la ou les stations qui vous intéresse
Lorsque vous êtes sur la page d'une station, l'onglet "Info" vous permet de visualiser son identifiant

Les identifiants de station sont des codes uniques commençant par une elttre suivi de 9 chiffres.
ex : la station de Cognac (16) est identifier par : R314001001
Chaque station a une fréquence de mesures qui peut varier de 5 à 30 minutes.

-- API et Données ----------------------------------------------------------
HubEau est un service (API) de diffusion de données publiques de Eau France.
EauFrance est un service public d'information sur l'eau.
Basé sur le dictionnaire de référence SANDRE
En savoir plus : 
 EauFrance
 HubEau : https://hubeau.eaufrance.fr
 Généralités API : https://hubeau.eaufrance.fr/page/apis

API Hydrométrie
===============
Cet API est mise à jour à partie des données PHyC toutes les 2 minutes sur les dernières 24 heures.
Comprend un historique de 1 mois.
Le script HubEau conserve un historique plus long dans sa base de données locale.

API Hydrométrie : https://hubeau.eaufrance.fr/page/api-hydrometrie
Référenciel Hydrométrie : http://www.sandre.eaufrance.fr/notice-doc/r%C3%A9f%C3%A9rentiel-hydrom%C3%A9trique-3

Données disponibles :
	Sites : tronçon d'un cours d'eau ou les observations sont homogènes et comparables.
	Stations : station d'observation sur un site
	Observations : les observations d'une station

Les données sont disponibles dans plusieurs formats : CSV, JSON, etc...
Les données retournées sont paginés, chaque page retourne un bloc de données avec unc hamp pour indiquer si il y a une suite.
Taille maximale d'une page : 5000
Code retour de requête :
	200 : OK toutes les réponses sont présentes
	206 : OK il reste des données disponibles (pages suivantes)
	400 : requête incorrecte
	401 : accès non autorisé
	403 : accès interdit
	404 : non trouvé
	500 : erreur interne du serveur

Stations
Les stations appartienne a un site, sont identifié par un identifiant unique et contienne des informations géographique.
	code_station : code station
	libelle_station : nom de la station en clair
	code_site : code du site
	libelle_site : nom du site en clair
	code_commune_station : code de la commune ou se trouve la station (INSEE)
	libelle_commune : nom de la commune ou se trouve la station
	code_departement : code du département ou se trouve la station (INSEE)
	code_region : code de la région ou se trouve la station (INSEE)
	code_cours_eau : code du cours d'eau sur lequele se trouve la station (SANDRE) 
	type_station
	coordonnee_x_station
	coordonnee_y_station
	code_projection
	longitude :
	latitude :
	influence_locale_station
	commentaire_station
	
Mesures
Les dates sont exprimées UTC au format ISO 8601
Les hauteurs d'eau (H) sont exprimées en millimètres (mm)
Les débits (Q) sont exprimés en litre par seconde (l/s) : non utilisé par le script

-------------------------------------------------------------------------------
Utilisation de l'API hydrométrie par le script HubEau :
Le format de données utilisé : JSON
La notion de site n'est pas géré, seul sont utilisés Station et Observation
Taille des pages de donnes : 400 par défaut
Le script ne fait aucune recherche de stations a ce stade, 
	les identifiants de station doivent être connu (voir chapitre "Trouver une station" plus haut.



