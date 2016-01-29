#!/usr/bin/env python
# coding:utf8

import sys
reload(sys)
sys.setdefaultencoding( "utf8" )
import jieba
import jieba.posseg as pseg
from snownlp import SnowNLP
import MySQLdb
import MySQLdb.cursors
from run import HOST, PORT, USER, PASSWORD, DATABASE, CHARSET
import json

# jieba.enable_parallel(4)

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

class Knowledger(object):
	def __init__(self, keyword):
		print '生成新闻知识图谱'
		(db, cursor) = connectdb()
		cursor.execute("update task set status=2 where keyword=%s", [keyword])
		cursor.execute("select id, title, content from news where keyword=%s",[keyword])
		news = cursor.fetchall()

		for item in news:
			nodes = {}
			links = {}
			forces = {}
			forces['nodes'] = '['
			forces['links'] = '['
			nodeId = 0

			sentences = item['content'].split('。')
			sentences.append(item['title'])

			tmp = []

			for i in sentences:
				i = i.replace('\t', '').replace('\n', '').strip()

				if i == '':
					continue

				if i in tmp:
					continue
				tmp.append(i)

				tpJ = []
				thJ = []
				tpS = []
				thS = []

				words = pseg.cut(i)
				for word, flag in words:
					if flag == 'ns' and not word in tpJ:
						tpJ.append(word)

					if flag == 'nr' and not word in thJ:
						thJ.append(word)

				words = SnowNLP(i.decode('utf8'))	
				for word, flag in words.tags:
					if flag == 'ns' and not word in tpS:
						tpS.append(word)

					if flag == 'nr' and not word in thS:
						thS.append(word)

				tp = list(set(tpJ) & set(tpS))
				th = list(set(thJ) & set(thS))
				tr = []

				for j in tp:
					if not j in tr:
						tr.append(j)
					if not nodes.has_key(j):
						nodes[j] = nodeId
						nodeId += 1
						forces['nodes'] += '{"name": "' + j + '", "group": 1},'

				for j in th:
					if not j in tr:
						tr.append(j)
					if not nodes.has_key(j):
						nodes[j] = nodeId
						nodeId += 1
						forces['nodes'] += '{"name": "' + j + '", "group": 2},'

				for x in xrange(0, len(tr)):
					if not links.has_key(tr[x]):
						links[tr[x]] = {}
					for y in xrange(0, len(tr)):
						if y == x:
							continue
						if not links[tr[x]].has_key(tr[y]):
							links[tr[x]][tr[y]] = 0
						links[tr[x]][tr[y]] += 1

			for key, value in links.items():
				for k, v in value.items():
					if nodes[key] > nodes[k]:
						continue
					forces['links'] += '{"source": ' + str(nodes[key]) + ', "target": ' + str(nodes[k]) + ', "value": ' + str(v) + '},'

			if forces['nodes'][-1] == ',':
				forces['nodes'] = forces['nodes'][:-1]

			if forces['links'][-1] == ',':
				forces['links'] = forces['links'][:-1]

			forces = '{"nodes":' + forces['nodes'] + '], "links": ' + forces['links'] + ']}'
			cursor.execute("update news set knowledge=%s where id=%s",[forces, item['id']])
		closedb(db, cursor)
		return