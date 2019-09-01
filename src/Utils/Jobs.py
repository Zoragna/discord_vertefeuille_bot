from Utils.Persistence_Utils import *


class PersistentJobs(Persistent):
    accepted_jobs = ["cuisinier", "paysan", "forestier", "bijoutier", "prospecteur", "historien", "tailleur",
                     "ferronier", "sculpteur"]

    Jobs_rows = ["createdBy", "updatedBy", "job", "name", "id"]
    JobsAnvils_rows = ["createdBy", "updatedBy", "id", "tier", "bronze", "gold"]

    def init_database(self):
        self.write('''CREATE TABLE IF NOT EXISTS Jobs (
        CreatedBy text NOT NULL,
        UpdatedBy text NOT NULL,
        Job text NOT NULL,
        "Name" varchar(100) NOT NULL,
        Id SERIAL,
        PRIMARY KEY("Name", Job));''', ())
        self.write('''CREATE TABLE IF NOT EXISTS JobsAnvils ( 
        CreatedBy text NOT NULL,
        UpdatedBy text NOT NULL,
        Id integer NOT NULL,
        Tier Text NOT NULL,
        Bronze boolean NOT NULL,
        Gold boolean NOT NULL,
        PRIMARY KEY(Id, Tier));''', ())
