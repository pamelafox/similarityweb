import os
import random
from xml.dom import minidom

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api.labs import taskqueue
from google.appengine.ext import deferred

import jinja2
import webapp2  
import json

import amazoncred
import amazonops
import models


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)
  

def is_debug():
  if os.environ['SERVER_SOFTWARE'].startswith('Dev'):
    return True
  else:
    return False
   
 
class BasePage(webapp2.RequestHandler):

  def get(self):
    page = memcache.get(self.get_filename())
    if is_debug(): 
      page = None
    if page is None:
      template = JINJA_ENVIRONMENT.get_template('/templates/%s' % self.get_filename())
      page = template.render(self.get_template_values())
      memcache.set(self.get_filename(), page, 60*1)
    self.response.out.write(page)

  def post(self):
    self.get()
    
  def get_template_values(self):
    return {}
    
class IndexPage(BasePage):
  def get_filename(self):
    return 'index.html'


class BookWebPage(BasePage):
  def get_filename(self):
    return 'web.html'
    
    
class RecentPage(BasePage):
  def get_filename(self):
    return 'recent.html'


class PopularPage(BasePage):
  def get_filename(self):
    return 'popular.html'


class BookWebsService(webapp2.RequestHandler):
  def get(self):
    order = self.request.get('order')
    num = self.request.get('num')
    webs_str = memcache.get(order + num)
    if is_debug():
      webs_str = None
    if webs_str is None:
      num = int(num)
      if order == '-views' and num < 5: #popular
        webs = models.BookWeb.all().order(order).fetch(40)
        random.shuffle(webs)
        webs = webs[0:num]
      else:
        webs = models.BookWeb.all().order(order).fetch(num)
      webs_str = json.dumps([w.to_dict() for w in webs])
      memcache.set(order, webs_str, 60)
    # Might change popular to just be last week/day/etc
    self.response.out.write(webs_str)
  
class BookSearchService(webapp2.RequestHandler):
  def get(self):
    keywords = self.request.GET.get('keywords', 'fox')
    result = amazonops.search_books(keywords)
    self.response.headers['Content-Type'] = 'application/json'
    self.response.out.write(json.dumps(result))
 
   
class BookWebService(webapp2.RequestHandler):
  def get(self):
    asin = self.request.GET.get('asin', '192913214X')
    book_web_str = memcache.get('bookweb' + asin)
    if book_web_str is None:
      book_web = models.BookWeb.get_by_key_name(asin)
      if book_web is None:
        #amazonops.calculate_books_web(asin)
        deferred.defer(amazonops.calculate_books_web, asin, _countdown=0)
        book_web_str = '{"status": "deferred"}'
      else:
        book_web_str = book_web.json
        memcache.set('bookweb' + asin, book_web_str)
        models.BookWeb.incr_views(asin)
    else:
      models.BookWeb.incr_views(asin)
    self.response.headers['Content-Type'] = 'application/json'
    self.response.out.write(book_web_str)


app = webapp2.WSGIApplication([('/', IndexPage),
                               ('/recent', RecentPage),
                               ('/popular', PopularPage),
                               (r'/[a-zA-Z0-9]{10}', BookWebPage),
                               ('/service/bookweb', BookWebService),
                               ('/service/bookwebs', BookWebsService),
                               ('/service/booksearch', BookSearchService),
                              ], debug=True)

