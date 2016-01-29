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
print 'load model'
import gensim
model = gensim.models.Word2Vec.load("static/data/wiki.zh.text.model")
print 'load finish'

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
		(db, cursor) = connectdb()
		cursor.execute("update task set status=3 where keyword=%s", [keyword])

		return