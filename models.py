from datetime import datetime
import time
import re
import logging
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api.labs import taskqueue
from google.appengine.ext import deferred
from google.appengine.api import users
from google.appengine.ext.db import Key

# Use ASIN as the key
class BookWeb(db.Model):
  title = db.StringProperty()
  json = db.TextProperty()
  date = db.DateTimeProperty(auto_now_add=True)
  views = db.IntegerProperty(default=1)
  
  def to_dict(self):
    return {'asin': self.key().name(),
            'views': self.views,
            'title': self.title}

  def get_views(self):
   views = self.views
   cached_views = memcache.get('views-' + str(self.key().id()), self.key().kind())
   if cached_views:
     views += cached_views
   return views

  @classmethod
  def flush_views(cls, id):
   book_web = cls.get_by_key_name(id)
   if not book_web:
     book_web = cls()

   # Get the current value
   value = memcache.get('views-' + str(id), cls.kind())
   # Subtract it from the memcached value
   if not value:
     return

   memcache.decr('views-' + str(id), int(value), cls.kind())

   # Store it to the counter
   book_web.views += int(value)
   book_web.put()

  @classmethod
  def incr_views(cls, id, interval=5, value=1):
   """Increments the named counter.

   Args:
     name: The name of the counter.
     interval: How frequently to flush the counter to disk.
     value: The value to increment by.
   """
   memcache.incr('views-' + str(id), delta=value, namespace=cls.kind(), initial_value=0)
   interval_num = get_interval_number(datetime.now(), interval)
   task_name = '-'.join([cls.kind(), re.sub('[^a-zA-Z0-9-]*', '', str(id)), 'views', str(interval), str(interval_num)])
   try:
     deferred.defer(cls.flush_views, id, _name=task_name)
   except (taskqueue.TaskAlreadyExistsError, taskqueue.TombstonedTaskError, taskqueue.TransientError):
     pass

def get_interval_number(ts, duration):
   """Returns the number of the current interval.

   Args:
     ts: The timestamp to convert
     duration: The length of the interval
   Returns:
     int: Interval number.
   """
   return int(time.mktime(ts.timetuple()) / duration)
