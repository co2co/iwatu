#_*_ coding:UTF-8 _*_
import re

'''
配置登陆账号和密码，格式如下：
----------------------------
'域名':('用户名','密码','登录地址')
----------------------------
'''
account = {
	'www.aaa.net':('username','password','http://www.aaa.com/member.php?mod=logging&action=login&loginsubmit=yes&frommessage&inajax=1'),
	'www.bbbb.com':('username','password','http://www.bbb.com/member.php?mod=logging&action=login&loginsubmit=yes&frommessage&inajax=1')
}


'''主题里可供采集的图片数小于这个数量则放弃采集'''
pic_limit = 6

'''程序能使用的最大线程数，小心，过大容易被封号封IP的'''
ThreadPool = 10

'''这是代理服务器设置文件，请按照格式设置以及确保代理服务器处于正常运作状态。不使用代理（直连）请留空'''
proxies = {
			'''http':'127.0.0.1:7777'''
}


'''自定义请求（post）的头部，达到伪装成浏览器的目的'''
headers = {
			'User-Agent':r'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36',
			'X-Forwarded-For':r'http://www.facebook.com/'
		}

#定义正则表达式
preg = {
		'aaa':{
						'listpreg':'<a href=\"([\w\.\-\/\:]*)\"\s*onclick=\"atarget\(this\)\"\s*title=\"[\w\.\-\/\:\?\=\&\%]*\"\s*class=\"z\"',
						'imagepreg':'<img .* zoomfile=\"([\w\.\-\/\:\?\=\&\%]*)\"',
						'titlepreg':'<title>(.*)<\/title>'
		},
		'bbb':{
						'listpreg':'<a href=\"([\w\.\-]*)\"\s*style=\"[\w\-\:\;\s]*\"',
						'imagepreg':'<img\s*src=\"([\w\/\s\.]*)\"\s*onload=\"[\w\(\,\'\s\)]*\"',
						'titlepreg':'<title>(.*)<\/title>'

		}
}
