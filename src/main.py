# Discord Bot for Les Descendants de VerteFeuille
# French guild on Lord of the Rings Online
#
# add url :
# https://discordapp.com/oauth2/authorize?client_id=614569601287585841&scope=bot
#

import discord
import os
import datetime
import psycopg2
import logging
import pprint

from Utils import Configuration, \
    Characters, Jobs, Reputations, \
    Calendar, Twitters, Persistence_Utils, Annuary

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor

logging.basicConfig()

annuary_path = "lotro_annuaire.xlsx"

DATABASE_URL = os.environ["DATABASE_URL"]
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]

if "ENVIRONMENT" in os.environ and os.environ["ENVIRONMENT"] == "PROD":
    connection = psycopg2.connect(DATABASE_URL, sslmode='require')
    jobstores = {
        'sqlalchemy': SQLAlchemyJobStore(url=DATABASE_URL)
    }
    logging.getLogger('apscheduler').setLevel(logging.DEBUG)
else:
    connection = psycopg2.connect("postgres://localhost", user="postgres", password="root", database="lotro")
    # postgresql+psycopg2://scott:tiger@localhost/mydatabase
    # dialect+driver://username:password@host:port/database
    jobstores = {
        'sqlalchemy': SQLAlchemyJobStore(url="postgresql+psycopg2://postgres:root@localhost/lotro")
    }
executors = {
    'default': ThreadPoolExecutor(20),
    'processpool': ProcessPoolExecutor(5)
}
job_defaults = {
    'coalesce': False,
    'max_instances': 3
}
scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults)
scheduler.start()

Annuary.init_databases(connection)

persistentConfiguration = Configuration.PersistentConfiguration(connection)

client = Persistence_Utils.Bot(persistentConfiguration)

persistentCharacters = Characters.PersistentCharacters(connection)
persistentJobs = Jobs.PersistentJobs(connection)
persistentReputations = Reputations.PersistentReputations(connection)
persistentCalendar = Calendar.PersistentCalendars(connection, scheduler, client)
persistentTwitters = Twitters.PersistentTwitters(connection, persistentConfiguration, client)

persistentConfiguration.set_client(client)


@client.map_input("aide/.*", "", "Legolas aide", "Afficher l'aide")
async def general_help(message, words, **kwargs):
    print(words)
    if len(words) > 0:
        entry = "/".join(words)
        if entry in client.help:
            embed = discord.Embed(title="Commandes d'aide disponibles", color=0x37f23c)
            for title in client.help[entry]:
                embed.add_field(name=title, value=client.help[entry][title], inline=False)
            await message.channel.send(embed=embed)
    else:
        embed = discord.Embed(title="Commandes d'aide disponibles", color=0x37f23c)
        embed.add_field(name="Legolas aide twitter",
                        value="Liste des commandes d'aide associées à Twitter", inline=False)
        embed.add_field(name="Legolas aide admin",
                        value="Liste des commandes d'aide associées à la gestion des permissions vis à vis du bot", inline=False)
        embed.add_field(name="Legolas aide annuaire",
                        value="Liste des commandes liées à l'annuaire", inline=False)
        embed.add_field(name="Legolas aide calendrier",
                        value="Liste des commandes liées au calendrier", inline=False)
        await message.channel.send(embed=embed)


@client.map_input("twitter/{account}/{action}", "twitter",
                  "Legolas twitter <twitter_user> [ajouter/retirer] #<salon> [#<salon> ...]",
                  "Ajouter ou retirer un salon pour la diffusion d'un compte twitter")
@Persistence_Utils.Bot.is_admin(persistentConfiguration)
async def process_twitter_account(message, words, **kwargs):
    account = kwargs["account"]
    action = kwargs["action"]
    msg = ""
    channels = message.channel_mentions
    if action == "ajouter":
        try:
            dic = {"createdBy": message.author.name, "username": account}
            twitter_account = Twitters.TwitterAccount.from_dict(dic)
            persistentTwitters.add_account(twitter_account)
        except psycopg2.errors.lookup("25P02"):
            print("twitter account already created")
        for mention_channel in channels:
            dic = {"createdBy": message.author.name, "username": account,
                   "channelId": mention_channel.id}
            twitter_channel = Twitters.TwitterChannel.from_dict(dic)
            persistentTwitters.add_channel(twitter_channel)
            msg += "'" + account + "' transmet désormais les messages sur '" + mention_channel.mention + "'\n"
    elif action == "retirer":
        channel_ids = [channel.id for channel in channels]
        twitter_channels = persistentTwitters.get_channels(account)
        twitter_channels = [twt_chnl for twt_chnl in twitter_channels if
                            twt_chnl.channel_id in channel_ids]
        for twitter_channel in twitter_channels:
            persistentTwitters.remove_channel(twitter_channel.id)
            twt_channel = client.get_channel(twitter_channel.channel_id)
            msg += "'" + account + "' ne transmet plus les messages sur '" + twt_channel.mention + "'\n"
    await message.channel.send(msg)


@client.map_input("twitter/list", "twitter",
                  "Legolas twitter list",
                  "Lister les comptes et les salons liés")
async def list_twtitter_accounts(message, words, **kwargs):
    msg = ""
    guild_id = message.guild.id
    twitter_accounts = persistentTwitters.get_accounts()
    if len(twitter_accounts) == 0:
        msg = "Pas de retransmission programmée."
    for twitter_account in twitter_accounts:
        msg += "**" + twitter_account.username + "**"
        twitter_channels = persistentTwitters.get_channels(twitter_account.username)
        for twitter_channel in twitter_channels:
            client_channel = client.get_channel(twitter_channel.channel_id)
            if guild_id == client_channel.guild.id:
                msg += "   " + client_channel.mention
                twitter_filters = persistentTwitters.get_filters(twitter_channel.id)
                for twitter_filter in twitter_filters:
                    msg += "*" + twitter_filter.sentence + "*"
                msg += "\n"
    await message.channel.send(msg)


@client.map_input("twitter/filtre/{twitter_user}/retirer/{sentence}/.*", "twitter",
                  "Legolas twitter filtre <twitter_user> retirer \"texte\" #<salon> [#<salon> ...]",
                  "Retirer un filtre pour un salon pour un compte twitter")
@Persistence_Utils.Bot.is_admin(persistentConfiguration)
async def remove_twitter_filter(message, words, **kwargs):
    modified_channels = message.channel_mentions
    twitter_channels = persistentTwitters.get_channels(kwargs["twitter_user"])
    sentence = kwargs["sentence"].replace("_", " ")
    msg = ""
    if len(modified_channels) > 0:
        modified_channel_ids = [modified_channel.id for modified_channel in modified_channels]
        twitter_channels = [twt_ch for twt_ch in twitter_channels if
                            twt_ch.channel_id in modified_channel_ids]
    for twitter_channel in twitter_channels:
        channel_name = client.get_channel(twitter_channel.channel_id).name
        if "<#" == sentence[:2] and ">" == sentence[-1]:  # a channel mention
            persistentTwitters.remove_filter(twitter_channel.id)
            msg += "Tous les filtres de transmission de '%s' dans le salon '%s' ont été retirés." \
                   % twitter_channel.username, channel_name
        else:
            persistentTwitters.remove_filter(twitter_channel.id, sentence)
            msg += "Le filtre de transmission sur '%s' pour '%s' dans le salon '%s' a été retiré." \
                   % sentence, twitter_channel.username, channel_name
        await message.channel.send(msg)


@client.map_input("twitter/filtre/ajouter/.*", "twitter",
                  "Legolas twitter filtre <twitter_user> [ajouter/retirer] \"texte\" #<salon> [#<salon> ...]",
                  "Ajouter un filtre pour un salon pour un compte twitter")
@Persistence_Utils.Bot.is_admin(persistentConfiguration)
async def add_twitter_filter(message, words, **kwargs):
    modified_channels = message.channel_mentions
    twitter_channels = persistentTwitters.get_channels(words[0])
    sentence = words[1].replace("_", " ")
    msg = ""
    for modified_channel in modified_channels:
        twitter_chnls = [twt_ch for twt_ch in twitter_channels if
                         twt_ch.channel_id == modified_channel.id and twt_ch.username == words[3]]
        if len(twitter_chnls) == 0:
            dic = {"createdBy": message.author.name, "username": words[3],
                   "channel": modified_channel.id}
            twitter_channel = Twitters.TwitterChannel.from_dict(dic)
            dic_id = persistentTwitters.add_channel(twitter_channel)
        else:
            dic_id = twitter_chnls[0].id
        dic = {"createdBy": message.author.name, "updatedBy": message.author.name,
               "id": dic_id, "sentence": sentence}
        twitter_filter = Twitters.TwitterFilter.from_dict(dic)
        persistentTwitters.add_filter(twitter_filter)
        msg += "Les tweets de %s contenant %s sont transmis vers %s !" \
               % (words[3], sentence, modified_channel.mention)
    await message.channel.send(msg)


@client.map_input("erreur/list", "admin",
                  "Legolas erreur list",
                  "Lister les personnes qui reçoivent les rapports d'erreur du bot")
async def list_error_reporters(message, words, **kwargs):
    channel = message.channel
    reports = [report for report in persistentConfiguration.get_reports() if report.guild_id == channel.guild.id]
    msg = "Pas de membres enregistrés pour recevoir les rapports d'erreur."
    if len(reports) > 0:
        msg = ", ".join(
            [client.get_user(report.user_id).name for report in reports if
             client.get_user(report.user_id) is not None])
        if len(reports) == 1:
            msg += " reçoit "
        else:
            msg += "reçoivent "
        msg += "les rapports d'erreur."
    await channel.send(msg)


@client.map_input("erreur/ajouter/.*", "admin",
                  "Legolas erreur ajouter @Utilisateur [@Utilisateur ...]",
                  "Ajouter des personnes qui reçoivent les rapports d'erreur du bot")
@Persistence_Utils.Bot.is_admin(persistentConfiguration)
async def add_error_reporter(message, words, **kwargs):
    channel = message.channel
    msg = "Vous n'avez pas préciser de personnes à ajouter !"
    if len(message.mentions) >= 1:
        guild_id = message.guild.id
        for member in message.mentions:
            dic = {"createdBy": message.author.name, "guildId": guild_id, "userId": member.id}
            report = Configuration.Report.from_dict(dic)
            persistentConfiguration.add_report(report)
        if len(message.role_mentions) > 1:
            msg = "Membres ajoutés"
        else:
            msg = "Membre ajouté"
        msg += " pour recevoir les rapports d'erreur."
    await channel.send(msg)


@client.map_input("erreur/retirer/.*", "admin",
                  "Legolas erreur retirer [@Utilisateur ...]",
                  "Retirer aux personnes qui reçoivent les rapports d'erreur du bot")
@Persistence_Utils.Bot.is_admin(persistentConfiguration)
async def remove_error_reporter(message, words, **kwargs):
    guild_id = message.guild_id
    channel = message.channel
    msg = "Vous n'avez pas préciser de personnes à ajouter !"
    if len(message.mentions) >= 1:
        for member in message.mentions:
            persistentConfiguration.remove_report(guild_id, member.id)
        if len(message.mentions) > 1:
            msg = "Membres retirés"
        else:
            msg = "Membre retiré"
        msg += " de la liste de ceux qui recoivent les rapports d'erreur."
    await channel.send(msg)


@client.map_input("admin/list", "admin",
                  "Legolas admin list",
                  "Lister les rôles qui ont des droits supplémentaires auprès du bot")
@Persistence_Utils.Bot.is_admin(persistentConfiguration)
async def list_administrators(message, words, **kwargs):
    channel = message.channel
    guild_id = message.guild.id
    admins = persistentConfiguration.get_admins(guild_id)
    msg = "Pas de rôle enregistrés pour administrer le bot."
    if len(admins) > 0:
        msg = ", ".join([channel.guild.get_role(admin.role_id).name for admin in admins if
                         channel.guild.get_role(admin.role_id) is not None])
    await channel.send(msg)


@client.map_input("admin/ajouter/.*", "admin",
                  "Legolas admin ajouter @Role [@Role ...]",
                  "Ajouter des rôles qui ont des droits supplémentaires auprès du bot")
@Persistence_Utils.Bot.is_admin(persistentConfiguration)
async def add_administrators(message, words, **kwargs):
    guild_id = message.guild.id
    channel = message.channel
    msg = "Vous n'avez pas mentionné de rôles !"
    if len(message.role_mentions) >= 1:
        for role in message.role_mentions:
            dic = {"createdBy": message.author.name, "guildId": guild_id, "roleId": role.id}
            admin = Configuration.Admin.from_dict(dic)
            persistentConfiguration.add_admin(admin)
        if len(message.role_mentions) > 1:
            msg = "Rôles ajoutés"
        else:
            msg = "Rôle ajouté"
        msg += " aux administrateurs du bot"
    await channel.send(msg)


@client.map_input("admin/retirer/.*", "admin",
                  "Legolas admin retirer [@Role ...]",
                  "Retirer des rôles qui ont des droits supplémentaires auprès du bot")
@Persistence_Utils.Bot.is_admin(persistentConfiguration)
async def remove_administrators(message, words, **kwargs):
    guild_id = message.guild.id
    channel = message.channel
    msg = "Vous n'avez pas mentionné de rôles !"
    if len(message.role_mentions) >= 1:
        for role in message.role_mentions:
            persistentConfiguration.remove_admin(guild_id, role.id)
        if len(message.role_mentions) > 1:
            msg = "Rôles retirés"
        else:
            msg = "rôle retiré"
        msg += " des administrateurs du bot"
    await channel.send(msg)


@client.map_input("nouveau/list", "nouveau", "Legolas nouveau list", "WIP")
async def list_newbies_channels(message, words, **kwargs):
    await message.channel.send("WIP")


@client.map_input("nouveau/ajouter", "nouveau", "Legolas nouveau ajouter", "WIP")
async def list_newbies_channels(message, words, **kwargs):
    await message.channel.send("WIP")


@client.map_input("nouveau/retirer", "nouveau", "Legolas nouveau retirer", "WIP")
async def list_newbies_channels(message, words, **kwargs):
    await message.channel.send("WIP")


@client.map_input("annuaire/excel", "annuaire", "Legolas annuaire excel",
                  "Recevoir en Message Privé l'annuaire sous format excel")
async def send_excel_sheets(message, words, **kwargs):
    channel = message.author
    with open(annuary_path, "rb") as annuaire_stream:
        msg = "Voici l'annuaire en format .xlsx !"
        file = discord.File(annuaire_stream)
    await channel.send(msg, file=file)


@client.map_input("annuaire/personnage/list", "annuaire/personnage",
                  "Legolas annuaire personnage list",
                  "Lister les personnages présents dans l'annuaire")
async def list_characters(message, words, **kwargs):
    guild_id = message.guild.id
    msg = ",\n".join([repr(character) for character in persistentCharacters.get_characters(guild_id)])
    if msg == "":
        msg = "Pas de personnages enregistrés !"
    await message.channel.send(msg)


@client.map_input("annuaire/personnage/{action}/.*", "annuaire/personnage",
                  "Legolas annuaire personnage [ajouter/màj/retirer] pseudo_ig [accepted_class accepted_color (1-120)]",
                  "Ajouter/Mettre à jour/Retirer un personnage dans/de l'annuaire")
async def process_characters(message, words, **kwargs):
    guild_id = message.guild.id
    channel = message.channel
    action = kwargs["action"]
    dic = Characters.Character.process_creation(words[4:])
    dic["createdBy"] = message.author.name
    dic["updatedBy"] = message.author.name
    dic["guildId"] = guild_id
    character = Characters.Character.from_dict(dic)
    can_modify_character = kwargs["is_admin"] or persistentCharacters.get_creator(character.name) == message.author.name
    msg = ""
    annuary_modified = False
    if action == "ajouter":
        try:
            persistentCharacters.add_character(character)
            msg = "Votre personnage a été ajouté !"
        except psycopg2.IntegrityError:
            if can_modify_character:
                persistentCharacters.update_character(character)
                msg = "Votre personnage a été mis à jour !"
        annuary_modified = True
    elif action == "màj":
        if can_modify_character:
            persistentCharacters.update_character(character)
            msg = "Votre personnage a été mis à jour !"
            annuary_modified = True
    elif action == "retirer":
        if persistentCharacters.get_creator(words[4]) == message.author.name:
            persistentCharacters.remove_character(words[4])
            msg = "Votre personnage a été retiré !"
            annuary_modified = True
        else:
            msg = "Vous ne possédez pas ce personnage !"
    if annuary_modified:
        # TODO Maybe this could deserve a decorator (we need to split this into methods then)
        Annuary.storeAnnuary(annuary_path, characters=persistentCharacters.get_characters(guild_id))
    await channel.send(msg)


@client.map_input("annuaire/personnage/chercher/.*", "annuaire/personnage",
                  "Legolas annuaire personnage chercher [accepted_class ...] [pseudo_ig ...] [accepted_color ...] [(1-120)]-(1-120)]",
                  "Rechercher un/des personnage(s) dans l'annuaire")
async def search_characters(message, words, **kwargs):
    dic = Characters.PersistentCharacters.process_query(words)
    dic["guildId"] = message.guild.id
    characters = persistentCharacters.search_characters(dic)
    msg = ",\n".join([repr(character) for character in characters])
    await message.channel.send(msg)


@client.map_input("annuaire/métier/list", "annuaire/métier",
                  "Legolas annuaire métier list",
                  "Lister les métiers présents dans l'annuaire")
async def list_jobs(message, words, **kwargs):
    guild_id = message.guild.id
    channel = message.channel
    msg = "Pas de métiers enregistrés"
    jobs = persistentJobs.get_jobs(guild_id)
    if len(jobs) > 0:
        msg = "**Liste des artisans**\n"
    for job in jobs:
        msg += str(job)
        anvils = persistentJobs.get_anvils(guild_id, job.id_)
        for anvil in anvils:
            msg += str(anvil)
        msg += "\n"
    await channel.send(msg)


@client.map_input("annuaire/métier/retirer/{name}/{job}", "annuaire/métier",
                  "Legolas annuaire métier retirer [pseudo_ig] [métier]",
                  "Retirer le métier du personnage dans l'annuaire")
async def remove_job(message, words, **kwargs):
    msg = "Vous n'avez pas rajouté cette entrée, vous ne pouvez pas la modifier !"
    name = kwargs["name"]
    job = kwargs["job"]
    can_modify_job = kwargs["is_admin"] or persistentJobs.get_creator(name, job) == message.author.name
    if can_modify_job:
        id_ = persistentJobs.get_job_id(name, job)
        persistentJobs.remove_job(name, job)
        persistentJobs.remove_anvil(id_)
        msg = "Votre métier a été retiré "
    await message.channel.send(msg)


@client.map_input("annuaire/métier/{action}/.*", "annuaire/métier",
                  "Legolas annuaire métier pseudo_ig [accepted_jobs] [[accepted_tier]:[or/bronze] ...]",
                  "Ajouter ou mettre à jour un métier dans l'annuaire, optionnellement ses enclumes.")
async def update_or_add_job(message, words, **kwargs):
    guild_id = message.guild.id
    action = kwargs["action"]
    msg = ""

    dic = Jobs.Job.process_creation([word for word in words if len(word.split(':')) != 2])
    dic["createdBy"] = message.author.name
    dic["updatedBy"] = message.author.name
    dic["guildId"] = guild_id
    job = Jobs.Job.from_dict(dic)

    dic = Jobs.JobAnvil.process_creation([word for word in words if len(word.split(':')) == 2])
    dic["createdBy"] = message.author.name
    dic["updatedBy"] = message.author.name
    dic["guildId"] = guild_id
    job_anvil = Jobs.JobAnvil.from_dict(dic)

    can_modify_job = kwargs["is_admin"] or persistentJobs.get_creator(job.name, job.job) == message.author.name
    if action == "ajouter":
        try:
            persistentJobs.add_job(job)
            persistentJobs.add_anvil(job_anvil)
            msg = "Votre métier a été ajouté !"
        except psycopg2.IntegrityError:
            if can_modify_job:
                persistentJobs.update_anvil(job_anvil)
                msg = "Votre métier a été mis à jour !"
    elif action == "màj":
        if can_modify_job:
            persistentJobs.update_anvil(job_anvil)
            msg = "Votre métier a été mis à jour !"
    await message.channel.send(msg)


@client.map_input("annuaire/métier/chercher/.*", "annuaire/métier",
                  "Legolas annuaire métier chercher [[accepted_jobs]] [[artisanat]]",
                  "WIP")
async def search_jobs(message, words, **kwargs):
    await message.channel.send("WIP")


@client.map_input("annuaire/réputation/list", "annuaire/réputation",
                  "Legolas annuaire réputation list",
                  "Lister les réputations dans l'annuaire")
async def list_reputations(message, words, **kwargs):
    await message.channel.send("WIP")


@client.map_input("annuaire/réputation/ajouter/.*", "annuaire/réputation",
                  "Legolas annuaire réputation ajouter []",
                  "WIP")
async def add_reputations(message, words, **kwargs):
    await message.channel.send("WIP")


@client.map_input("annuaire/réputation/màj/.*", "annuaire/réputation",
                  "Legolas annuaire réputation màj []", "WIP")
async def update_reputations(message, words, **kwargs):
    await message.channel.send("WIP")


@client.map_input("annuaire/réputation/retirer/.*", "annuaire/réputation",
                  "Legolas annuaire réputation retirer []", "WIP")
async def remove_reputations(message, words, **kwargs):
    await message.channel.send("WIP")


@client.map_input("annuaire/réputation/chercher/.*", "annuaire/réputation",
                  "Legolas annuaire réputation chercher []", "WIP")
async def search_reputations(message, words, **kwargs):
    await message.channel.send("WIP")


@client.map_input("calendrier/list", "calendrier",
                  "Legolas calednrier list",
                  "Recevoir le calendrier")
async def list_events(message, words, **kwargs):
    guild_id = message.guild.id
    date = datetime.datetime.today().timestamp()
    events = persistentCalendar.get_events(guild_id, after=date)
    embed = None
    msg = ""
    if len(events) > 0:
        embed = discord.Embed(title="Calendrier")
        for event in events:
            embed.add_field(name=event.name.replace("_", " "), value=repr(event), inline=False)
    else:
        msg = "Pas d'évènements dans le calendrier !"
    await message.channel.send(msg, embed=embed)


@client.map_input("calendrier/prochain", "calendrier",
                  "Legolas calendrier prochain",
                  "Recevoir le prochain évènement dans le calendrier")
async def next_event(message, words, **kwargs):
    embed = None
    msg = ""
    guild_id = message.guild.id
    date = datetime.datetime.today().timestamp()
    events = persistentCalendar.get_events(guild_id, after=date)
    if len(events) > 1:
        event = events[0]
        embed = discord.Embed(title="Calendrier")
        embed.add_field(name=event.name.replace("_", " "), value=repr(event), inline=False)
    else:
        msg = "Pas d'évènements dans le calendrier !"
    await message.channel.send(msg, embed=embed)


@client.map_input("calendrier/retirer/{name}/{begin_date}", "calendrier",
                  "Legolas calendrier retirer \"nom\" jj/mm/aaaa",
                  "Retirer l'évènement nommé commençant au jour donné")
@Persistence_Utils.Bot.is_admin(persistentConfiguration)
async def remove_event(message, words, **kwargs):
    name = kwargs["name"]
    splits = kwargs["begin_date"].split('/')
    date = datetime.datetime(splits[2], splits[1], splits[0]).timestamp()
    persistentCalendar.remove_event(name, date)
    msg = "L'évènement du '%s' commençant le %s a été retiré" % (name, splits)
    await message.channel.send(msg)


@client.map_input("calendrier/{action}/.*", "calendrier",
                  "Legolas calendrier [ajouter/màj] \"nom\" jj/mm/aaa jj/mm/aaaa \"description\" #channel_de_difussion",
                  "Ajouter un évènement au calendrier (le nom est plus court que la description)")
@Persistence_Utils.Bot.is_admin(persistentConfiguration)
async def process_event_modification(message, words, **kwargs):
    guild_id = message.guild.id
    msg = "Vous n'avez pas mentionné le canal dans lequel votre évènement sera annoncé ! (le midi la veille)"
    action = kwargs["action"]

    dic = Calendar.Event.process_creation(words)
    dic["createdBy"] = message.author.name
    dic["updatedBy"] = message.author.name
    dic["guildId"] = guild_id
    if len(message.channel_mentions) == 1:
        dic["channelId"] = message.channel_mentions[0].id
        print(dic)
        _event = Calendar.Event.from_dict(dic)
        if action == "ajouter":
            try:
                if persistentCalendar.add_event(_event):
                    msg = "Evènement ajouté !"
                else:
                    msg = "Evènement ajouté ! (aucune notification ne sera envoyée)"
            except psycopg2.IntegrityError:
                msg = "Un évènement avec ce nom existe déjà"
        elif action == "màj":
            persistentCalendar.update_event(_event)
            msg = "Evènement mis à jour !"
    await message.channel.send(msg)


pprint.pprint(client.mapping)
pprint.pprint(client.help)

@client.event
async def on_member_join(member):
    guild_id = member.guild.id
    # if guild_id in new_member_channels:
    #    new_channel = client.get_channel(new_member_channels[guild_id])
    #    await new_channel.send("Bienvenue " + member.mention + " !")


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        print("Read my own message")
        return
    if message.channel.type != discord.ChannelType.text:
        print("Message not in text channel")
        return
    if message.content.startswith(client.caller):
        command_msg = "[" + str(message.guild) + "][" + message.channel.name + "][" + \
                          str(message.created_at) + "] '" + message.content + "' from '" + message.author.name + "'"
        print(command_msg)
        await client.process_input(message)


@client.event
async def on_ready():
    print('------')
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')


client.run(DISCORD_TOKEN)
