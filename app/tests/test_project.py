"""
用户项目管理模块测试用例
"""
import os
import sys
import unittest

from flask_pymongo import PyMongo
from pymongo import MongoClient

from utils import UtilsTestCase

sys.path.append('.')
from app.models import User, Project
from app.main.views import app


class ProjectTestCase(UtilsTestCase):
    # 重载setUp方法，每个用例方法的执行都会重复进行setUp和tearDown
    def setUp(self):
        # 创建数据库和表
        mongodb_url = os.getenv('MONGODB_URL')
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
        # 创建一个用户user
        user = User(user_name='mql', passwd_hash='python', mongo=self.mongo)
        user.save()
        # 添加项目
        proj = Project('mqlabc/learngit', project_url='https://github.com/mqlabc/learngit', mongo=self.mongo,
                       owners_list=['mql', 'lml'])
        proj.save()
        # 创建另一个用户user1
        user1 = User(user_name='lml', passwd_hash='python', mongo=self.mongo)
        user1.save()

        self.client = app.test_client()  # 创建测试客户端
        self.runner = app.test_cli_runner()  # 创建测试命令运行器

        app.config.update(TESTING=True, mongo=self.mongo)

    def test_0_new_project(self):
        token = self.login({'username': 'mql', 'password': 'python'})
        proj_info = {'project_name': 'alibaba/cooma', 'project_url': 'https://github.com/alibaba/cooma'}
        response = self.client.post('/api/projects', headers=UtilsTestCase.get_api_headers(token), json=proj_info)

        # FTS2-1：用户添加系统中不存在的项目
        self.assertTrue(response.status_code == 201)
        url = response.headers.get('Location')
        self.assertIn('alibaba/cooma', url)
        self.assertTrue(len(os.listdir('OSSprojects/alibaba/cooma')) != 0)
        self.assertTrue(['mql'] == Project.get_project('alibaba/cooma', self.mongo).owners_list)

        # FTS2-3：用户添加系统中存在且属于自己的项目
        response = self.client.post('/api/projects', headers=UtilsTestCase.get_api_headers(token), json=proj_info)
        self.assertTrue(response.status_code == 400)

        # FTS2-2：用户添加系统中存在且不属于自己的项目
        token1 = self.login({'username': 'lml', 'password': 'python'})
        proj_info = {'project_name': 'alibaba/cooma', 'project_url': 'https://github.com/alibaba/cooma'}
        response = self.client.post('/api/projects', headers=UtilsTestCase.get_api_headers(token1), json=proj_info)
        self.assertTrue(response.status_code == 201)
        url = response.headers.get('Location')
        self.assertIn('alibaba/cooma', url)
        self.assertIn('lml', Project.get_project('alibaba/cooma', self.mongo).owners_list)

    def test_1_get_projects(self):
        # FTS2-4：获取项目列表
        token = self.login({'username': 'mql', 'password': 'python'})
        response = self.client.get('/api/projects', headers=UtilsTestCase.get_api_headers(token))
        self.assertTrue(response.status_code == 200)
        data = response.json
        projects = [project['project_name'] for project in data.get('data').get('projects_list')]
        self.assertIn('mqlabc/learngit', projects)

    def test_2_update_projects(self):
        # FTS2-5：更新已为最新版本的项目
        token = self.login({'username': 'mql', 'password': 'python'})
        response = self.client.put('/api/projects/mqlabc/learngit', headers=UtilsTestCase.get_api_headers(token))
        self.assertTrue(response.status_code == 200)
        self.assertIn('got the newest version', response.get_data(as_text=True))
        self.assertEqual({'v1.0', 'v2.0'}, set(self.get_versions('mqlabc/learngit')))

        # FTS2-6：更新不是最新版本的项目
        # 修改project
        myquery = {'project_name': 'mqlabc/learngit'}
        newest_version_name = 'v1.0'
        version_names_list = ['v1.0']
        new_values = {'$set': {'newest_version': newest_version_name, 'versions_list': version_names_list}}
        # 更新newest_version字段
        self.mongo.db.projects.update_one(myquery, new_values)

        response = self.client.put('/api/projects/mqlabc/learngit', headers=UtilsTestCase.get_api_headers(token))
        self.assertTrue(response.status_code == 201)
        self.assertIn('updated', response.get_data(as_text=True))
        self.assertEqual({'v1.0', 'v2.0'}, set(self.get_versions('mqlabc/learngit')))

    def test_3_delete_project(self):
        # FTS2-7：删除自己拥有的项目
        token = self.login({'username': 'mql', 'password': 'python'})
        response = self.client.delete('/api/projects/mqlabc/learngit', headers=UtilsTestCase.get_api_headers(token))
        self.assertTrue(response.status_code == 200)
        self.assertIn('deleted', response.get_data(as_text=True))
        self.assertNotIn('mql', Project.get_project('mqlabc/learngit', self.mongo).owners_list)

        # FTS2-8：删除自己没有的项目
        response = self.client.delete('/api/projects/mqlabc/learngit', headers=UtilsTestCase.get_api_headers(token))
        self.assertTrue(response.status_code == 404)
        self.assertIn("hasn't added the project", response.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
