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
import MySQLdb
import MySQLdb.cursors
from run import HOST, PORT, USER, PASSWORD, DATABASE, CHARSET, REDISPASSWORD

# 连接数据库
def connectdb():
	db = MySQLdb.connect(host=HOST, user=USER, passwd=PASSWORD, db=DATABASE, port=PORT, charset=CHARSET, cursorclass = MySQLdb.cursors.DictCursor)
	db.autocommit(True)
	cursor = db.cursor()
	return (db,cursor)

# 关闭数据库
def closedb(db,cursor):
	db.close()
	cursor.close()

class Crawler(object):
	def __init__(self, keyword):
		print '爬取新闻数据'
		(db, cursor) = connectdb()
		cursor.execute("insert into task(keyword,status,info) values(%s, %s, %s)",[keyword, 0, ''])
		cursor.execute("delete from news where keyword=%s",[keyword])
		closedb(db, cursor)

		self.keyword = keyword
		self.urlThread = 4
		self.crawlThread = 20
		self.r = redis.StrictRedis(host=HOST, password=REDISPASSWORD, port=6379, db=0)
		self.r.setnx('search_id', 0)
		self.search_id = self.r.incr('search_id')
		self.news = []
		self.target = 180
		self.hungry = 0

	# 执行任务
	def run(self):
		self.r.set('page_id_%d' % self.search_id, -1)

		for x in xrange(0, self.urlThread):
			threading.Thread(target=self.access, name='Accessor_%d' % x).start()

		for x in xrange(0, self.crawlThread):
			threading.Thread(target=self.crawl, name='Crawler_%d' % x).start()

		while 1:
			if self.urlThread == 0 and self.crawlThread == 0:
				return
			else:
				time.sleep(2)

	# 获取url子线程
	def access(self):
		headers = {}
		headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36"
		while 1:
			page_id = self.r.incr('page_id_%d' % self.search_id)

			if len(self.news) >= self.target or self.hungry >= 500:
				self.urlThread -= 1
				if self.urlThread == 0:
					self.r.delete('page_id_%d' % self.search_id)
				return

			url = 'http://zhannei.baidu.com/cse/search?q=' + self.keyword + '&p=' + str(page_id) + '&s=16378496155419916178&entry=1&area=2'

			try:
				request = urllib2.Request(url=url, headers=headers)
				response = urllib2.urlopen(request, timeout=1)
				html = response.read()
				html = BeautifulSoup(html)
				result = html.select('.c-title a')
			except Exception, e:
				continue
			else:
				for item in result:
					href = item.get('href')
					if href.split('//')[1][:4] == 'news' and href[-4:] == 'html' and not self.r.sismember('urls_%d' % self.search_id, href):
						self.r.sadd('urls_%d' % self.search_id, href)
						self.r.sadd('urls_%d_tmp' % self.search_id, href)
			finally:
				pass

			time.sleep(2)

	# 获取新闻内容子线程
	def crawl(self):
		headers = {}
		headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36"
		while 1:
			print self.urlThread, self.crawlThread, len(self.news), self.hungry
			if len(self.news) >= self.target or self.hungry >= 500:
				self.crawlThread -= 1
				if self.crawlThread == 0:
					self.r.delete('urls_%d' % self.search_id)
					self.r.delete('urls_%d_tmp' % self.search_id)
				return 

			target = self.r.spop('urls_%d_tmp' % self.search_id)

			if target == None:
				self.hungry += 1
				time.sleep(random.random())
				continue

			try:
				request = urllib2.Request(url=target, headers=headers)
				response = urllib2.urlopen(request, timeout=1)
				html = response.read()
				html = BeautifulSoup(html)
				title = html.select('#artical_topic')[0].get_text().split('(')[0].strip()
				timestamp = html.select('.ss01')[0].get_text().strip().encode('utf8')
				content = html.select('#main_content p')
				tmp = ''
				for item in content:
					if item.get_text() == '':
						continue
					tmp += item.get_text() + '\t'
				content = tmp
				# images = html.select('#main_content img')
			except Exception, e:
				continue
			else:
				if len(self.news) >= self.target:
					continue
				# self.news.append([self.keyword, target, title, int(time.mktime(time.strptime(timestamp,'%Y-%m-%d %H:%M:%S'))), content])
				if title in self.news:
					continue
				print title
				self.news.append(title)
				(db, cursor) = connectdb()
				cursor.execute("insert into news(keyword,url,title,timestamp,content,knowledge) values(%s,%s,%s,%s,%s,%s)", [self.keyword, target, title, int(time.mktime(time.strptime(timestamp,'%Y年%m月%d日 %H:%M'))), content,''])
				closedb(db, cursor)
			finally:
				pass

