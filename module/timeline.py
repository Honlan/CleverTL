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
		self.keyword = keyword
		(db, cursor) = connectdb()
		cursor.execute("update task set status=3 where keyword=%s", [keyword])
		cursor.execute("delete from timeline where keyword=%s",[keyword])
		cursor.execute("select * from news where keyword=%s", [keyword])
		news = cursor.fetchall()
		closedb(db, cursor)

		result = []
		titles = []
		tmp = {}
		times = []
		links = []
		for item in news:
			title = item['title']
			timestamp = int(item['timestamp'])
			tag = item['tag']
			content = item['content']

			if title in titles:
				continue
			titles.append(title)

			links.append([item['id'], int(time.mktime(time.strptime(time.strftime('%Y-%m-%d', time.localtime(float(timestamp))), '%Y-%m-%d'))), title + content])

			if not tmp.has_key(str(tag)):
				tmp[str(tag)] = []

			sentences = self.get_most_important_sentences(title, content, 5)

			for item in sentences:
				if not item[0] in tmp[str(tag)]:
					tmp[str(tag)].append(item[0])
					times.append(timestamp)
					result.append({'timestamp': timestamp, 'sentence': item[0], 'title': title, 'vector': item[2], 'tag': tag, 'rank': 1})

		self.get_links(links)

		self.tmean = np.median(times)
		self.tstd = np.std(times)

		(db, cursor) = connectdb()

		records = self.timeline(result, 9999)
		for item in records:
			cursor.execute('insert into timeline(keyword,timestamp,title,sentence,tag,rank) values(%s,%s,%s,%s,%s,%s)',[keyword,item['timestamp'],item['title'],item['sentence'],item['tag'],item['rank']])

		cursor.execute("delete from task where keyword=%s",[keyword])

		closedb(db, cursor)

		return

	def cosine(self, s1, s2):
		inner = 0
		for k, v in s1.items():
			if s2.has_key(k):
				inner += v * s2[k]

		norm1 = 0
		for k, v in s1.items():
			norm1 += v * v
		norm1 = math.sqrt(norm1)

		norm2 = 0
		for k, v in s2.items():
			norm2 += v * v
		norm2 = math.sqrt(norm2)

		if norm1 == 0 or norm2 == 0:
			tmp = 0
		else:
			tmp = float(inner) / (norm1 * norm2)

		return tmp

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
			vector = self.sentence2vector(item)
			cos = self.cosine(title, vector)
			result.append((item, cos, vector))
		result.sort(lambda x,y:cmp(x[1],y[1]),reverse=True)
		if len(result) > N:
			return result[:N]
		else:
			return result

	def timeline(self, sentences, num):
		count = len(sentences)
		similarity = {}

		tmin = 999
		tmax = -999
		for x in xrange(0, count):
			similarity[str(x)] = {}
			for y in xrange(0, count):
				if x == y:
					similarity[str(x)][str(y)] = 0
				elif x > y:
					similarity[str(x)][str(y)] = similarity[str(y)][str(x)]
				else:
					# similarity[str(x)][str(y)] = self.cosine(sentences[x]['vector'], sentences[y]['vector'])
					similarity[str(x)][str(y)] = self.cosine(sentences[x]['vector'], sentences[y]['vector']) * math.exp(-(sentences[x]['timestamp'] - sentences[y]['timestamp']) * (sentences[x]['timestamp'] - sentences[y]['timestamp']) / (self.tstd * self.tstd / 16))
					if similarity[str(x)][str(y)] > tmax:
						tmax = similarity[str(x)][str(y)]
					if similarity[str(x)][str(y)] < tmin:
						tmin = similarity[str(x)][str(y)]
		tmp = 0
		for x in xrange(0, count):
			for y in xrange(0, count):
				similarity[str(x)][str(y)] = (similarity[str(x)][str(y)] - tmin) / (tmax - tmin) 
				tmp += similarity[str(x)][str(y)]

		loop = 0

		# ratio = []
		# tmin = 999
		# tmax = -999
		# for x in xrange(0, count):
		# 	tmp = math.exp(-(sentences[x]['timestamp'] - self.tmean) * (sentences[x]['timestamp'] - self.tmean) / (2 * self.tstd * self.tstd))
		# 	ratio.append(tmp)
		# 	if tmp > tmin:
		# 		tmin = tmp
		# 	elif tmp < tmax:
		# 		tmax = tmp
		# for x in xrange(0, count):
		# 	ratio[x] = (ratio[x] - tmin) / (tmax - tmin) 

		maxrank = np.max([x['rank'] for x in sentences])
		param = 1

		while True:
			loop += 1
			ranks = []
			total = np.sum([x['rank'] for x in sentences])
			for x in xrange(0, count):
				tmp = 0
				for y in xrange(0, count):
					tmp += param * float(sentences[y]['rank']) * (float(sentences[y]['rank']) / float(total)) * similarity[str(y)][str(x)]
				ranks.append(tmp)

			totalChange = 0
			for x in xrange(0, count):
				totalChange += abs(ranks[x] - sentences[x]['rank'])

			for x in xrange(0, count):
				sentences[x]['rank'] = ranks[x]

			maxrank = np.max([x['rank'] for x in sentences])
			param = 1 / maxrank

			if totalChange  < 0.0000001 or loop == 100:
				break

			print 'loop ' + str(loop) + ': ' + str(totalChange)

		sentences.sort(lambda x, y:cmp(x['rank'], y['rank']), reverse=True)

		if len(sentences) > num:
			sentences = sentences[:num]

		sentences.sort(lambda x, y:cmp(x['timestamp'], y['timestamp']), reverse=True)
		return sentences

	def get_links(self, links):
		count = len(links)
		result = {}
		(db, cursor) = connectdb()
		cursor.execute("update news set links='' where keyword=%s", [self.keyword])
		for x in xrange(0, count):
			data_id = links[x][0]
			print 'calculate links for ' +  str(x)
			for y in xrange(0, count):
				if y == x:
					continue

				if not links[x][1] / (24 * 3600) == links[y][1] / (24 * 3600):
					continue

				if not result.has_key(str(data_id)):
					result[str(data_id)] = []

				tmp = self.cosine(self.sentence2vector(links[x][2]), self.sentence2vector(links[y][2])) * 0.6
				result[str(data_id)].append([links[y][0], tmp])

		for key, value in result.items():
			tmp = ''
			for item in value:
				if item[1] < 0.2:
					continue
				tmp += str(item[0]) + ':' + str(item[1]) + ',' 
			if not tmp == '':
				tmp = tmp[:-1]
			cursor.execute("update news set links=%s where id=%s", [tmp, int(key)])

		closedb(db, cursor)
		return