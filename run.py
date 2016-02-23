#!/usr/bin/env python
# coding:utf8

import sys
reload(sys)
sys.setdefaultencoding( "utf8" )
sys.settrace 
from flask import *
import warnings
warnings.filterwarnings("ignore")
from config import *
from module.crawl import *
from module.classify import *
from module.knowledge import *
from module.timeline import *
import numpy as np
import math
# print 'load model'
# import gensim
# model = gensim.models.Word2Vec.load("static/data/wiki.zh.text.model")
# print 'load finish'

app = Flask(__name__)
app.config.from_object(__name__)

# 首页
@app.route('/')
def index():
	(db,cursor) = connectdb()
	cursor.execute("select count(*) as count, keyword from timeline group by keyword")
	keywords = cursor.fetchall()
	for item in keywords:
		item['count'] = math.log(item['count']) * 4 + 10
	closedb(db,cursor)
	return render_template('index.html', keywords=keywords)

# 核心任务
@app.route('/search', methods=['POST'])
def search():
	data = request.form
	if data['token'] == TOKEN:
		start = time.time()
		Crawler(data['keyword']).run()
		print time.time() - start
		Classifier(data['keyword'])
		print time.time() - start
		Knowledger(data['keyword'])
		print time.time() - start
		Timeliner(data['keyword'])
		print time.time() - start
		return json.dumps({'ok': True})
	else:
		return json.dumps({'ok': False})

@app.route('/timeline/<keyword>')
def timeline(keyword):
	(db,cursor) = connectdb()
	# 处理时间项
	cursor.execute('select * from timeline where keyword=%s order by rank desc',[keyword])
	timeline = list(cursor.fetchall())
	for item in timeline:
		item['timestamp'] = time.strftime('%Y-%m-%d', time.localtime(float(item['timestamp'])))
		item['timestamp'] = int(time.mktime(time.strptime(item['timestamp'], '%Y-%m-%d')))
	tmp = []
	ratio = float(len(timeline)) / 120
	for x in [1,2,3,4,6,7]:
		count = 0
		length = float(len([y['tag'] for y in timeline if y['tag'] == x]))
		for item in timeline:
			if item['tag'] == x:
				tmp.append(item)
				count += 1
			if count >= length / ratio:
			# if count >= 20:
				break
	timeline = tmp
	timeline.sort(lambda x,y:cmp(x['timestamp'],y['timestamp']))

	begintime = np.min([x['timestamp'] for x in timeline])
	endtime = np.max([x['timestamp'] for x in timeline])
	day = (endtime - begintime) / 3600 / 24
	slot = np.argmax([float(day)/(math.ceil(float(day)/x)*x) for x in xrange(5,11)]) + 5
	interval = math.ceil(day / slot)

	begintime -= interval * 3600 * 24
	endtime += interval * 3600 * 24
	slot += 2
	xs = [time.strftime('%m-%d', time.localtime(begintime + x * 3600 * 24 * interval)) for x in xrange(0, slot + 1)]
	axis = {'slot':slot, 'xs':xs, 'begintime': begintime, 'endtime': endtime}

	curves = {'1': {}, '2': {}, '3': {}, '4': {}, '6': {}, '7': {}}
	maxnum = {'line':0, 'stack':0, 'band':0}
	allX = []
	stack = {}
	tmp = endtime - begintime
	for item in timeline:
		item['x'] = (float(item['timestamp']) - begintime) / tmp
		if not str(item['x']) in  allX:
			allX.append(str(item['x']))
		if not curves[str(item['tag'])].has_key(str(item['x'])):
			curves[str(item['tag'])][str(item['x'])] = 0
		curves[str(item['tag'])][str(item['x'])] += 1
		if not stack.has_key(str(item['x'])):
			stack[str(item['x'])] = 0
		stack[str(item['x'])] += 1
	maxnum['stack'] = np.max([v for k,v in stack.items()])
	allX.sort(lambda x,y:cmp(float(x), float(y)))
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
	for item in timeline:
		item['timestamp'] = time.strftime('%Y-%m-%d', time.localtime(float(item['timestamp'])))

	# 处理新闻
	cursor.execute('select * from news where keyword=%s',[keyword])
	news = list(cursor.fetchall())
	closedb(db,cursor)
	tmp = []
	for item in news:
		item['timestamp'] = time.strftime('%Y-%m-%d', time.localtime(float(item['timestamp'])))
		item['timestamp'] = int(time.mktime(time.strptime(item['timestamp'], '%Y-%m-%d')))
		if (item['timestamp'] - begintime) * (item['timestamp'] - endtime) < 0:
			item['content'] = item['content'].replace('\t', '<br/>')
			item['knowledge'] = json.loads(item['knowledge'])
			tmp.append(item)
	news = tmp

	curves3D = {'1': {}, '2': {}, '3': {}, '4': {}, '6': {}, '7': {}, 'all': {}, 'stack': {}}
	allX3D = []
	tmp = endtime - begintime
	day = int(tmp / 3600 / 24)
	for x in xrange(0, day + 1):
		allX3D.append('%.4f' % (float(x) / day))
	for item in news:
		item['x'] = '%.4f' % ((float(item['timestamp']) - begintime) / tmp)
		if not curves3D[str(item['tag'])].has_key(str(item['x'])):
			curves3D[str(item['tag'])][str(item['x'])] = 0
		curves3D[str(item['tag'])][str(item['x'])] += 1
		if not curves3D['all'].has_key(str(item['x'])):
			curves3D['all'][str(item['x'])] = 0
		curves3D['all'][str(item['x'])] += 1
	allX3D.sort(lambda x,y:cmp(float(x), float(y)))
	for key, value in curves3D.items():
		tmp = []
		for i in allX3D:
			if value.has_key(i):
				tmp.append([i, value[i]])
			else:
				tmp.append([i, 0])
		curves3D[key] = tmp
	layer = []
	for key in ['1', '2', '3', '4', '6', '7']:
		value = curves3D[key]
		tmp = []
		for x in xrange(0, len(allX3D)):
			tmp.append({'x': float(value[x][0]), 'y0': curves3D['stack'][x][1], 'y': value[x][1]})
			curves3D['stack'][x][1] += value[x][1]
		layer.append(tmp)
	curves3DMax = np.max([x[1] for x in curves3D['all']])
	curves3D = layer

	newsbegintime = np.min([x['timestamp'] for x in news])
	newsendtime = np.max([x['timestamp'] for x in news])
	axis['newsbegintime'] = newsbegintime
	axis['newsendtime'] = newsendtime
	print time.strftime('%Y-%m-%d', time.localtime(float(newsbegintime)))
	print time.strftime('%Y-%m-%d', time.localtime(float(newsendtime)))

	return render_template('timeline.html', news=json.dumps(news), timeline=json.dumps(timeline), axis=json.dumps(axis), curves=json.dumps(curves), maxnum=json.dumps(maxnum), curves3D=curves3D, curves3DMax=curves3DMax)

if __name__ == '__main__':
	app.run(debug=True)