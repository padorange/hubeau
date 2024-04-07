#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# python 2-3 compatibility
# from __future__ import print_function
# from __future__ import division

__application__="hubeau.py"
__version__="0.9.8"
__copyright__="Copyright 2010-2023, Pierre-Alain Dorange"
__license__="BSD-3-Clauses"		# voir https://en.wikipedia.org/wiki/BSD_licenses
__author__="Pierre-Alain Dorange"
__contact__="pdorange@mac.com"

"""
	hubeau.py
	-----------------------------------------------------------------------------------------
	Réalisé avec Python 3.11.x, testé sur Debian 12 (bookworm)
	-----------------------------------------------------------------------------------------
	Permet de suivre les mesures de hauteur des cours d'eau Français diffusée par l'API HubEau :
		- Télécharge les dernières mesures (API HubEau + json)
		- Stocke les mesures en local (sqlite + sqlalchemy), permet un historique
		- Permet de faire des graphiques (matplotlib)
		- Génère une page HTML5+CSS+JavaScript de suivi (ElementTree)

	Voir readme pour plus de détails

	-- Licence (BSD-3-Clauses : https://en.wikipedia.org/wiki/BSD_licenses) ------------------
	Copyright (c) 2010-2024, Pierre-Alain Dorange
	All rights reserved.

	-- Modules spécifiques à installer (licences : voir readme) ---------------------------
	Requests 2.28.x (https://requests.readthedocs.io/en/master/)
		permet de simplifier la gestion HTML des données
	MatPlotLib 3.3.x (https://matplotlib.org/)
		permet de réaliser de jolis graphiques
	SQLAlchemy 1.4.6 : (https://www.sqlalchemy.org/)
		permet de simplifier la gestion SQL en faisant correspondre des objects Python avec des tables SQL
		pour effectuer une lecture+sauvegarde simplifiée des deonnées dans une base mysql

	-- Modules spécifiques utilisés par la page HTML (licence : voir readme.txt) --------------
	leaflet.js 1.9.x (https://leafletjs.com/)

	-- Modules standards utilisés (Python) ----------------------------------------------------
	sqlite : Base de données SQL locale mono-utilisateur
	configparser : 	Gestion des fichier ini
	ElementTree (xml.tree) : Création fichier html5

	-- Historique -----------------------------------------------------------------------------
	Initialement développé pour suivre les crues (vigicrues.gouv.fr) 
	puis étendu via l'api-hydrométrie du portail HubEau.

	0.1 : janvier 2010
		première version avec extraction des données depuis le source HTML de la page vigicrues.gouv.fr
	0.6 : janvier 2020
		implémentation du nouveau modèle de données vigicrues, soit 
			API v1 de la plateforme opendata hubeau.eaufrance.fr avec les données au format JSON
		création de graphe via pyplot (module matplotlib)
		ajustement de l'échelle x des graphes pour une comparaison facilitée des graphes
	0.7 : fevrier 2020
		stockage des mesures dans une base de données SQLite locale
		gestion des ajouts de nouvelles mesures
		ajout d'un fichier de config (ini) pour stocker les paramètres par défaut
	0.8 : mai 2020
		petites améliorations et gestion d'erreur (un peu plus de résilience)
		améliorations affichage du graphique
		amélioration des performances
	0.9 : juin-octobre 2020
		amélioration gestion des arguments de la ligne de commande (par bascule ON/OFF)
		recherche de stations multi-critères (cours d'eau, nom, commune, département)
		ajout carte openstreetmap des stations mesurées et/ou résultats via leaflet.js
	0.9.4 : janvier-avril 2021
		ajout de marqueurs de couleurs sur carte avec couleurs correspondates au graphique
		début préparation pour compatibilité python3
		couleurs homogène entre les graphes et Leaflet
	0.9.5 : mai 2021
		compatibilité Python 2.7.x et 3.7.x
		affichage résultats recherche sur une carte
		optimisation démarrage : ne charger que les données nécessaires à la session
		gestion de la limite des 30 jours de l'API HubEau
	0.9.6 : janvier 2023
		optimisation mise à jour de la base de données (station : downloaddata + checkdata)
		intégration de Leaflet 1.9.3 (aucun changement pour hubeau.py)
		intégration de matplotlib 3 (aucun changement pour hubeau.py)
	0.9.7 : novembre 2023
		optimisation affichage avancement du chargement
		correction affichage statistiques à coté du graphique en mode mix=OFF
		vérification compatibilité avec requests 2.28, matplotlib 3.6.3 et sqlalchemy 1.4.46
		préparation pour évoluer vers le futur sqlalchemy 2
	0.9.8 : avril 2024
		optimisation chargement de la base de données (suivant la longueur du graphique)
		optimisation de l'axe >X pour les périodes longues
	A Faire
		Mise à jour des infos stations dans la base lors de chargement des données
		Faire évoluer les librairies vers plus récents (request, sqlalchemy, matplotlib...)
			SQLAlchemy 1.4.6 vers 2.0
			MatPlotLib 3.3 vers 3.8
			Request 2.28 vers 2.31
		Option pour compacter les anciennes données
		Option pour simplifer les graphiques longs avec moyennage des données
		Gestion d'autres API HubEau : température, piezomètre, qualité... ?
		Option OSM pour afficher le cours d'eau sur la carte ?
	Bug
		gérer le code erreur 400 (date trop ancienne et mieux retourner les erreurs en HTML
"""

# astuce unicode (Python 2.7.x) : permet de définir unicode comme encodage par défaut
import sys
if sys.version_info.major==2:
	reload(sys)
	sys.setdefaultencoding('utf8')

# -- Modules standard Python -------------------------------------------------------------------
import getopt					# module interface avec le système
import os.path					# module interface les système de fichier (gestion chemains)
import time, datetime			# module de gestion des dates au format unix
import webbrowser				# module pour ouvrir une URL dans le navigateur par défaut
if sys.version_info.major==2:	# python 2
	import ConfigParser as configparser		# gestion fichier.INI (paramètres et configuration)
else:							# python 3
	import configparser						# gestion fichier.INI (paramètres et configuration)
import codecs					# gestion des encodages de fichier
from xml.etree import ElementTree as ET		# module pour gérer le format XML (ici pour crée du HTML)

# -- modules externes (dépendances à installer) -------------------------------------------------
import sqlalchemy				# modules d'abstraction SQL (ici utilisé pour stocker les données via SQLite)
import sqlalchemy.orm					# mapper configuration ORM
import sqlalchemy.ext.declarative		# extension ORM
								# matplotlib 3.x : librairie de création de graphes : https://matplotlib.org/
import matplotlib.pyplot as plt			# module principal pour créer des graphes
import matplotlib.dates as pltdates		# module pour gérer des dates dans les graphes
import matplotlib.style as pltstyle		# module pour gérer des styles dans les graphes
import matplotlib.figure as pltfig		# module pour gérer des figures et axes (base des graphes)
import matplotlib.ticker as pltticker	# module pour gérer les formattages de données
import requests					# module intelligent de gestion du protocole HTTP et JSON

# -- Constantes et Globales ----------------------------------------------------------------------
_debug=False				# active le mode debug
_debug_update=False			# mode debug pour les mise à jour de données
_debug_sql=False			# mode debug pour les appels SQL
_verbose=True				# mode trace avec affichage d'informations intermédiaires

user_agent="%s/%s" % (__file__,__version__)

# Nombre maximal de stations affichable sur un seul graphique
maxGraph=6
# marqueurs colorés pour Leaflet : https://github.com/pointhi/leaflet-color-markers
colorList=("blue","orange","green","violet","yellow","red","grey","gold","black")

default_directory="html"
default_config="hubeau.ini"
default_css="""
	body { background-color: lightgrey; }
	.clearfix { overflow: auto; }
	.plot { float: left; } 
	#datamapid { height: 400px; }
	#searchmapid { height: 800px; }
	#bid { background-color: lightblue; padding: 5px; margin: auto; }
	#gid { box-shadow: 1px 2px 3px rgba(0, 0, 0, .5); margin: 5px; }
	"""

# définit le répertoire par défaut comme celui du source (gestion du lancement hors dossier source)
path=os.path.dirname(os.path.abspath(__file__))	
os.chdir(path)	

# sqlalchemy : prépare les classes globales nécessaires à la gestion ORM de SQLAlchemy
Base=sqlalchemy.orm.declarative_base()

# -- Classes ---------------------------------------------------------------------------------------

class Config():
	"""	objet Config pour regrouper les paramètres utilisés, stockés dans le fichier INI de configuration
		certaines valeurs par défaut (__init__) sont surchargées par la lecture du fichier de configration (load)
		voir hubeau.ini
	"""
	def __init__(self):
		# paramètres console par défaut
		self.download=True			# active le téléchargement des dernières mesures (mise à jour)
		self.info=False				# active l'affichage détaillée des infos station dans la console
		self.show=True				# active l'affichage fichier HTML crée avec les résultats
		self.map=False
		self.css=default_css		# feuille de style CSS pour le rendu HTML
		self.plotdays=0
		
		# chargement des paramaètre depuis le fichier de configuration (hubeau.ini)
		# avec valeurs par défaut si erreur de chargement ou valeur non définie
		config=configparser.RawConfigParser()
		with codecs.open(default_config,'r',encoding='utf-8') as f:
			if sys.version_info.major==2:
				config.readfp(f)
			else:
				config.read_file(f)
		try:	# chemin pour la sauvegarde des résultats (images et html)
			directory=config.get('data','dir')
		except:
			directory=default_directory
		self.imgpath=os.path.join(".",directory)	# chemin pour la sauvegarde des résultats (images et html)
		try:	# nom du fichier html à créer
			self.html=config.get('data','index')
		except:
			self.html="index.html"
		try:	# nom de la base de données
			self.dbPath=config.get('data','dbname')
		except:
			self.dbPath="."
		try:	# liste des identifiants de stations à gérer
			list=config.get('stations','id')
			self.idList=list.split(',')
		except:
			self.idList=[]
		try:	# taille par défaut des données téléchargées par pages (nb mesures)
			self.datasize=config.getint('stations','newdata')
		except:
			self.datasize=1000
		try:	# taille par défaut des données affichées (nombre de jours)
			self.plotdays=config.getfloat('plot','days')
		except:
			self.plotdays=10.0
		try:	# affichage carte dans le html
			self.map=config.getboolean('plot','map')
		except:
			self.map=False
		try:	# fusionne tout les graphes en 1 seul
			self.mix=config.getboolean('plot','mix')
		except:
			self.mix=False
		try:	# affiche les grilles sur les graphes
			self.grid=config.getboolean('plot','grid')	
		except:
			self.grid=True
		try:	# nature de la mesure (titre de la courbe)
			self.glabel=config.get('plot','glabel')
		except:
			self.glabel=u"Hauteur"
		try:
			self.ylabel=config.get('plot','ylabel')
		except:	# unité de la mesure axe Y (mètres)
			self.ylabel=u"Hauteur (mètres)"
		try:	# couleur du graphe
			self.grafcolor=config.get('plot','grafcolor')
		except:
			self.grafcolor="black"
		try:	# couleur de fond des données graphes pour le remplissage
			self.fillcolor=config.get('plot','fillcolor')
		except:
			self.fillcolor=None
		try:	# marge mini et maxi (mètres) au-dela des données pour l'echelle Y
			self.grafymargin=config.getfloat('plot','grafymargin')
		except:
			self.grafymargin=0.5
		try:	# l'écart mini (mètres) pour l'affichage des données
			self.ymin=config.getfloat('plot','ymin')	
		except:
			self.ymin=4.0
		try:	# taille des libellés sur les axes
			self.labelsize=config.getint('plot','labelsize')
		except:
			self.labelsize=8
		try:	# taille des libellés sur les axes
			self.axesize=config.getint('plot','axesize')
		except:
			self.axesize=8
		try:	# taille des libellés sur les axes
			self.titlesize=config.getint('plot','titlesize')
		except:
			self.titlesize=10
		try:
			w=config.getint('plot','plotwidth')
			h=config.getint('plot','plotheight')
		except:
			(w,h)=(10.0,3.0)
		self.plotsize=(0.01*w,0.01*h)	# convert pixels to inches
		try:	# définit la taille de l'image en pouces (1 inch=100 pixels)
			w=config.getint('plot','plotwidth')
			h=config.getint('plot','mixplotheight')
		except:
			(w,h)=(10.0,3.0)
		self.mixplotsize=(0.01*w,0.01*h)	# convert pixels to inches
		if _debug: 
			print(self)
		return

	def getHTMLPath(self):
		return os.path.join(self.imgpath,self.html)

	def __str__(self):
		text="jours: %.1f" % self.plotdays
		text+="\nrequête: %d" % self.datasize
		text+="\nshow: %s" % self.show
		text+="\nmap: %s" % self.map
		return text

class DataBase():
	"""	Gestion globale de la base de données avec un chargement au début et sauvegarde à la fin
		via la variable state de chaque objet 
			state=0 	nouveau, sera ajouté à la base de données à la mise à jour
			state=1		mise à jour, sera mis à jour dans la base de données
			state=2		chargé, existe déjà ne sera ni mis à jour, ni ajouté
	"""
	def __init__(self,config):
		""" initialise le moteur SQLite via SQLAlchemy """
		Engine=sqlalchemy.create_engine("sqlite:///%s" % config.dbPath,echo=_debug_sql)
		self.plotdays=config.plotdays
		self.engine=Engine
		Base.metadata.create_all(self.engine)
		self.session=sqlalchemy.orm.sessionmaker(bind=Engine)()

	def load(self,idList=[]):
		""" charger les données, pour les stations requises (idList) 
			optimisation pour ne charger que les données nécessaire pour l'affichage du graphique (plotdays)
		"""
		stations=StationList()
		dt=datetime.timedelta(days=self.plotdays+1)
		t0=datetime.datetime.utcnow()
		tm=t0-dt
		print("Chargement partiel de la base de données (%d station(s))" % len(idList))
		for s in idList:	# pour chaque station
			station=self.session.query(Station).filter(Station.id==s).one_or_none()
			if station:
				station.dbInit(2)
				stations.append(station)
				# requete MySQL pour les données de la staion
				results=self.session.query(StationData).filter(StationData.station==s,StationData.t>=tm).all()
				if _verbose or _debug:
					print("  - chargement de %s (%d mesures(s))" % (station.getID(),len(results)))
				# charger les données en mémoire
				for r in results:
					r.dbInit(2)
					station.addData(r)
		return stations

	def store(self,stations):
		""" stocker les données de la liste stations, suivant l'état 'state'
				0 : nouvelle donnée a stocker dans la base de données
				1 : mise à jour énce'ssire (non géré)
				2 : déjà stocké, ne rien faire
		"""
		for station in stations:
			if station.state==0:			# nécessite un ajout (station)
				self.session.add(station)
				self.session.commit()
			for data in station.data:
				if data.state==0:			# nécessite un ajout (station.data)
					self.session.add(data)
				elif data.state==1:			# nécessite un ajout (station.data)
					self.session.update(data)
			self.session.commit()

class StationData(Base):
	""" StationData: pour stocker les mesures des stations en mémoire
			id : identifiant de la station
			t :	date-time de la mesure
			v : valeur de la mesure
			state :	0	nouveau
					1	à mettre à jour
					2	déja chargé
	"""

	# sqlalchemy : champs sql lié à l'objet
	__tablename__="data"
	id=sqlalchemy.Column(sqlalchemy.Integer,primary_key=True,autoincrement="auto")
	station=sqlalchemy.Column(sqlalchemy.String)
	t=sqlalchemy.Column(sqlalchemy.DateTime)
	v=sqlalchemy.Column(sqlalchemy.Float)

	def __init__(self,station,t,v):
		self.id=None
		self.station=station
		self.t=t
		self.v=v
		self.dbInit(0)

	def dbInit(self,state=2):
		self.state=state

	def __str__(self):
		return "%s : %s,%.21f" % (self.station,self.t.strftime("%d/%m/%Y @ %H:%M"),self.v)

class Station(Base):
	""" objet Station
		encapsule une station de mesure VigieCrues, permet de charger les données mesurées et de faire des analyses
			id : identifiant unique vigiecrues/hubeau (voir ci-dessous)
			data : liste des mesures, couple (date-time, valeur)
		Référence API hydrométrie : http://hubeau.eaufrance.fr/page/api-hydrometrie

		Les mesures disponibles dépendent des stations et sont horodatés
			* horodatatage : ISO 8601 en heure UTC (temps universel), 
				en france métropolitaine  ajouter 1 heure l'hiver et 2 heures l'été
			* H : Niveau d'eau (hauteur) : données en millimètres
			* Q : Débit (optionnel) : données en litre/seconde

		Les stations hydrométriques ont un identifiant unique de 10 caractères (1 lettre et 9 chiffres)
		on peut retrouver les identifiant de stations de manière cartographique depuis vigicrues.gouv.fr

		Voir des exemples d'identifiants de stations dans le fichier hubeau.ini (commentaires)
	"""

	# sqlalchemy : champs sql lié à l'objet
	__tablename__='station'
	id=sqlalchemy.Column(sqlalchemy.String,primary_key=True)
	nom=sqlalchemy.Column(sqlalchemy.String)
	type=sqlalchemy.Column(sqlalchemy.String)
	departement=sqlalchemy.Column(sqlalchemy.Integer)
	longitude=sqlalchemy.Column(sqlalchemy.Float)
	latitude=sqlalchemy.Column(sqlalchemy.Float)
	coursdeau_code=sqlalchemy.Column(sqlalchemy.String)
	coursdeau=sqlalchemy.Column(sqlalchemy.String)
	actif=sqlalchemy.Column(sqlalchemy.Boolean)

	def __init__(self,id=-1):
		""" initialise la structure """
		self.id=id					# identifiant hubeau
		self.nom=u""				# nom de la station de mesure (après interrogation)
		self.type=u""				# type de station
		self.departement=-1			# département ou se situe la station
		self.longitude=0.0			# longitude de la station
		self.latitude=0.0			# latitude de la station
		self.coursdeau_code=u""		# code du cours d'eau ou se situe la station
		self.coursdeau=u""			# nom du cours d'eau ou se situe la station
		self.actif=False			# station active
		self.dbInit(0)

	def dbInit(self,state=2):
		""" initialisation supplémentaire après un chargement via sqlalchemy """
		self.data=[]				# données récupérée (après téléchargement), liste de StationData
		self.imgname=u""				# nom du fichier image du graphe (après sauvegarde)
		self.x_lim=[datetime.datetime.utcnow(),datetime.datetime(1900,1,1,0,0,0)]
		self.y_lim=[9999.9,0.0]
		self.state=state			# état 2 : existe déjà (aucune mise à jour)

	def getID(self):
		""" retourne l'identifiant de la station """
		return self.id

	def getName(self,withID=False,withDep=True):
		""" Retourne le nom mis en forme (chaine)
				withID :  pour intéger l'identifiant dans le nom
				withDep : pour intégrer le numéro du département dans le nom
		"""
		if withID:
			name=u"%s" % str(self.id)
			next=u":"
		else:
			name=u""
			next=u""
		if len(self.nom)<=0:
			name=name+next+u"(no name)"
		else:
			name=name+next+self.nom
			if len(name)>0:
				next=u" "
			else:
				next=u""
			if withDep:
				name=name+next+u"(%d)" % self.departement
		return name	

	def addData(self,data):
		""" ajoute data à la liste existante et calcule les min/max au fur et à mesure """
		if data.t<self.x_lim[0]:
			self.x_lim[0]=data.t
		if data.t>self.x_lim[1]:
			self.x_lim[1]=data.t
		if data.v<self.y_lim[0]:
			self.y_lim[0]=data.v
		if data.v>self.y_lim[1]:
			self.y_lim[1]=data.v
		self.data.append(data)

	def checkData(self,data):
		""" vérifie la présence de data dans la liste existante et retourne l'état 
			0.9.6 : optimisation en parcourant la liste depuis le fin (liste trié par ordre chronologique)
					et en stoppant dès que les dates sont inférieure à la date de la data.
		"""
		if data.station==self.id:
			for d in self.data[::-1]:
				if d.t<data.t:
					break
				elif d.t==data.t:
					if abs(d.v-data.v)<0.001:
						return 2	# existe déjà (rien à faire)
					else:
						return 1	# existe mais avec une autre valeur (mise à jour)
		else:
			print(u"ERROR, not the same station")
		return 0	# n'existe pas (il faudra l'ajouter)

	def showName(self,withID=False,withDep=True,prefix=""):
		""" Affiche le nom de la station avec les mêmes options que getName"""
		print(u"%sStation: %s" % (prefix,self.getName(withID,withDep)))

	def showInfo(self):
		""" Affiche les informations détaillées de la station """
		print(u"-----")
		self.showName(withID=True)
		print(u"\tCours d'eau: %s (%s)" % (self.coursdeau,self.coursdeau_code))
		print(u"\tActif:", self.actif)
		print(u"\tType:", self.type)
		print(u"\tLocalisation: %.4f, %.4f" % (self.longitude,self.latitude))
		print(u"\tMesures: %d" % len(self.data))

	def showData(self,limit=0):
		""" Afficher toutes les mesures disponibles """
		print("\tDonnées (date, hauteur) %s mesure(s)" % len(self.data))
		if limit<=0:
			datas=self.data
		else:
			self.data.sort(key=lambda item: item.t)
			datas=self.data[-limit:]
		for d in datas:
			print("\t%s\t%.2f" % (d.t.strftime("%d/%m/%Y @ %H:%M"),d.v))
				
	def showSummarize(self):
		""" Afficher un résumé des données téléchargées avec une brève analyse """
		r=self.analyze(h=4.0)
		last=r.getlast()
		print(u"dernière mesure : %.3f m @ %s" % (last.v,last.t.strftime("%d/%m/%Y @ %H:%M")))
		print(u"variations:")
		print(u" 4H : %+.3f m, vitesse: %+.1f cm/h" % (r.getdeltavalue(),100.0*r.getspeed()))
		r=self.analyze(h=24.0)
		print(u"24H : %+.3f m, vitesse: %+.1f cm/h" % (r.getdeltavalue(),100.0*r.getspeed()))
		r=self.analyze(h=168.0)
		print(u" 7J : %+.3f m, vitesse: %+.1f cm/h" % (r.getdeltavalue(),100.0*r.getspeed()))

	def downloadInfo(self):
		""" télécharge les informations de description de la station de mesure 
			Via une requete HTTP au format JSON :
				http://hubeau.eaufrance.fr/page/api-hydrometrie#!/hydrometrie/stations
		"""
		hubeauStationAPI="http://hubeau.eaufrance.fr/api/v1/hydrometrie/referentiel/stations"
		urlstation="%s?code_station=%s&format=json&size=20"
		url=urlstation % (hubeauStationAPI,self.id)
		if _debug:
			print(u"url:",url)
		r=requests.get(url,headers={'user-agent':user_agent})			# télécharge les données brutes depuis l'URL
		if r.status_code<=206:
			content=r.headers['content-type']
			if 'json' in content:
				json=r.json()				# convertir les données brutes en objet JSON
				jdata=json["data"]			# récupère la porton data du JSON
				if len(jdata)==1:			# recopie les données JSON dans les champs de l'objet Station
					data=jdata[0]
					self.nom=data['libelle_station']
					self.departement=int(data['code_departement'])
					self.longitude=float(data['longitude_station'])
					self.latitude=float(data['latitude_station'])
					self.coursdeau_code=data['code_cours_eau']
					self.coursdeau=data['libelle_cours_eau']
					self.type=data['type_station']
					self.actif=data['en_service']
				else:
					print(u"ERREUR, il y a %d réponse(s) pour la station %s" % (len(jdata),self.id))
			else:
				print(u"ERREUR")
				print(u"url:",url)
				print(u"La réponse n'est pas au format JSON :",content)
		else:
			print(u"ERREUR")
			print(u"url:",url)
			print(u"Etat HTTP :",r.status_code)

	def downloadData(self,date=None,pagesize=100):
		""" télécharge les données de la station de mesure 
			Via une requete HTTP au format JSON :
				http://hubeau.eaufrance.fr/page/api-hydrometrie#!/hydrometrie/observations
			Recupère par défaut toutes les mesures ou à partir d'une date données (date)
				- pagesize permet de préciser le nombre de données par pages.
			Gère le retour de données en multi-pages
			Ne gère pas les durées inter-mesure, la limite size est définit en nombre de mesures pas en temps
			certaines stations ont des mesures toutes les heures, d'autres toutes les demi-heures
		"""
		hubeauHydroAPI="http://hubeau.eaufrance.fr/api/v1/hydrometrie/observations_tr"
		time_format = "%Y-%m-%dT%H:%M:%SZ"		# converson date-heure de chaine API HubEau à standard unix et vis-et-versa
		if date:	# si une date est précisée adapter la requête pour réduire le nombre de données
			datetimeStr=date.strftime(time_format)
			urldata="%s?code_entite=%s&size=%d&grandeur_hydro=H&date_debut_obs=%s&fields=date_obs,resultat_obs"
			url=urldata % (hubeauHydroAPI,self.id,pagesize,datetimeStr)
		else:
			urldata="%s?code_entite=%s&size=%d&grandeur_hydro=H&fields=date_obs,resultat_obs"
			url=urldata % (hubeauHydroAPI,self.id,pagesize)
		page=1
		print("\t",end="")
		while url:
			if _debug:
				print("url (%d):" % page,url)
			r=requests.get(url,headers={'user-agent':user_agent})		# télécharge les données brutes depuis l'URL
			if r.status_code<=206:
				content=r.headers['content-type']
				if 'json' in content:
					json=r.json()			# converti les données brutes en objet JSON
					v=json["api_version"]
					v=v.split('.')
					if v[0]=='1':	# vérifie la version API
						next=json["next"]
						if next and _debug:
							print("> chargement page suivante")
						datas=json["data"]			# récupère la parties données du JSON
						if _debug:
							print("downloaded datas:",len(datas))
						print(".",end="",flush=True)
						for data in datas:					# parcourir les données (couple date-heure et valeur de mesure)
							datetimeStr=data['date_obs']				# extraire la valeur date-heure
							time_format = "%Y-%m-%dT%H:%M:%SZ"			
							t=datetime.datetime.fromtimestamp(time.mktime(time.strptime(datetimeStr, time_format)))
							valueStr=data['resultat_obs']			# extraire la valeur de hauteur
							v=float(valueStr)/1000.0				# convertir la valeur de miilimètre vers mètres
							d=StationData(self.id,t,v)
							d.state=self.checkData(d)
							if d.state==0:
								if _debug_update:
									print("new data",d)
								self.addData(d)
							elif d.state==1:
								print("ERROR data need updates", d)
					else:
						print("ERROR : API version not handled",v)
				else:
					print("ERROR : La réponse n'est pas au format JSON :",content)
				page=page+1
				url=next
			else:
				print("url:",url)
				print("HTTP Status error :",r.status_code)
				url=None
		print()

	def initPlot(self,config):
		""" crée un objet plot pour pouvoir dessiner un ou plusieurs graphes dedans """
		if config.mix:
			size=config.mixplotsize
		else:
			size=config.plotsize
		self.fig,self.axes=plt.subplots(figsize=size)
	
	def createGraph(self,config,x_lim=None,y_lim=None,figure=None,axes=None,index=0):
		""" Construit la graphe des mesures avec les données disponibles
			et crée une image PNG
				display : permet d'activer l'affichage du graphe en GUI (via tkinter)
			x_lim permet de fixer un mini-maxi pour l'axe X (date-heure)
			y_lim permet de fixer un mini-maxi pour l'axe Y (hauteur d'eau)
			si non précisé les mini-maxi sont calculés à partir des données du graphe
			si précisé cela permet d'avoir les mêmes échelles sur plusieurs graphes
		"""
		# 1. Prépare les données pour le graphe pyplot

		# 1.1. prépare les données pour pyplot.plot_date et repère les min/max
		self.data.sort(key=lambda item: item.t)
		if x_lim==None:
			datas=self.data
		else:
			datas=[]
			for d in self.data:
				if d.t>=x_lim[0] and d.t<=x_lim[1]:
					datas.append(d)
		if x_lim:	# set x min/max to x_lim parameter if set, otherwise to data min/max
			(xmin,xmax)=x_lim
		else:
			(xmin,xmax)=self.x_lim
		if y_lim:	# set y min/max to y_lim parameter if set, otherwise to data min/max
			(ymin,ymax)=y_lim
		else:
			(ymin,ymax)=self.y_lim
		xdata=[]	# les données de l'axe X : les dates-heures des mesures
		ydata=[]	# les données de l'axe Y : les mesures (hauteur)
		for d in datas:		# convertir les mesures en données compatible pyplot
			xdata.append(pltdates.date2num(d.t))
			ydata.append(d.v)

		# 1.2. Ajuste les min/max des hauteurs (axe Y) pour bien visualiser les données
		if _debug:
			print("raw y min/max: %.2f,%.2f" % (ymin,ymax))
		ymin=ymin-config.grafymargin
		ymax=ymax+config.grafymargin
		d=ymax-ymin
		if (d<config.ymin):
			ymin=ymin-0.5*(config.ymin-d)
			if ymin<0:
				ymax=ymax+config.ymin
				ymin=0.0
			else:
				ymax=ymax+0.5*(config.ymin-d)
		if _debug:
			print("adjusted y min/max: %.2f,%.2f" % (ymin,ymax))

		# 1.3. Détermine l'affichage des axes X suivant les données
		if _debug:
			print("raw x min/max: %s, %s" % (xmin.strftime("%d/%m/%Y @ %H:%M"),xmax.strftime("%d/%m/%Y @ %H:%M")))
		dj=1.0*(xmax-xmin).total_seconds()/86400.0 		# convertir les secondes en jours
		if _debug:
			print("delta x : %.2f" % dj)
		if dj<=2.0:		# si moins de 2 jours afficher aussi les heures + un marqueur
			fmt='%d/%m/%y %H:%M'
			majorloc=pltdates.AutoDateLocator(minticks=2,maxticks=5)
			minorloc=pltdates.HourLocator()
			mark='o-'
		else:			# sinon n'afficher que les jours (pas les heures) + sans marqueur
			fmt='%d/%m/%y'
			mark='-'
			if dj<200:
				majorloc=pltdates.AutoDateLocator(minticks=2,maxticks=7)
				minorloc=pltdates.DayLocator()
			else:
				majorloc=pltdates.AutoDateLocator(minticks=2,maxticks=7)
				minorloc=pltdates.MonthLocator()
		# 2. Créer le graphique (pyplot)

		# créer le graphique et son style de base + ajouter les données
		plt.rcParams.update({'figure.autolayout':True})
		if figure and axes:
			if config.mix:
				self.fig=figure
				self.axes=axes
			else:
				print("error (creategraph): mix option but not figure defined")
		else:
			if config.mix:
				print("error (creategraph): no mix option but figure defined")
			else:
				self.initPlot(config)

		plt.grid(config.grid)
		if config.mix:	# option mix : regroupement de toutes les stations sur un seul graphe
			if index==0:	# index 0 => courbe principale (remplissage)
				gcolor=config.grafcolor
				fcolor=config.fillcolor
				gwidth=2.0
			else:	# autre courbes (pas de remplissage et dégradé de couleurs)
				gcolor=colorList[index]
				fcolor=None
				gwidth=1.0
			glabel=str(self.id)
		else:	# pas d'option mix : chaque courbe a son propre graphe
			gcolor=config.grafcolor
			glabel=config.glabel
			fcolor=config.fillcolor
			gwidth=1.0
		# dessine les données dans le graphe
		plt.plot_date(xdata,ydata,fmt=mark,color=gcolor,label=glabel,linewidth=gwidth)
		if fcolor:
			self.axes.fill_between(xdata,0,ydata,facecolor=fcolor)
		# formatte l'axe des X (dates)
		self.axes.legend(loc="lower left",fontsize="x-small")
		plt.xlim(xmin,xmax)	# fixe l'échelle de l'axe X
		self.axes.xaxis.set_major_locator(majorloc)
		self.axes.xaxis.set_minor_locator(minorloc)
		xfmt=pltdates.DateFormatter(fmt)
		self.axes.xaxis.set_major_formatter(xfmt)
		self.axes.xaxis.set_tick_params(labelsize=config.labelsize)
		labels=self.axes.get_xticklabels()
		plt.setp(labels,rotation=0.0,horizontalalignment='center')

		# formatte l'axe des Y (mesures)
		plt.ylim(ymin,ymax)	# fixe l'échelle de l'axe Y
		plt.ylabel(config.ylabel,fontsize=config.axesize,color='xkcd:royal blue')
		yfmt=pltticker.FormatStrFormatter("%.1f")
		self.axes.yaxis.set_major_formatter(yfmt)
		self.axes.yaxis.set_tick_params(labelsize=config.labelsize)

	def saveGraph(self,config):
		self.imgname='%s.png' % self.id
		path=os.path.join(config.imgpath,self.imgname)
		self.fig.savefig(path)

	def showGraph(self):
		plt.show()

	def analyze(self,datemax=None,h=4.0):
		result=None
		if len(self.data)>0:
			datas=[]
			self.data.sort(key=lambda item: item.t)
			if datemax==None:
				datemax=self.data[-1].t
			datemin=datemax-datetime.timedelta(hours=h)
			for d in self.data:
				if d.t>=datemin and d.t<=datemax:
					datas.append(d)
			if len(datas)>0:
				result=AnalyzeData(datas)
			else:
				print("ERROR analyze no data in the interval",datemin,"-",datemax)
		else:
			print("ERROR analyze no data")
		return result

	def getStation(self,config,size=25):
		""" Télécharge les données pour une station de mesures hydrométrique suivant son identifiant Vigiecrues
			en utilisant le protocole v1 de l'API hubeau
			Enchaine les fonctions de téléchargement de l'objet Station pour avoir toutes les données
		"""
		
		if config.download:
			# 1. Récupère les informations de la station de mesure
			self.downloadInfo()
			if not config.info:
				self.showName(withID=True,prefix="  - ")
			# 2. Récupère les mesures de la station (date+hauteur)
			if len(self.data)>0:	# extrait la dernière date des données locales
				self.data.sort(key=lambda item: item.t)
				date=self.data[-1].t
				# hubeau API 1.1 n'autorise pas les dates inférieures à 1 mois
				dt=datetime.datetime.now()-date
				if dt.days>28:
					date=None
			else:
				date=None
			print("      download from:",date,"pagesize (max):",config.datasize)
			self.downloadData(date,config.datasize)
		# 3. Afficher les données
		if len(self.data)>0:
			if config.info:
				self.showSummarize()
			return True
		else:
			print("erreur : aucune données pour la station",self.getID())
			return False

class AnalyzeData():
	""" AnalyzeData : objet permettant l'analyse des données brutes d'une station
		pour calculer des paramétres d'évolution.
		Les données passées à Init correspondate a une sélection préalable
	"""
	def __init__(self,datas):
		""" parcourt les données fournis pour calculer les paramètres d'évolution :
				moyenne
				vitesse
			datas est une liste de données (couple date,mesures) ordonnées par date
	 	"""
		self.first=datas[0]		# date première mesure
		self.last=datas[-1]		# date dernière mesure
		self.dtime=self.last.t-self.first.t		# écart temporel entre le début et la fin
		self.dvalue=self.last.v-self.first.v	# écrat de valeurs de mesure entre le début et la fin
		self.mini=9999.9
		self.maxi=0.0
		self.mean=0.0
		# calcul de la moyenne, le mini et le maxi
		for d in datas:
			self.mean=self.mean+d.v
			if d.v>self.mini: self.mini=d.v
			if d.v<self.maxi: self.maxi=d.v
		self.mean=self.mean/len(datas)
		# calcul de la vitesse
		if self.dtime.total_seconds()>0.0:	
			self.speed=(self.dvalue)/(self.dtime.total_seconds()/3600.0)
		else:
			self.speed=0.0

	def getlast(self):
		""" retourne la dernière données"""
		return self.last

	def getdeltatime(self):
		""" retourne l'écart temporel entre le début et la fin des données """
		return self.dtime

	def getdeltavalue(self):
		""" retourne l'écart en hauteur (mètres) entre le début et la fin"""
		return self.dvalue

	def getmean(self):
		""" retourne la valeur moyenen de hauteur 'mètres) des données"""
		return self.mean
	
	def getspeed(self):
		""" retourne la vitesse d'évolution entre le début et la fin"""
		return self.speed

class StationList(list):
	""" Encapsule une liste d'objets de type Station
		intègre la création d'une page HTML incluant les graphes de chaque station de la liste
	"""
	def __init__(self):
		list.__init__(self)

	def append(self,item):
		""" ajout d'une station à la liste """
		self.state=self.checkStation(item)
		if self.state==0:	# ajout seulement si nouvelle
			list.append(self,item)
		elif self.state==1:
			print("ERROR, need station updates",item)

	def checkStation(self,station):
		""" vérifie la présence d'une station dans la liste et retourne l'état """
		for s in self:
			if s.id==station.id:
				s.data=station.data
				return 2	# existe déjà
		return 0	# nouvelle (existe pas déjà)

	def computeMinMax(self,date_min=None,date_max=None):
		""" calcule les min/max communs à toutes les stations sur une période données 
			(préparation normalisation du graphique """
		x_lim=None
		y_lim=None
		for s in self:	# parcours toutes les stations
			# calculer les min/max de la station pour la période données
			tmin=datetime.datetime.utcnow()
			tmax=datetime.datetime(1900,1,1,0,0,0)
			vmin=9999.9
			vmax=0.0
			if date_min==None and date_max==None:
				for d in s.data:
					if d.t>tmax: tmax=d.t
					if d.t<tmin: tmin=d.t
					if d.v>vmax: vmax=d.v
					if d.v<vmin: vmin=d.v
			else:
				if date_min==None:
					date_min=datetime.datetime(1900,1,1,0,0,0)
				if date_max==None:
					date_max=datetime.datetime.utcnow()		
				for d in s.data:
					if d.t>=date_min and d.t<=date_max:
						if d.t>tmax: tmax=d.t
						if d.t<tmin: tmin=d.t
						if d.v>vmax: vmax=d.v
						if d.v<vmin: vmin=d.v
			# chercher les min/max des axes entre tous les graphes
			if x_lim==None:
				x_lim=[tmin,tmax]
				if _debug:
					print("no x limit, set:",x_lim)
			else:
				if tmin<x_lim[0]: x_lim[0]=tmin
				if tmax>x_lim[1]: x_lim[1]=tmax
				if _debug:
					print("adjusted x limit, to:",x_lim," / according:",tmin,tmax)
			if y_lim==None:
				y_lim=[vmin,vmax]
				if _debug:
					print("no y limit, set:",y_lim)
			else:
				if vmin<y_lim[0]: y_lim[0]=vmin
				if vmin>y_lim[1]: y_lim[1]=vmax
				if _debug:
					print("adjusted y limit, to:",y_lim," / according:",vmin,vmax)
		if _debug:
			print("absolute x limit:",x_lim)
			print("absolute y limit:",y_lim)
		return(x_lim,y_lim)
		
	def getMinMax(self):
		""" retourne les min/max globaux """
		return (self.x_lim,self.y_lim)

	def generateHTML(self,config,search=False):
		""" Crée un fichier index.html dans le répertoire des images
			et qui encapsule les graphes créés (images), permet un affichage des résultats
			La création du fichier html est réalisée via le module ElementTree
		"""
		# étape 1 : préparation fichier HTML
		path=os.path.join(config.imgpath,config.html)
		path=config.getHTMLPath()
		if _verbose or _debug:
			print("Mise à jour du fichier HTML:",path)
		date_fin=datetime.datetime.utcnow()
		date_deb=date_fin-datetime.timedelta(days=config.plotdays)
		(x_lim,y_lim)=self.computeMinMax(date_deb,date_fin)
		if _debug:
			print("Période",date_deb,"-",date_fin)
			print("x_lim",x_lim)
			print("y_lim",y_lim)
		# étape 2 : génère le fichier HTML5+CSS+JS (en UTF-8)
		html=HubEauHTML(config)
		if len(self)>0:
			if search:
				mapid="searchmapid"
				div=ET.Element('div',attrib={'id':'bid','class':'clearfix'})
				html.addToBody(div)
				p=ET.Element('h3')
				div.append(p)
				p=ET.Element('p')
				div.append(p)
				p.text=u"Recherche:"
				if config.map:
					p.text=u"%d stations trouvée(s), voir carte ci-dessous" % len(self)
				else:
					for s in self:
						p=ET.Element('p')
						div.append(p)
						p.text=u"Station %s" % self[0].getName(withID=True)
			else:
				mapid="datamapid"
				if config.mix:
					self[0].initPlot(config)
					figure=self[0].fig
					axes=self[0].axes
				else:
					figure=None
					axes=None
				i=0
				for s in self:		# parcours les stations
					# créer le graphe de la station
					s.createGraph(config,x_lim,y_lim,figure=figure,axes=axes,index=i)
					if not config.mix:	# sans option mix, chaque station a son propre graph et propre stats
						s.saveGraph(config)
						# incorpore le graphe (image) dans le HTML
						iname=os.path.basename(s.imgname).split('.')[0]
						div=ET.Element('div',attrib={'id':'bid','class':'clearfix'})
						html.addToBody(div)
						img=ET.Element('img',attrib={'id':'gid','src':s.imgname,'alt':iname,'class':'plot'})
						div.append(img)
						p=ET.Element('h3')
						div.append(p)
						p.text=u"Station %s" % s.getName(withID=True)
						p=ET.Element('p')
						div.append(p)
						p.text=u"Liens : "
						a=ET.Element('a',attrib={'href':'https://www.vigicrues.gouv.fr/niv3-station.php?CdStationHydro=%s' % s.getID()})
						p.append(a)
						a.text=u"VigieCrue"
						a=ET.Element('a',attrib={'href':'https://www.hydro.eaufrance.fr/stationhydro/%s/fiche' % s.getID()})
						p.append(a)
						a.text=u"Fiche Station"
						lastm=True
						for ih in (4.0,24.0,168.0):	# calcul les variations pour les décalage horaires indiquées
							a=s.analyze(h=ih)
							if lastm:
								last=a.getlast()
								p=ET.Element('p')
								div.append(p)
								p.text=u"dernière mesure : %.3f m @ %s" % (last.v,last.t.strftime("%d/%m/%Y @ %H:%M"))
								lastm=False
							p=ET.Element('p')
							div.append(p)
							p.text=u"%d H variation: %+.3f m, vitesse: %+.1f cm/h" % (int(ih),a.getdeltavalue(),100.0*a.getspeed())
					i=i+1
				if config.mix:	# avec l'option lmix, il y a regroupement des graphes en 1 seul et les stats de la première station uniquement
					self[0].saveGraph(config)
					# incorpore le graphe (image) dans le HTML
					iname=os.path.basename(self[0].imgname).split('.')[0]
					div=ET.Element('div',attrib={'id':'bid','class':'clearfix'})
					html.addToBody(div)
					img=ET.Element('img',attrib={'id':'gid','src':self[0].imgname,'alt':iname,'class':'plot'})
					div.append(img)
					p=ET.Element('h3')
					div.append(p)
					p.text=u"Station %s" % self[0].getName(withID=True)
					p=ET.Element('p')
					div.append(p)
					p.text=u"Liens : "
					a=ET.Element('a',attrib={'href':'https://www.vigicrues.gouv.fr/niv3-station.php?CdStationHydro=%s' % self[0].getID()})
					p.append(a)
					a.text=u"VigieCrue"
					a=ET.Element('a',attrib={'href':'https://www.hydro.eaufrance.fr/stationhydro/%s/fiche' % self[0].getID()})
					p.append(a)
					a.text=u"Fiche Station"
					lastm=True
					for ih in (4.0,24.0,168.0):
						a=self[0].analyze(h=ih)
						if lastm:
							last=a.getlast()
							p=ET.Element('p')
							div.append(p)
							p.text=u"dernière mesure : %.3f m @ %s" % (last.v,last.t.strftime("%d/%m/%Y @ %H:%M"))
							lastm=False
						p=ET.Element('p')
						div.append(p)
						p.text=u"%d H variation: %+.3f m, vitesse: %+.1f cm/h" % (int(ih),a.getdeltavalue(),100.0*a.getspeed())
			if config.map>0:	# création du code Javascript pour affichier la carte OSM via leaflet.js
											# carte avec marqueurs des stations et recentrée pour afficher tous les marqueurs
											# marquerus avec couleurs spécifique correspondante aux graphes
				div=ET.Element('div',attrib={'id':'%s' % mapid})
				html.addToBody(div)
				script=ET.Element('script')
				script.text="""
					var mymap = L.map('%s').setView([0.0,0.0,],5);
					L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', 
						{ attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
						}).addTo(mymap);
					var icon=new Array();""" % mapid
				if len(self)>len(colorList):
					mlength=0
				else:
					mlength=len(self)
				if mlength==0:
					script.text+="""
					icon[%d] = new L.Icon({
						iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-%s.png',
						shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
						iconSize: [25, 41],	iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41]});""" % (0,colorList[0])
				else:
					for i in range(mlength):
						script.text+="""
						icon[%d] = new L.Icon({
							iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-%s.png',
							shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
							iconSize: [25, 41],	iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41]});""" % (i,colorList[i])
				script.text+="""
					var markers = L.featureGroup();"""
				txt=""
				colorIndex=0;
				for s in self:		# pour chaque station crée un marqueur avec les infos de la station
					if search:
						txt+="""
							m=L.marker([%.8f,%.8f], {icon: icon[%d]}).addTo(mymap);
							m.bindPopup('%s:%s<br>(%s)');
							m.addTo(markers);
							""" % (s.latitude,s.longitude,colorIndex,s.id,s.nom,s.coursdeau)
					else:
						lastm=True
						infoTxt=""
						for ih in (4.0,24.0,168.0):
							a=s.analyze(h=ih)
							if lastm:
								last=a.getlast()
								infoTxt+=u"dernière mesure : %.3f m @ %s" % (last.v,last.t.strftime("%d/%m/%Y @ %H:%M"))
								lastm=False
							infoTxt+=u"<br>%d H variation: %+.3f m, vitesse: %+.1f cm/h" % (int(ih),a.getdeltavalue(),100.0*a.getspeed())
						txt+="""
							m=L.marker([%.8f,%.8f], {icon: icon[%d]}).addTo(mymap);
							m.bindPopup('%s:%s<br>(%s)<br>%s');
							m.addTo(markers);
							""" % (s.latitude,s.longitude,colorIndex,s.id,s.nom,s.coursdeau,infoTxt)
					if mlength>0:
						colorIndex=colorIndex+1
				txt+="mymap.fitBounds(markers.getBounds().pad(0.5));"
				script.text+=txt
				html.addToBody(script)
		else:
			p=ET.Element('h3')
			html.addToBody(p)
			p.text=u"ERROR"
			p=ET.Element('p')
			html.addToBody(p)
			p.text=u"Aucune Station dans la liste, rien à afficher"
		if _debug:
			print(html)
		if _debug:
			print("html/path",path)
			print("html/data")
			print(html)
		html.write(path)

	def showMap(self,config):
		""" showMap : affiche sur une carte OSM l'emplacement des stations de la liste
		"""
		baseUrl="https://www.openstreetmap.org/?mlat=%.4f&mlon=%.4f&#map=%d/%.4f/%.4f"
		station=self[0]
		if station:
			lat=station.latitude
			lon=station.longitude
			zoom=16	
			url=baseUrl % (lat,lon,zoom,lat,lon)
			webbrowser.open(url,autoraise=True)
	
	def show(self,config):
		""" Lancer la navigateur pour ouvrir le fichier HTML avec les résultats """
		path=os.path.join(config.imgpath,config.html)
		webbrowser.open(path,autoraise=True)

class HubEauHTML():
	""" HubEauHTML
		Création et manipulation d'une page HTML via la librairie ET (xml.etree)
	"""
	def __init__(self,config):
		""" Création de la structure de base d'une page HTML Hubeau avec header et un corps vide
			L'entête inclus les styles CSS Hubeau et la librairie javascript Leaflet
			
			self.html
			self.body
		"""
		self.config=config

		self.html=ET.Element('html')
		head=ET.Element('head')
		self.html.append(head)
		meta=ET.Element('meta',attrib={'charset':'UTF-8'})
		head.append(meta)
		title=ET.Element('title')
		title.text=u"Suivi hauteur de la Charente via hubeau.eaufrance.fr"
		head.append(title)
		style=ET.Element('style')
		style.text=config.css
		head.append(style)
		if config.map:		# code pour la librairie Leaflet (en ligne)
			"""leafletSrcCSS='https://unpkg.com/leaflet@1.7.1/dist/leaflet.css'
			leafletShaCSS='sha512-xodZBNTC5n17Xt2atTPuE1HxjVMSvLVW9ocqUKLsCC5CXdbqCmblAshOMAS6/keqq/sMZMZ19scR4PsZChSR7A=='
			leafletSrcJS='https://unpkg.com/leaflet@1.7.1/dist/leaflet.js'
			leafletShaJS='sha512-XQoYMqMTK8LvdxXYG3nZ448hOEQiglfqkJs1NOQV44cWnUrBc8PkAOcXy20w0vlaXaVUearIOBhiXZ5V3ynxwA=='
			"""
			leafletSrcCSS='https://unpkg.com/leaflet@1.9.3/dist/leaflet.css'
			leafletShaCSS='sha256-kLaT2GOSpHechhsozzB+flnD+zUyjE2LlfWPgU04xyI='
			leafletSrcJS='https://unpkg.com/leaflet@1.9.3/dist/leaflet.js'
			leafletShaJS='sha256-WBkoXOwTeyKclOHuWtc+i2uENFpDZ9YPdf5Hf+D7ewM='
			link=ET.Element('link', attrib={'rel':'stylesheet', 'href':leafletSrcCSS, 'integrity':leafletShaCSS, 'crossorigin':''})
			head.append(link)
			script=ET.Element('script', attrib={'src':leafletSrcJS, 'integrity':leafletShaJS, 'crossorigin':''})
			head.append(script)
		self.body=ET.Element('body')
		self.html.append(self.body)
	
	def addToBody(self,elem):
		self.body.append(elem)
		return

	def write(self,path):
		with open(path,'w') as f:
			f.write("<!DOCTYPE html>\n")	# ajout du doctype en première ligne
			if sys.version_info.major==2:
				ET.ElementTree(self.html).write(f, encoding='utf-8',method='html')
			else:
				ET.ElementTree(self.html).write(f, encoding='unicode',method='html')
		return

class StationRequest():
	""" StationRequest : permet de construire une recherche de station(s) de mesure
		interroge l'API hubeau-hydro pour retrouver une ou plusieurs stations
			- river : pour rechercher un cours d'eau par son noms
			- station : pour rechercher par le nom de la station
			- city : pour rechercher par la dénomination de la commune
			- departement : pour rechercher dans un département
		On peut combiner les critères
	"""
	def __init__(self,config):
		self.config=config
		self.river=None
		self.name=None
		self.city=None
		self.departement=None

	def do(self,river=None,station=None,city=None,departement=None):
		self.river=river
		self.name=station
		self.city=city
		self.departement=departement
		hubeauStationAPI="http://hubeau.eaufrance.fr/api/v1/hydrometrie/referentiel/stations"
		finalurl="format=json&size=100"
		requesturl=""
		separator="?"
		result=StationList()
		if self.river:
			if _debug:
				print("recherche par cours d'eau:",self.river)
			requesturl+=separator+"libelle_cours_eau=%s" % self.river
			separator="&"
		if self.name:
			if _debug:
				print("recherche par libellé:",self.name)
			requesturl+=separator+"libelle_station=%s" % self.name
			separator="&"
		if self.city:
			if _debug:
				print("recherche par code commune:",self.city)
			requesturl+=separator+"code_commune_station=%s" % self.city
			separator="&"
		if self.departement:
			if _debug:
				print("recherche par code département:",self.departement)
			requesturl+=separator+"code_departement=%s" % self.departement
			separator="&"
		if len(requesturl)>0:
			url=hubeauStationAPI+requesturl+separator+finalurl
		else:
			url=None
		page=1
		nb=0
		while url:
			if _debug:
				print("url (%d):" % page,url)
			r=requests.get(url,headers={'user-agent':user_agent})		# télécharge les données brutes depuis l'URL
			if r.status_code<=206:
				content=r.headers['content-type']
				if 'json' in content:
					json=r.json()				# convertir les données brutes en objet JSON
					next=json["next"]
					datas=json["data"]			# récupère la porton data du JSON
					if _debug:
						print("results:",len(datas))
					for data in datas:
						if _debug:
							print("candidate:",data['code_station'])
						if data['en_service']:
							s=Station(data['code_station'])
							s.nom=data['libelle_station']
							s.departement=int(data['code_departement'])
							s.longitude=float(data['longitude_station'])
							s.latitude=float(data['latitude_station'])
							s.coursdeau_code=data['code_cours_eau']
							s.coursdeau=data['libelle_cours_eau']
							s.type=data['type_station']
							s.actif=data['en_service']
							s.showName(True)
							result.append(s)
							nb+=1
					page=page+1
					url=next
				else:
					print("url:",url)
					print("Response is not a JSON",content)
			else:
				print("url:",url)
				print("HTTP Status error :",r.status_code)
		if nb<1:
			print("Aucun résultat")
		return result

# --  Aide  --------------------------------------------------------------------------------
#			lettre-code : {nom-long, type de valeur, valeur par défaut, aide}
arguments={	'h':("help",None,None,"aide"),
			'r':("findriver","<nom>",None,"cherche les stations se trouvant sur le cours d'eau"),
			'n':("findname","<nom>",None,"cherche les stations dont le nom correspond"),
			'c':("findcity","<nom>",None,"cherche les stations d'une commune par code INSEE"),
			'e':("finddep","<nom>",None,"cherche les stations d'un département par code INSEE"),
			's':("station","<liste>",None,"liste des codes stations a afficher"),
			't':("time","<d>","10","nombre de jours a représenter sur la graphique"),
			'g':("show",None,"Non","Affiche le graphique dans le navigateur"),
			'd':("database",None,"Non","Ne pas télécharger les mises à jour de données"),
			'm':("mix",None,"Oui","Fusionne les données en un seul graphique"),
			'i':("info",None,"Non","Affiche les informations des stations interrogées"),
			'o':("osm",None,"Oui","Affiche la carte avec les stations localisées"),
			'x':("debug",None,"Non","Active le mode deboggage")
		}

def show_usage():
	print("--------------------------------------------")
	print("%s %s" %(__file__,__version__))
	print("  %s" % __copyright__)
	print("  Licence : %s" % __license__)
	print("Récupère les mesures de hauteur de cours d'eau")
	print("depuis l'API HubEau hydrométrie.")
	print("Créer un graphique et une mise en page HTML")
	print("--------------------------------------------")
	print("options :")
	for a in arguments:
		(arg,attrb,default,help)=arguments[a]
		if attrb:
			arg+=":%s" % attrb
		if default:
			help+=" (défaut=%s)" % default
		print("  -%s (--%s)\t%s" % (a,arg,help))
	print("--------------------------------------------")
	print()

# -- Démarrage --------------------------------------------------------------------------------

def main(argv):
	global _debug

	print("--",__file__,__version__,"-----------------")
	# 1. initialise et charger les paramètres '.INI)
	config=Config()
	# 2. charger les paramètres de la CLI (command line interface)
	shortList=""	# chaine avec les arguments courts (1 lettre, suivi de : si valeur a passer)
	longList=[]		# les des noms d'arguments long (suivi de = si valeur à passer)
	for a in arguments:
		(arg,attrb,default,help)=arguments[a]
		if attrb:
			a+=':'
			arg+='='
		shortList+=a
		longList.append(arg)
	idList=[]
	search=False
	riversearch=None
	namesearch=None
	citysearch=None
	depsearch=None
	try: 
		opts,args=getopt.getopt(argv,shortList,longList)
	except:
		show_usage()
		sys.exit(2)
	for opt,arg in opts:	# parcourir les arguments pour mettre à jour la configuration par défaut
		opt=opt.replace('-','')
		if _debug:
			print(opt,":",arg)
		option=None
		for a in arguments:
			(ida,attrb,default,help)=arguments[a]
			if opt in (a,ida):
				option=a
		if option=="h":
			show_usage()
			exit()
		elif option=="s":
			al=arg.split(",")
			for a in al:
				idList.append(a)
		elif option=="g":
			config.show=not config.show
		elif option=="d":
			config.download=not config.download
		elif option=="r":
			riversearch=arg
			search=True
		elif option=="n":
			namesearch=arg
			search=True
		elif option=="c":
			citysearch=arg
			search=True
		elif option=="e":
			depsearch=arg
			search=True
		elif option=="i":
			config.info=not config.info
		elif option=="t":
			config.plotdays=float(arg)
		elif option=="m":
			config.mix=not config.mix
		elif option=="o":
			config.map=not config.map
		elif option=="x":
			_debug=True
		else:
			print("ERREUR : paramètre",opt,"non géré")
	if len(idList)==0:	# si aucune stations dans la CLI, charger la config par défaut (.INI)
		idList=config.idList
	if len(idList)>maxGraph:
		print("alerte : liste stations trop longue, max=",maxGraph)
		idList=idList[:maxGraph]
	# 3. charger les données (stations et mesures)
	db=DataBase(config)
	dbStationlist=db.load(idList)
	# 4. oriente l'exécution selon les options choisies
	if not os.path.exists(config.imgpath):		# créer le dosier pour sauvegarde les HTML et images
		os.mkdir(config.imgpath)
	if search:	# recherche de stations 
		if _debug:
			print("recherche")
			print(" (cours d'eau):",riversearch)
			print(" (libellé):",namesearch)
			print(" (commune):",citysearch)
			print(" (département):",depsearch)
		request=StationRequest(config)
		stationList=request.do(river=riversearch,station=namesearch,city=citysearch,departement=depsearch)
		stationList.generateHTML(config,search)	# créer le fichier HTMl de la liste des stations demandées
		if config.show:
			stationList.show(config)
	else:	# pas de recherche, mettre à jour les données de(s) station(s)
		if os.path.exists(config.imgpath):			# vérifier l'existance des chemins de sauvegarde
			if os.path.isdir(config.imgpath):
				# 4a. charger les dernières données de chaque station de la liste requête (hubeau)
				if config.download:
					print("Mise à jour des stations :")
				stationList=StationList()
				for item in idList :				# parcourir les stations candidates et mettre en liste les stations avec données
					station=Station(item)
					for s in dbStationlist:
						if s.id==item:				# si la station et déjà dans la base de données reprendre celle-ci (avec les données)
							station=s
							break
					if station.getStation(config):		# charge les nouvelles données et mettre à jour
						stationList.append(station)		# ajouter à la liste des stations gérées (test existance intégré)
				# 4b. Créer la page HTML et le ou les graphiques associés
				stationList.generateHTML(config)	# créer le fichier HTMl de la liste des stations demandées
				if config.show:
					stationList.show(config)
				# 4c. Mise à jour des données de la base de données locales
				print("Sauvegarde des nouvelles données")
				db.store(stationList)	# mémoriser les mises à jour
			else:
				print("erreur : le chemin de sauvegarde n'est pas vers un répertoire")
				print("\t",config.imgpath)
		else:
			print("erreur : le chemin de sauvegarde n'existe pas")
			print("\t",config.imgpath)

if __name__ == '__main__' :
	main(sys.argv[1:])

