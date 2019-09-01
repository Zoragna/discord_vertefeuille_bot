from Utils.Persistence_Utils import *
import sys


class PersistentReputations(Persistent):
    accepted_tiers = ["apprenti", "compagnon", "expert", "artisan", "maître", "suprême", "rhovanion", "estemnet",
                      "ouestemnet", "anòrien"]
    accepted_factions = ["Hall_de_Thorin", "La_Société_Matthom", "Les_hommes_de_Bree", "La_ligue_de_la_Taverne",
                         "L'association_de_la_bière", "La_ligue_des_chasseurs_de poulets_en_Eriador", "Les_Eglains",
                         "Les_Rôdeurs_d'Esteldìn", "Les_Gardiens_d'Annùminas", "Les_Elfes_de_Fondcombe",
                         "Le_Conseil_du_Nord", "Lossoth_de_Forochel", "Le_Vieux'groupe", "Galadhrim",
                         "Les_Gardes_de_la_Garnison_de_Fer", "Les_Mineurs_de_la_Garnison_de_Fer",
                         "Algraig,_hommes_de_l'Enedwaith", "La_Compagnie_grise",
                         "(((Il y a beaucoup de réputations dans ce jeu, je crois qu'il manque tout à partir de ~Isengard)))"]
    accepted_levels = {
        "ennemi": {"min": -20000, "max": -10000},
        "étranger": {"min": -10000, "max": 0},
        "neutre": {"min": 0, "max": 10000},
        "connaissance": {"min": 10000, "max": 30000},
        "ami": {"min": 30000, "max": 55000},
        "allié": {"min": 55000, "max": 85000},
        "aparenté": {"min": 85000, "max": 130000},
        "respecté": {"min": 130000, "max": 190000},
        "honoré": {"min": 190000, "max": 280000},
        "célébré": {"min": 280000, "max": sys.maxsize},
    }
    Reputations_rows = ["createdBy", "updatedBy", "name", "level", "faction"]

    def init_database(self):
        self.write('''CREATE TABLE IF NOT EXISTS Reputations (
        CreatedBy text NOT NULL,
        UpdatedBy text NOT NULL,
        "Name" varchar(100),
        Faction varchar(100),
        Level text,
        PRIMARY KEY("Name", Faction));''', ())

    def addCharacter(self, character):
        pass

    def updateCharacter(self, character):
        pass

    def removeCharacter(self, name):
        pass

    def searchCharacters(self, name=None, min_level=None, max_level=None, profession=None):
        pass
