"""
Flask视图函数
"""
import json
import os

from flask import Flask, url_for, request, g
from flask_cors import CORS
from flask_httpauth import HTTPBasicAuth
from flask_pymongo import PyMongo
from pymongo import MongoClient

from ..errors import my_auth_error, api_message
from ..models import User, Project, Version
from ..utils import get_tags_github
from ..visualize import to_treemap, to_linechart

app = Flask(__name__)

mongodb_url = os.getenv('MONGODB_URL')
client = MongoClient(mongodb_url)
if os.getenv('RUN'):
    if 'run' not in client.list_database_names():
        db = client['run']
        foo_collection = db['foo']
        foo_collection.insert_one({'message': 'db created'})
    mongo = PyMongo(app, uri=f'{mongodb_url}/run')
    app.config['SECRET_KEY'] = 'mql'
    app.config['mongo'] = mongo
    if not User.get_user('mql', app.config['mongo']):
        common_user = User(user_name='mql', passwd_hash='python', mongo=app.config['mongo'])
        common_user.save()

CORS(app, supports_credentials=True)
auth = HTTPBasicAuth()
# 此处修改了httpauth包中的error_handler，直接返回json信息
auth.error_handler(my_auth_error)


@app.route('/api/treemap', methods=['POST'])
# @app.route('/api/treemap', methods=['GET'])
def query_treemap():
    project_name = request.json.get('project_name')
    version_name = request.json.get('version_name')
    # project_name = 'alibaba/cooma'
    # version_name = '0.4.0'
    version = app.config['mongo'].db.versions.find_one({'project_name': project_name, 'version_name': version_name})
    calc_results = version['calc_results']
    c = to_treemap(calc_results, project_name, version_name)
    treemap_opts_str = c.dump_options_with_quotes()
    data = {'treemap_opts': json.loads(treemap_opts_str)}
    return api_message(200, code=1000, data=data)


@app.route('/api/linechart', methods=['POST'])
def query_linechart():
    project_name = request.json.get('project_name')
    versions = app.config['mongo'].db.versions.find({'project_name': project_name})
    versions_data = [{
        'version_name': version['version_name'],
        'complexity': version['calc_results']['complexity'],
        'maintainability': version['calc_results']['maintainability'],
        'testability': version['calc_results']['testability'],
        'readability': version['calc_results']['readability'],
        'reusability': version['calc_results']['reusability'],
        'inheritance': version['calc_results']['inheritance'],
    }
        for version in versions if version['calc_results']]
    c = to_linechart(versions_data, project_name)
    linechart_opts_str = c.dump_options_with_quotes()
    data = {'linechart_opts': json.loads(linechart_opts_str)}
    return api_message(200, code=1000, data=data)


@app.route('/api/users', methods=['POST'])
def new_user():
    user_name = request.json.get('user_name')
    passwd_hash = request.json.get('passwd_hash')
    if user_name is None or passwd_hash is None:
        # missing arguments
        return api_message(400)
    user = User.get_user(user_name, app.config['mongo'])
    if user is not None:
        return api_message(400, message='there has been a user with the same name')
    try:
        user = User(**request.json, mongo=app.config['mongo'])
        user.save()
    except TypeError as e:
        return api_message(400, message=str(e))
    new_info = {'Location': url_for('get_user', user_name=user.user_name, _external=True)}
    response_data, http_code = api_message(201)
    return response_data, http_code, new_info


@app.route('/api/users/<user_name>')
def get_user(user_name):
    user = User.get_user(user_name, app.config['mongo'])
    if user is None:
        return api_message(400)
    return dict(user), 200


@auth.verify_password
def verify_password(username, client_password):
    # 本函数可用来设置g.user
    token = request.headers.get('Token')
    user = User.verify_auth_token(token, app.config['mongo'])
    if user is not None:
        # 为后面应用里使用user做铺垫
        g.user = user
        return True
    else:
        return False


@app.route('/api/token', methods=['POST'])
def get_auth_token():
    user_name = request.json.get('username')
    passwd_hash = request.json.get('password')
    valid_time = request.json.get('valid_time')
    # 用户名和密码判空留给前端
    # if user_name is None or passwd_hash is None:
    #     # missing arguments
    #     return api_error(400, 'username and password required', code=1001)
    # user = User.get_user(user_name, app.config['mongo'])
    user = User.get_user(user_name, app.config['mongo'])
    if not user:
        return api_message(404, message=f'no user named {user_name}')
    if not user.verify_password(passwd_hash):
        return api_message(401, message=f'wrong passwd')
    if not user.logout:
        return api_message(401, message=f'{user_name} already login')
    if valid_time:
        token = user.generate_auth_token(valid_time)
    else:
        token = user.generate_auth_token()
    data = {'token': token.decode('utf-8')}
    return api_message(200, 1000, data=data)


@app.route('/api/userinfo')
@auth.login_required
def get_user_info():
    data = dict(g.user)
    data['token'] = request.headers.get('Token')
    data['roles'] = 'normal'
    data['avatar'] = 'https://wpimg.wallstcn.com/f778738c-e4f8-4870-b634-56703b4acafe.gif'
    return api_message(200, 1000, data=data)


@app.route('/user/logout', methods=['POST'])
@auth.login_required
def user_logout():
    # g.user.log_out()
    data = {'message': f'{g.user.user_name} log out'}
    return api_message(200, 1000, data=data)


@app.route('/api/resource')
@auth.login_required
def get_resource():
    return api_message(200, 1000, message='Hello, %s!' % g.user.user_name)


# 尽量在view中进行逻辑处理，方便发送错误信息
# 考虑clone出错等情况
@app.route('/api/projects', methods=['POST'])
@auth.login_required
def new_project():
    request_dict = request.json
    project = Project.get_project(request_dict['project_name'], app.config['mongo'])
    # 前端检查：项目不存在
    if project is None:
        request_dict['owners_list'] = [g.user.user_name]
        request_dict['mongo'] = app.config['mongo']
        project = Project(**request_dict)
        project.save()
    else:
        # 项目存在且已经在user名下
        if g.user.user_name in project.owners_list:
            message = f'User {g.user.user_name} has added project {project.project_name}.'
            return api_message(400, message=message)
        # 项目存在且不在user名下，则增加名字并更新项目
        project.owners_append(g.user.user_name)
    new_info = {'Location': url_for('get_project', project_name=project.project_name, _external=True)}
    response_data, http_code = api_message(201, code=1000)
    return response_data, http_code, new_info


@app.route('/api/projects', methods=['GET'])
@auth.login_required
def get_projects():
    # 通过user来选择可以获取的列表，通过jsonify才可以正常返回
    data = {'projects_list': Project.get_projects(g.user.user_name, app.config['mongo'])}
    return api_message(200, 1000, data=data)


@app.route('/api/paged_projects', methods=['GET'])
@auth.login_required
def get_paged_projects():
    page = int(request.args.get('page'))
    page_size = int(request.args.get('limit'))
    paged_projects = Project.get_paged_projects(g.user.user_name, page, page_size, app.config['mongo'])
    total = Project.get_n_projects(g.user.user_name, app.config['mongo'])
    data = {'projects_list': paged_projects, 'total': total}
    return api_message(200, 1000, data=data)


@app.route('/api/demo_projects', methods=['GET'])
def get_demo_projects():
    # 通过user来选择可以获取的列表，通过jsonify才可以正常返回
    # mql是访客的代称
    data = {'projects_list': Project.get_projects('mql', app.config['mongo'])}
    return api_message(200, 1000, data=data)


@app.route('/api/projects/<path:project_name>', methods=['GET'])
@auth.login_required
def get_project(project_name):
    project = Project.get_project(project_name, app.config['mongo'])
    # 通过user来判断是否可以获取
    if project is None:
        return api_message(404, message=f"The user {g.user.user_name} hasn't added the project {project_name}.")
    if g.user.user_name in project.owners_list:
        data = dict(project)
        return api_message(200, 1000, data=data)
    else:
        return api_message(403, message=f"The user {g.user.user_name} hasn't added the project {project_name}.")


# 更新项目
# 现在都是成功更新，要学习如何抛出错误
@app.route('/api/projects/<path:project_name>', methods=['PUT'])
@auth.login_required
def update_project(project_name):
    versions_list = get_tags_github(project_name)
    # 没有版本则直接返回，维持本地的fake tag
    if len(versions_list) == 0:
        return api_message(200, code=1000, message='got the newest version')
    project = Project.get_project(project_name, app.config['mongo'])
    newest_version_ = versions_list[-1]
    if project.newest_version != newest_version_:
        project.update()
        new_info = {'Location': url_for('get_project', project_name=project.project_name, _external=True)}
        response_data, http_code = api_message(201, 1000,
                                               message=f'updated {project_name} to newest version {newest_version_}')
        return response_data, http_code, new_info
    else:
        return api_message(200, code=1000, message='got the newest version')


@app.route('/api/projects/<path:project_name>', methods=['DELETE'])
@auth.login_required
def delete_project(project_name):
    # 通过user来来判断是否可删除
    project = Project.get_project(project_name, app.config['mongo'])
    if project is None or (g.user.user_name not in project.owners_list):
        return api_message(404, message=f"The user {g.user.user_name} hasn't added the project {project_name}.")
    project.delete(g.user.user_name)
    # 直接添加message字段，可以在前端显示
    return api_message(200, 1000, message=f'{project_name} has been deleted')


# 获取version信息，version中可能有不合法的字符,所以用json来传
@app.route('/api/version', methods=['GET'])
@auth.login_required
def get_version():
    request_dict = request.json
    # request_dict = dict(project_name='alibaba/cooma', version_name='0.4.0')
    version = Version.get_version(request_dict['project_name'], request_dict['version_name'], app.config['mongo'])
    # 通过user来判断是否可以获取
    # 没找到version
    if version is None:
        return api_message(404)
    if 'mql' in version.project.owners_list:
        data = dict(version)
        return api_message(200, 1000, data=data)


# 扫描、计算version的指标数值
@app.route('/api/version', methods=['PUT'])
@auth.login_required
def get_version_results():
    request_dict = request.json
    version = Version.get_version(request_dict['project_name'], request_dict['version_name'], app.config['mongo'])
    # 通过user来判断是否可以获取
    if version is None:
        return api_message(404)
    if g.user.user_name in version.project.owners_list:
        if not version.scanned:
            version.scan()
        if not version.calculated:
            version.calc()
    return api_message(201, code=1000, message='finished scanning and claculating task')


# 获取某个项目的version信息
@app.route('/api/versions/<path:project_name>', methods=['GET'])
@auth.login_required
def get_versions(project_name):
    # project_name = request.json.get('project_name')
    # 通过user来选择可以获取的列表，通过jsonify才可以正常返回
    data = {'versions_list': Version.get_versions(project_name, app.config['mongo'])}
    return api_message(200, code=1000, data=data)


if __name__ == '__main__':
    app.run()
