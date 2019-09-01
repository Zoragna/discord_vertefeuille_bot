from Utils.Persistence_Utils import *

import datetime


class Event(Element):
    rows = [("createdBy",str), ("updatedBy",str), ("name",str), ("guildId",int), ("begin",int), ("end",int),
            ("description",str)]

    def __init__(self, creator, updator, name, guild_id, begin, end, description):
        self.created_by = creator
        self.updated_by = updator
        self.name = name
        self.guild_id = guild_id
        self.begin = begin
        self.end = end
        self.description = description

    def __repr__(self):
        representation = str(datetime.datetime.fromtimestamp(self.begin))
        representation += "=>" + str(datetime.datetime.fromtimestamp(self.end))
        representation += " : " + self.description
        return representation

    @staticmethod
    def process_creation(words):
        dic = {}
        for word in words:
            splits = word.split("/")
            if len(splits) == 3:
                date = int(datetime.datetime(int(splits[2]), int(splits[1]), int(splits[0])).timestamp())
                if "begin" in dic:
                    if date < dic["begin"]:
                        dic["end"] = dic["begin"]
                        dic["begin"] = date
                    else:
                        dic["end"] = date
                else:
                    dic["begin"] = date
            else:
                if "name" in dic:
                    if len(word) < len(dic["name"]):
                        dic["description"] = dic["name"]
                        dic["name"] = word
                    else:
                        dic["description"] = word
                else:
                    dic["name"] = word
        return dic

    @classmethod
    def from_dict(cls, dic):
        if Event.validate(dic, Event.rows):
            return cls(dic["createdBy"], dic["updatedBy"], dic["name"], dic["guildId"], dic["begin"], dic["end"],
                       dic["description"])
        else:
            raise InitializationException()


class PersistentCalendars(Persistent):

    def init_database(self):
        self.write('''CREATE TABLE IF NOT EXISTS Calendar (
        CreatedBy text NOT NULL,
        UpdatedBy text NOT NULL,
        "Name" varchar(100) NOT NULL,
        GuildId bigint NOT NULL,
        "Begin" bigint NOT NULL,
        "End" bigint NOT NULL,
        Description text NOT NULL,
        PRIMARY KEY("Name", "Begin", "End"));''', ())

    def add_event(self, event: Event):
        self.write(
            '''INSERT INTO Calendar (CreatedBy, UpdatedBy, "Name", GuildId, "Begin", "End", Description) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)''',
            (event.created_by, event.updated_by, event.name, event.guild_id, event.begin, event.end, event.description))

    def remove_event(self, name):
        self.write('''DELETE FROM Calendar WHERE "Name"=%s''', name)

    def update_event(self, event: Event):
        self.write('''UPDATE Calendar 
        SET CreatedBy=%s, UpdatedBy=%s, "Name"=%s, "Begin"=%s, "End"=%s, Description=%s WHERE "Name"=%s"''',
                   (event.created_by, event.updated_by, event.name, event.begin, event.end, event.description,
                    event.name))

    def get_events(self, guild_id=None, **kwargs):
        query = "SELECT * FROM Calendar "
        objects = ()
        if guild_id is not None:
            query += ''' WHERE GuildId=%s'''
            objects += (guild_id, )
            if len(kwargs) > 0:
                query += " AND"
        elif len(kwargs) > 0:
            query += " WHERE"
        if "after" in kwargs and "before" in kwargs:
            query += ''' "Begin">=%s AND "Begin"<=%s'''
            objects += (kwargs["after"], kwargs["before"])
        elif "after" in kwargs:
            query += ''' "Begin">=%s'''
            objects += (kwargs["after"], )
        elif "before" in kwargs:
            query += ''' "Begin"<=%s'''
            objects += (kwargs["before"],)
        query += ''' ORDER BY "Begin" ASC'''
        results = self.read(query, objects)
        events = []
        for result in results:
            events.append(Event(result[0], result[1], result[2], result[3], result[4], result[5], result[6]))
        return events
