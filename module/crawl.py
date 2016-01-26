#!/usr/bin/env python
# coding:utf8

import redis
import time
import threading
import urllib2
import random
from bs4 import BeautifulSoup
import sys
reload(sys)
sys.setdefaultencoding( "utf8" )
# from db import connectdb, closedb
from run import HOST, REDISPASSWORD

class Crawler(object):
	def __init__(self, keyword):
		self.keyword = keyword
		self.urlThread = 10
		self.crawlThread = 20
		self.r = redis.StrictRedis(host=HOST, password=REDISPASSWORD, port=6379, db=0)
		self.r.setnx('search_id', 0)
		self.search_id = self.r.incr('search_id')
		self.news = []

	# 执行任务
	def run(self):
		self.r.set('page_id_%d' % self.search_id, -1)

		for x in xrange(0, self.urlThread):
			threading.Thread(target=self.access, name='Accessor_%d' % x).start()

		time.sleep(1)

		for x in xrange(0, self.crawlThread):
			threading.Thread(target=self.crawl, name='Crawler_%d' % x).start()

		while 1:
			if self.urlThread == 0 and self.crawlThread == 0:
				# (db, cursor) = connectdb()
				# cursor.executemany("insert into news(keyword,url,title,timestamp,content) values(%s,%s,%s,%s,%s)", self.news)
				# closedb(db, cursor)
				return self.news
			else:
				time.sleep(0.5)

	# 获取url子线程
	def access(self):
		headers = {}
		headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36"
		while 1:
			page_id = self.r.incr('page_id_%d' % self.search_id)
			# 检查是否还有新的索引任务
			if page_id < 0:
				self.urlThread -= 1
				if self.urlThread == 0:
					self.r.delete('page_id_%d' % self.search_id)
				return

			if page_id > 5:
				self.r.set('page_id_%d' % self.search_id, -999)
				continue

			url = 'http://zhannei.baidu.com/cse/search?q=' + self.keyword + '&p=' + str(page_id) + '&s=16378496155419916178&entry=1&area=2'

			request = urllib2.Request(url=url, headers=headers)
			response = urllib2.urlopen(request, timeout=1)
			html = response.read()
			html = BeautifulSoup(html)
			result = html.select('.c-title a')

			for item in result:
				href = item.get('href')
				if href.split('//')[1][:4] == 'news' and href[-4:] == 'html' and not self.r.sismember('urls_%d' % self.search_id, href):
					self.r.sadd('urls_%d' % self.search_id, href)

	# 获取新闻内容子线程
	def crawl(self):
		headers = {}
		headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36"
		while 1:
			if self.urlThread == 0 and self.r.scard('urls_%d' % self.search_id) == 0:
				self.crawlThread -= 1
				if self.crawlThread == 0:
					self.r.delete('urls_%d' % self.search_id)
				return 

			target = self.r.spop('urls_%d' % self.search_id)
			# 判断是否有url剩余
			if target == None:
				time.sleep(random.random())
				continue

			try:
				request = urllib2.Request(url=target, headers=headers)
				response = urllib2.urlopen(request, timeout=1)
				html = response.read()
				html = BeautifulSoup(html)
				title = html.select('#artical_topic')[0].get_text().split('(')[0].strip()
				timestamp = html.select('.ss01')[0].get_text().strip()
				content = html.select('#main_content p')
				tmp = ''
				for item in content:
					if item.get_text() == '':
						continue
					tmp += item.get_text() + '\t'
				content = tmp
				# images = html.select('#main_content img')
			except Exception, e:
				pass
			else:
				print title
				self.news.append({'keyword': self.keyword, 'url': target, 'title': title, 'timestamp': timestamp, 'content': content})
			finally:
				pass

