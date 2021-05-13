"""
# My MongoDB ORM
"""
from flask_pymongo import PyMongo
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, SignatureExpired, BadSignature
from .utils import CodeManager, CodeScanner, IndicatorsCalculator, get_tags_local, get_last_commit_local


# 后续为get_users加入分页功能
class User:
    def __init__(self, user_name: str, passwd_hash: str, mongo: PyMongo, logout=True):
        self.__collection_name__ = 'users'
        self.user_name = user_name
        self.passwd_hash = passwd_hash
        self.logout = logout
        self.mongo = mongo

    @staticmethod
    def keys():
        return 'user_name', 'logout'

    def __getitem__(self, item):
        return getattr(self, item)

    @staticmethod
    def get_user(user_name, mongo):
        user = mongo.db.users.find_one({'user_name': user_name})
        if user is None:
            return None
        del user['_id']
        user['mongo'] = mongo
        user = User(**user)
        return user

    # 密码在前端加密一次
    def verify_password(self, password):
        return self.passwd_hash == password

    def save(self):
        user_data = dict(self)
        user_data['passwd_hash'] = self.passwd_hash
        self.mongo.db.users.insert_one(user_data)

    def generate_auth_token(self, expiration=3600):
        s = Serializer('SECRET_KEY', expires_in=expiration)
        # 生成一个以user_name为值，user_name为关键字的字典的加密令牌。令牌中同时加入了一个过期时间1h
        return s.dumps({'user_name': self.user_name})

    @staticmethod
    def verify_auth_token(token, mongo):
        s = Serializer('SECRET_KEY')
        try:
            data = s.loads(token)
        except SignatureExpired:
            # valid token, but expired
            return None
        except TypeError:
            return None
        except BadSignature:
            # invalid token
            return None
        user = User.get_user(data['user_name'], mongo)
        return user

    def log_out(self):
        myquery = {'user_name': self.user_name}
        new_values = {'$set': {'logout': True}}
        self.mongo.db.users.update_one(myquery, new_values)

    def log_in(self):
        myquery = {'user_name': self.user_name}
        new_values = {'$set': {'logout': False}}
        self.mongo.db.users.update_one(myquery, new_values)


class Project:
    def __init__(self, project_name: str, project_url: str, mongo: PyMongo, newest_version=None,
                 owners_list=None, versions_list=None):
        if versions_list is None:
            versions_list = []
        if owners_list is None:
            owners_list = []
        self.project_path = f'OSSprojects/{project_name}'
        self.__collection_name__ = 'projects'
        self.project_name = project_name
        self.project_url = project_url
        # 用来判断是否更新
        self.newest_version = newest_version
        self.owners_list = owners_list
        self.versions_list = versions_list
        self.mongo = mongo

    @staticmethod
    def keys():
        return 'project_name', 'project_url', 'newest_version', 'versions_list'

    def __getitem__(self, item):
        return getattr(self, item)

    @staticmethod
    def get_project(project_name, mongo):
        project = mongo.db.projects.find_one({'project_name': project_name})
        if project is None:
            return None
        del project['_id']
        project['mongo'] = mongo
        project = Project(**project)
        return project

    @staticmethod
    def get_projects(user_name, mongo):
        # 某个用户的项目列表
        # field只要和array中的任意一个value相同，该文档就会被检索
        projects_cursor = mongo.db.projects.find({'owners_list': {'$in': [user_name]}})
        projects_list = list(projects_cursor)
        # 用于展示用户的项目信息，暂时全部返回
        for i in range(len(projects_list)):
            projects_list[i]['_id'] = str(projects_list[i]['_id'])
        return projects_list

    @staticmethod
    def get_n_projects(user_name, mongo):
        n_projects = mongo.db.projects.count({'owners_list': {'$in': [user_name]}})
        return n_projects

    @staticmethod
    def get_paged_projects(user_name, page, page_size, mongo):
        skip = page_size * (page - 1)
        projects_cursor = mongo.db.projects.find({'owners_list': {'$in': [user_name]}}).limit(page_size).skip(skip)
        projects_list = list(projects_cursor)
        # 用于展示用户的项目信息，暂时全部返回
        for i in range(len(projects_list)):
            projects_list[i]['_id'] = str(projects_list[i]['_id'])
        return projects_list

    def save(self):
        code_manager = CodeManager(self.project_name, self.project_url, project_path=self.project_path)
        code_manager.clone()
        # versions_list: List of Version objects; self.versions_list: List of version_names
        # 拿到versions_list信息
        versions_list = get_tags_local(self.project_name)
        self.versions_list = [d['version_name'] for d in versions_list]
        if len(self.versions_list) == 0:
            self.versions_list = ['fake tag (no tags)']
        self.newest_version = self.versions_list[-1]
        data = dict(self)
        data['owners_list'] = self.owners_list
        self.mongo.db.projects.insert_one(data)
        # 对于versions_list, insert_many?
        version_values = [{'project_name': self.project_name,
                           'version_name': version['version_name'],
                           'scanned': False,
                           'calculated': False,
                           'calc_results': None,
                           'version_committer': version['version_committer'],
                           'version_time': version['version_time']}
                          for version in versions_list]
        if len(versions_list) > 0:
            self.mongo.db.versions.insert_many(version_values)
        else:
            commit_value = get_last_commit_local(self.project_name)
            self.mongo.db.versions.insert_one(commit_value)
        return True

    def owners_append(self, user_name):
        self.owners_list.append(user_name)
        self.update()
        myquery = {'project_name': self.project_name}
        new_values = {'$set': {'owners_list': self.owners_list}}
        self.mongo.db.projects.update_one(myquery, new_values)

    def update(self):
        code_manager = CodeManager(self.project_name, self.project_url, project_path=self.project_path)
        code_manager.update()
        versions_list = get_tags_local(self.project_name)
        version_names_list = [d['version_name'] for d in versions_list]
        newest_version_ = versions_list[-1]
        newest_version_name = newest_version_['version_name']
        idx = version_names_list.index(self.newest_version)
        new_versions = versions_list[(idx + 1):]

        myquery = {'project_name': self.project_name}

        new_values = {'$set': {'newest_version': newest_version_name, 'versions_list': version_names_list}}
        # 更新newest_version字段
        self.mongo.db.projects.update_one(myquery, new_values)
        # 插入新的version
        # TypeError: documents must be a non - empty list
        if len(new_versions) > 0:
            self.mongo.db.versions.insert_many(new_versions)
        return True

    def delete(self, user_name):
        self.owners_list.remove(user_name)
        if len(self.owners_list) == 0:
            code_manager = CodeManager(self.project_name, self.project_url, project_path=self.project_path)
            code_manager.remove()
            self.mongo.db.projects.delete_one({'project_name': self.project_name})
            self.mongo.db.versions.delete_many({'project_name': self.project_name})
        myquery = {'project_name': self.project_name}
        new_values = {'$set': {'owners_list': self.owners_list}}
        self.mongo.db.projects.update_one(myquery, new_values)
        return True


# 把Version独立出来作为Project的versions_list的对象，用来存储结果，分析在Project中调用
class Version:
    def __init__(self, project, version_name, mongo, version_committer, version_time, scanned=False, calculated=False,
                 calc_results=None):
        if calc_results is None:
            calc_results = {}
        self.project = project
        self.project_name = self.project.project_name
        self.version_name = version_name
        self.mongo = mongo
        self.version_committer = version_committer
        self.version_time = version_time
        self.scanned = scanned
        self.calculated = calculated
        self.version_scan_results_dir = f'OSSresults/{self.project_name}/java/{self.version_name}'
        self.calc_results = calc_results

    @staticmethod
    def keys():
        return 'project_name', 'version_name', 'scanned', 'calculated', 'calc_results', 'version_committer', 'version_time'

    def __getitem__(self, item):
        return getattr(self, item)

    @staticmethod
    def get_version(project_name, version_name, mongo):
        version = mongo.db.versions.find_one({'project_name': project_name, 'version_name': version_name})
        project = Project.get_project(project_name, mongo)
        if version is None:
            return None
        del version['_id']
        del version['project_name']
        version['project'] = project
        version['mongo'] = mongo
        return Version(**version)

    @staticmethod
    def get_versions(project_name, mongo):
        versions_cursor = mongo.db.versions.find({'project_name': project_name}).sort('version_time')
        versions_list = list(versions_cursor)
        # 用于展示用户的项目信息，暂时全部返回
        for i in range(len(versions_list)):
            versions_list[i]['_id'] = str(versions_list[i]['_id'])
            versions_list[i]['version_time'] = str(versions_list[i]['version_time'])
        return versions_list

    def scan(self):
        # 在project的的时候就存到mongodb？后面只需要去更新字段？
        cs = CodeScanner(self)
        cs.checkout()
        cs.scan()
        myquery = {'project_name': self.project_name, 'version_name': self.version_name}
        new_values = {'$set': {'scanned': True}}
        self.mongo.db.versions.update_one(myquery, new_values)
        return True

    def calc(self):
        # 在project的的时候就存到mongodb？后面只需要去更新字段？
        ci = IndicatorsCalculator(self)
        indicators = ci.calc_indicators()
        myquery = {'project_name': self.project_name, 'version_name': self.version_name}
        new_values = {'$set': {'calculated': True, 'calc_results': indicators}}
        self.mongo.db.versions.update_one(myquery, new_values)
        return True
