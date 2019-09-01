from Utils.Persistence_Utils import *

import datetime
import discord
import asyncio
import traceback
from apscheduler.job import Job


class Event(Element):
    rows = [("createdBy", str), ("updatedBy", str), ("name", str), ("guildId", int), ("channelId", int),
            ("begin", int), ("end", int), ("description", str)]

    def __init__(self, creator, updator, name, guild_id, channel_id, begin, end, description):
        self.created_by = creator
        self.updated_by = updator
        self.name = name
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.begin = begin
        self.end = end
        self.description = description

    def __repr__(self, show_channel=False):
        representation = str(datetime.datetime.fromtimestamp(self.begin)).split(' ')[0]
        representation += "=>" + str(datetime.datetime.fromtimestamp(self.end)).split(' ')[0]
        representation += " : " + self.description
        if show_channel:
            representation += "(<#" + str(self.channel_id) + ">)"
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
                if len(word) > 3 and word[:2] == "<#" and word[-1] == ">":
                    pass
                elif "name" in dic:
                    word = word.replace("_", " ")
                    if len(word) < len(dic["name"]):
                        dic["description"] = dic["name"]
                        dic["name"] = word
                    else:
                        dic["description"] = word
                else:
                    dic["name"] = word.replace("_", " ")
        return dic

    @classmethod
    def from_dict(cls, dic):
        if Event.validate(dic, Event.rows):
            return cls(dic["createdBy"], dic["updatedBy"], dic["name"], dic["guildId"], dic["channelId"], dic["begin"],
                       dic["end"],
                       dic["description"])
        else:
            raise InitializationException()

    @staticmethod
    def recall(client: discord.Client, event):
        channel = client.get_channel(event.channel_id)
        coroutine = channel.send(str(event))
        future = asyncio.run_coroutine_threadsafe(coroutine, client.loop)
        future.result()


class PersistentCalendars(Persistent):

    def __init__(self, connection, scheduler, client: discord.Client):
        super().__init__(connection)
        self.scheduler = scheduler
        self.client = client

    def init_database(self):
        self.write('''CREATE TABLE IF NOT EXISTS Calendar (
        CreatedBy text NOT NULL,
        UpdatedBy text NOT NULL,
        "Name" varchar(100) NOT NULL,
        GuildId bigint NOT NULL,
        ChannelId bigint NOT NULL,
        "Begin" bigint NOT NULL,
        "End" bigint NOT NULL,
        Description text NOT NULL,
        PRIMARY KEY("Name", "Begin"));''', ())

    def add_event(self, event: Event):
        self.write(
            '''INSERT INTO Calendar (CreatedBy, UpdatedBy, "Name", GuildId, ChannelId, "Begin", "End", Description) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
            (event.created_by, event.updated_by, event.name, event.guild_id, event.channel_id, event.begin, event.end,
             event.description))
        begin_date = datetime.datetime.fromtimestamp(event.begin)
        trigger_date = begin_date - datetime.timedelta(hours=12)
        _id = event.name + str(event.begin)
        try :
            job = self.scheduler.add_job(Event.recall, next_run_time=str(trigger_date),
                                         trigger='date', id=_id, replace_existing=True,
                                         args=[self.client, event])
            print(job)
            return True
        except Exception as e :
            print("Job adding exc. ===>"+str(e))
            print(traceback.format_exc())
            return False

    def remove_event(self, name, begin):
        self.write('''DELETE FROM Calendar WHERE "Name"=%s AND "Begin"=%s''', (name, begin))
        _id = name + str(begin)
        self.scheduler.remove_job(_id)

    def update_event(self, event: Event):
        self.write('''UPDATE Calendar 
        SET UpdatedBy=%s, "Name"=%s, "End"=%s, Description=%s, ChannelId=%s
        WHERE "Name"=%s AND "Begin"=%s''',
                   (event.updated_by, event.name, event.end, event.description, event.channel_id,
                    event.name, event.begin))
        trigger_date = datetime.datetime.today() + datetime.timedelta(seconds=30)
        _id = event.name + str(event.begin)
        self.scheduler.update_job(Event.recall, args=[self.client, event], next_run_time=trigger_date)

    def get_events(self, guild_id=None, **kwargs):
        query = "SELECT * FROM Calendar "
        objects = ()
        if guild_id is not None:
            query += ''' WHERE GuildId=%s'''
            objects += (guild_id,)
            if len(kwargs) > 0:
                query += " AND"
        elif len(kwargs) > 0:
            query += " WHERE"
        if "after" in kwargs and "before" in kwargs:
            query += ''' "Begin">=%s AND "Begin"<=%s'''
            objects += (kwargs["after"], kwargs["before"])
        elif "after" in kwargs:
            query += ''' "Begin">=%s'''
            objects += (kwargs["after"],)
        elif "before" in kwargs:
            query += ''' "Begin"<=%s'''
            objects += (kwargs["before"],)
        query += ''' ORDER BY "Begin" ASC'''
        results = self.read(query, objects)
        events = []
        for result in results:
            events.append(Event(result[0], result[1], result[2], result[3], result[4], result[5], result[6], result[7]))
        return events
