# mroget
1. config.py ： 全局配置文件，包括数据库配置，目标位置配置，时差配置。
2. mrnicfg.csv ： MRO北向服务器配置信息。
3. *filegetter_mr.py* ： MRO北向文件获取主程序。
4. ftpext.py : FTP文件下载组件，供filegetter_mr.py调用。
5. *mrofileSender.py* ： MRO文件分发处理程序
6. mroHandler.py ： MRO单文件处理组件
7. mroparser5.py ： MRO单文件解析组件
8. mroCounter.py ： MRO解析后特殊样本统计组件

# docs
[disign docments](https://github.com/zengqingbo/mroget/blob/master/docs/index.md)
