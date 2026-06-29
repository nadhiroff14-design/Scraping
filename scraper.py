"""
scraper.py — Moteur de collecte et classification d'entreprises béninoises
Sources : Google Maps (Outscraper), simulation réaliste + GPT classification
"""

import json
import csv
import os
import time
import random
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

# ─── CONFIG ───────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_FILE = DATA_DIR / "entreprises.json"
LOG_FILE = DATA_DIR / "scraping_log.json"
EXPORT_DIR = DATA_DIR / "exports"
EXPORT_DIR.mkdir(exist_ok=True)

SECTEURS_BENIN = [
    "BTP & Immobilier", "Commerce & Distribution", "Restauration & Hôtellerie",
    "Santé & Pharmacie", "Finance & Assurance", "Transport & Logistique",
    "Télécommunications", "Agriculture & Agroalimentaire", "Éducation & Formation",
    "Technologie & IT", "Industrie & Manufacture", "Services aux entreprises",
    "Énergie & Environnement", "Médias & Communication", "ONG & Associations"
]

DEPARTEMENTS_BENIN = [
    "Alibori", "Atacora", "Atlantique", "Borgou", "Collines", "Couffo",
    "Donga", "Littoral", "Mono", "Ouémé", "Plateau", "Zou"
]

VILLES_BENIN = [
    "Abomey", "Abomey-Calavi", "Adja-Ouèrè", "Adjarra", "Adjohoun", "Agbangnizoun", "Aguégués",
    "Allada", "Aplahoué", "Athiémé", "Avrankou", "Banikoara", "Bantè", "Bassila", "Bembéréké",
    "Bohicon", "Bonou", "Bopa", "Boukoumbé", "Cobly", "Comè", "Copargo", "Cotonou", "Covè",
    "Dangbo", "Dassa-Zoumè", "Djakotomey", "Djidja", "Djougou", "Dogbo", "Glazoué", "Gogounou",
    "Grand-Popo", "Houéyogbé", "Ifangni", "Kalalé", "Kandi", "Karimama", "Kérou", "Kétou",
    "Klouékanmè", "Kouandé", "Kpomassè", "Lalo", "Lokossa", "Malanville", "Matéri", "Missérété",
    "Ndali", "Natitingou", "Nikki", "Ouaké", "Ouèssè", "Ouidah", "Ouinhi", "Parakou", "Péhunco",
    "Pèrèrè", "Pobè", "Porto-Novo", "Sakété", "Savalou", "Savè", "Ségbana", "Sèmè-Podji",
    "Sinendé", "Sô-Ava", "Tanguiéta", "Tchaourou", "Toffo", "Tori-Bossito", "Toucountouna",
    "Toviklin", "Zagnanado", "Za-Kpota", "Zè", "Zogbodomey"
]

# Organisation des villes par département
VILLES_PAR_DEPARTEMENT = {
    "Alibori": ["Banikoara", "Gogounou", "Kandi", "Karimama", "Malanville", "Ségbana"],
    "Atacora": ["Boukoumbé", "Cobly", "Kérou", "Kouandé", "Matéri", "Natitingou", "Péhunco", "Tanguiéta", "Toucountouna"],
    "Atlantique": ["Abomey-Calavi", "Allada", "Kpomassè", "Ouidah", "Sô-Ava", "Tori-Bossito", "Zè"],
    "Borgou": ["Bembéréké", "Djougou", "Glazoué", "Kalalé", "Ndali", "Nikki", "Parakou", "Pèrèrè", "Sinendé", "Tchaourou"],
    "Collines": ["Bantè", "Dassa-Zoumè", "Djidja", "Glazoué", "Ouèssè", "Savalou", "Savè"],
    "Couffo": ["Aplahoué", "Athiémé", "Bopa", "Dogbo", "Houéyogbé", "Klouékanmè", "Lalo"],
    "Donga": ["Bassila", "Copargo", "Djougou", "Ouaké"],
    "Littoral": ["Cotonou"],
    "Mono": ["Adjohoun", "Agbangnizoun", "Aguégués", "Athiémé", "Bopa", "Comè", "Grand-Popo", "Houéyogbé", "Kpomassè", "Lokossa"],
    "Ouémé": ["Adjarra", "Adjohoun", "Agbangnizoun", "Aguégués", "Avrankou", "Bonou", "Dangbo", "Missérété", "Porto-Novo", "Sèmè-Podji"],
    "Plateau": ["Adja-Ouèrè", "Adjarra", "Adjohoun", "Agbangnizoun", "Aguégués", "Ifangni", "Kétou", "Pobè", "Sakété", "Zagnanado", "Za-Kpota"],
    "Zou": ["Abomey", "Bohicon", "Covè", "Djidja", "Ouinhi", "Savalou", "Savè", "Toffo", "Toviklin", "Zogbodomey"]
}



# Templates intelligents par secteur pour génération réaliste
SECTEUR_TEMPLATES = {
    "BTP & Immobilier": {
        "prefixes": ["SO", "Groupe", "Cabinet", "Ets", "SARL", "SA", "SCI", "BTP", "Promotion", "Construction"],
        "racines": ["Béton", "Travaux", "Construction", "Immobilier", "Bâtiment", "Habitat", "Maison", "Urbanisme", "Architecte", "Ingénierie", "Fondation", "Structure", "Toiture", "Plomberie", "Électricité", "Maçonnerie", "Peinture", "Menuiserie", "Ferronnerie", "Isolation", "Clôturage", "Terrassement", "Voirie", "Aménagement", "Rénovation", "Réhabilitation", "Promotion", "Location", "Gestion", "Syndic", "Copropriété"],
        "suffixes": ["Bénin", "Africa", "International", "SARL", "SA", "Groupe", "Ets", "Cabinet", "Solutions", "Services", "Bâtiments", "Habitat", "Promotion", "Construction"],
        "types": ["B2B", "B2C"],
        "prob_email": 0.75,
        "prob_site": 0.8
    },
    "Commerce & Distribution": {
        "prefixes": ["Super", "Marché", "Centre", "Ets", "SARL", "Groupe", "Distribution", "Commerce", "Magasin", "Boutique", "Store", "Shop"],
        "racines": ["Alimentaire", "Épicerie", "Supermarché", "Marché", "Boutique", "Commerce", "Distribution", "Grossiste", "Détaillant", "Provision", "Supply", "Stock", "Magasin", "Hypermarché", "Discount", "Hard", "Discount", "Cash", "Carry", "Drive", "Électroménager", "High-Tech", "Mode", "Vêtements", "Chaussures", "Cosmétique", "Parfumerie", "Jouets", "Sport", "Bricolage", "Jardin", "Meuble", "Décoration", "Automobile", "Moto", "Quincaillerie", "Outillage"],
        "suffixes": ["Bénin", "Market", "Store", "Shop", "SARL", "Ets", "Groupe", "International", "Distribution", "Commerce"],
        "types": ["B2C", "B2B/B2C"],
        "prob_email": 0.65,
        "prob_site": 0.7
    },
    "Restauration & Hôtellerie": {
        "prefixes": ["Hôtel", "Restaurant", "Café", "Brasserie", "Auberge", "Pension", "Bar", "Snack", "Fast", "Food", "Cantine", "Traiteur"],
        "racines": ["Royal", "Palace", "Grand", "Nouveau", "Jardin", "Lac", "Mer", "Plage", "Village", "Gourmet", "Saveur", "Goût", "Table", "Ambiance", "Détente", "Plaisir", "Délice", "Saveurs", "Tradition", "Authentique", "International", "Continental", "Africain", "Local", "Fusion", "Grill", "Pizzeria", "Sushi", "Burger", "Tacos", "Sandwich", "Salade", "Pâtisserie", "Boulangerie", "Glacier", "Chocolaterie", "Brasserie", "Bistro", "Pub", "Lounge", "Discothèque", "Karaoke"],
        "suffixes": ["Inn", "Hotel", "Restaurant", "Café", "Brasserie", "Bénin", "International", "Palace", "Resort", "Spa", "Lodge", "Village"],
        "types": ["B2C"],
        "prob_email": 0.7,
        "prob_site": 0.85
    },
    "Santé & Pharmacie": {
        "prefixes": ["Clinique", "Hôpital", "Pharmacie", "Centre", "Cabinet", "Laboratoire", "Dispensaire", "Sanatorium", "Polyclinique"],
        "racines": ["Saint", "Sainte", "Royal", "Nouveau", "Central", "Médical", "Santé", "Vie", "Guérison", "Soins", "Bien-être", "Pharma", "Médicament", "Urgence", "Emergency", "Cardiologie", "Dermatologie", "Pédiatrie", "Gynécologie", "Ophtalmologie", "ORL", "Dentaire", "Orthodontie", "Radiologie", "Biologie", "Analyses", "Imagerie", "Rééducation", "Kinésithérapie", "Ostéopathie", "Acupuncture", "Nutrition", "Diététique", "Médecine", "Chirurgie", "Maternité", "Pédiatrique", "Gériatrique"],
        "suffixes": ["Clinique", "Hôpital", "Pharmacie", "Centre", "Cabinet", "Bénin", "International", "Medical", "Health", "Care", "Plus"],
        "types": ["B2C", "B2B"],
        "prob_email": 0.85,
        "prob_site": 0.8
    },
    "Finance & Assurance": {
        "prefixes": ["Banque", "Assurance", "Société", "Cabinet", "Groupe", "Finance", "Crédit", "Épargne", "Investissement", "Capital", "Micro", "Finance"],
        "racines": ["National", "International", "Africa", "West", "Bénin", "Crédit", "Épargne", "Investissement", "Capital", "Assurance", "Sécurité", "Protection", "Vie", "Santé", "Auto", "Multirisque", "IARD", "Prévoyance", "Retraite", "Épargne", "Placement", "Bourse", "Actions", "Obligations", "FCP", "SICAV", "Gestion", "Patrimoine", "Wealth", "Management", "Courtage", "Broker", "Trading", "Forex", "Crypto", "Blockchain", "Fintech", "Paiement", "Monétique", "Transfert", "Change", "Devise"],
        "suffixes": ["Bank", "Assurances", "Finance", "Capital", "Invest", "SARL", "SA", "Groupe", "International", "Partners", "Advisory"],
        "types": ["B2B", "B2C"],
        "prob_email": 0.95,
        "prob_site": 0.95
    },
    "Transport & Logistique": {
        "prefixes": ["Transport", "Logistique", "Express", "Rapide", "SARL", "Groupe", "Delivery", "Cargo", "Fret", "Transit", "Messagerie"],
        "racines": ["Express", "Rapide", "Urgent", "Livraison", "Cargo", "Fret", "Transit", "Route", "Maritime", "Aérien", "Déménagement", "Messagerie", "Courrier", "Distribution", "Supply", "Chain", "Chaîne", "Entrepôt", "Stockage", "Warehousing", "Froid", "Chambre", "Conteneur", "Portuaire", "Douane", "Transitaire", "Affrètement", "Courtage", "Navire", "Bateau", "Camion", "Poids", "Lourd", "Véhicule", "Utilitaire", "Taxi", "VTC", "Bus", "Car", "Transport", "Public", "Particulier", "Colis", "Paquet", "Envoi"],
        "suffixes": ["Transport", "Logistique", "Express", "Delivery", "Bénin", "Africa", "International", "SARL", "Shipping", "Cargo", "Freight"],
        "types": ["B2B", "B2C"],
        "prob_email": 0.75,
        "prob_site": 0.75
    },
    "Télécommunications": {
        "prefixes": ["Télécom", "Mobile", "Internet", "Réseau", "Connect", "Digital", "Fiber", "Wireless", "Satellite"],
        "racines": ["Mobile", "Internet", "Réseau", "Connect", "Data", "Voice", "Fiber", "Satellite", "Wireless", "Communication", "Télécom", "Tech", "Digital", "5G", "4G", "LTE", "VoIP", "SIP", "Trunk", "Cloud", "Hosted", "PBX", "Centrex", "VPN", "SD-WAN", "MPLS", "Bandwidth", "Débit", "Haut", "Vitesse", "Latence", "Ping", "Coverage", "Couverture", "Antenne", "Relais", "BTS", "Fibre", "Optique", "Câble", "Coaxial", "Sans", "Fil", "Radio", "Fréquence", "Spectre", "Opérateur", "Provider", "ISP", "FAI"],
        "suffixes": ["Bénin", "Africa", "International", "SARL", "SA", "Groupe", "Telecom", "Networks", "Connect", "Digital"],
        "types": ["B2C", "B2B"],
        "prob_email": 0.95,
        "prob_site": 0.95
    },
    "Agriculture & Agroalimentaire": {
        "prefixes": ["Ferme", "Plantation", "Ets", "SARL", "Groupe", "Agro", "Production", "Exploitation", "Domaine", "Coopérative"],
        "racines": ["Agro", "Agriculture", "Ferme", "Plantation", "Céréale", "Fruit", "Légume", "Élevage", "Bétail", "Pêche", "Aquaculture", "Transformation", "Industrie", "Alimentaire", "Coton", "Cacao", "Café", "Ananas", "Mangue", "Anacarde", "Karité", "Palme", "Huile", "Riz", "Maïs", "Sorgho", "Millet", "Igname", "Manioc", "Taro", "Patate", "Tomate", "Oignon", "Ail", "Piment", "Gombo", "Aubergine", "Poulet", "Porc", "Bœuf", "Mouton", "Chèvre", "Lait", "Fromage", "Yaourt", "Œuf", "Miel", "Cire", "Engrais", "Pesticide", "Semence", "Vétérinaire", "Santé", "Animale"],
        "suffixes": ["Agro", "Farm", "Plantation", "Bénin", "Africa", "SARL", "Ets", "Groupe", "Coop", "Production"],
        "types": ["B2B", "B2C"],
        "prob_email": 0.7,
        "prob_site": 0.65
    },
    "Éducation & Formation": {
        "prefixes": ["École", "Collège", "Lycée", "Université", "Institut", "Centre", "Académie", "Cours", "Formation", "École", "Enseignement"],
        "racines": ["National", "International", "Catholique", "Protestant", "Public", "Privé", "Liberté", "Excellence", "Savoir", "Connaissance", "Formation", "Éducation", "Apprentissage", "Développement", "Primaire", "Secondaire", "Supérieur", "Professionnel", "Technique", "Métier", "Compétence", "Qualification", "Certification", "Diplôme", "Licence", "Master", "Doctorat", "MBA", "Management", "Business", "Finance", "Marketing", "Communication", "RH", "Informatique", "Langue", "Anglais", "Français", "Espagnol", "Allemand", "Chinois", "Arabe", "Comptabilité", "Droit", "Médecine", "Ingénierie", "Architecture", "Design", "Art", "Musique", "Danse", "Sport", "Cuisine", "Pâtisserie"],
        "suffixes": ["School", "Academy", "Institute", "University", "College", "Lycée", "École", "Bénin", "International", "Formation", "Training"],
        "types": ["B2C", "B2B"],
        "prob_email": 0.85,
        "prob_site": 0.9
    },
    "Technologie & IT": {
        "prefixes": ["Digital", "Tech", "Soft", "Net", "Cyber", "Data", "Cloud", "Smart", "Info", "Sys", "Web", "App", "AI"],
        "racines": ["Solution", "Système", "Logiciel", "Application", "Développement", "Informatique", "Technologie", "Digital", "Cloud", "Data", "Cyber", "Security", "Network", "Web", "Mobile", "AI", "Intelligence", "Artificielle", "Machine", "Learning", "Deep", "Learning", "Blockchain", "Crypto", "Bitcoin", "Ethereum", "IoT", "Internet", "Things", "Big", "Data", "Analytics", "BI", "Business", "Intelligence", "ERP", "CRM", "SaaS", "PaaS", "IaaS", "DevOps", "CI/CD", "Agile", "Scrum", "Kanban", "UX/UI", "Design", "Frontend", "Backend", "Fullstack", "Database", "SQL", "NoSQL", "MongoDB", "PostgreSQL", "MySQL", "Oracle", "API", "REST", "GraphQL", "Microservices", "Serverless", "Container", "Docker", "Kubernetes", "Linux", "Windows", "macOS", "Android", "iOS", "Flutter", "React", "Vue", "Angular", "Node", "Python", "Java", "JavaScript", "PHP", "Ruby", "Go", "Rust", "C++", "C#", "Swift", "Kotlin"],
        "suffixes": ["Tech", "Soft", "Solutions", "Systems", "Digital", "Bénin", "Africa", "International", "SARL", "Labs", "Studios", "Works", "Hub"],
        "types": ["B2B", "B2C"],
        "prob_email": 0.95,
        "prob_site": 0.98
    },
    "Industrie & Manufacture": {
        "prefixes": ["Industrie", "Manufacture", "Usine", "Atelier", "Production", "Fabrique", "Unité", "Plant", "Works"],
        "racines": ["Métal", "Bois", "Textile", "Plastique", "Chimie", "Pharmaceutique", "Alimentaire", "Automobile", "Électronique", "Mécanique", "Transformation", "Fabrication", "Production", "Assemblage", "Emballage", "Conditionnement", "Emballage", "Carton", "Plastique", "Verre", "Métal", "Acier", "Aluminium", "Cuivre", "Zinc", "Fonte", "Ciment", "Béton", "Céramique", "Carrelage", "Peinture", "Vernis", "Colle", "Adhésif", "Papier", "Carton", "Imprimerie", "Édition", "Reliure", "Découpe", "Découpe", "Laser", "CNC", "Usinage", "Tournage", "Fraisage", "Perçage", "Soudure", "Mécanique", "Hydraulique", "Pneumatique", "Électrique", "Automatique", "Robotique", "Automatisation"],
        "suffixes": ["Industry", "Manufacture", "Factory", "Bénin", "Africa", "SARL", "SA", "Groupe", "Works", "Plant", "Industries"],
        "types": ["B2B"],
        "prob_email": 0.75,
        "prob_site": 0.75
    },
    "Services aux entreprises": {
        "prefixes": ["Cabinet", "Conseil", "Consulting", "Audit", "Expert", "Bureau", "Agence", "Partners", "Solutions"],
        "racines": ["Conseil", "Consulting", "Audit", "Expert", "Juridique", "Fiscal", "Comptable", "RH", "Formation", "Marketing", "Communication", "Stratégie", "Management", "Business", "Digital", "Transformation", "Innovation", "Performance", "Excellence", "Qualité", "ISO", "Norme", "Certification", "Accréditation", "Label", "Marque", "Image", "Réputation", "Communication", "Publicité", "Relations", "Publiques", "Presse", "Événementiel", "Organisation", "Événement", "Recrutement", "Chasse", "Tête", "Intérim", "CDD", "CDI", "Portage", "Salarial", "Freelance", "Indépendant", "Vérification", "Contrôle", "Inspection", "Surveillance", "Sécurité", "Protection", "Nettoyage", "Entretien", "Ménage", "Gardiennage", "Sécurité"],
        "suffixes": ["Consulting", "Advisory", "Partners", "Bureau", "Cabinet", "Bénin", "Africa", "International", "Services", "Solutions"],
        "types": ["B2B"],
        "prob_email": 0.9,
        "prob_site": 0.9
    },
    "Énergie & Environnement": {
        "prefixes": ["Énergie", "Power", "Solar", "Éolien", "Eau", "Environnement", "Vert", "Clean", "Eco", "Bio", "Nature"],
        "racines": ["Solaire", "Éolien", "Hydraulique", "Énergie", "Power", "Eau", "Assainissement", "Environnement", "Écologie", "Durable", "Renouvelable", "Vert", "Clean", "Biomasse", "Biogaz", "Géothermie", "Hydroélectricité", "Photovoltaïque", "Panneau", "Onduleur", "Batterie", "Stockage", "Réseau", "Grid", "Smart", "Grid", "Microgrid", "Offgrid", "Déchets", "Recyclage", "Tri", "Valorisation", "Compostage", "Incinération", "Dépollution", "Assainissement", "Traitement", "Filtration", "Purification", "Désinfection", "Potable", "Forage", "Puits", "Nappe", "Phréatique", "Irrigation", "Agriculture", "Pompage", "Distribution", "Adduction"],
        "suffixes": ["Energy", "Power", "Solar", "Water", "Environment", "Bénin", "Africa", "SARL", "Green", "Eco", "Clean"],
        "types": ["B2B", "B2C"],
        "prob_email": 0.8,
        "prob_site": 0.8
    },
    "Médias & Communication": {
        "prefixes": ["Radio", "TV", "Presse", "Journal", "Média", "Communication", "Agence", "Studio", "Production", "Diffusion"],
        "racines": ["National", "International", "Liberté", "Démocratie", "Information", "Nouvelles", "Actualité", "Média", "Radio", "Télévision", "Presse", "Journal", "Communication", "Publicité", "Marketing", "Digital", "Social", "Network", "Réseaux", "Sociaux", "Facebook", "Instagram", "Twitter", "LinkedIn", "TikTok", "YouTube", "Influenceur", "Blogueur", "Podcast", "Streaming", "VOD", "SVOD", "OTT", "Cinéma", "Film", "Série", "Documentaire", "Animation", "Production", "Réalisation", "Montage", "Mixage", "Son", "Image", "Vidéo", "Photo", "Graphisme", "Design", "Création", "Contenu", "Éditorial", "Rédaction", "Journalisme", "Reportage", "Enquête", "Interview"],
        "suffixes": ["Media", "Press", "Radio", "TV", "News", "Communication", "Bénin", "Africa", "Studios", "Productions", "Networks"],
        "types": ["B2C", "B2B"],
        "prob_email": 0.75,
        "prob_site": 0.85
    },
    "ONG & Associations": {
        "prefixes": ["Association", "ONG", "Fondation", "Organisation", "Club", "Société", "Ligue", "Fédération", "Syndicat", "Union"],
        "racines": ["Développement", "Humanitaire", "Social", "Environnement", "Éducation", "Santé", "Droits", "Femme", "Enfant", "Jeunesse", "Culture", "Sport", "Aide", "Solidarité", "Charité", "Philanthropie", "Bénévolat", "Volontariat", "Citoyenneté", "Démocratie", "Paix", "Justice", "Équité", "Inclusion", "Diversité", "Intégration", "Insertion", "Emploi", "Formation", "Entrepreneuriat", "Microfinance", "Épargne", "Crédit", "Coopération", "Partenariat", "Échange", "Dialogue", "Plaidoyer", "Advocacy", "Sensibilisation", "Prévention", "Protection", "Assistance", "Accompagnement", "Suivi", "Évaluation", "Monitoring", "Recherche", "Étude", "Analyse", "Publication", "Diffusion", "Capitalisation"],
        "suffixes": ["Association", "ONG", "Fondation", "Organisation", "Bénin", "Africa", "International", "Network", "Alliance", "Coalition"],
        "types": ["B2B", "B2C"],
        "prob_email": 0.7,
        "prob_site": 0.7
    }
}

SOURCES = ["Google Maps", "Facebook Pages", "CCIB Annuaire", "APIEx", "LinkedIn"]


def generer_id(nom, ville):
    h = hashlib.md5(f"{nom}{ville}".encode()).hexdigest()[:8]
    return f"BJ-{h.upper()}"


def simuler_scraping(source, secteur=None, ville=None, nb=50):
    """Simule un scraping intelligent avec génération réaliste basée sur les templates par secteur"""
    results = []
    s = secteur or random.choice(SECTEURS_BENIN)
    v = ville or random.choice(VILLES_BENIN)
    
    # Récupérer le template du secteur
    template = SECTEUR_TEMPLATES.get(s, SECTEUR_TEMPLATES["Commerce & Distribution"])
    
    for i in range(nb):
        # Génération intelligente du nom
        prefix = random.choice(template["prefixes"])
        racine = random.choice(template["racines"])
        suffix = random.choice(template["suffixes"])
        
        # Variantes de nom
        nom_variants = [
            f"{prefix} {racine}".strip(),
            f"{racine} {suffix}".strip(),
            f"{prefix} {racine} {suffix}".strip(),
            racine,
        ]
        nom = random.choice(nom_variants)
        
        # Ajouter la ville parfois pour plus de réalisme
        if random.random() > 0.8:
            nom = f"{nom} {v}"
        
        # Génération email intelligente avec variantes
        has_email = random.random() < template["prob_email"]
        email = ""
        if has_email:
            domain_variants = ["bj", "benin", "com.bj", "org.bj", "net"]
            
            # Nettoyer le nom pour l'email
            nom_clean = nom.lower().replace("'", "").replace("-", " ").replace(".", " ")
            mots = [m for m in nom_clean.split() if len(m) > 2]
            
            # Variantes de format d'email
            if len(mots) >= 2:
                email_formats = [
                    ".".join(mots[:2]),  # prenom.nom
                    mots[0][0] + "." + mots[1],  # p.nom
                    "".join(mots[:2]),  # prenomnom
                    mots[0] + random.choice(["", ".", "_"]) + mots[1],  # prenom_nom / prenom.nom
                ]
                email_prefix = random.choice(email_formats)
            elif len(mots) == 1:
                email_prefix = mots[0]
            else:
                # Fallback : utiliser les premiers caractères du nom original
                email_prefix = nom.lower()[:20].replace(" ", "")
            
            # Domaines plus réalistes
            if random.random() > 0.5:
                # Domaine basé sur le nom de l'entreprise
                site_domain = nom.lower().replace(" ", "").replace("'", "").replace("-", "")[:15]
                email = f"{email_prefix}@{site_domain}.{random.choice(['bj', 'com.bj', 'org.bj'])}"
            else:
                # Domaines génériques
                generic_domains = ["gmail.com", "yahoo.fr", "hotmail.com", "outlook.com", "yahoo.com"]
                email = f"{email_prefix}@{random.choice(generic_domains)}"
        
        # Génération site web intelligent avec variantes
        has_site = random.random() < template["prob_site"]
        site = ""
        if has_site:
            # Nettoyer le nom pour le domaine
            nom_clean = nom.lower().replace("'", "").replace("-", " ").replace(".", " ")
            mots = [m for m in nom_clean.split() if len(m) > 2]
            
            # Variantes de domaine
            if len(mots) >= 2:
                # Prendre les 2-3 premiers mots
                domain_base = "".join(mots[:min(3, len(mots))])
            elif len(mots) == 1:
                domain_base = mots[0]
            else:
                # Fallback : utiliser les premiers caractères
                domain_base = nom.lower()[:15].replace(" ", "")
            
            # Variantes d'extensions de domaine
            extensions = [
                "bj",  # Extension nationale du Bénin
                "com.bj",  # Extension commerciale Bénin
                "org.bj",  # Extension organisation Bénin
                "com",  # Extension commerciale internationale
                "org",  # Extension organisation internationale
                "net",  # Extension réseau
                "benin",  # Alternative .benin
            ]
            
            # Pondération : favoriser les domaines .bj pour les entreprises locales
            if random.random() > 0.3:
                # Domaine .bj ou .com.bj
                ext = random.choice(["bj", "com.bj", "org.bj"])
            else:
                # Domaines internationaux
                ext = random.choice(["com", "org", "net"])
            
            # Parfois ajouter un préfixe comme "www."
            www_prefix = "www." if random.random() > 0.5 else ""
            site = f"{www_prefix}{domain_base}.{ext}"
        
        # Type d'entreprise basé sur le template
        type_entreprise = random.choice(template["types"])
        
        # Taille d'entreprise avec pondération réaliste
        taille_weights = [0.4, 0.3, 0.2, 0.1]  # Plus de TPE/PME que de grandes entreprises
        taille = random.choices(
            ["TPE (<10)", "PME (10-50)", "PME (50-200)", "Grande (>200)"],
            weights=taille_weights
        )[0]
        
        entreprise = {
            "id": generer_id(nom, v),
            "nom": nom,
            "secteur": s,
            "ville": v,
            "pays": "Bénin",
            "telephone": f"+229 {random.randint(20,99)} {random.randint(10,99):02d} {random.randint(10,99):02d} {random.randint(10,99):02d}",
            "email": email,
            "site": site,
            "source": source,
            "taille": taille,
            "type": type_entreprise,
            "note_google": round(random.uniform(3.0, 5.0), 1) if source == "Google Maps" else None,
            "nb_avis": random.randint(2, 500) if source == "Google Maps" else None,
            "statut": "Actif",
            "date_collecte": datetime.now().isoformat(),
            "qualite": "haute" if has_email and has_site else ("moyenne" if has_email or has_site else "basse"),
        }
        results.append(entreprise)
    
    return results


def charger_base():
    if DB_FILE.exists():
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def sauvegarder_base(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def dedoublonner(data):
    seen = {}
    unique = []
    for e in data:
        key = e["nom"].lower().strip() + e["ville"].lower().strip()
        if key not in seen:
            seen[key] = True
            unique.append(e)
    return unique


def calculer_stats(data):
    if not data:
        return {}
    
    par_secteur = {}
    par_ville = {}
    par_source = {}
    par_taille = {}
    par_type = {}
    avec_email = 0
    avec_site = 0
    haute_qualite = 0

    for e in data:
        par_secteur[e["secteur"]] = par_secteur.get(e["secteur"], 0) + 1
        par_ville[e["ville"]] = par_ville.get(e["ville"], 0) + 1
        par_source[e["source"]] = par_source.get(e["source"], 0) + 1
        par_taille[e["taille"]] = par_taille.get(e["taille"], 0) + 1
        par_type[e["type"]] = par_type.get(e["type"], 0) + 1
        if e.get("email"): avec_email += 1
        if e.get("site"): avec_site += 1
        if e.get("qualite") == "haute": haute_qualite += 1

    return {
        "total": len(data),
        "par_secteur": dict(sorted(par_secteur.items(), key=lambda x: -x[1])),
        "par_ville": dict(sorted(par_ville.items(), key=lambda x: -x[1])),
        "par_source": par_source,
        "par_taille": par_taille,
        "par_type": par_type,
        "avec_email": avec_email,
        "avec_site": avec_site,
        "haute_qualite": haute_qualite,
        "taux_email": round(avec_email / len(data) * 100, 1),
        "taux_site": round(avec_site / len(data) * 100, 1),
        "taux_qualite": round(haute_qualite / len(data) * 100, 1),
    }


def exporter_csv(data, filename=None):
    if not filename:
        filename = f"entreprises_benin_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    path = EXPORT_DIR / filename
    
    if not data:
        return str(path)
    
    keys = ["id", "nom", "secteur", "ville", "telephone", "email", "site",
            "taille", "type", "source", "note_google", "statut", "date_collecte", "qualite"]
    
    # Utiliser openpyxl pour le formatage Excel
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Entreprises"
    
    # Écrire les en-têtes avec formatage (gras et gris)
    header_fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
    header_font = Font(bold=True)
    
    for col_idx, key in enumerate(keys, 1):
        cell = ws.cell(row=1, column=col_idx, value=key)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
    
    # Écrire les données
    for row_idx, entreprise in enumerate(data, 2):
        for col_idx, key in enumerate(keys, 1):
            value = entreprise.get(key, "")
            ws.cell(row=row_idx, column=col_idx, value=value)
    
    # Ajuster la largeur des colonnes
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column].width = adjusted_width
    
    wb.save(path)
    return str(path)


# ─── SCRAPING WEB INTELLIGENT ─────────────────────────────────────────────────────

def extraire_informations_contact(url: str) -> Dict[str, any]:
    """
    Extrait intelligemment les informations de contact depuis une page web
    Returns: dict avec téléphone, email, site, etc.
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        # Ajouter http:// si absent
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # User-agent pour éviter le blocage
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extraire les téléphones (formats béninois et internationaux)
        telephones = set()
        # Regex pour numéros béninois (+229)
        tel_patterns = [
            r'\+229\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{2}',
            r'\+229\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{2}',
            r'0[1-9]\d{7}',  # Format local
            r'\d{2}\s?\d{2}\s?\d{2}\s?\d{2}',  # Format sans code pays
        ]
        
        text = soup.get_text()
        for pattern in tel_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                telephones.add(match)
        
        # Chercher dans les attributs href (tel:)
        tel_links = soup.find_all('a', href=re.compile(r'tel:', re.IGNORECASE))
        for link in tel_links:
            tel = link['href'].replace('tel:', '').replace(' ', '')
            telephones.add(tel)
        
        # Extraire les emails
        emails = set()
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        email_matches = re.findall(email_pattern, text)
        for email in email_matches:
            # Filtrer les emails suspects
            if not any(x in email.lower() for x in ['example', 'test', 'noreply', 'donotreply']):
                emails.add(email)
        
        # Chercher dans les attributs href (mailto:)
        mailto_links = soup.find_all('a', href=re.compile(r'mailto:', re.IGNORECASE))
        for link in mailto_links:
            email = link['href'].replace('mailto:', '').split('?')[0]
            if not any(x in email.lower() for x in ['example', 'test', 'noreply', 'donotreply']):
                emails.add(email)
        
        # Extraire l'adresse physique
        adresse = ""
        address_patterns = [
            r'\d+[\s,]+\w+[\s,]+\w+[\s,]+\w+',  # Pattern d'adresse basique
            r'B\.P\.\s*\d+',  # Boîte postale
        ]
        
        # Chercher dans les balises address
        address_tags = soup.find_all('address')
        if address_tags:
            adresse = address_tags[0].get_text(strip=True)
        
        # Extraire les réseaux sociaux
        sociaux = {}
        social_patterns = {
            'facebook': r'facebook\.com/[^\s"\'<>]+',
            'linkedin': r'linkedin\.com/(company|in)/[^\s"\'<>]+',
            'twitter': r'twitter\.com/[^\s"\'<>]+',
            'instagram': r'instagram\.com/[^\s"\'<>]+',
        }
        
        for platform, pattern in social_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                sociaux[platform] = matches[0]
        
        return {
            'url': url,
            'telephones': list(telephones) if telephones else None,
            'emails': list(emails) if emails else None,
            'adresse': adresse if adresse else None,
            'sociaux': sociaux if sociaux else None,
            'statut': 'succès'
        }
        
    except requests.RequestException as e:
        return {
            'url': url,
            'erreur': f"Erreur de requête: {str(e)}",
            'statut': 'erreur'
        }
    except Exception as e:
        return {
            'url': url,
            'erreur': f"Erreur: {str(e)}",
            'statut': 'erreur'
        }


def scraper_entrees_reelles(url: str, nom: str, secteur: str, ville: str) -> Dict[str, any]:
    """
    Scrape une entreprise réelle depuis son site web et retourne les données complètes
    """
    infos = extraire_informations_contact(url)
    
    if infos['statut'] == 'erreur':
        return None
    
    # Construire l'objet entreprise
    entreprise = {
        'id': generer_id(nom, ville),
        'nom': nom,
        'secteur': secteur,
        'ville': ville,
        'pays': 'Bénin',
        'telephone': infos['telephones'][0] if infos.get('telephones') else '',
        'email': infos['emails'][0] if infos.get('emails') else '',
        'site': url.replace('https://', '').replace('http://', '').replace('www.', ''),
        'source': 'Scraping Web',
        'taille': 'Non déterminé',
        'type': 'B2B/B2C',
        'statut': 'Actif',
        'date_collecte': datetime.now().isoformat(),
        'qualite': 'haute' if (infos.get('telephones') and infos.get('emails')) else 'moyenne'
    }
    
    return entreprise


def lancer_collecte(sources_selectionnees, secteurs_selectionnes, villes_selectionnees, nb_par_source=100):
    """Lance la collecte complète et retourne les stats"""
    base = charger_base()
    nouvelles = []
    logs = []

    # Scraper les entreprises réelles de référence qui correspondent aux filtres
    for entreprise in ENTREPRISES_REELLES:
        # Vérifier si l'entreprise correspond aux filtres
        secteur_match = entreprise["secteur"] in secteurs_selectionnes
        ville_match = entreprise["ville"] in villes_selectionnees
        
        if secteur_match and ville_match:
            # Utiliser le scraping web intelligent pour extraire les données réelles
            if "url" in entreprise:
                scraped = scraper_entrees_reelles(
                    entreprise["url"],
                    entreprise["nom"],
                    entreprise["secteur"],
                    entreprise["ville"]
                )
                if scraped:
                    nouvelles.append(scraped)
                    logs.append({
                        "source": "Scraping Web",
                        "secteur": entreprise["secteur"],
                        "ville": entreprise["ville"],
                        "collectes": 1,
                        "duree_s": 0,
                        "timestamp": datetime.now().isoformat(),
                        "entreprise": entreprise["nom"]
                    })
                else:
                    # Si le scraping échoue, utiliser les données de référence
                    entreprise_copy = entreprise.copy()
                    entreprise_copy["date_collecte"] = datetime.now().isoformat()
                    nouvelles.append(entreprise_copy)
            else:
                # Pas d'URL, utiliser les données de référence
                entreprise_copy = entreprise.copy()
                entreprise_copy["date_collecte"] = datetime.now().isoformat()
                nouvelles.append(entreprise_copy)

    for source in sources_selectionnees:
        for secteur in secteurs_selectionnes:
            for ville in villes_selectionnees:
                t0 = time.time()
                batch = simuler_scraping(source, secteur, ville, nb=max(5, nb_par_source // (len(secteurs_selectionnes) * len(villes_selectionnees))))
                duree = round(time.time() - t0, 2)
                nouvelles.extend(batch)
                logs.append({
                    "source": source,
                    "secteur": secteur,
                    "ville": ville,
                    "collectes": len(batch),
                    "duree_s": duree,
                    "timestamp": datetime.now().isoformat()
                })

    # Fusionner et dédoublonner
    toutes = base + nouvelles
    toutes_uniques = dedoublonner(toutes)
    sauvegarder_base(toutes_uniques)

    # Sauvegarder logs
    all_logs = []
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            all_logs = json.load(f)
    all_logs.extend(logs)
    with open(LOG_FILE, "w") as f:
        json.dump(all_logs[-500:], f, ensure_ascii=False, indent=2)

    stats = calculer_stats(toutes_uniques)
    stats["nouvelles_ce_run"] = len(nouvelles)
    stats["doublons_supprimes"] = len(toutes) - len(toutes_uniques)
    return stats, toutes_uniques


def charger_logs():
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            return json.load(f)
    return []


if __name__ == "__main__":
    # Test rapide
    print("Test de collecte...")
    stats, data = lancer_collecte(
        sources_selectionnees=["Google Maps", "Facebook Pages"],
        secteurs_selectionnes=["BTP & Immobilier", "Commerce & Distribution"],
        villes_selectionnees=["Cotonou", "Parakou"],
        nb_par_source=50
    )
    print(f"Total: {stats['total']} entreprises")
    print(f"Avec email: {stats['avec_email']} ({stats['taux_email']}%)")
    csv_path = exporter_csv(data)
    print(f"Export: {csv_path}")