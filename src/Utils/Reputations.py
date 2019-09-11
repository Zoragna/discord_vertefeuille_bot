from Utils.Persistence_Utils import *
from typing import List

import sys

# TODO this should be scraped (updated 11.09.19)
factions = ["Armée de l'ouest", "Armée de l'ouest - Armes",
            "Armée de l'ouest - Armures", "Armée de l'ouest - Provisions",
            "Cavaliers de Rohan", "Clan du Ciel rouge", "Conquête de Gorgoroth",
            "Conseil du Nord", "Défenseurs de Minas Tirith", "Dol Amroth",
            "Elfes de Felegoth", "Elfes de Fondcombe", "Ennemi de Fushaum Bal",
            "Ents de la Forêt de Fangorn", "Galadrhim", "Gardes de la Garnison de fer",
            "Hommes de Bree", "Hommes de Dale", "Hommes de Dor-en-Ernil",
            "Hommes de la vallée de l'Entalluve", "Hommes dse Norcrofts",
            "Hommes des Sutcrofts", "Hommes du Lebennin", "Hommes du Pays de Dun",
            "Hommes du Plateau", "Hommes du Val de Ringlò", "La Compagnie Grise",
            "La Confrérie de la cervoise", "La Ligue des tavernes", "La Société des Matthoms",
            "Les Algraig, Hommes d'Enedwaith", "Les Cavaliers de Stangarde", "Les Cavaliers de Théodred",
            "Les Églain", "Les Eldgangs", "Les Éorlingas", "Les Gardiens d'Annùminas", "Les Helmingas",
            "Héros de la Gorge du Limeclair", "Lossoth du Forochel", "Malledhrim", "Mineurs de la Garnison de fer",
            "Nains d'Erebor", "Palais de Thorin", "Pelargir", "Peuple des Landes Farouches", "Rôdeurs d'Esteldín",
            "Rôdeurs de l'Ithilien", "Survivants des Landes Farouches"]
guilds = ["bijoutiers", "cuisiniers", "érudits", "fabricants d'armes",
          "ferroniers", "menuisiers", "tailleurs"]
allegiances = ["Le Royaume du Gondor", "La Cour de Lothlòrien",
               "Le Peuple de Durin", "Les Hobbits de la Compagnie"]


class Reputation(Element):
    accepted_factions = [faction.replace(' ', '_') for faction in factions]
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
    rows = [("createdBy", str), ("updatedBy", str), ("guildId", int), ("name", str), ("level", str),
            ("faction", str)]

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


class Allegiance(Element):
    accepted_allegiances = [allegiance.replace(' ', '_') for allegiance in allegiances]
    rows = [("createdBy", str), ("updatedBy", str), ("guildId", int), ("name", str), ("level", int),
            ("allegiance", str)]

    def __init__(self, creator, updator, name, allegiance, level, guild_id):
        self.created_by = creator
        self.updated_by = updator
        self.guild_id = guild_id
        self.name = name
        self.level = level
        self.allegiance = allegiance

    def __repr__(self):
        representation = self.name + ", niv."
        representation += self.level.capitalize() + " auprès de "
        representation += self.allegiance.replace("_", " ")
        return representation

    @staticmethod
    def process_creation(words):
        dic = {}
        for word in words:
            if word in Allegiance.accepted_allegiances:
                dic["allegiance"] = word
            else:
                try:
                    test = int(word)
                    dic["level"] = test
                except ValueError:
                    dic["name"] = word
        return dic

    @classmethod
    def from_dict(cls, dic):
        if Reputation.validate(dic, Reputation.rows):
            return cls(dic["createdBy"], dic["updatedBy"], dic["name"], dic["level"], dic["allegiance"], dic["guildId"])
        else:
            raise InitializationException()


class Craftsmanship(Element):
    accepted_guilds = [guild.replace(' ', '_') for guild in guilds]
    accepted_craftsmanship = ["Initié", "Apprenti", "Compagnon", "Expert", "Artisan",
                              "Maître", "Maître d'Estemnet", "Maître d'Ouestemnet"]
    rows = [("createdBy", str), ("updatedBy", str), ("guildId", int), ("name", str), ("level", str),
            ("guild", str)]

    def __init__(self, creator, updator, name, guild, level, guild_id):
        self.created_by = creator
        self.updated_by = updator
        self.guild_id = guild_id
        self.name = name
        self.level = level
        self.guild = guild

    def __repr__(self):
        representation = self.name + ", "
        representation += self.level.capitalize() + " auprès de "
        representation += self.guild.replace("_", " ")
        return representation

    @staticmethod
    def process_creation(words):
        dic = {}
        for word in words:
            if word in Craftsmanship.accepted_guilds:
                dic["guild"] = word
            elif word in Craftsmanship.accepted_craftsmanship:
                dic["level"] = word
            else:
                dic["name"] = word
        return dic

    @classmethod
    def from_dict(cls, dic):
        if Reputation.validate(dic, Reputation.rows):
            return cls(dic["createdBy"], dic["updatedBy"], dic["name"], dic["level"], dic["guild"], dic["guildId"])
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

    # TODO this & the associated commands
    def add_allegiance(self, allegiance):
        pass

    def remove_allegiance(self, name, allegiance=None):
        pass

    def update_allegiance(self, allegiance):
        pass

    def get_allegiances(self, guild_id=None):
        pass

    def add_craftsmanship(self, craftsmanship):
        pass

    def remove_craftsmanship(self, name, craftsmanship=None):
        pass

    def update_craftsmanship(self, craftsmanship):
        pass

    def get_craftsmanship_s(self, guild_id=None):
        pass

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
            query_key = None
            if key == "name":
                query_key = '''"Name"'''
            elif key == "faction":
                query_key = "faction"
            elif key == "level":
                query_key = "level"
            if query_key is not None:
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
