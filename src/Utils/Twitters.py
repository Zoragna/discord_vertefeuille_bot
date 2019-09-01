import asyncio

from Utils.Persistence_Utils import *

import os
import tweepy
import discord
import datetime
import traceback
from typing import List

TWITTER_CONSUMER_KEY = os.environ["TWITTER_CONSUMER_KEY"]
TWITTER_CONSUMER_SECRET = os.environ["TWITTER_CONSUMER_SECRET"]
TWITTER_ACCESS_TOKEN = os.environ["TWITTER_ACCESS_TOKEN"]
TWITTER_ACCESS_SECRET_TOKEN = os.environ["TWITTER_ACCESS_SECRET_TOKEN"]


class TwitterAccount(Element):
    rows = [("createdBy", str), ("username", str)]

    def __init__(self, creator, username):
        self.created_by = creator
        self.username = username

    @classmethod
    def from_dict(cls, dic):
        if TwitterAccount.validate(dic, TwitterAccount.rows):
            return cls(dic["createdBy"], dic["username"])
        raise InitializationException()


class TwitterChannel(Element):
    request_rows = [("createdBy", str), ("username", str), ("channelId", int)]
    response_rows = [("createdBy", str), ("username", str), ("channelId", int), ("id", int)]

    def __init__(self, creator, username, channel, _id=-1):
        self.created_by = creator
        self.username = username
        self.channel_id = channel
        self.id = _id

    @classmethod
    def from_dict(cls, dic):
        if TwitterChannel.validate(dic, TwitterChannel.response_rows):
            return cls(dic["createdBy"], dic["username"], dic["channelId"], dic["id"])
        elif TwitterChannel.validate(dic, TwitterChannel.request_rows):
            return cls(dic["createdBy"], dic["username"], dic["channelId"])
        raise InitializationException()


class TwitterFilter(Element):
    rows = [("createdBy", str), ("updatedBy", str), ("id", int), ("sentence", str)]

    def __init__(self, creator, updator, _id, sentence):
        self.created_by = creator
        self.updated_by = updator
        self.twitter_channel_id = _id
        self.sentence = sentence

    @classmethod
    def from_dict(cls, dic):
        if TwitterFilter.validate(dic, TwitterFilter.rows):
            return cls(dic["createdBy"], dic["updatedBy"], dic["id"], dic["sentence"])
        raise InitializationException()


class PersistentTwitters(Persistent):

    def init_database(self):
        self.init_filters_database()
        self.init_channels_database()
        self.init_accounts_database()

    def __init__(self, connection, configuration, client):
        super().__init__(connection)
        self.client = client
        self.auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
        self.auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET_TOKEN)
        self.api = tweepy.API(self.auth)
        self.twitter_listener = TwitterListener(self, configuration, self.client)
        self.twitter_stream = tweepy.Stream(auth=self.api.auth, listener=self.twitter_listener)

    def init_accounts_database(self):
        self.write('''CREATE TABLE IF NOT EXISTS TwitterAccounts (
                CreatedBy text NOT NULL,
                Username varchar(100) PRIMARY KEY );
                ''', ())
        self.follows = [str(self.api.get_user(twitter_account.username).id) for twitter_account in self.get_accounts()]
        self.twitter_stream.filter(follow=self.follows, is_async=True)

    def add_account(self, twitter_account: TwitterAccount) -> None:
        self.write('''INSERT INTO TwitterAccounts (CreatedBy, Username) VALUES (%s, %s)''',
                   (twitter_account.created_by, twitter_account.username))

    def remove_account(self, username):
        twitter_channel_ids = self.get_channel_ids(username)
        for twitter_channel_id in twitter_channel_ids:
            self.remove_filter(twitter_channel_id)
        self.remove_channel(username)
        self.write('''DELETE FORM TwitterAccounts WHERE Username=%s''', username)

    def get_accounts(self, username=None):
        if username is None:
            results = self.read("SELECT * FROM TwitterAccounts", ())
        else:
            results = self.read('''SELECT * FROM TwitterAccounts WHERE Username="%s"''', username)
        accounts = []
        for result in results:
            accounts.append(TwitterAccount(result[0], result[1]))
        return accounts

    def init_channels_database(self):
        self.write('''CREATE TABLE IF NOT EXISTS TwitterChannels ( 
        CreatedBy text NOT NULL,
        Username varchar(100),
        Channel bigint NOT NULL,
        Id SERIAL,
        PRIMARY KEY (Username, Channel));''', ())

    def add_channel(self, twitter_channel: TwitterChannel):
        self.write(
            '''INSERT INTO TwitterChannels (CreatedBy, Username, Channel) VALUES (%s, %s, %s)''',
            (twitter_channel.created_by, twitter_channel.username, twitter_channel.channel_id))
        results = self.read('''SELECT * FROM TwitterChannels WHERE Username=%s AND Channel=%s''',
                            (twitter_channel.username, twitter_channel.channel_id))
        return results[0][3]

    def remove_channel(self, username, channel_id=None):
        if channel_id is None:
            self.write('''DELETE FROM TwitterChannels WHERE Username=%s''', username)
        else:
            self.write('''DELETE FROM TwitterChannels WHERE Username=%s AND Channel=%s''', (username, channel_id))

    def get_channels(self, username=None) -> List[TwitterChannel]:
        if username is None:
            results = self.read("SELECT * FROM TwitterChannels", ())
        else:
            results = self.read('''SELECT * FROM TwitterChannels WHERE Username=%s''', username)
        channels = []
        for result in results:
            channels.append(TwitterChannel(result[0], result[1], result[2], result[3]))
        return channels

    def get_channel_ids(self, username):
        results = self.read('''SELECT Id FROM TwitterChannels WHERE Username="%s"''', username)
        ids = []
        for result in results:
            ids.append(result[0])
        return ids

    def init_filters_database(self):
        self.write('''CREATE TABLE IF NOT EXISTS TwitterFilters (
        CreatedBy text NOT NULL,
        UpdatedBy text NOT NULL,
        Id integer NOT NULL,
        Sentence varchar(300),
        PRIMARY KEY(Id, Sentence)); ''', ())

    def add_filter(self, twitter_filter: TwitterFilter):
        self.write('''INSERT INTO TwitterFilters (CreatedBy, UpdatedBy, Id, Sentence) VALUES (%s, %s, %s, %s) \
                   ON CONFLICT (Id, Sentence) DO UPDATE SET UpdatedBy=%s, Sentence=%s''',
                   (twitter_filter.created_by, twitter_filter.updated_by,
                    twitter_filter.twitter_channel_id, twitter_filter.sentence,
                    twitter_filter.updated_by, twitter_filter.sentence))

    def remove_filter(self, twitter_channel_id, sentence=None):
        if sentence is None:
            self.write("DELETE FROM TwitterFilters WHERE Id=%s", twitter_channel_id)
        else:
            self.write('''DELETE FROM TwitterFilters WHERE Id=%s AND Sentence=%s''', (twitter_channel_id, sentence))

    def get_filters(self, twitter_id=None):
        if twitter_id is None:
            results = self.read("SELECT * FROM TwitterFilters", ())
        else:
            results = self.read("SELECT * FROM TwitterFilters WHERE Id=%s", twitter_id)
        filters = []
        for result in results:
            filters.append(TwitterFilter(result[0], result[1], result[2], result[3]))
        return filters

    def update_filter(self, twitter_filter: TwitterFilter):
        self.write('''UPDATE TwitterFilters SET UpdatedBy=%s, Sentence=%s WHERE Id=%s''',
                   (twitter_filter.updated_by, twitter_filter.sentence, twitter_filter.twitter_channel_id))


class TwitterListener(tweepy.StreamListener):

    def __init__(self, twitter, configuration, client):
        super().__init__()
        self.persistentTwitters = twitter
        self.persistentConfiguration = configuration
        self.client = client

    def on_status(self, status: tweepy.Status):

        status_text = status.text
        status_json = status._json
        status_screen_name = status.user.screen_name
        status_name = status.user.name
        status_image_url = status.user.profile_image_url_https
        print("==>" + status_text)
        if status.in_reply_to_status_id is None:
            if "retweeted_status" not in status_json:
                embed = discord.Embed(title="@" + status_screen_name,
                                      url="https://twitter.com/" + status_screen_name, description=status_text)
            else:
                retweet = status.retweeted_status
                embed = discord.Embed(title="@" + retweet.user.screen_name,
                                      url="https://twitter.com/" + retweet.user.screen_name, description=retweet.text)
            embed.set_author(name=status_name, icon_url=status_image_url)
            if "media" in status_json["entities"]:
                first_media = status_json["entities"]["media"][0]
                embed.set_thumbnail(url=first_media["media_url"])
            embed.set_footer(text="Twitter",
                             icon_url="http://goinkscape.com/wp-content/uploads/2015/07/twitter-logo-final.png")

            twitter_accounts = self.persistentTwitters.get_accounts_with_name(status_screen_name)
            if len(twitter_accounts) == 0:
                print("[" + str(
                    datetime.datetime.today()) + "] No account registered with name '" + status_screen_name + "'")
                return

            twitter_account = twitter_accounts[0]
            username = twitter_account.username

            channel_ids = self.persistentTwitters.get_channel_ids(username)
            for channel_id in channel_ids:
                twitter_channel = self.client.get_channel(channel_id)
                try:
                    if self.filter_tweet(channel_id, twitter_channel, embed.description):
                        coro = twitter_channel.send("@everyone", embed=embed)
                        fut = asyncio.run_coroutine_threadsafe(coro, self.client.loop)
                        fut.result()
                except discord.HTTPException:
                    msg = "[" + str(datetime.datetime.today()) + "][" + twitter_channel.guild.name + "]"
                    msg += "Could not sent '" + status_text + "' from '" + status_screen_name + "'"
                    msg += " on channel '" + twitter_channel.name + "'"
                    error_msg = msg + "\n" + traceback.format_exc()

                    coroutine = self.persistentConfiguration.warn_error(error_msg, twitter_channel.guild.id)
                    future = asyncio.run_coroutine_threadsafe(coroutine, self.client.loop)
                    future.result()

    def on_error(self, status_code):
        if status_code == 420:
            return False

    def filter_tweet(self, twitter_id, channel, text):
        twitter_filters = self.persistentTwitters.get_filters(twitter_id, channel.id)
        for twitter_filter in twitter_filters:
            if twitter_filter.sentence in text:
                return True
        return len(twitter_filters) == 0
