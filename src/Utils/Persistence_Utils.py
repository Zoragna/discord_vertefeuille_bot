import traceback

import datetime
from psycopg2.errors import lookup


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


class InitializationException(Exception):
    pass
