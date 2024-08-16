"""
依赖
----------------------
git-python

需求
----------------------
Python3.6 + (经过测试>> 3.6, 3.8 )

要给出的数据
----------------------
1. git.exe位置
2. 仓库目录
3. commit回溯次数（要一直回溯到服务器文件的所在commit），默认为1。
4. 服务器IP、账户、密码
5. 服务器项目目录

使用流程
----------------------
1. 填写数据
2. 运行
3. 查看展示出的文件列表
4. 确认同步

计划
----------------------
1. 将配置信息独立到另外一个py文件中，在主文件导入。使用时只需要修改配置文件        ✔
2. 支持作为命令行指令来运行，逐步向用户索求所需信息。（git位置只主动索要一次）

BUG
----------------------
1. 遇到新创建的目录内的文件时，无法自动在FTP服务器执行目录创建。                 ✔

"""
from config import *
import os
os.environ['GIT_PYTHON_GIT_EXECUTABLE'] = GIT_PATH    # 设置 git.exe 位置

from git import Repo
from ftplib import FTP
import ftplib


def get_parent_commit(commit, level=1):
    if commit.parents:
        parent_commit = commit.parents[0]
    
        if level >= 2:
            return get_parent_commit(parent_commit, level-1)
        else:
            return parent_commit
    else:
        raise Exception("该Commit不存在父级！")
        

def create_missing_directories(ftp, initial_path, path):
   """
   Given an FTP connection and a path, create any missing directories along the path.
   
   正常情况返回 False，报错返回错误对象。
   """
   # 分割路径
   directories = path.strip('/').split('/')
   # 如果路径以'/'结束，添加一个空目录来处理根目录
   if path.endswith('/'):
       directories.append('')
 
   # 初始化当前路径
   current_path = ''

   for directory in directories:
       if directory:
           try:
               # 尝试进入下一级目录
               ftp.cwd(directory)
               current_path += f"/{directory}"
           except ftplib.error_perm as e:
               # 如果目录不存在，尝试创建它
               if '550' in str(e):  # 550表示目录不存在
                   try:
                       ftp.mkd(directory)  # 创建目录
                       ftp.cwd(directory)  # 进入新创建的目录
                       current_path += f"/{directory}"
                       print(f"Directory {current_path} created.")
                   except ftplib.error_perm as e:
                       print(f"Failed to create directory {directory}: {e}")
                       ftp.cwd(initial_path)    # 返回前重置路径
                       return e
                   except Exception as e:
                       return e
               else:
                   # 如果是其他错误，重新抛出
                   return e
           except Exception as e:
               return e
 
   # 如果所有目录都创建成功，返回False
   ftp.cwd(initial_path)    # 返回前重置路径
   return False


# 打开Git仓库
repo_path = REPO_PATH                                                           # 不要删除这个变量，因为它被用了不止一次。该赋值能降低与配置文件的耦合度。
repo = Repo(repo_path)                          # 设置仓库目录

# 获取最新提交
latest_commit = repo.head.commit

# 获取上一个提交
previous_commit = get_parent_commit(latest_commit, COMMIT_RETREAT_TIMES)

# 获取文件变更
diff = previous_commit.diff(latest_commit)

# 获取文件变更
files = []
for change in diff:
    print(f'Change: {change.change_type}, File: {change.a_path}')
    files.append(change.a_path)

print("========是否继续？========")
os.system("pause")

# 连接到服务器
ftp = FTP(FTP_ADDRESS)                        
ftp.login(user=FTP_ACCOUNT, passwd=FTP_PASSWORD)               # 登录
initial_path = ftp.pwd()

print("路径为：", initial_path)
os.system("pause")

error_log = {}

n = 0
for filepath in files:
    n += 1
    print("正在同步第 %s 个文件..." % n)
    source_file = repo_path + filepath      
    target_file = PROJECT_DIR + filepath
    print(target_file)
    
    # 确保不存在的路径都被自动创建
    result = create_missing_directories(
                ftp, 
                initial_path,
                os.path.dirname(target_file))
                
    # 写入错误日志
    if result:
        error_log[filepath] = str(result)

    try:
        # 上传文件
        with open(source_file, 'rb') as file:
            ftp.storbinary('STOR %s' % target_file, file)
    except Exception as e:
        error_log[filepath] = str(e)

print("========文件更新完成！========\n\n")
print("========错误日志：=========")
print("更新失败的文件数量: ", len(error_log))
for k, v in error_log.items():
    print("文件: ", k)
    print("    错误: ", v)
os.system("pause")
