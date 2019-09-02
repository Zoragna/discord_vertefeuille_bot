from Utils.Persistence_Utils import *
from typing import List


class Job(Element):
    request_rows = [("createdBy", str), ("updatedBy", str), ("guildId", int), ("job", str), ("name", str)]
    response_rows = [("createdBy", str), ("updatedBy", str), ("guildId", int), ("job", str), ("name", str), ("id", int)]

    accepted_jobs = ["cuisinier", "paysan", "forestier", "bijoutier", "prospecteur", "historien", "tailleur",
                     "ferronier", "sculpteur"]

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

    accepted_tiers = ["apprenti", "compagnon", "expert", "artisan", "maître", "suprême", "rhovanion", "estemnet",
                      "ouestemnet", "anòrien"]

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
                dic["tier"] = splits[0]
                if splits[1] == "bronze":
                    dic["bronze"] = True
                elif splits[1] == "or":
                    dic["bronze"] = True
                    dic["gold"] = True
            elif word in JobAnvil.accepted_tiers:
                dic["tier"] = word
        return dic

    @classmethod
    def from_dict(cls, dic):
        if JobAnvil.validate(dic, JobAnvil.rows):
            return cls(dic["createdBy"], dic["updatedBy"], dic["guildId"], dic["id"], dic["tier"],
                       dic["bronze"], dic["gold"])
        else:
            raise InitializationException()


class PersistentJobs(Persistent):

    def init_database(self):
        self.init_database_jobs()
        self.init_database_anvils()

    def init_database_jobs(self):
        self.write('''CREATE TABLE IF NOT EXISTS Jobs (
                CreatedBy text NOT NULL,
                UpdatedBy text NOT NULL,
                GuildId bigint NOT NULL,
                Job text NOT NULL,
                "Name" varchar(100) NOT NULL,
                Id SERIAL,
                PRIMARY KEY("Name", Job));''', ())

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

    def init_database_anvils(self):
        self.write('''CREATE TABLE IF NOT EXISTS JobsAnvils ( 
                CreatedBy text NOT NULL,
                UpdatedBy text NOT NULL,
                Id integer NOT NULL,
                Tier Text NOT NULL,
                Bronze boolean NOT NULL,
                Gold boolean NOT NULL,
                PRIMARY KEY(Id, Tier));''', ())

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

    def get_anvils(self, guild_id=None, id_=None):
        if guild_id is None and id_ is None:
            results = self.read('''SELECT * FROM JobsAnvils''', ())
        elif guild_id is None and id_ is not None:
            results = self.read('''SELECT * FROM JobsAnvils WHERE Id=%s''', id_)
        elif guild_id is not None and id_ is None:
            results = self.read('''SELECT * FROM JobsAnvils WHERE Guild_Id=%s''', guild_id)
        else:
            results = self.read('''SELECT * FROM JobsAnvils WHERE Guild_Id=%s AND Id=%s''', (guild_id, id_))
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
