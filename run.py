#!/usr/bin/env python
# coding:utf8

import sys
reload(sys)
sys.setdefaultencoding( "utf8" )
from flask import *
import warnings
warnings.filterwarnings("ignore")
from config import *
from module.crawl import *
from module.db import connectdb, closedb
import numpy as np
import math

app = Flask(__name__)
app.config.from_object(__name__)

# 首页
@app.route('/')
def index():
	return render_template('index.html')

# 核心任务
@app.route('/search', methods=['POST'])
def search():
	data = request.form
	raw_news = Crawler(data['keyword']).run()
	return json.dumps({'news': raw_news})

@app.route('/timeline/<keyword>')
def timeline(keyword):
	(db,cursor) = connectdb()
	cursor.execute('select * from news where keyword=%s',[keyword])
	news = list(cursor.fetchall())
	for x in xrange(0, len(news)):
		news[x]['content'] = news[x]['content'].replace('\t', '<br/>')
		news[x]['knowledge'] = json.loads(news[x]['knowledge'])
	cursor.execute('select * from timeline where keyword=%s order by rank desc',[keyword])
	timeline = list(cursor.fetchall())
	tmp = []
	for x in [1,2,3,4,6,7]:
		count = 0
		# length = len([y['tag'] for y in timeline if y['tag'] == x])
		for item in timeline:
			if item['tag'] == x:
				tmp.append(item)
				count += 1
			# if count >= length / 5:
			if count >= 20:
				break
	timeline = tmp
	timeline.sort(lambda x,y:cmp(x['timestamp'],y['timestamp']))
	closedb(db,cursor)

	begintime = np.min([int(time.mktime(time.strptime(x['timestamp'], '%Y-%m-%d'))) for x in timeline])
	endtime = np.max([int(time.mktime(time.strptime(x['timestamp'], '%Y-%m-%d'))) for x in timeline])
	day = (endtime - begintime) / 3600 / 24
	slot = np.argmax([float(day)/(math.ceil(float(day)/x)*x) for x in xrange(5,11)]) + 5
	interval = math.ceil(day / slot)

	begintime -= interval * 3600 * 24
	endtime += interval * 3600 * 24
	slot += 2
	xs = [time.strftime('%m-%d', time.localtime(begintime + x * 3600 * 24 * interval)) for x in xrange(0, slot + 1)]
	axis = json.dumps({'from':int(begintime), 'to':int(endtime), 'slot':slot, 'interval':interval, 'xs':xs})

	curves = {'1': {}, '2': {}, '3': {}, '4': {}, '6': {}, '7': {}}
	maxnum = {'line':0, 'stack':0, 'band':0}
	allX = []
	stack = {}
	tmp = endtime - begintime
	for item in timeline:
		item['x'] = (float(time.mktime(time.strptime(item['timestamp'], '%Y-%m-%d'))) - begintime) / tmp
		if not str(item['x']) in  allX:
			allX.append(str(item['x']))
		if not curves[str(item['tag'])].has_key(str(item['x'])):
			curves[str(item['tag'])][str(item['x'])] = 0
		curves[str(item['tag'])][str(item['x'])] += 1
		if not stack.has_key(str(item['x'])):
			stack[str(item['x'])] = 0
		stack[str(item['x'])] += 1
	maxnum['stack'] = np.max([v for k,v in stack.items()])
	allX.sort(lambda x,y:cmp(float(x), (y)))
	for key, value in curves.items():
		tmp = []
		for i in allX:
			if value.has_key(i):
				tmp.append([i, value[i]])
				if value[i] > maxnum['line']:
					maxnum['line'] = value[i]
			else:
				tmp.append([i, 0])
		curves[key] = tmp
	maxnum['band'] = np.sum([np.max([v[1] for v in value]) for key,value in curves.items()])
	print maxnum

	return render_template('timeline.html', news=json.dumps(news), timeline=json.dumps(timeline), axis=axis, curves=json.dumps(curves), maxnum=json.dumps(maxnum))

if __name__ == '__main__':
	app.run(debug=True)