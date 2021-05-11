import sys
import os
import shutil
import stat
import unittest

from flask_pymongo import PyMongo
from pymongo import MongoClient

sys.path.append('..')
from app.main.views import app
from app.models import User, Version


def readonly_handler(func, path, execinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)


class UtilsTestCase(unittest.TestCase):

    def setUp(self):
        mongodb_url = os.getenv('MONGODB_URL')
        # 创建数据库和表
        mongo_client = MongoClient(mongodb_url)
        if 'test' not in mongo_client.list_database_names():
            db = mongo_client['test']
            foo_collection = db['foo']
            foo_collection.insert_one({'message': 'db created'})
        else:
            mongo_client.drop_database('test')
            db = mongo_client['test']
            foo_collection = db['foo']
            foo_collection.insert_one({'message': 'db created'})
        self.mongo_client = mongo_client
        self.mongo = PyMongo(app, uri=f'{mongodb_url}/test')
        # 创建一个用户
        user = User(user_name='mql', passwd_hash='python', mongo=self.mongo)
        user.save()

        self.client = app.test_client()  # 创建测试客户端
        self.runner = app.test_cli_runner()  # 创建测试命令运行器

        app.config.update(TESTING=True, mongo=self.mongo)

    def tearDown(self):
        self.mongo_client.drop_database('test')
        if os.path.exists('OSSprojects'):
            shutil.rmtree('OSSprojects', onerror=readonly_handler)
        if os.path.exists('OSSresults'):
            shutil.rmtree('OSSresults', onerror=readonly_handler)

    # 返回token的登录工具类
    def login(self, name_passwd):
        response = self.client.post('/api/token', json=name_passwd)
        data = response.json
        return data.get('data').get('token')

    # def test_get_token(self):
    #     token = self.login({'username': 'mql', 'password': 'python'})
    #     self.assertIsNotNone(token)

    @staticmethod
    def get_api_headers(token):
        return {
            'Token': token,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

    def get_versions(self, project_name):
        versions = Version.get_versions(project_name, self.mongo)
        return [version['version_name'] for version in versions]


if __name__ == '__main__':
    unittest.main()
