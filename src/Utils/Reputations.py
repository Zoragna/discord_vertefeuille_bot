from Utils.Persistence_Utils import *
from typing import List

import sys


class Reputation(Element):
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
        "frère": {"min": 85000, "max": 130000},
        "respecté": {"min": 130000, "max": 190000},
        "honoré": {"min": 190000, "max": 280000},
        "acclamé": {"min": 280000, "max": sys.maxsize},
    }

    rows = [("createdBy", str), ("updatedBy", str), ("guildId", int), ("name", str), ("level", str), ("faction", str)]

    def __init__(self, creator, updator, name, faction, level, guild_id):
        self.created_by = creator
        self.updated_by = updator
        self.guild_id = guild_id
        self.name = name
        self.level = level
        self.faction = faction

    def __repr__(self):
        representation = self.name + ", "
        representation += self.level.capitalize() + " auprès de "
        representation += self.faction.replace("_", " ")
        return representation

    @staticmethod
    def process_creation(words):
        dic = {}
        for word in words:
            if word in Reputation.accepted_factions:
                dic["faction"] = word
            elif word in Reputation.accepted_levels:
                dic["level"] = word
            else:
                dic["name"] = word
        return dic

    @classmethod
    def from_dict(cls, dic):
        if Reputation.validate(dic, Reputation.rows):
            return cls(dic["createdBy"], dic["updatedBy"], dic["name"], dic["level"], dic["faction"], dic["guildId"])
        else:
            raise InitializationException()


class PersistentReputations(Persistent):

    def add_reputation(self, reputation):
        self.write('''INSERT INTO Reputations (CreatedBy, UpdatedBy, GuildId, "Name", Faction, Level) 
        VALUES (%s, %s, %s, %s, %s, %s)''',
                   (reputation.created_by, reputation.updated_by, reputation.guild_id,
                    reputation.name, reputation.faction, reputation.level))

    def remove_reputation(self, name, faction=None):
        if faction is not None:
            self.write('''DELETE FROM Reputations WHERE "Name"=%s AND Faction=%s''', (name, faction))
        else:
            self.write('''DELETE FROM Reputations WHERE "Name"=%s''', name)

    def update_reputation(self, reputation):
        self.write('''UPDATE Reputations 
                       SET UpdatedBy=%s, Level=%s
                       WHERE "Name"=%s ANd Faction=%s''',
                   (reputation.updated_by, reputation.level,
                    reputation.name, reputation.faction))

    def get_reputations(self, guild_id=None):
        if guild_id is None:
            results = self.read('''SELECT * FROM Reputations''', ())
        else:
            results = self.read('''SELECT * FROM Reputations WHERE GuildId=%s''', guild_id)
        reputations = []
        for result in results:
            reputations.append(Reputation(result[0], result[1], result[2], result[3], result[4], result[5]))
        return reputations

    @staticmethod
    def process_reputation_query(words):
        dic = {}
        for word in words:
            if word in Reputation.accepted_levels:
                if "level" not in dic:
                    dic["level"] = []
                dic["level"].append(word)
            elif word in Reputation.accepted_factions:
                if "faction" not in dic:
                    dic["faction"] = []
                dic["faction"].append(word)
            else:
                if "name" not in dic:
                    dic["name"] = []
                dic["name"].append(word)
        return dic

    def search_reputations(self, request_dict):
        query = "SELECT * FROM Reputations"
        objects = ()
        first = True
        for key, value in request_dict.iteritems():
            if first:
                query += " WHERE"
                first = False
            else:
                query += " AND"
            if key == "name":
                query_key = '''"Name"'''
            elif key == "faction":
                query_key = "faction"
            elif key == "level":
                query_key = "level"
            if isinstance(value, List):
                query += Reputation.list_query_list(value, query_key)
                for val in value:
                    objects += (val,)
            else:
                query += query_key + "=%s"
                objects += (value,)
        results = self.read(query, objects)
        reputations = []
        for result in results:
            reputations.append(Reputation(result[0], result[1], result[2], result[3], result[4], result[5]))
        return reputations
