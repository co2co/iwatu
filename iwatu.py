#!/usr/bin/python
#_*_ coding:utf-8 _*_

'''''''''''''''''''''
author:co2co
e-mail:myco2co@gmail.com
version:0.2.0
date-time:2015/1/4
'''''''''''''''''''''

import os,re,requests,random,sqlite3,time
from multiprocessing.dummy import Pool as ThreadPool
import sys 
import config #这个是程序的配置文件


class iWaTu:
	
	def __init__(self,domain):
		'''这是初始化函数，用来初始化一些变量'''

		self.setup(domain)


	def setup(self,domain):
		'''这个函数主要用来初始化request对象以及初始化一些变量'''

		'''初始化Session'''
		self.domain = domain
		self.s = requests.Session()
		self.pic_limit = config.pic_limit #主题里可供采集的图片数小于这个数量则放弃采集
		#self.filter_keywords = config.filter_keywords #暂时不知道怎么实现好
		self.ThreadPool = int(config.ThreadPool)
		print("当前使用的线程数：%s" % self.ThreadPool)
		self.s.headers.update(config.headers) #载入自定义的post headers头
		if len(config.proxies)==0:
			proxies = {}
		else:
			proxies = config.proxies #载入代理设置
		self.s.proxies.update(proxies) #载入代理设置
		'''选择合适的正则表达式'''
		self.choose_preg(domain)

		'''初始化数据库'''
		if not os.path.isfile('iwatu.db'):
			self.create_db()

		'''提示用户当前采集模式是直连还是使用代理'''
		if not len(proxies)==0:
			print("已进入代理采集模式，请确保代理服务器能正常工作。当前工作IP是：%s" % self.debug_view_ip())
		else:
			print("目前是直连模式，请注意采集频率免得被封IP。当前工作IP是：%s" % self.debug_view_ip())

		'''登陆目标论坛并且保存cookies在Sessions对象中'''
		if domain.find('http') == -1:
			domain = 'http://' + domain
		self.login_bbs(domain)

	def choose_preg(self, domain):

		for each_item in config.preg.items():
			match = re.search(each_item[0], domain)
			if match:
				self.listpreg = re.compile(each_item[1]['listpreg'])
				self.imagepreg = re.compile(each_item[1]['imagepreg'])
				self.titlepreg = re.compile(each_item[1]['titlepreg'])
				print("已选择正则表达式方案为：%s" % each_item[0])
				return(True)
		else:
			print("当前域名没有适合的正则表达式可用，程序将会退出。")
			sys.exit()


	def login_bbs(self, domain):
		'''这个函数是用来登录论坛的'''

		for each_item in config.account.items():
			#print("尝试用Account里的%s去匹配当前任务:%s" % (each_item[0],domain))
			match = re.search(each_item[0],domain)
			if match:
				username = each_item[1][0]
				password = each_item[1][1]
				loginurl = each_item[1][2]
				print("登录账号匹配成功：[%s]:[%s]:[%s]" % (username, password, loginurl))

				postdata = {
							'loginfield':'username',
							'cookietime':2592000,
							'username':username,
							'password':password,
							'questionid':0,
							'answer':'',
							'loginsubmit':'true'
							
				}
				#本地路径用os.path.join是很好，因为python会自动判断当前系统然后加上合适的连接符
				#但是如果在合并网址的时候用这个函数，那么在windows的平台上就会出错，因为windows平台的连接符是“\”
				#loginurl = domain + '/' + r'member.php?mod=logging&action=login&loginsubmit=yes&frommessage&inajax=1'
				#loginurl = domain + '/' + r'bbs/logging.php?action=login'
				
				try:
					getdata = self.s.post(loginurl, data=postdata, timeout=10)
				except:
					print("%s获取远程页面失败！" % loginurl)
				#print(getdata.cookies)
				return(True) #这里如果不在获得了正确的返回值时（也就是成功登陆后）Return，那么就会一直循环到结束，然后提示没有账户密码
		'''如果for循环完了都没有找到一个匹配的，那就是没有了'''
		print("缺少对应的账户密码，程序即将以游客身份采集！")


	def create_db(self):
		'''这个函数是用来初始化数据库的，由于目前python3还没有mysql的库支持，所以只能暂时用sqlite了，残念'''

		try:  #尝试新建表。创建数据库只要python有权限一般都不会失败，要留意的是新建表
			conn = sqlite3.connect('iwatu.db')
			cursor = conn.cursor()
			cursor.execute('create table urls (url varchar(255) not null PRIMARY KEY,log int(2) not null,competence int(2) not null,domain varchar(255) not null)')
			cursor.execute('create table dlink (dlink varchar(255) not null PRIMARY KEY,log int(2) not null,title varchar(255) not null,domain varchar(255) not null,referer varchar(255) not null)')
			cursor.execute('create table localpath (localpath varchar(255) not null PRIMARY KEY,log int(2) not null,title varchar(255) not null,downloadtime varchar(100) not null,referer varchar(255) not null)')
			print("创建数据库以及相关的表成功！")
		except sqlite3.Error as e:
			print("创建数据库出错，请debug...")
			print("Error : %s" % e)
			os.remove('iwatu.db')
			sys.exit() #数据库以及相关表的正常创建是这个程序的基础，如果这里出问题就没必要继续运行下去，必须中断退出
		finally:
			if cursor:cursor.close
			if conn: #不管怎样，如果连接打开了总得关闭调以回收系统资源的
				conn.commit
				conn.close


	def handle_pagelist(self,targeturl, x=None, y=0):
		'''这是列表页处理函数，负责把主题页的地址分析出来然后再提交给主题页处理函数去处理'''

		print("进入列表页处理程序...")

		list_urls = [] #这是用来放当前要处理的连接的容器

		#判断任务是单一列表页还是多个列表页
		if targeturl.find('*') != -1:
			if x==None:
				x=1
				print("你指定了任务为多页面模式，但是页数未指定，程序采用默认值：'1'")
			urlhandler = targeturl.split('*') #以*为标记截断原始URL
			starturl = urlhandler[0]+str(x)+urlhandler[1]  #初始化任务的第一个列表页地址
			list_urls.append(starturl) #并且放入页面链接的list
			while x<=y: #用循环把用户指定的连接创建出来并且一一放入list里面
				x = x+1
				mission_url = urlhandler[0]+str(x)+urlhandler[1]
				list_urls.append(mission_url)  #循环生成链接地址并且放入list里面
		else:
			list_urls.extend(targeturl) #如果找不到'*'那么就是单一页面的任务而已，直接放入去就可以了

		if len(list_urls)>0:
			print("分析任务进行中，请稍后...")
			pool = ThreadPool(self.ThreadPool)
			pool.map_async(self.multi_handle_pagelist, list_urls)
			pool.close()
			pool.join()  #调用方法要加‘()’啊你妹！
			print("All Done!")
		else:
			print("没有列表页需要处理")


	def multi_handle_pagelist(self,single_pagelist):
		'''这是列表页处理函数的子函数，是被多进程调用的，目的是加快分析处理'''

		(domain,pagename) = os.path.split(single_pagelist)
		conn = sqlite3.connect('iwatu.db')
		cursor = conn.cursor()
		try:
			getdata = self.s.post(single_pagelist, timeout=10) #列表页一般游客都有权限读取的，所以不用去登陆了
			getdata.encoding = 'gbk'
		except:
			print("下载%s远程页面失败，因此无法进行分析！" % single_pagelist)
		#if getdata.status_code == requests.codes.ok:
		subjectlist = self.listpreg.findall(getdata.text)
		if len(subjectlist)>0:
			for each_link in subjectlist:
				if not each_link.find(r'http://') == -1: #判断是否包含domain头，已经有则直接追加进去列表，如果没有则补上再追加
					each_link = each_link
				else:
					each_link = domain + '/' + each_link

				check_it = cursor.execute('select url from urls where url=?',(each_link,)).fetchall()
				if len(check_it)==0:
					cursor.execute('insert into urls(url,log,competence,domain) values(?,?,?,?)',(each_link,0,1,self.domain)) #注意这里的域名要用不带http的
		else:
			print("%s找不到可供采集的主题页！" % (single_pagelist))
			#print(getdata.text)
		#else:
			#print(getdata.status_code)
		#清场
		if cursor:cursor.close()  #神啊，拜托找人敲一下我的这个猪脑袋吧，方法老是忘记加圆括号啊！T_T
		if conn:
			conn.commit()
			conn.close()


	def handle_subjectpage(self,single_subjectpage=None):
		'''这是主题页处理函数，负责把每一个图片的地址分析出来'''

		print("进入主题页处理程序...")
		targeturl=[]
		#先判断参数那里有没有任务传进来，如果有，先加上
		if single_subjectpage!=None:
			targeturl.append(single_subjectpage)
		#下面把数据库里未处理过的主题也一并放进来去处理
		conn = sqlite3.connect('iwatu.db')
		cursor = conn.cursor()
		result = cursor.execute('select * from urls where log=0 and competence=1 and domain=?', (self.domain,)).fetchall()
		old_exists_list = []
		for each_tuple in result:
			old_exists_list.append(each_tuple[0]) 
		targeturl.extend(old_exists_list)   #extend会自动把来源按照“一定的系统内部规律”打散再加入：列表会按照“，”打散成字符串；字符串则会打散成字母
		if cursor:cursor.close()
		if conn:
			conn.commit()
			conn.close()

		if len(targeturl)>0:
		#创建进程池正式开始处理啦
			print("分析任务进行中，请稍后...")
			pool = ThreadPool(self.ThreadPool) 
			pool.map_async(self.multi_handle_subjectpage, targeturl)
			pool.close()
			pool.join()
			print("All Done!")
		else:
			print("没有主题页需要处理")


	def multi_handle_subjectpage(self,single_subjectpage):
		'''这是主题页处理函数的子函数，是被多进程调用的，目的是加快分析的速度'''

		(http_domain,filename)=os.path.split(single_subjectpage)
		#链接数据库并获得游标
		conn = sqlite3.connect('iwatu.db')
		cursor = conn.cursor()
		
		try:
			getdata = self.s.post(single_subjectpage, timeout=10)
			getdata.encoding = 'gbk'
		except:
			print("%s下载远程页面失败，因此无法进行分析！" % single_subjectpage)
		#if getdata.status_code == requests.codes.ok:
		'''search返回一个对象，findall返回一个list。
			取得search的具体内容要用object.groups()或者object.group(0)这样的方法去获取匹配到的内容。
			而findall的list嘛，就是object.list(0)这样的方法啦。
			这里为了训练特意用了不同的方式去获取匹配到的内容'''
		image_list = self.imagepreg.findall(getdata.text)
		if len(image_list)>0:
			if not len(image_list)<self.pic_limit:
				title_temp = self.titlepreg.search(getdata.text) 
				if not title_temp:
					title = '匹配标题失败'
				else:
					title = title_temp.group(1)
					title = re.sub(r'\W', '', title) #替换掉特殊字符再入数据库
				
				for each_link in image_list:
					if not each_link.find(r'http://') == -1:  #判断地址是否完整，即是否已经包含主域名，如果有，直接追加进去list里面
						each_link = each_link
					else:	#如果没有，则补上domain头，再追加进去list里面
						each_link = http_domain + '/' + each_link

					result = cursor.execute('select dlink from dlink where dlink=?',(each_link,)).fetchall()  #如果有记录，这里会返回一个List
					if len(result):
						#print("%s:图片下载地址已经存在，跳过..." % single_subjectpage)
						try: 
							cursor.execute('update urls set log=1 where url=?',(single_subjectpage,))
						except:
							pass 
							'''这里不对出错做任何处理的原因是：
							有时程序是从subject节点运行的，于是就导致了图片下载连接入库了，但是urls那里是没有记录的。
							所以试图去更新一个不存在的记录就必然会出错。
							设置这个更新动作主要是兼容解决【程序前期可能的设置、调试错漏导致分析出了图片地址，而没有更新urls的log记录，
							后面这个主题页就会一直出现，而图片链接那里却有记录的死循环】'''
					else:
						cursor.execute('insert into dlink(dlink,log,title,domain,referer) values(?,?,?,?,?)',(each_link,0,title,self.domain,single_subjectpage))
						cursor.execute('update urls set log=1 where url=?',(single_subjectpage,))
						#print("图片地址已入库 : %s" % each_link)
			else:
				print("%s可供采集的图片数小于%s张（config文件中的预设值），因此放弃采集此主题！" % (single_subjectpage, self.pic_limit))
		else:
			#零星找不到的情况下很可能是单个帖子的权限问题无法浏览，如果是大面积出现则应该是IP被ban了
			cursor.execute('update urls set competence=0 where url=?',(single_subjectpage,))
			print("%s无法找到匹配的图片链接地址，可能是正则表达式有误、权限不足或者是IP被服务器屏蔽了" % single_subjectpage)
		#else:
			#print(getdata.status_code)
		#函数任务完成了，清场吧！
		if cursor:cursor.close()
		if conn:
			conn.commit()
			conn.close()


	def handle_download_picture(self):
		'''这是下载图片的主函数'''

		print("进入图片下载程序...")
		picture_list = []
		conn = sqlite3.connect('iwatu.db')
		cursor = conn.cursor()
		sql='select dlink,title,referer from dlink where log=0'
		picture_list = cursor.execute(sql).fetchall()
		if cursor:cursor.close()
		if conn:
			conn.commit()
			conn.close()

		if len(picture_list) !=0:
			print("下载任务进行中，请稍后...")
			pool = ThreadPool(self.ThreadPool)
			'''
			for each_tuple in picture_list:
				print("添加新任务到子进程(父Pid:%s)：%s" % (os.getpid(),each_tuple[0]))
				#根据sql的查询内容来看，这个list应该分别是0放dlink,1放title，2放referer
				p.apply_async(self.multi_handle_download_picture, args=(each_tuple,))
			'''
			pool.map_async(self.multi_handle_download_picture, picture_list)
			pool.close()
			pool.join()
			print("All Done!")
		else:
			print("没有搜索到需要下载的图片连接记录")


	def multi_handle_download_picture(self, single_picture_url_tuple): #注意！这里传过来的是一个图片连接的元组，内含多种信息
		'''这是下载图片的子函数，是被多进程调用的，目的是加快速度'''

		single_picture_url = single_picture_url_tuple[0]
		title = single_picture_url_tuple[1]
		title = re.sub(r'\W', '', title)
		referer = single_picture_url_tuple[2]
		domainpreg = re.compile(r'[\w]*\.[\w]*\.[\w]*')
		match = domainpreg.search(single_picture_url)
		if match:
			domain = match.group(0)
			if os.path.exists(domain)==False:  #先新建父目录 os.path.exists判断目录也就是文件夹是否存在，os.path.isfile则用来判断文件是否存在
				try:
					os.mkdir(domain)
					#print("%s:目录新建成功！" % domain)
				except IOError as e:
					print("Error : %s" % e)
			dirname = os.path.join(domain, title)
			if os.path.exists(dirname)==False:  #再根据标题创建子目录
				try:
					os.mkdir(dirname)
					#print("%s:目录新建成功！" % dirname)
				except IOError as e:
					print("Error : %s" % e)
			(http_path,filename) = os.path.split(single_picture_url) #这里是为了拿出那个filename……
			localpath = os.path.join(dirname, filename) #最后组合出保存为本地文件的完整路径
			#localpath = os.path.join(os.getcwd(), localpath)
			try:
				getdata = self.s.get(single_picture_url, timeout=10)
			except:
				print("获取远程图片(%s)失败！" % single_picture_url)
			#if getdata.status_code == requests.codes.ok:
				#print("尝试把图片保存到%s" % (localpath))
			with open(localpath,'wb') as pi:
				pi.write(getdata.content)
				#print("%s已经下载保存好了！让我们更新一下数据库的记录吧！" % filename)
				conn = sqlite3.connect('iwatu.db')
				cursor = conn.cursor()
				cursor.execute('update dlink set log=1 where dlink =?',(single_picture_url,))
				#print("更新记录成功！让我们再记录一下图片在本地的存储位置吧！")
				downloadtime = str(time.ctime())
				cursor.execute('insert into localpath(localpath,log,title,downloadtime,referer) values(?,?,?,?,?)', (localpath,0,title,downloadtime,referer))
					#print("%s下载完成！" % title)
			#else:
				#print(getdata.status_code)
		else:
			print("匹配域名失败！程序无法继续创建目录只能退出！")
			sys.exit() #目录都创建不了还下个P，退出算啦
		#清场
		if cursor:cursor.close()
		if conn:
			conn.commit()
			conn.close()





	def debug_view_db(self, tablename):
		'''这是数据表查询函数，用来查询数据表里的数据的，嘛，一般用来自检啦'''

		try:
			conn = sqlite3.connect('iwatu.db')
			cursor = conn.cursor()
			sql='select * from '+str(tablename)
			result = cursor.execute(sql).fetchall()
			return result
		except sqlite3.Error as e:
			print("Error : %s" % e)
		finally:
			if cursor:cursor.close
			if conn:
				conn.commit
				conn.close


	def debug_view_ip(self):
		'''这是IP查询函数，用来查询程序是否正常运作于代理模式中，正常返回IP地址，错误返回None'''

		ip = re.compile(r'[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*')
		whereismyip = 'http://whereismyip.com/'
		try:
			getdata = self.s.get(whereismyip, timeout=10)
		except:
			print("%s:获取远程页面失败！" % whereismyip)
			print("请检查代理是否正常运作")
			sys.exit() #代理模式失败了，应该是代理不行吧……

		#if getdata.status_code == requests.codes.ok:
		match = ip.search(getdata.text)
		if match:
			return(match.group(0))
		else:
			print("匹配IP地址失败！")	
