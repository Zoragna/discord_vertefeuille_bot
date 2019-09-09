from Utils.Persistence_Utils import *
from typing import List


class Character(Element):
    rows = [("createdBy",str), ("updatedBy",str), ("guildId",int), ("class",str), ("level",int), ("mainTrait",str),
            ("name",str)]

    accepted_classes = ["cambrioleur", "capitaine", "champion", "chasseur", "gardien", "gardien_des_runes",
                        "maître_du_savoir", "ménestrel", "sentinelle", "béornide"]
    accepted_colors = ["bleu", "jaune", "rouge"]

    def __init__(self, creator, updator, guild_id, cls, level, main_trait, name):
        self.created_by = creator
        self.updated_by = updator
        self.guild_id = guild_id
        self.class_ = cls
        self.level = level
        self.main_trait = main_trait
        self.name = name

    def __repr__(self):
        representation = self.name + " " + self.class_ + " " + self.main_trait + " niv." + str(self.level)
        return representation

    @staticmethod
    def process_creation(words):
        dic = {}
        for word in words:
            if word in Character.accepted_classes:
                dic["class"] = word
            elif word in Character.accepted_colors:
                dic["mainTrait"] = word
            else:
                try:
                    test = int(word)
                    dic["level"] = test
                except ValueError:
                    dic["name"] = word
        return dic

    @classmethod
    def from_dict(cls, dic):
        if Character.validate(dic, Character.rows):
            return cls(dic["createdBy"], dic["updatedBy"], dic["guildId"], dic["class"], dic["level"], dic["mainTrait"], dic["name"])
        else:
            raise InitializationException()


class PersistentCharacters(Persistent):

    def init_database(self):
        self.write('''CREATE TABLE IF NOT EXISTS Characters (
        CreatedBy text NOT NULL,
        UpdatedBy text NOT NULL,
        GuildId bigint NOT NULL,
        Class text NOT NULL,
        "Level" SMALLINT,
        MainTrait text NOT NULL,
        "Name" varchar(100),
        PRIMARY KEY ("Name"));''', ())

    def add_character(self, chara):
        self.write('''INSERT INTO Characters (CreatedBy, UpdatedBy, GuildId, Class, "Level", MainTrait, "Name") 
                   VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                   (chara.created_by, chara.updated_by, chara.guild_id, chara.class_, chara.level, chara.main_trait, chara.name))

    def update_character(self, chara):
        self.write('''UPDATE Characters 
        SET UpdatedBy=%s, Class=%s, "Level"=%s, MainTrait=%s
        WHERE "Name"=%s''',
                   (chara.updated_by, chara.class_, chara.level, chara.main_trait,
                    chara.name))

    def get_characters(self, guild_id=None):
        if guild_id is None :
            results = self.read('''SELECT * FROM Characters''',())
        else :
            results = self.read('''SELECT * FROM Characters WHERE GuildId=%s''', guild_id)
        characters = []
        for result in results :
            characters.append(Character(result[0], result[1], result[2], result[3], result[4], result[5], result[6]))
        return characters

    def remove_character(self, name):
        self.write('''DELETE FROM Characters WHERE "Name"=%s''', name)

    @staticmethod
    def process_query(words):
        dic = {}
        for word in words:
            if word in Character.accepted_classes:
                if "class" not in dic:
                    dic["class"] = []
                dic["class"].append(word)
            elif word in Character.accepted_colors:
                if "trait" not in dic:
                    dic["trait"] = []
                dic["trait"].append(word)
            else:
                splits = word.split('-')
                if len(splits) == 2:
                    if len(splits[0]) > 0:
                        dic["min_level"] = int(splits[0])
                    if len(splits[1]) > 0:
                        dic["max_level"] = int(splits[1])
                else:
                    dic["name"] = word
        return dic

    def search_characters(self, request_dict):
        query = "SELECT * FROM Characters"
        objects = ()
        if len(request_dict) > 0:
            query += " WHERE"
            first = True
            for key, value in request_dict.items():
                if first:
                    first = False
                else:
                    query += " AND"
                if key == "min_level":
                    query += ''' "Level" >= %s'''
                    objects += (value,)
                elif key == "max_level":
                    query += ''' "Level" <= %s'''
                    objects += (value,)
                elif key == "name":
                    query += ''' "Name" = %s'''
                    objects += (value,)
                elif key == "class":
                    if isinstance(value, List):
                        query += " "+Element.list_query_list(value, "Class")
                        for val in value:
                            objects += (val,)
                    else:
                        query += ''' Class=%s'''
                        objects += (value,)
                elif key == "trait":
                    if isinstance(value, List):
                        query += " "+Element.list_query_list(value, "MainTrait")
                        for val in value:
                            objects += (val,)
                    else:
                        query += ''' MainTrait=%s'''
                        objects += (value,)
                elif key == "guildId":
                    query += " GuildId=%s"
                    objects += (value,)
        results = self.read(query, objects)
        characters = []
        for result in results:
            characters.append(Character(result[0], result[1], result[2], result[3], result[4], result[5], result[6]))
        return characters

    def get_creator(self, name):
        results = self.read('''SELECT * FROM Characters WHERE "Name"=%s''', name)
        if len(results) == 0:
            return ""
        return results[0][0]
