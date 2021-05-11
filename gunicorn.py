# 并行工作进程数
workers = 4
# 指定每个工作者的线程数
threads = 2
# 监听外网端口5000
bind = '0.0.0.0:5000'
# 设置守护进程,将进程交给supervisor管理
daemon = True
# 设置最大并发量
worker_connections = 2000
# 设置进程文件目录
pidfile = 'log/gunicorn.pid'
# 设置访问日志和错误信息日志路径
accesslog = 'log/gunicorn_acess.log'
errorlog = 'log/gunicorn_error.log'
# 设置日志记录水平
loglevel = 'info'
