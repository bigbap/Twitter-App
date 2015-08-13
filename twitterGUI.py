__author__ = 'User'

import tkinter
import sqlite3
import tweepy
import json
import threading
import webbrowser
import sys
import time
import os

class Listener(tweepy.StreamListener):
    def on_data(self, data):
        try:
            data = json.loads(data)

            tweet = data["text"]
            id = data["id_str"]
            lang = data["lang"]

            if lang == "en":
                conn = sqlite3.connect(DB)
                c = conn.cursor()
                try:
                    c.execute('INSERT INTO tweets (id, tweet) VALUES (?, ?)', (id, tweet))
                    conn.commit()
                except Exception as e:
                    print(e)
                    pass
                conn.close()
        except Exception as e:
            print(str(e) + "\n")
        finally:
            return True

    def on_error(self, status):
        print("error: " + str(status))

class twitterGUI(tkinter.Tk):
    def __init__(self,parent):
        tkinter.Tk.__init__(self,parent)

        self.wm_protocol('WM_DELETE_WINDOW', self.on_exit)

        self.parent = parent
        self.initialize()

    def initialize(self):
        self.frame=tkinter.Frame()
        self.contentFrame=tkinter.Frame(self.frame, bg="white")
        self.frame.grid()
        self.resizable(False,False)

        self.setupGrid()

    def setupGrid(self):
        for widget in self.contentFrame.winfo_children():
            widget.destroy()

        self.contentFrame.grid()

        tweets = self.getTweets()
        row = 1
        label = tkinter.Label(self.contentFrame, anchor="w", fg="white", bg="grey", text="Tweet ID", padx=1, pady=1)
        label.grid(column=0, row=0, sticky='EW')
        label = tkinter.Label(self.contentFrame, anchor="w", fg="white", bg="grey", text="Tweet URL", padx=1, pady=1)
        label.grid(column=1, row=0, sticky='EW')
        label = tkinter.Label(self.contentFrame, anchor="w", fg="white", bg="grey", text="Tweet", padx=1, pady=1)
        label.grid(column=2, row=0, sticky='EW')
        label = tkinter.Label(self.contentFrame, anchor="w", fg="white", bg="grey", text="Action", padx=1, pady=1)
        label.grid(column=3, row=0, columnspan=2, sticky='EW')
        for record in tweets:
            try:
                tweet = record['tweet'].encode('utf-8')
            except Exception as e:
                tweet = e
            id = record['id']
            url = 'http://www.twitter.com/user/status/' + str(id)
            data = {'id':id}

            label = tkinter.Label(self.contentFrame, anchor="w", fg="black", bg="white", text=id, padx=3, pady=3)
            label.grid(column=0, row=row, sticky='EW')
            label = tkinter.Label(self.contentFrame, anchor="w", fg="blue", bg="white", text=url, padx=3, pady=3)
            label.bind("<Button-1>", lambda event, arg=data: self.openLink(event, arg))
            label.grid(column=1, row=row, sticky='EW')
            label = tkinter.Label(self.contentFrame, anchor="w", fg="black", bg="white", text=tweet, padx=3, pady=3)
            label.grid(column=2, row=row, sticky='EW')
            button = tkinter.Button(self.contentFrame, text=u"Approve")
            button.bind("<ButtonPress-1>", lambda event, arg=data: self.onApprove(event, arg))
            button.grid(column=3, row=row, padx=3, pady=3)
            button = tkinter.Button(self.contentFrame, text=u"Disprove")
            button.bind("<ButtonPress-1>", lambda event, arg=data:  self.onDisprove(event, arg))
            button.grid(column=4, row=row, padx=3, pady=3)
            row += 1

        self.contentFrame.grid_columnconfigure(0,weight=1)

    def onApprove(self, event, arg):
        id = arg['id']
        conn = sqlite3.connect(DB)
        c = conn.cursor()

        try:
            c.execute('UPDATE tweets SET approved = 1 WHERE id = ?', (id,))
            print(id, " approved")

        except Exception as e:
            print(e)
            pass

        conn.commit()
        conn.close()
        self.setupGrid()

    def onDisprove(self, event, arg):
        id = arg['id']
        conn = sqlite3.connect(DB)
        c = conn.cursor()

        try:
            c.execute('UPDATE tweets SET processed = 1 WHERE id = ?', (id,))
            print(id, " disproved")

        except Exception as e:
            print(e)
            pass

        conn.commit()
        conn.close()
        self.setupGrid()

    def getTweets(row=0):
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        rows = []
        try:
            c.execute('SELECT id, tweet, dtadded, processed FROM tweets WHERE processed = 0 and approved = 0 ORDER BY id DESC LIMIT 20')
            rows = c.fetchall()

        except Exception as e:
            print(e)
            pass

        conn.commit()
        conn.close()

        return rows

    def openLink(self, event, id):
        webbrowser.open_new(r'http://www.twitter.com/user/status/' + str(id['id']))

    def on_exit(self):
        """When you click to exit, this function is called"""
        threading.Timer(0, exitApp).start()
        self.destroy()

class ProcessTweet():
    def __init__(self):
        self.running = True

        self.processTimer = threading.Timer(5, self.run)
        self.processTimer.start()

    def run(self):
        limitInterval = 15*60 #send a batch of 20 tweets every 15 minutes
        tweetInterval = 0 #send 1 tweet every 30 seconds
        tweetsProcessed = 0 #current number of tweets sent for this 15 minute interval
        while self.running:
            if tweetsProcessed < 20 and limitInterval > 0 and tweetInterval <= 0:
                print("processing...")
                conn = sqlite3.connect(DB)
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                try:
                    c.execute('SELECT id, tweet, dtadded, processed FROM tweets WHERE processed = 0 AND approved = 1 ORDER BY dtadded ASC LIMIT 1')
                    for row in c.fetchall():
                        id = row['id']
                        try:
                            url = 'http://www.twitter.com/user/status/' + str(id)
                            tweet = row['tweet'].encode('utf-8').decode('utf-8')
                            print(tweet)
                            print(url)
                            api.retweet(id)
                            c.execute('UPDATE tweets SET processed = 1 WHERE id = ?', (id,))
                            print("tweet processed.", '\n')
                            tweetsProcessed += 1
                            break
                        except tweepy.TweepError as e:
                            print("Can't process tweet. ", e, '\n')

                except Exception as e:
                    print(e)
                    pass

                conn.commit()
                conn.close()

            #update intervals
            tweetInterval -= 1
            limitInterval -= 1

            if tweetInterval < 0:
                tweetInterval = 30
            if limitInterval < 0:
                limitInterval = 60*15

            time.sleep(1)

    def destroy(self):
        self.running = False
        self.processTimer.cancel()

def exitApp():
    print("exiting...")
    twitterStream.disconnect()
    processTweet.destroy()
    sys.exit(0)

processTweet = ''
twitterStream = ''

CURR_DIR = os.path.dirname(__file__) + '\\'
DB = CURR_DIR + 'twitter.db'

if __name__ == "__main__":
    #setup db
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    try:
        c.execute("CREATE TABLE if not exists tweets (id int PRIMARY KEY NOT NULL, tweet text, dtadded default CURRENT_TIMESTAMP NOT NULL, processed bit default 0 NOT NULL, approved bit default 0 NOT NULL)")
        conn.commit()
    except Exception as e:
        print(e)
        pass
    conn.close()

    dataFile = open(CURR_DIR + 'data.json')
    dataStr = dataFile.read()
    dataJson = json.loads(dataStr)
    dataFile.close()

    keywords = []
    users = []
    try:
        for key in dataJson['keywords'].keys():
            keywords.append(dataJson['keywords'][key])

        for user in dataJson['users'].keys():
            users.append(dataJson['users'][user])
    except Exception as e:
        exit()

    authFile = open(CURR_DIR + '..\\twitterAuth.json')
    authStr = authFile.read()
    authJson = json.loads(authStr)
    authFile.close()
    ckey = authJson['ckey']
    csecret = authJson['csecret']
    atoken = authJson['atoken']
    asecret = authJson['asecret']

    try:
        auth = tweepy.OAuthHandler(ckey, csecret)
        auth.set_access_token(atoken, asecret)

        api = tweepy.API(auth)

        twitterStream = tweepy.Stream(auth=api.auth, listener=Listener())
        twitterStream.filter(track=keywords, async=True)

        processTweet = ProcessTweet()
    except Exception as e:
        print(e)

    #setup GUI
    app = twitterGUI(None)
    app.title('Twitter APP')
    app.mainloop()
