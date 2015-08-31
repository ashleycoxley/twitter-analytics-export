import requests
import re
import time
import json
import datetime
import urllib
import os
import logging
import cStringIO
import codecs
import pytz
import urlparse
import httplib
import csv


def get_date_range(no_days):
    """Return date strings in UTC format. The data is returned as 
    (start, end)
    with the end date being today and the begin date being 'no_days' prior.
    Twitter's maximum total days is 90."""

    today = datetime.datetime.utcnow()
    prior = today - datetime.timedelta(days=no_days)

    def add_milliseconds(timestamp): # arbitrary since millisecond precision not necessary
        milli_ts = int(time.mktime(timestamp.timetuple()) * 1000)
        milli_ts = str(milli_ts)
        return milli_ts

    start = add_milliseconds(prior)
    end = add_milliseconds(today)

    return (start, end)



def get_tweet_data(session, start_time, end_time, user_agent):
    """Complete the process behind clicking 'Export data' at 
    https://analytics.twitter.com/user/USERNAME/tweets
    Data is returned as a raw string containing comma-separated data"""

    export_url = "https://analytics.twitter.com/user/USERNAME/tweets/export.json"
    bundle_url = "https://analytics.twitter.com/user/USERNAME/tweets/bundle"

    export_data = {
        'start_time' : end_time,
        'end_time' : start_time,
        'lang' : 'en'
    }
    querystring = '?' + urllib.urlencode(export_data)

    status = 'Pending'
    counter = 0
    while status == 'Pending':
        attempt = session.post(export_url + querystring, headers=user_agent)
        status_dict = json.loads(attempt.text)
        status = status_dict['status']
        counter += 1
        print counter, status
        time.sleep(5)

    csv_header = {'Content-Type': 'application/csv',
              'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
              'Accept-Encoding': 'gzip, deflate, sdch',
              'Accept-Language': 'en-US,en;q=0.8',
              'Upgrade-Insecure-Requests': '1',
              'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36'}

    data_req = session.get(bundle_url + querystring, headers=csv_header)
    print "data_req response: ", data_req.status_code
    return data_req.text


def format_data(data_string):
    """Transform raw data string into list-of-lists format"""
    lines = data_string.split('\"\n\"')
    split_data = [re.split(r"\"\s*,\s*\"", line) for line in lines]

    return split_data


def get_filename(f_path, start_time, end_time):
    """Build descriptive filename for CSV"""
    f_name = 'twitter_data_' + start_time + '_' + end_time + '.csv'
    full_path = f_path + f_name

    return full_path



class UnicodeWriter: # grabbed from Python's csv module docs
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)



if __name__ == '__main__':
    # variables
    user = 'USERNAME'
    pw = 'PASSWORD'
    no_days = 60
    f_path = '/path/to/desired/csv_directory/'

    tw_url = "https://twitter.com/"
    session = requests.session()
    first_req = session.get(tw_url)

    auth_token_str = re.search(r'<input type="hidden" value="([a-zA-Z0-9]*)" name="authenticity_token"\>',
          first_req.text)
    authenticity_token = auth_token_str.group(1)

    login_url = 'https://twitter.com/sessions'
    user_agent = {'User-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36'}
    
    payload = {
        'session[username_or_email]' : user,
        'session[password]' : pw,
        'remember_me' : '1',
        'return_to_ssl' : 'true',
        'scribe_log' : None,
        'redirect_after_login':'/',
        'authenticity_token': authenticity_token
    }

    login_req = session.post(login_url, data=payload, headers=user_agent)
    print "login_req response: ", login_req.status_code

    start_time, end_time = get_date_range(no_days)
    data_string = get_tweet_data(session, start_time, end_time, user_agent)

    split_data = format_data(data_string)
    outfile = get_filename(f_path, start_time, end_time)
    
    with open(outfile, 'w') as f:
        writer = UnicodeWriter(f)
        for line in split_data:
            writer.writerow(line)

    print "CSV downloaded: ", outfile


