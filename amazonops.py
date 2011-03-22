import os
import logging
from xml.dom import minidom
from django.utils import simplejson
from google.appengine.api import memcache

import bottlenose
import amazoncred
import models


def setup_amazon():
  return bottlenose.Amazon(amazoncred.ACCESS_KEY_ID, amazoncred.SECRET_ACCESS_KEY, amazoncred.ASSOCIATE_TAG)

def get_elem(node, name):
  elem = node.getElementsByTagName(name)
  if len(elem) > 0:
    return elem[0].firstChild.wholeText
  else:
    return ''
    
def get_item_details(item):
  item_details = {}
  item_details['asin'] = get_elem(item, 'ASIN')
  item_attrs = item.getElementsByTagName('ItemAttributes')[0]
  item_details['author'] = get_elem(item_attrs, 'Author')
  item_details['title'] = get_elem(item_attrs, 'Title')
  if len(item.getElementsByTagName('ListPrice')) > 0:
    item_details['price'] = item.getElementsByTagName('ListPrice')[0].getElementsByTagName('FormattedPrice')[0].firstChild.wholeText
  if len(item.getElementsByTagName('EditorialReviews')) > 0:
    item_details['review'] = item.getElementsByTagName('EditorialReviews')[0].getElementsByTagName('EditorialReview')[0].getElementsByTagName('Content')[0].firstChild.wholeText
  images = {}
  if len(item.getElementsByTagName('SmallImage')) > 0:
    images['small'] = item.getElementsByTagName('SmallImage')[0].getElementsByTagName('URL')[0].firstChild.wholeText
  if len(item.getElementsByTagName('MediumImage')) > 0:
    images['medium'] = item.getElementsByTagName('MediumImage')[0].getElementsByTagName('URL')[0].firstChild.wholeText
  if len(item.getElementsByTagName('LargeImage')) > 0:
    images['large'] = item.getElementsByTagName('LargeImage')[0].getElementsByTagName('URL')[0].firstChild.wholeText
  item_details['images'] = images
  return item_details

def lookup_book(asin):
  amazon = setup_amazon()
  response = amazon.ItemLookup(ItemId=asin, ResponseGroup='Medium')
  dom = minidom.parseString(response)
  item = dom.getElementsByTagName('Item')[0]
  return get_item_details(item)
      
def search_books(keywords):
  amazon = setup_amazon()
  response = amazon.ItemSearch(SearchIndex='Books', ResponseGroup='Medium', Keywords=keywords)
  dom = minidom.parseString(response)
  items = dom.getElementsByTagName('Item')
  items_json = []
  for item in items:
    items_json.append(get_item_details(item))
  return items_json
  
def find_similar_books(asin, book_details, book_graph, look_again=True):
  response = memcache.get('similar' + asin)
  if response is None:
    amazon = setup_amazon()
    response = amazon.SimilarityLookup(ItemId=asin, ResponseGroup='Medium')
    memcache.set('similar' + asin, response)
  dom = minidom.parseString(response)
  items = dom.getElementsByTagName('Item')
  asins = []
  book_graph[asin] = []
  for item in items:
    item_details = get_item_details(item)
    item_asin = item_details['asin']
    book_graph[asin].append(item_asin)
    book_details[item_asin] = item_details
    if look_again:
      find_similar_books(item_asin, book_details, book_graph, look_again=False)
    
def calculate_books_web(asin):
  # we want a data structure of the ASIN->ASIN nodes
  # we also want one hash with all the item details
  book_details = {}
  book_graph = {}
  # put parent node in items
  book_details[asin] = lookup_book(asin)
  find_similar_books(asin, book_details, book_graph, look_again=True)
  web = {'book_details': book_details, 'book_graph': book_graph, 'asin': asin}
  book_web = models.BookWeb(key_name=asin)
  book_web.title = book_details[asin]['title']
  book_web.json = simplejson.dumps(web)
  book_web.put()