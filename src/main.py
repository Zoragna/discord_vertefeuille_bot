## Discord Bot for Les Descendants de VerteFeuille
# French guild on Lord of the Rings Online
#
## add url :
# https://discordapp.com/oauth2/authorize?client_id=614569601287585841&scope=bot
#

import discord
import os
import datetime
import psycopg2
import json
import codecs

from Utils import Configuration, \
    Characters, Jobs, Reputations, \
    Calendar, Twitters, Persistence_Utils, Annuary

import traceback
from apscheduler.schedulers.background import BackgroundScheduler


class CommandException(Exception):
    pass


annuary_path = "lotro_annuaire.xlsx"
local = True

DATABASE_URL = os.environ["DATABASE_URL"]
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]

if local:
    connection = psycopg2.connect("postgres://localhost", user="postgres", password="root", database="lotro")
else:
    connection = psycopg2.connect(DATABASE_URL, sslmode='require', database="lotro")

client = discord.Client()

persistentConfiguration = Configuration.PersistentConfiguration(connection, client)
persistentCharacters = Characters.PersistentCharacters(connection)
persistentJobs = Jobs.PersistentJobs(connection)
persistentReputations = Reputations.PersistentReputations(connection)
persistentCalendar = Calendar.PersistentCalendars(connection)
persistentTwitters = Twitters.PersistentTwitters(connection, persistentConfiguration, client)

persistentConfiguration.init_database()
persistentCharacters.init_database()
persistentJobs.init_database()
persistentReputations.init_database()
persistentCalendar.init_database()
persistentTwitters.init_database()

sched = BackgroundScheduler()


@sched.scheduled_job('interval', seconds=5)
def this_interval_is_not_working():
    print(".")


def ProcessSentences(text):
    result = text
    print("Process Sentences")
    print(text)
    while result.count("\"") != 0 and result.count("\"") % 2 == 0:
        first = result.find("\"")
        second = result[first + 1:].find("\"")
        old_sequence = result[first:first + second + 2]
        new_sequence = old_sequence.replace(" ", "_").replace("\"", "")
        # print("Sequence")
        # print(old_sequence)
        # print(new_sequence)
        # print("Sentence")
        # print(result)
        result = result.replace(old_sequence, new_sequence)
        # print(result)
    print(result)
    if result.count("\"") % 2 == 1:
        print("Process Sentences END FAILIG")
        raise CommandException()
    print("Process Sentences END")
    return result


def get_json(path):
    with open(path, "rb") as stream:
        return json.load(stream)


@client.event
async def on_member_join(member):
    guild_id = member.guild.id
    # if guild_id in new_member_channels:
    #    new_channel = client.get_channel(new_member_channels[guild_id])
    #    await new_channel.send("Bienvenue " + member.mention + " !")


help_json = get_json("help.json")
print("fichier d'aide")
print(help_json)


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.channel.type != discord.ChannelType.text:
        return
    if message.content.startswith('Legolas'):
        msg = ""
        channel = message.channel
        is_embed = False
        file = None

        words = message.content.split(' ')
        command_msg = "[" + str(message.guild) + "][" + channel.name + "][" + str(message.created_at) + "] '" + str(
            words) + "' from '" + message.author.name + "'"
        print(command_msg)

        try:
            this_character_thing = message.content.count("\"")
            if this_character_thing > 0:
                if this_character_thing % 2 == 1:
                    raise CommandException()
                words = ProcessSentences(message.content).split(' ')
            is_admin = message.author.name == message.guild.owner.name or persistentConfiguration.is_admin(
                message.author, message.guild.id)
            guild_id = message.guild.id

            if words[1] == "aide":
                entry = "/".join(words[1:])
                if entry in help_json:
                    is_embed = True
                    embed = discord.Embed(title="Commandes d'aide disponibles", color=0x37f23c)
                    for title in help_json[entry]:
                        embed.add_field(name=title, value=help_json[entry][title], inline=False)

            elif words[1] == "twitter":
                if words[2] == "list":
                    msg = ""
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

                elif words[2] == "filtre" and is_admin:
                    modified_channels = message.channel_mentions
                    twitter_channels = persistentTwitters.get_channels(words[3])
                    sentence = words[5].replace("_", " ")
                    if words[4] == "retirer":
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
                                msg += "Le filtre de transmission sur '%s' pour '%s' dans le salon '%s' a été retiré.\n" \
                                       % sentence, twitter_channel.username, channel_name
                    elif words[4] == "ajouter":
                        for modified_channel in modified_channels:
                            twitter_chnls = [twt_ch for twt_ch in twitter_channels if
                                             twt_ch.channel_id == modified_channel.id and twt_ch.username == words[3]]
                            dic_id = -1
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
                elif is_admin:
                    account = words[2]
                    action = words[3]
                    channels = message.channel_mentions
                    if action == "ajouter":
                        try:
                            dic = {"createdBy": message.author.name, "username": account}
                            twitter_account = Twitters.TwitterAccount.from_dict(dic)
                            persistentTwitters.add_account(twitter_account)
                        except psycopg2.errors.UniqueViolation:
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
                            msg += "'" + account + "' ne transmet plus les messages sur '" + channel.mention + "'\n"

            elif words[1] == "erreur" and is_admin:
                if words[2] == "list":
                    reports = [report for report in persistentConfiguration.get_reports() if
                               report.guild_id == channel.guild.id]
                    if len(reports) > 0:
                        msg = ", ".join(
                            [client.get_user(report.user_id).name for report in reports if
                             client.get_user(report.user_id) is not None])
                        if len(reports) == 1:
                            msg += " reçoit "
                        else:
                            msg += "reçoivent "
                        msg += "les rapports d'erreur."
                    else:
                        msg = "Pas de membres enregistrés pour recevoir les rapports d'erreur."
                elif words[2] == "ajouter":
                    if len(message.mentions) >= 1:
                        for member in message.mentions:
                            dic = {"createdBy": message.author.name, "guildId": guild_id, "userId": member.id}
                            report = Configuration.Report.from_dict(dic)
                            persistentConfiguration.add_report(report)
                        if len(message.role_mentions) > 1:
                            msg = "Membres ajoutés"
                        else:
                            msg = "Membre ajouté"
                        msg += " pour recevoir les rapports d'erreur."
                elif words[2] == "retirer":
                    if len(message.mentions) >= 1:
                        for member in message.mentions:
                            persistentConfiguration.remove_report(guild_id, member.id)
                        if len(message.mentions) > 1:
                            msg = "Membres retirés"
                        else:
                            msg = "Membre retiré"
                        msg += " de la liste de ceux qui recoivent les rapports d'erreur."

            elif words[1] == "admin" and not is_admin:
                msg = "Vous ne pouvez pas utiliser cette commande !"

            elif words[1] == "admin" and is_admin:
                if words[2] == "list":
                    admins = persistentConfiguration.get_admins(guild_id)
                    if len(admins) > 0:
                        msg = ", ".join([channel.guild.get_role(admin.role_id).name for admin in admins if
                                         channel.guild.get_role(admin.role_id) is not None])
                    else:
                        msg = "Pas de rôle enregistrés pour administrer le bot."
                elif words[2] == "ajouter":
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
                elif words[2] == "retirer":
                    if len(message.role_mentions) >= 1:
                        for role in message.role_mentions:
                            persistentConfiguration.remove_admin(guild_id, role.id)
                        if len(message.role_mentions) > 1:
                            msg = "Rôles retirés"
                        else:
                            msg = "rôle retiré"
                        msg += " des administrateurs du bot"
                elif words[2] == "nouveau":
                    if words[3] == "ajouter":
                        msg = "WIP"
                    elif words[3] == "retirer":
                        msg = "WIP"
                    elif words[3] == "list":
                        msg = "WIP"

            elif words[1] == "annuaire":
                annuary_modified = False
                if words[2] == "excel":
                    channel = message.author
                    with open(annuary_path, "rb") as annuaire_stream:
                        msg = "Voici l'annuaire en format .xlsx !"
                        file = discord.File(annuaire_stream)
                elif words[2] == "personnage":
                    if len(words) > 3:
                        dic = Characters.Character.process_creation(words[4:])
                        dic["createdBy"] = message.author.name
                        dic["updatedBy"] = message.author.name
                        dic["guildId"] = guild_id
                        character = Characters.Character.from_dict(dic)
                        can_modify_character = is_admin or persistentCharacters.get_creator(
                            character.name) == message.author.name
                        if words[3] == "ajouter":
                            try:
                                persistentCharacters.add_character(character)
                                msg = "Votre personnage a été ajouté !"
                            except psycopg2.IntegrityError:
                                if can_modify_character:
                                    persistentCharacters.update_character(character)
                                    msg = "Votre personnage a été mis à jour !"
                            annuary_modified = True
                        elif words[3] == "màj":
                            if can_modify_character:
                                persistentCharacters.update_character(character)
                                msg = "Votre personnage a été mis à jour !"
                                annuary_modified = True
                        elif words[3] == "retirer":
                            if is_admin or persistentCharacters.get_creator(words[4]) == message.author.name:
                                persistentCharacters.remove_character(words[4])
                                msg = "Votre personnage a été retiré !"
                                annuary_modified = True
                            else:
                                msg = "Vous ne possédez pas ce personnage !"
                        elif words[3] == "chercher":
                            dic = Characters.PersistentCharacters.process_query(words[4:])
                            dic["guildId"] = guild_id
                            characters = persistentCharacters.search_characters(dic)
                            msg = ",\n".join([repr(character) for character in characters])
                    else:
                        msg = ",\n".join(
                            [repr(character) for character in persistentCharacters.get_characters(guild_id)])
                        if msg == "":
                            msg = "Pas de personnages enregistrés !"
                elif words[2] == "métier":
                    dic = Characters.Character.process_creation(words[4:])
                    dic["createdBy"] = message.author.name
                    dic["updatedBy"] = message.author.name
                    dic["guildId"] = guild_id
                    character = Characters.Character.from_dict(dic)
                    can_modify_character = is_admin or persistentCharacters.get_creator(
                        character.name) == message.author.name
                    if words[3] == "ajouter":
                        msg = "WIP"
                    elif words[3] == "màj":
                        msg = "WIP"
                    elif words[3] == "retirer":
                        msg = "WIP"
                elif words[2] == "enclumes":
                    if words[3] == "ajouter":
                        msg = "WIP"
                    elif words[3] == "màj":
                        msg = "WIP"
                    elif words[3] == "retirer":
                        msg = "WIP"
                elif words[2] == "réputation":
                    if words[3] == "ajouter":
                        msg = "WIP"
                    elif words[3] == "màj":
                        msg = "WIP"
                    elif words[3] == "retirer":
                        msg = "WIP"
                    elif words[3] == "chercher":
                        msg = "WIP"
                if annuary_modified:
                    Annuary.storeAnnuary(annuary_path, characters=persistentCharacters.get_characters(guild_id))
            elif words[1] == "calendrier":
                if len(words) == 2:
                    date = datetime.datetime.today().timestamp()
                    events = persistentCalendar.get_events(guild_id, after=date)
                    if len(events) > 0:
                        is_embed = True
                        embed = discord.Embed(title="Calendrier")
                        for event in events:
                            embed.add_field(name=event.name.replace("_", " "), value=repr(event), inline=False)
                    else:
                        msg = "Pas d'évènements dans le calendrier !"
                else:
                    if words[2] == "prochain":
                        date = datetime.datetime.today().timestamp()
                        events = persistentCalendar.get_events(guild_id, after=date)
                        if len(events) > 1:
                            event = events[0]
                            is_embed = True
                            embed = discord.Embed(title="Calendrier")
                            embed.add_field(name=event.name.replace("_", " "), value=repr(event), inline=False)
                        else:
                            msg = "Pas d'évènements dans le calendrier !"
                    elif words[2] == "retirer" and is_admin:
                        msg = "Les évènements suivants ont été retirés :\n"
                        for name in words[3:]:
                            persistentCalendar.remove_event(name)
                            msg += name + ",\n"
                        msg = msg[:-2]
                    elif is_admin:
                        dic = Calendar.Event.process_creation(words[3:])
                        dic["createdBy"] = message.author.name
                        dic["updatedBy"] = message.author.name
                        dic["guildId"] = guild_id
                        print(dic)
                        _event = Calendar.Event.from_dict(dic)
                        if words[2] == "ajouter":
                            try:
                                persistentCalendar.add_event(_event)
                                msg = "Evènement ajouté !"
                            except psycopg2.errors.UniqueViolation:
                                msg = "Un évènement avec ce nom existe déjà"
                        elif words[2] == "màj":
                            persistentCalendar.update_event(_event)
                            msg = "Evènement mis à jour !"
            print("!")
            if msg != "" and not is_embed:
                await channel.send(msg, file=file)
            elif is_embed:
                await channel.send(embed=embed, file=file)
            else:
                await channel.send("Il semblerait que je ne puisse pas faire suivre votre requête !")
        except (IndexError, CommandException) as e:
            await channel.send("Il semblerait que je ne puisse pas faire suivre votre requête !")
        except Persistence_Utils.InitializationException:
            await channel.send("Votre demande ne suit pas le format attendu.")
        except psycopg2.errors.UniqueViolation:
            await channel.send("Une entrée existe déjà pour cet objet")
        except Exception as e:
            msg = "Erreur, l'administrateur et d'autres personnes ont été notifiées !"
            await message.channel.send(msg)

            msg = "[" + message.guild.name + "][ERROR]" + str(e)
            error_msg = msg + "\n" + traceback.format_exc() + "\ncaused by:" + command_msg
            await persistentConfiguration.warn_error(error_msg, message.guild.id)


@client.event
async def on_ready():
    print('------')
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')


client.run(DISCORD_TOKEN)
