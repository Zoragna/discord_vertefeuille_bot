from Utils.Persistence_Utils import *

import datetime
import discord
import asyncio
import traceback


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


class Recall(Element):
    rows = [("name", str), ("begin", int), ("delay", int)]

    def __init__(self, name, begin, delay):
        self.name = name
        self.begin = begin
        self.delay = delay

    def __repr__(self, show_channel=False):
        recall_date = self.begin + self.delay
        return str(datetime.datetime.fromtimestamp(recall_date))

    @staticmethod
    def process_creation(words):
        dic = {}
        for word in words:
            splits = word.split("/")
            if len(splits) == 3:
                date = datetime.datetime(int(splits[2]), int(splits[1]), int(splits[0])).timestamp()
                dic["begin"] = date
            else:
                splits = word.split(':')
                if len(splits) == 3:
                    dic["delay"] = datetime.timedelta(hours=int(splits[0][1:]), minutes=int(splits[1]),
                                                      seconds=int(splits[2])).total_seconds()
                    if splits[0][0] == "-":
                        dic["delay"] = - dic["delay"]

                else:
                    dic["name"] = word.replace("_", " ")
        return dic

    @classmethod
    def from_dict(cls, dic):
        if Recall.validate(dic, Recall.rows):
            return cls(dic["name"], dic["begin"], dic["delay"])
        else:
            raise InitializationException()


class PersistentCalendars(Persistent):

    def __init__(self, connection, scheduler, client: discord.Client):
        super().__init__(connection)
        self.scheduler = scheduler
        self.client = client

    def add_event(self, event: Event):
        self.write(
            '''INSERT INTO Calendar (CreatedBy, UpdatedBy, "Name", GuildId, ChannelId, "Begin", "End", Description) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
            (event.created_by, event.updated_by, event.name, event.guild_id, event.channel_id, event.begin, event.end,
             event.description))

    def remove_event(self, name, begin):
        self.write('''DELETE FROM Calendar WHERE "Name"=%s AND "Begin"=%s''', (name, begin))
        _id = name + str(begin)
        self.remove_recall(name, begin)

    def update_event(self, event: Event):
        self.write('''UPDATE Calendar 
        SET UpdatedBy=%s, "Name"=%s, "End"=%s, Description=%s, ChannelId=%s
        WHERE "Name"=%s AND "Begin"=%s''',
                   (event.updated_by, event.name, event.end, event.description, event.channel_id,
                    event.name, event.begin))

    def get_event(self, name, begin):
        results = self.read('''SELECT * FROM Calendar WHERE "Name"=%s AND "Begin"=%s''', (name, begin))
        if len(results) == 1:
            result = results[0]
            return Event(result[0], result[1], result[2], result[3], result[4], result[5], result[6], result[7])
        else:
            return None

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

    def add_recall(self, recall):
        event = self.get_event(recall.name, recall.begin)
        _id = recall.name + "#" + str(recall.begin) + "@" + str(recall.delay)
        trigger_date = datetime.datetime.fromtimestamp(recall.begin + recall.delay)
        self.scheduler.add_job(Event.recall, next_run_time=str(trigger_date),
                               trigger='date', id=_id, replace_existing=True,
                               args=[self.client, event])

    def remove_recall(self, name, begin, delay=None):
        if delay is None:
            jobs = self.scheduler.get_jobs()
            begin_pattern = name + "#" + str(begin)
            delays = [job.id.replace(begin_pattern + "@", '') for job in jobs if job.id.startswith(begin_pattern)]
            for delay in delays:
                _id = begin_pattern + "@" + delay
                self.scheduler.remove_job(id=_id)
        else:
            _id = name + "#" + str(begin) + "@" + str(delay)
            self.scheduler.remove_job(id=_id)

    def get_recalls(self, event_name=None, event_begin=None, guild_id=None, **kwargs):
        if guild_id is None:
            events = self.get_events(**kwargs)
        else:
            events = self.get_events(guild_id, **kwargs)
        beginnings = set([event.name + str(event.begin) for event in events])
        recalls = []
        for job in self.scheduler.get_jobs():
            if job.id.split('@')[0] in beginnings:
                name = job.id.split('#')[0]
                begin = int(job.id.split('#')[1].split('@')[0])
                delay = int(job.id.split('@')[1])
                if event_name is None and event_begin is None:
                    recalls.append(Recall(name, begin, delay))
                elif event_name == name and event_begin == begin:
                    recalls.append(Recall(name, begin, delay))
        return recalls
