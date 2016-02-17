#!/usr/bin/env python
# coding:utf8

import time
import math
import sys
reload(sys)
sys.setdefaultencoding( "utf8" )
import jieba.analyse
import MySQLdb
import MySQLdb.cursors
from run import HOST, PORT, USER, PASSWORD, DATABASE, CHARSET
import numpy as np

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

class Timeliner(object):
	def __init__(self, keyword):
		print '生成时间线'
		# self.model = model
		(db, cursor) = connectdb()
		cursor.execute("update task set status=3 where keyword=%s", [keyword])
		cursor.execute("delete from timeline where keyword=%s",[keyword])
		cursor.execute("select * from news where keyword=%s", [keyword])
		news = cursor.fetchall()
		closedb(db, cursor)

		count = 0
		result = {}
		titles = []
		tmp = {}
		times = []
		for item in news:
			count += 1

			title = item['title']
			timestamp = int(item['timestamp'])
			tag = item['tag']
			content = item['content']

			if title in titles:
				continue
			titles.append(title)

			if not result.has_key(str(tag)):
				result[str(tag)] = []

			if not tmp.has_key(str(tag)):
				tmp[str(tag)] = []

			sentences = self.get_most_important_sentences(title, content, 5)

			for item in sentences:
				if not item[0] in tmp[str(tag)]:
					tmp[str(tag)].append(item[0])
					times.append(timestamp)
					result[str(tag)].append({'timestamp': timestamp, 'sentence': item[0], 'title': title, 'rank': 1})

		self.tmean = np.median(times)
		self.tstd = np.std(times)

		(db, cursor) = connectdb()
		for key, value in result.items():
			records = self.timeline(value, 9999)
			for item in records:
				cursor.execute('insert into timeline(keyword,timestamp,title,sentence,tag,rank) values(%s,%s,%s,%s,%s,%s)',[keyword,item['timestamp'],item['title'],item['sentence'],int(key),item['rank']])

		cursor.execute("delete from task where keyword=%s",[keyword])

		closedb(db, cursor)

		return

	def cosine(self, s1, s2):
		inner = 0
		count = 0
		for k1, v1 in s1.items():
			for k2, v2 in s2.items():
				# try:
				# 	inner += 10 * v1 * v2 * abs(self.model.similarity(k1.decode('utf8'), k2.decode('utf8')))
				# except Exception, e:
				# 	if k1 == k2:
				# 		inner += 10 * v1 * v2
				# else:
				# 	pass
				# finally:
				# 	count += 1

				count += 1
				if k1 == k2:
					inner += 10 * v1 * v2
		return float(inner) / (float(count) + 0.000000001)

	def sentence2vector(self, sentence): 
		sentence = jieba.analyse.extract_tags(sentence, topK=999, withWeight=True, allowPOS=())
		result = {}
		for item in sentence:
			result[item[0]] = item[1]
		return result

	def get_most_important_sentences(self, title, content, N):
		title = self.sentence2vector(title)
		content = content.replace('\t', '。').replace('\n', '。')
		content = content.split('。')
		result = []
		for item in content:
			if len(item.decode('utf8')) < 30:
				continue
			item = item.strip()
			cos = self.cosine(title, self.sentence2vector(item))
			result.append((item, cos))
		result.sort(lambda x,y:cmp(x[1],y[1]),reverse=True)
		if len(result) > N:
			return result[:N]
		else:
			return result

	def timeline(self, sentences, num):
		count = len(sentences)
		similarity = {}

		for x in xrange(0, count):
			sentences[x]['vector'] = self.sentence2vector(sentences[x]['sentence'])

		for x in xrange(0, count):
			similarity[str(x)] = {}
			for y in xrange(0, count):
				if x == y:
					similarity[str(x)][str(y)] = 0
				elif x > y:
					similarity[str(x)][str(y)] = similarity[str(y)][str(x)]
				else:
					similarity[str(x)][str(y)] = self.cosine(sentences[x]['vector'], sentences[y]['vector']) * math.exp(-abs(float(sentences[x]['timestamp'] - sentences[y]['timestamp']) / 3600 / 24 / 7))

		loop = 0
		ratio = []
		for x in xrange(0, count):
			ratio.append(math.exp(-(sentences[x]['timestamp'] - self.tmean) * (sentences[x]['timestamp'] - self.tmean) / (2 * self.tstd * self.tstd)))

		while True:
			loop += 1
			ranks = []
			total = np.sum([x['rank'] for x in sentences])
			for x in xrange(0, count):
				tmp = 0
				for y in xrange(0, count):
					tmp += float(sentences[y]['rank']) * similarity[str(y)][str(x)]
				ranks.append(tmp * ratio[x] / float(total))

			totalChange = 0
			for x in xrange(0, count):
				totalChange += abs(ranks[x] - sentences[x]['rank'])

			for x in xrange(0, count):
				sentences[x]['rank'] = ranks[x]

			if totalChange  < 0.000000001 or loop == 1000:
				break

		sentences.sort(lambda x, y:cmp(x['rank'], y['rank']), reverse=True)

		if len(sentences) > num:
			sentences = sentences[:num]

		sentences.sort(lambda x, y:cmp(x['timestamp'], y['timestamp']), reverse=True)

		return sentences

