#!/usr/bin/env python
# coding:utf8

from tgrocery import Grocery
import sys
reload(sys)
sys.setdefaultencoding( "utf8" )
import MySQLdb
import MySQLdb.cursors
from run import HOST, PORT, USER, PASSWORD, DATABASE, CHARSET

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

class Classifier(object):
	def __init__(self, keyword):
		print '进行新闻分类'
		(db, cursor) = connectdb()
		cursor.execute("update task set status=1 where keyword=%s", [keyword])
		cursor.execute("select id, title from news where keyword=%s",[keyword])
		news = cursor.fetchall()
		new_grocery = Grocery('static/paris')
		new_grocery.load()

		for item in news:
			tag = new_grocery.predict(item['title'])
			if tag == '新闻背景':
				tag = 1
			elif tag == '事实陈述':
				tag = 2
			elif tag == '事件演化':
				tag = 3 
			elif tag == '各方态度':
				tag = 4
			elif tag == '直接关联':
				tag = 6
			elif tag == '暂无关联':
				tag = 7
			cursor.execute("update news set tag=%s where id=%s", [tag, item['id']])
		closedb(db, cursor)
		return