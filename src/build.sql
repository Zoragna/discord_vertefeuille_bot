CREATE TABLE IF NOT EXISTS Jobs (
                CreatedBy text NOT NULL,
                UpdatedBy text NOT NULL,
                GuildId bigint NOT NULL,
                Job text NOT NULL,
                "Name" varchar(100) NOT NULL,
                Id SERIAL,
                PRIMARY KEY("Name", Job));

CREATE TABLE IF NOT EXISTS JobsAnvils (
                CreatedBy text NOT NULL,
                UpdatedBy text NOT NULL,
                Id integer NOT NULL,
                Tier Text NOT NULL,
                Bronze boolean NOT NULL,
                Gold boolean NOT NULL,
                PRIMARY KEY(Id, Tier));

CREATE TABLE IF NOT EXISTS Reputations (
        CreatedBy text NOT NULL,
        UpdatedBy text NOT NULL,
        "Name" varchar(100),
        Faction varchar(100),
        Level text,
        GuildId bigint NOT NULL,
        PRIMARY KEY("Name", Faction));

CREATE TABLE IF NOT EXISTS Allegiances (
        CreatedBy text NOT NULL,
        UpdatedBy text NOT NULL,
        "Name" varchar(100),
        Allegiance varchar(100),
        Level int,
        GuildId bigint NOT NULL,
        PRIMARY KEY("Name", Allegiance));

CREATE TABLE IF NOT EXISTS Characters (
        CreatedBy text NOT NULL,
        UpdatedBy text NOT NULL,
        GuildId bigint NOT NULL,
        Class text NOT NULL,
        "Level" SMALLINT,
        MainTrait text NOT NULL,
        "Name" varchar(100),
        PRIMARY KEY ("Name"));

CREATE TABLE IF NOT EXISTS Craftsmanship (
        CreatedBy text NOT NULL,
        UpdatedBy text NOT NULL,
        "Name" varchar(100),
        Guild varchar(100),
        Level text,
        GuildId bigint NOT NULL,
        PRIMARY KEY("Name", Guild));

CREATE TABLE IF NOT EXISTS ReportId (
        CreatedBy text NOT NULL,
        GuildId bigint NOT NULL,
        Id bigint NOT NULL,
        PRIMARY KEY(GuildId, Id));

CREATE TABLE IF NOT EXISTS AdminId (
        CreatedBy text NOT NULL,
        GuildId bigint NOT NULL,
        Id bigint NOT NULL,
        PRIMARY KEY(GuildId, Id));

CREATE TABLE IF NOT EXISTS TwitterAccounts (
                CreatedBy text NOT NULL,
                Username varchar(100) PRIMARY KEY );

CREATE TABLE IF NOT EXISTS TwitterChannels (
        CreatedBy text NOT NULL,
        Username varchar(100),
        Channel bigint NOT NULL,
        Id SERIAL,
        PRIMARY KEY (Username, Channel));

CREATE TABLE IF NOT EXISTS TwitterFilters (
        CreatedBy text NOT NULL,
        UpdatedBy text NOT NULL,
        Id integer NOT NULL,
        Sentence varchar(300),
        PRIMARY KEY(Id, Sentence));

CREATE TABLE IF NOT EXISTS Calendar (
        CreatedBy text NOT NULL,
        UpdatedBy text NOT NULL,
        "Name" varchar(100) NOT NULL,
        GuildId bigint NOT NULL,
        ChannelId bigint NOT NULL,
        "Begin" bigint NOT NULL,
        "End" bigint NOT NULL,
        Description text NOT NULL,
        PRIMARY KEY("Name", "Begin"));
