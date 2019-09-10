from Utils.Persistence_Utils import *
from typing import List


class Job(Element):
    request_rows = [("createdBy", str), ("updatedBy", str), ("guildId", int), ("job", str), ("name", str)]
    response_rows = [("createdBy", str), ("updatedBy", str), ("guildId", int), ("job", str), ("name", str), ("id", int)]

    accepted_jobs = ["bijoutier", "cuisinier", "érudit", "fabricants_d'armes", "fermier", "ferronier", "forestier",
                     "prosepcteur", "tailleur"]

    def __init__(self, creator, updator, guild_id, job, name, id_=-1):
        self.created_by = creator
        self.updated_by = updator
        self.guild_id = guild_id
        self.job = job
        self.name = name
        self.id_ = id_

    def __repr__(self):
        representation = self.name + " " + self.job
        return representation

    @staticmethod
    def process_creation(words):
        dic = {}
        for word in words:
            if word in Job.accepted_jobs:
                dic["job"] = word
            else:
                dic["name"] = word
        return dic

    @classmethod
    def from_dict(cls, dic):
        if Job.validate(dic, Job.response_rows):
            return cls(dic["createdBy"], dic["updatedBy"], dic["guildId"], dic["job"], dic["name"], dic["id"])
        elif Job.validate(dic, Job.request_rows):
            return cls(dic["createdBy"], dic["updatedBy"], dic["guildId"], dic["job"], dic["name"])
        else:
            raise InitializationException()


class JobAnvil(Element):
    rows = [("createdBy", str), ("updatedBy", str), ("guildId", int), ("id", int), ("tier", str),
            ("bronze", bool), ("gold", bool)]

    accepted_tiers = ["apprenti", "compagnon", "expert", "artisan", "maître", "suprême", "ouestfolde", "anòrien"]

    def __init__(self, creator, updator, guild_id, id_, tier, bronze, gold):
        self.created_by = creator
        self.updated_by = updator
        self.guild_id = guild_id
        self.id_ = id_
        self.tier = tier
        self.bronze = bronze
        self.gold = gold

    def __repr__(self):
        representation = ""
        if self.bronze or self.gold:
            representation += self.tier + " : "
        if self.bronze:
            representation += ":bronze:"
        if self.gold:
            representation += ":or"
        return representation

    @staticmethod
    def process_creation(words):
        dic = {}
        for word in words:
            splits = word.split(':')
            if len(splits) == 2:
                if splits[0] in JobAnvil.accepted_tiers:
                    dic["tier"] = splits[0]
                if splits[1] == "bronze":
                    dic["bronze"] = True
                    dic["gold"] = False
                elif splits[1] == "or":
                    dic["bronze"] = True
                    dic["gold"] = True
        return dic

    @classmethod
    def from_dict(cls, dic):
        if JobAnvil.validate(dic, JobAnvil.rows):
            return cls(dic["createdBy"], dic["updatedBy"], dic["guildId"], dic["id"], dic["tier"],
                       dic["bronze"], dic["gold"])
        else:
            raise InitializationException()


class PersistentJobs(Persistent):

    def add_job(self, job):
        self.write('''INSERT INTO Jobs (CreatedBy, UpdatedBy, GuildId, Job, "Name") VALUES (%s, %s, %s, %s, %s)''',
                   (job.created_by, job.updated_by, job.guild_id, job.job, job.name))

    def get_job_id(self, name, job):
        results = self.read('''SELECT * FROM Jobs WHERE "Name"=%s AND Job=%s''', (name, job))
        if len(results) == 1:
            return results[0][5]
        else:
            return -1

    def remove_job(self, name, job):
        id_ = self.get_job_id(name, job)
        self.write('''DELETE FROM JobsAnvils WHERE Id=%s''', id_)
        self.write('''DELETE FROM Jobs WHERE "Name"=%s AND Job=%s''', (name, job))

    def get_jobs(self, guild_id=None):
        if guild_id is None:
            results = self.read('''SELECT * FROM Jobs''', ())
        else:
            results = self.read('''SELECT * FROM Jobs WHERE GuildId=%s''', guild_id)
        jobs = []
        for result in results:
            jobs.append(Job(result[0], result[1], result[2], result[3], result[4], result[5]))
        return jobs

    def get_creator(self, name, job):
        results = self.read('''SELECT * FROM Jobs WHERE "Name"=%s AND Job=%s''', (name, job))
        if len(results) == 1:
            return results[0][3]
        else:
            return ""

    @staticmethod
    def process_job_query(words):
        dic = {}
        for word in words:
            if word in Job.accepted_jobs:
                if "job" not in dic:
                    dic["job"] = []
                dic["job"].append(word)
            else:
                try:
                    test = int(word)
                    dic["guildId"] = test
                except ValueError:
                    if "name" not in dic:
                        dic["name"] = []
                    dic["name"].append(word)
        return dic

    def search_jobs(self, request_dict):
        query = "SELECT * FROM Jobs"
        objects = ()
        first = True
        for key, value in request_dict.iteritems():
            if first:
                query += " WHERE"
                first = False
            else:
                query += " AND"
            if key == "job":
                if isinstance(value, List):
                    query += '''( Job=%s'''
                    query += ''' OR Job=%s'''.join(["" for _ in value])
                    query += '''")'''
                    for val in value:
                        objects += (val,)
                else:
                    query += '''Job=%s'''
                    objects += (value,)
            elif key == "name":
                query += '''"Name" = %s'''
                objects += (value,)
            elif key == "guildId":
                query += "GuildId=%s"
                objects += (value,)
        results = self.read(query, objects)
        jobs = []
        for result in results:
            jobs.append(Job(result[0], result[1], result[2], result[3], result[4], result[5]))
        return jobs

    def add_anvil(self, anvil: JobAnvil):
        self.write('''INSERT INTO JobsAnvils 
                    (CreatedBy, UpdatedBy, Id, Tier, Bronze, Gold) VALUES (%s,%s,%s,%s,%s,%s)'''
                   , (anvil.created_by, anvil.updated_by, anvil.id_, anvil.tier, anvil.bronze, anvil.gold))

    def remove_anvil(self, id_, tier=None):
        if tier is None:
            self.write('''DELETE FROM JobsAnvils WHERE Id=%s''', id_)
        else:
            self.write('''DELETE FROM JobsAnvils WHERE Id=%s AND Tier=%s''', (id_, tier))

    def update_anvil(self, anvil: JobAnvil):
        self.write('''UPDATE JobsAnvils 
                SET UpdatedBy=%s, Bronze=%s, Gold=%s
                WHERE Id=%s AND Tier=%s''',
                   (anvil.updated_by, anvil.bronze, anvil.gold,
                    anvil.id_, anvil.tier))

    def get_anvils(self, id_=None):
        if id_ is None:
            results = self.read('''SELECT * FROM JobsAnvils''', ())
        else:
            results = self.read('''SELECT * FROM JobsAnvils WHERE Id=%s''', id_)
        anvils = []
        for result in results:
            anvils.append(JobAnvil(result[0], result[1], result[2], result[3], result[4], result[5], result[6]))
        return anvils

    @staticmethod
    def process_anvil_query(words):
        dic = {}
        for word in words:
            splits = word.split(':')
            if len(splits) == 2:
                dic[splits[0]] = splits[1].split(',')
            else :
                dic["id"] = int(word)
        return dic

    def search_anvils(self, request_dict):
        query = "SELECT * FROM Jobs"
        objects = ()
        first = True
        for key, value in request_dict.iteritems():
            if first:
                query += " WHERE"
                first = False
            else:
                query += " AND"
            if key == "id":
                if isinstance(value, List):
                    query += '''( Id=%s'''
                    query += ''' OR Id=%s'''.join(["" for _ in value])
                    query += '''")'''
                    for val in value:
                        objects += (val,)
                else:
                    query += '''Job=%s'''
                    objects += (value,)
            elif key in JobAnvil.accepted_tiers:
                query += "Tier=%s"
                objects += (key,)
                if isinstance(value, List):
                    if "bronze" in value and "gold" in value:
                        "AND (bronze=TRUE OR gold=TRUE)"
                    elif "bronze" in value:
                        "AND bronze=TRUE"
                    elif "gold" in value:
                        "AND gold=TRUE"
                else:
                    raise Exception()
        results = self.read(query, objects)
        anvils = []
        for result in results:
            anvils.append(JobAnvil(result[0], result[1], result[2], result[3], result[4], result[5], result[6]))
        return anvils
