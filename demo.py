#_*_coding:utf-8_*_
from iwatu import iWaTu
import time



def print_it(table):
		for each_record in table:
			print(each_record)


def main():

	target = [
				'http://www.sexinsex.net/bbs/forum-249-1.html',  #这些是虚构网址，请用实际存在的网址替换
				'http://www.sexinsex.net/bbs/forum-432-1.html' 
				]

	iwatu = iWaTu('www.sexinsex.net')  #实例化类并且传入域名作为参数
	start = time.time()
	for each_link in target:
		iwatu.handle_pagelist(each_link,1)
	print("------------------------列表页分析完成------------------------")
	iwatu.handle_subjectpage()
	print("------------------------主题页分析完成------------------------")
	iwatu.handle_download_picture()
	print("------------------------图片下载完成------------------------")

	urls = iwatu.debug_view_db('urls')
	#print_it(urls)
	dlink_items = iwatu.debug_view_db('dlink')
	#print_it(dlink_items)
	localpath_items = iwatu.debug_view_db('localpath')
	#print_it(localpath_items)
	print("总共分析出了%s个主题地址，包含%s幅图片可供下载，其中本地已经下载了%s幅" % (len(urls),len(dlink_items),len(localpath_items)))
	#iwatu.login_bbs('http://www.sexinsex.com')
	end = time.time()
	print("耗时 %0.2f 秒" % (end - start))

if __name__ == '__main__':
			main()		
