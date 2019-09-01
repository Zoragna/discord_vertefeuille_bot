from Utils.Persistence_Utils import *

import discord


class Admin(Element):
    rows = [("createdBy", str), ("guildId", int), ("roleId", int)]

    def __init__(self, creator, guild_id, role_id):
        self.created_by = creator
        self.guild_id = guild_id
        self.role_id = role_id

    @classmethod
    def from_dict(cls, dic):
        if Admin.validate(dic, Admin.rows):
            return cls(dic["createdBy"], dic["guildId"], dic["roleId"])
        raise InitializationException()


class Report(Element):
    rows = [("createdBy", str), ("guildId", int), ("userId", int)]

    def __init__(self, creator, guild_id, user_id):
        self.created_by = creator
        self.guild_id = guild_id
        self.user_id = user_id

    @classmethod
    def from_dict(cls, dic):
        if Report.validate(dic, Report.rows):
            return cls(dic["createdBy"], dic["guildId"], dic["userId"])
        raise InitializationException()


class PersistentConfiguration(Persistent):

    def __init__(self, connection, client):
        super().__init__(connection)
        self.client = client

    def init_database(self):
        self.write('''CREATE TABLE IF NOT EXISTS ReportId (
        CreatedBy text NOT NULL,
        GuildId bigint NOT NULL,
        Id bigint NOT NULL,
        PRIMARY KEY(GuildId, Id));''', ())
        self.write('''CREATE TABLE IF NOT EXISTS AdminId (
        CreatedBy text NOT NULL,
        GuildId bigint NOT NULL,
        Id bigint NOT NULL,
        PRIMARY KEY(GuildId, Id));''', ())

    def add_admin(self, admin: Admin):
        self.write('''INSERT INTO AdminId(CreatedBy, GuildId, Id) VALUES (%s, %s, %s)''',
                   (admin.created_by, admin.guild_id, admin.role_id))

    def remove_admin(self, guild_id, role_id):
        self.write("DELETE FROM AdminId WHERE GuildId=%s AND Id=%s", (guild_id, role_id))

    def get_admins(self, guild_id=None):
        if guild_id is None:
            results = self.read("SELECT * FROM AdminId", ())
        else:
            results = self.read("SELECT * FROM AdminId WHERE GuildId=%s", guild_id)
        admins = []
        for result in results:
            admins.append(Admin(result[0], result[1], result[2]))
        return admins

    def is_admin(self, user: discord.Member, guild_id):
        admins = self.get_admins(guild_id)
        for role in user.roles:
            for admin in admins:
                if admin.role_id == role.id:
                    return True
        return False

    def add_report(self, report: Report):
        self.write('''INSERT INTO ReportId(CreatedBy, GuildId, Id) VALUES (%s, %s, %s)''', (report.created_by,
                                                                                            report.guild_id,
                                                                                            report.user_id))

    def remove_report(self, guild_id, user_id):
        self.write("DELETE FROM ReportId WHERE GuildId=%s AND Id=%s", (guild_id, user_id))

    def get_reports(self):
        results = self.read("SELECT * FROM ReportId", ())
        reports = []
        for result in results:
            print("one reporter")
            reports.append(Report(result[0], result[1], result[2]))
        return reports

    async def warn_error(self, msg, guild_id):
        reporters = self.get_reports()
        if len(reporters) == 0:
            guild: discord.Guild = self.client.get_guild(guild_id)
            await guild.owner.send(msg)
        else:
            for reporter in reporters:
                print("someone has to be reported")
                reporter_id = reporter.user_id
                try:
                    await self.client.get_user(reporter_id).send(msg)
                except discord.HTTPException:
                    print("[ERROR in ERROR] Could not reach '" + reporter_id + "'")
