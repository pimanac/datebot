#!/usr/bin/env python3
# datebot.py

import praw
from prawoauth2 import PrawOAuth2Mini as pmini
import requests
import os
import math
from collections import deque
import time
import re
import json
import datetime
from dateutil import parser
import urllib


class bot():

   completed = []

   def __init__(self):
      print("Loading Config")
      self.__config__()

      print("Ready")

   def __config__(self):
      with open('config.json','r') as f:
         self.config = json.load(f);

   def reddit_connect(self):
      self.r = praw.Reddit('a tool to check submission dates')
      # scope_list = ['modflair','identity','modposts','wikiread','modwiki','read', 'modlog', 'privatemessages', 'submit']
      #scope_list = ['modflair','identity','modposts','read']
      #self.oauth = pmini(self.r, app_key=self.config['reddit']['key'],
      #                  app_secret=self.config['reddit']['secret'],
      #                  access_token=self.config['reddit']['access_token'],
      #                  refresh_token=self.config['reddit']['refresh_token'],
      #                  scopes=scope_list)
      #self.user = self.r.get_me()

      self.r.login(self.config['reddit']['username'],self.config['reddit']['password'])

      self.subreddit = self.r.get_subreddit(self.config['reddit']['subreddit'])

      self.subreddit = self.config['reddit']['subreddit']

   def process_submissions(self):
      print("Connecting")
      self.reddit_connect()

      for submission in self.r.get_subreddit(self.subreddit).get_new(limit=self.limit):
         report = False
         #Avoid duplicate work
         if submission.fullname in self.completed:
            continue

         print("checking "+submission.title)

         if submission.is_self:
            print("   is self")
            continue

         if submission.approved_by is not None:
            print("   already approved")
            continue

         content_creation = self.get_create_date(submission)

         if content_creation < 0:
            print("   Can't determine the submission date")
            continue

         #Get the reddit submission timestamp
         post_creation = submission.created_utc

         #Find content age, in days
         age = math.floor((post_creation - content_creation) / (60 * 60 * 24))

         #Pass on submissions that are new enough
         if age <= 31:
            print("   age is ok")
            continue
         else:
            print("   age is BAD!!!!!")
            self.on_outdated(submission,report)

         try:
            report = false
            self.on_outdated(submission,report)
         except:
            print("something went wrong")
            # pass

         self.completed += submission.fullname

   def get_create_date(self,submission):
      # youtube?
      if re.match('^(https?\:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$',submission.url):
         print("matches youtube")
         try:
            return self.get_youtube_age(submission)
         except:
            # raise
            pass

      # nytimes?
      if "nytimes.com" in submission.domain:
         print("matches nytimes")
         try:
            return self.get_nytimes_age(submission)
         except:
            #raise
            pass


      # http headers?
      try:
         print("checking headers")
         return self.get_http_header_age(submission)
      except:
         pass

      # url parsing?
      try:
         print("checking urls")
         return self.get_url_age(submission)
      except:
         # raise
         pass

      # finally, embedly because we only have so many requests per month for free
      try:
         print("checking embed.ly")
         return self.get_embedly_age(submisison)
      except:
         pass

      return -1

   def get_youtube_age(self,submission):
      # return the videos published epoch

      # get the video id
      print("submission.url")
      vid = parse_qs(urlparse(submission.url).query)["v"][0]
      key = self.config['youtube']['key']

      # grab the date
      uri="https://www.googleapis.com/youtube/v3/videos?id={0}&part=snippet&key={1}".format(vid,key)
      h={'Accept':'application/json','user-agent':'datebot'}

      data = requests.get(uri,h).text
      print("   got youtube data")

      jsondate = json.loads(data)['items'][0]['snippet']['publishedAt']
      d = parser.parse(jsondate)
      print("      extracted youtube date")
      return time.mktime(d.timetuple())

   def get_nytimes_age(self,submission):
      # return the article published epoch

      # get the video id
      link = urllib.quote_plus(submission.url)
      key = self.config['nytimes']['newswire']['key']

      # grab the date
      uri="http://api.nytimes.com/svc/news/v3/content.json?url={0}&api-key={1}".format(link,key)
      h={'Accept':'application/json','user-agent':'datebot'}

      data = requests.get(uri,h).text
      print("   got nytimes data")

      try:
         jsondate = json.loads(data)['results'][0]['created_date']
         d = parser.parse(jsondate)
         print("      extracted nytimes date")
         return time.mktime(d.timetuple())
      except:
         return -1

   def get_http_header_age(self,submission):
      headers = { 'user-agent':'datebot'}
      content = requests.get(submission.url, headers=headers)
      print("   got http headers")
      timestamp = time.strptime(content.headers['Last-Modified'], '%a, %d %b %Y %H:%M:%S %Z')
      content_creation = int(time.mktime(timestamp))
      print("      timestamp extracted from headers")
      return content_creation

   def get_url_age(self,submission):
      # see if we can get the date from the url
      regex = re.search('^http[s]?://.*/([\d]{4})/([\d]{2})/([\d]{2})/.*$',submission.url)
      year=regex.group(1)
      month=regex.group(2)
      day=regex.group(3)
      print("   url regex match")
      # this is iffy because we don't know if the url is utc.  It's close enough for
      # government work - make a human review.
      dt = datetime.datetime(int(year),int(month),int(day),0,0,0)
      t = dt.timetuple()
      print("      got date from url")
      return time.mktime(t)

   def get_embedly_age(self,submission):
      uri = 'http://api.embed.ly/1/extract'
      param = { 'url':submission.url,'key':self.config['embedly']['key']}
      content = requests.get(uri,headers={'user-agent':'pimanac datebot'})

      try:
         content_creation = data.json()['published']
         if content_creation == None:
            content_creation = -1
            return content_creation

         content_creation = content_creation / 1000
      except:
         content_creation = -1

      return content_creation


   # this is where all the fun happens
   def on_outdated(self,submission,report):

      submission.remove()


      message = (
         "Hi, " + submission.author.name + ".  Thank you for participating in /r/Politics. However, your submission has been removed for the following reason:\n\n"
         "* [Out of Date](http://www.reddit.com/r/politics/wiki/rulesandregs#wiki_the_.2Fr.2Fpolitics_on_topic_statement): "
         "/r/politics is for **current** US political news and information that has been published within the last 31 days. \n\n"
         "*I am a bot.  Sometimes I make a mistakes.  Please [Message the moderators](https://www.reddit.com/message/compose?to=/r/" + submission.subreddit.display_name + ""
         "&subject=Question regarding the removal of this submission by /u/" + submission.author.name + "&message=I have a question "
         "regarding the removal of this [submission](" + submission.permalink + "\)) if you feel this was in error.  Do not reply to this message because directly.*"

      )

      submission.add_comment(message).distinguish()

      submission.set_flair(flair_text="Out of Date")


      print("     " + submission.title + "   :    Out of date")



   def run(self):
      self.limit=1000
      while True:
         print("processing submissions")
         self.process_submissions()
         print("Sleeping")
         time.sleep(10)
         self.limit=50


if __name__=='__main__':
    datebot=bot()
    datebot.run()
