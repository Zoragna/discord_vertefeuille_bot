import traceback
import datetime
import discord
import pprint

from psycopg2.errors import lookup
from functools import wraps
from types import FunctionType


class CommandException(Exception):
    pass


class Bot(discord.Client):

    def __init__(self, configurator):
        super().__init__()
        self.mapping = {}
        self.configurator = configurator
        self.caller = "Legolas"
        self.help = {}

    @staticmethod
    async def empty_func(message, **kwargs):
        pass

    @staticmethod
    async def not_understood(message, **kwargs):
        await message.channel.send("Je n'ai pas compris ! ;(")

    @staticmethod
    async def unauthorized(message, **kwargs):
        await message.channel.send("Vous n'êtes pas authorisé à faire ça !")

    @staticmethod
    def find_key(dic):
        for key in dic:
            if key[0] == "{" and key[-1] == "}":
                return key[1:-1]
        return "__NOT_FOUND__"

    async def process_input(self, message: discord.Message):
        try:
            words = Bot.process_sentences(message.content).split(' ')
        except CommandException:
            await Bot.not_understood(message)
            return
        tmp = self.mapping
        func = Bot.empty_func
        kwargs = {}
        i = 0
        if words[0] == self.caller:
            words = words[1:]
        for i in range(len(words)):
            word = words[i]
            if word in tmp:
                tmp = tmp[word]
            else:
                found_key = Bot.find_key(tmp)
                if found_key != "__NOT_FOUND__":
                    kwargs[found_key] = word
                    tmp = tmp["{"+found_key+"}"]
                elif ".*" in tmp:
                    await Bot.launch_input(tmp[".*"], self.configurator, message, words[i:], **kwargs)
                    return
                else:
                    await Bot.not_understood(message)
                    return
        if len(words) == i + 1 and not isinstance(tmp, FunctionType):
            await Bot.launch_input(tmp[".*"], self.configurator, message, [], **kwargs)
        else:
            await Bot.launch_input(tmp, self.configurator, message, words[i+1:], **kwargs)

    @staticmethod
    async def launch_input(func, configurator, message: discord.Message, words, **kwargs):
        channel = message.channel
        print(func)
        print(words)
        print(kwargs)
        try:
            kwargs["is_admin"] = configurator.is_admin(message.author, message.guild.id)
            await func(message, words, **kwargs)
        except (IndexError, CommandException):
            await channel.send("Il semblerait que je ne puisse pas faire suivre votre requête !")
        except InitializationException:
            await channel.send("Votre demande ne suit pas le format attendu.")
        except lookup("25P02"):
            await channel.send("Une entrée existe déjà pour cet objet")
        except Exception as e:
            msg = "Erreur, l'administrateur et d'autres personnes ont été notifiées !"
            await message.channel.send(msg)

            msg = "[" + message.guild.name + "][ERROR]" + str(e)
            error_msg = msg + "\n" + traceback.format_exc() + "\ncaused by: '" + message.content + "'"
            await configurator.warn_error(error_msg, message.guild.id)

    def map_input(self, query, section="", command=None, description=""):
        def mapping_input_decorator(func):
            @wraps(func)
            def wrapped_function(*args, **kwargs):
                return func(*args, **kwargs)

            print(query)
            self.process_query(query, func)
            self.add_help([section], command, description)
        return mapping_input_decorator

    def is_admin(self):
        def decorator_is_admin(func):
            @wraps(func)
            def wrapper_is_admin(message, words, **kwargs):
                is_admin = message.author.name == message.guild.owner.name or \
                    self.configurator.is_admin(message.author, message.guild.id)
                if is_admin:
                    return func(message, words, **kwargs)
                else:
                    return Bot.unauthorized(message, **kwargs)

            return wrapper_is_admin

        return decorator_is_admin

    def process_query(self, query, func):
        words = query.split('/')
        self.add_mapping(words[:-1], words[-1], func)

    def add_mapping(self, words, key, value):
        Bot.add_to_attribute(self.mapping, words, key, value)

    def add_help(self, words, key, value):
        Bot.add_to_attribute(self.help, words, key, value)

    @staticmethod
    def add_to_attribute(attribute, words, key, value):
        tmp = attribute
        for word in words:
            if word not in tmp:
                tmp[word] = {}
            tmp = tmp[word]
        tmp[key] = value

    @staticmethod
    def process_inputs(text):
        text_process = text
        result = []
        while text_process.count("{") != 0 and result.count("}") != 0:
            first = text_process.find("{")
            second = text_process.find("}")
            need_sanitize_word = text_process[first:second + 1]
            text_process = text_process.replace(need_sanitize_word, "")
            word = need_sanitize_word.replace("{", "").replace("}", "")
            result.append(word)
        return result

    @staticmethod
    def process_sentences(text):
        result = text
        print("Process Sentences")
        print(text)
        while result.count("\"") != 0 and result.count("\"") % 2 == 0:
            first = result.find("\"")
            second = result[first + 1:].find("\"")
            old_sequence = result[first:first + second + 2]
            new_sequence = old_sequence.replace(" ", "_").replace("\"", "")
            result = result.replace(old_sequence, new_sequence)
        print(result)
        if result.count("\"") % 2 == 1:
            print("Process Sentences END FAILING")
            raise CommandException()
        print("Process Sentences END")
        return result


class Persistent(object):

    @staticmethod
    def sanitize_query(query):
        if query.replace("\n", "")[-1] != ";":
            query += ";"
        return query

    @staticmethod
    def sanitize_objects(objects):
        if not isinstance(objects, tuple):
            objects = (objects,)
        return objects

    def __init__(self, connection):
        self.connection = connection
        self.cursor = connection.cursor()

    def read(self, query, objects):
        query = Persistent.sanitize_query(query)
        objects = Persistent.sanitize_objects(objects)
        try:
            self.cursor.execute(query, objects)
            results = self.cursor.fetchall()
            print("[" + str(datetime.datetime.today()) + "]" + query % objects)
            return results
        except lookup("25P02") as e:
            self.cursor.execute("ROLLBACK")
            self.connection.commit()
            print("[" + str(datetime.datetime.today()) + "] ROLLBACK | " + query % objects)
            print(traceback.format_exc())
            return []

    def write(self, query, record):
        query = Persistent.sanitize_query(query)
        record = Persistent.sanitize_objects(record)
        try:
            self.cursor.execute(query, record)
            self.connection.commit()
            print("[" + str(datetime.datetime.today()) + "]" + query % record)
        except lookup("25P02") as e:
            self.cursor.execute("ROLLBACK")
            self.connection.commit()
            print("[" + str(datetime.datetime.today()) + "] ROLLBACK | " + query % record)
            print(traceback.format_exc())


class Element(object):

    @staticmethod
    def validate(dic, rows):
        if len(dic) != len(rows):
            return False
        for (key, cls) in rows:
            if key not in dic:
                return False
            if not isinstance(dic[key], cls):
                return False
        return True

    @staticmethod
    def list_query_list(values, key):
        query = ""
        query += "(" + key + "=%s"
        if len(values) > 1 :
            query += " OR " + key + "=%s".join(["" for _ in values])
        query += ")"
        return query


class InitializationException(Exception):
    pass
