import re
import os
import sys
import json
import time
import datetime
import requests
from .cq_calc import cq_calculator
from subprocess import getstatusoutput


def run_cmd(cmd, re_pattern=None):
    # print('*' * 80)
    # print(f'path: {os.getcwd()}')
    # print(f'command: {cmd}')
    print(f'\nrunning: {cmd}')
    code, stdout = getstatusoutput(cmd)
    # print('output:')
    lines = []
    for line in stdout.split('\n'):
        if line:
            # if re_pattern:
            #     s = re.search(re_pattern, line.strip())
            #     if s:
            #         print(s.group(0))
            # else:
            #     print(line.strip())
            lines.append(line.strip())
    # print('*' * 80)
    assert code == 0, f'command "{cmd}" gets error:\n{lines}'
    return lines


def to_time_str(t):
    # 保留数字
    t = ''.join(list(filter(str.isdigit, t)))[:14]
    return time.strftime('%Y/%m/%d %H:%M:%S', time.strptime(t, '%Y%m%d%H%M%S'))


def get_tags_github(full_name):
    """
    获取github项目的版本号，并将版本按照committer date排序
    :param full_name: 项目全名
    :return: 按照committer date排序的版本号
    """
    token = "e6e390e1e659c7fc921548752ee8932fcace2cb8"
    headers = {'Authorization': f'token {token}'}
    version_time = []
    i = 1
    while True:
        r = requests.get(
            f'https://api.github.com/repos/{full_name}/tags?page={i}&per_page=100',
            headers=headers)
        tags_of_page = json.loads(r.text)
        if len(tags_of_page) == 0:
            break
        for tag in tags_of_page:
            version = tag['name'].replace('/', '_')
            version_time.append(version)
        i = i + 1
    # 默认按时间正序
    return version_time[::-1]


def get_tags_local(full_name):
    """
    获取github项目的版本号，并将版本按照committer date排序，但在本项目中前端重复进行了排序
    :param full_name: 项目全名
    :return: 按照committer date排序的版本号
    """
    cmd0 = f'cd OSSprojects/{full_name}'
    # %D(tag name) %cn(committer name)<%cE(committer email)> %ct(committer date)
    cmd1 = 'git log --tags --decorate --simplify-by-decoration --pretty="%D,%cn<%cE>,%ct"'
    cmd = f'{cmd0} & {cmd1}'
    lines = run_cmd(cmd)
    versions_list = []
    for line in lines:
        # if line.startswith('HEAD'):
        #     # line = line[6:]
        #     line = ','.join(line.split(',')[-3:])
        version_name, committer, time_str = line.split(',')[-3:]
        if not version_name.startswith('tag: '):
            version_name_ = [s for s in line.split(', ') if s.startswith('tag: ')]
            if len(version_name_) > 0:
                version_name = version_name_[0]
        if len(version_name) == 0:
            continue
        versions_list.append({'version_name': version_name[5:],
                              'version_committer': committer,
                              'version_time': datetime.datetime.fromtimestamp(int(time_str)),
                              'project_name': full_name,
                              })
    # 默认按时间正序
    versions_list.sort(key=lambda d: d['version_time'])
    return versions_list


def get_last_commit_local(full_name):
    """
    获取github项目的版本号，并将版本按照committer date排序
    :param full_name: 项目全名
    :return: 按照committer date排序的版本号
    """
    cmd0 = f'cd OSSprojects/{full_name}'
    # %D(tag name) %cn(committer name)<%cE(committer email)> %ct(committer date)
    cmd1 = 'git log --decorate --simplify-by-decoration --pretty="%D,%cn<%cE>,%ct"'
    cmd = f'{cmd0} & {cmd1}'
    lines = run_cmd(cmd)
    committer_name, time_str = lines[0].split(',')[-2:]
    last_commit = {'version_name': 'fake tag (no tags)',
                   'version_committer': committer_name,
                   'version_time': datetime.datetime.fromtimestamp(int(time_str)),
                   'project_name': full_name,
                   }
    return last_commit


class CodeManager:
    def __init__(self, project_name: str, project_url: str, project_path):
        self.project_name = project_name
        self.project_url = project_url
        self.project_path = project_path

    def clone(self):
        # 已经存在，不再clone
        if os.path.exists(self.project_path):
            return
        # 仅支持github的项目
        project_url = f"https://github.com.cnpmjs.org/{self.project_name}"
        args = ["git", "clone", "--progress", project_url, f"{self.project_path}"]
        cmd = " ".join(args)
        run_cmd(cmd)

    def update(self):
        args = ["cd", f"{self.project_path}", "&", "git", "pull", "--progress"]
        cmd = " ".join(args)
        run_cmd(cmd)

    def remove(self):
        if sys.platform.startswith('win'):
            # rmdir /s（非空） /q（去掉确认）
            args = ["cd", "OSSprojects", "&", "rd", "/s", "/q", f"{self.project_name}".replace('/', '\\')]
            cmd = " ".join(args)
            run_cmd(cmd)
        else:
            args = ["cd", f"OSSprojects", "&", "rm", "-rf", f"{self.project_path}"]
            cmd = " ".join(args)
            run_cmd(cmd)


class CodeScanner:
    def __init__(self, version):
        self.version = version
        self.project = version.project

    def checkout(self):
        if self.version.version_name != 'fake tag (no tags)':
            args = ["cd", f"{self.project.project_path}", "&", "git", "checkout", f"{self.version.version_name}"]
            cmd = " ".join(args)
            run_cmd(cmd)

    def scan(self):
        # 已经存在，不再扫描
        if os.path.exists(f'OSSresults/{self.project.project_name}/java/{self.version.version_name}'):
            return
        # 将扫描结果放到'A/B'(project_name)中的'A'(maintainer)目录下
        maintainer, proj_short_name = self.project.project_name.split('/')
        # cleanProject=true 清除在目录中留下痕迹，避免影响git操作
        # *=false 关闭一些冗余功能
        args = ["SourceMeterJava",
                f"-projectName={proj_short_name}",
                f"-projectBaseDir={self.project.project_path}",
                f"-resultsDir=OSSresults/{maintainer}",
                f'-currentDate="{self.version.version_name}"',
                "-cleanProject=true",
                '-runRTEHunter=false',
                '-runAndroidHunter=false',
                '-runMetricHunter=false',
                '-runVulnerabilityHunter=false',
                '-runFB=false',
                '-runUDM=false',
                '-runFaultHunter=false']
        cmd = " ".join(args)
        run_cmd(cmd)


# 构造所有要计算的粒度（各级目录、文件），用来找到children
def generate_whole_set(index):
    whole_set = set()
    for path in index:
        frags = path.split('/')
        for i in range(len(frags), 0, -1):
            p_path = '/'.join(frags[:i])
            if p_path not in whole_set:
                whole_set.add(p_path)
            else:
                # 已经出现过这个path，则path的前面部分也出现过，直接跳出
                break
    return whole_set


# 找到子对象
def find_children(parent_path, whole_set):
    f = filter(lambda s: '/'.join(s.split('/')[:-1]) == parent_path, whole_set)
    return f


# 开始计算，是否可以参考胡正华老师的做法改成迭代计算？
def convert(target, proj_path, whole_set, fine_grained_dict):
    maintainability, testability, readability, reusability, inheritance, complexity = 0, 0, 0, 0, 0, 0
    for path in find_children(proj_path, whole_set):
        child = {"name": path, "children": []}
        target['children'].append(child)
        # 如果已经到达类粒度
        if path in fine_grained_dict:
            child['maintainability'] = fine_grained_dict[path]['maintainability']
            maintainability += fine_grained_dict[path]['maintainability']

            child['testability'] = fine_grained_dict[path]['testability']
            testability += fine_grained_dict[path]['testability']

            child['readability'] = fine_grained_dict[path]['readability']
            readability += fine_grained_dict[path]['readability']

            child['reusability'] = fine_grained_dict[path]['reusability']
            reusability += fine_grained_dict[path]['reusability']

            child['inheritance'] = fine_grained_dict[path]['inheritance']
            inheritance += fine_grained_dict[path]['inheritance']

            child['complexity'] = fine_grained_dict[path]['complexity']
            complexity += fine_grained_dict[path]['complexity']
        else:
            maintainability_, testability_, readability_, reusability_, inheritance_, complexity_ = \
                convert(child, path, whole_set, fine_grained_dict)
            maintainability += maintainability_
            testability += testability_
            readability += readability_
            reusability += reusability_
            inheritance += inheritance_
            complexity += complexity_
    target['maintainability'] = maintainability
    target['testability'] = testability
    target['readability'] = readability
    target['reusability'] = reusability
    target['inheritance'] = inheritance
    target['complexity'] = complexity
    return maintainability, testability, readability, reusability, inheritance, complexity


def convert2tree(target, proj_path, whole_set, class_maintainability_dict):
    """
    将类粒度的可维护性指标转换为包含各粒度质量指标的树形结构
    :param target: {"name": project_version, "children": []}，具有此结构的Python字典，project_version为代表项目版本的字符串
    :param proj_path: 即项目路径（名称）
    :param whole_set: 需要计算的实体集合
    :param class_maintainability_dict: 维护从类名到对应可维护性值映射的字典
    :return: 本项目的可维护性值
    """
    maintainability = 0
    for child_path in find_children(proj_path, whole_set):
        child = {"name": child_path, "children": []}
        target['children'].append(child)
        # 如果已经到达类粒度
        if child_path in class_maintainability_dict:
            child['maintainability'] = class_maintainability_dict[child_path]['maintainability']
            maintainability = maintainability + class_maintainability_dict[child_path]['maintainability']
        else:
            maintainability = maintainability + convert2tree(child, child_path, whole_set, class_maintainability_dict)
    target['maintainability'] = maintainability
    return maintainability


class IndicatorsCalculator:
    def __init__(self, version):
        self.version = version
        self.project = version.project
        self.version_scan_results_dir = version.version_scan_results_dir

    def calc_indicators(self):
        proj_short_name = self.project.project_name.split('/')[-1]
        # 注意此处是short_name
        df = cq_calculator(self.version_scan_results_dir, proj_short_name)
        index = df.index
        # 将df转换为dict
        fgd = df.to_dict('index')
        target = {'name': f'{self.project.project_name}({self.version.version_name})', 'children': []}
        whole_set = generate_whole_set(index)
        convert(target, proj_short_name, whole_set, fgd)
        # 删除冗余的扫描结果，节省磁盘空间
        if sys.platform.startswith('win'):
            # rmdir /s（非空） /q（去掉确认）
            cd_cmd = f"cd OSSresults\\{self.project.project_name}\\java & "
            # 新建version结果的备份文件夹
            md_cmd = cd_cmd + f'mkdir {self.version.version_name}_backup\\sourcemeter\\temp'
            run_cmd(md_cmd)
            # mv三个文件到备份文件夹
            mv_cmd1 = cd_cmd + f'move {self.version.version_name}\\{proj_short_name}-Class.csv {self.version.version_name}_backup'
            run_cmd(mv_cmd1)
            mv_cmd2 = cd_cmd + f'move {self.version.version_name}\\{proj_short_name}-Method.csv {self.version.version_name}_backup'
            run_cmd(mv_cmd2)
            mv_cmd3 = cd_cmd + f'move {self.version.version_name}\\sourcemeter\\temp\\{proj_short_name}-PMD.xml {self.version.version_name}_backup\\sourcemeter\\temp'
            run_cmd(mv_cmd3)
            # 删除原文件夹
            del_cmd = cd_cmd + f'rd /s /q {self.version.version_name}'
            run_cmd(del_cmd)
            # 重命名
            ren_cmd = cd_cmd + f'ren {self.version.version_name}_backup {self.version.version_name}'
            run_cmd(ren_cmd)
        else:
            # rmdir /s（非空） /q（去掉确认）
            cd_cmd = f"cd OSSresults/{self.project.project_name}/java & "
            # 新建version结果的备份文件夹
            md_cmd = cd_cmd + f'mkdir -p {self.version.version_name}_backup/sourcemeter/temp'
            run_cmd(md_cmd)
            # mv三个文件到备份文件夹
            mv_cmd1 = cd_cmd + f'mv {self.version.version_name}/{proj_short_name}-Class.csv {self.version.version_name}_backup'
            run_cmd(mv_cmd1)
            mv_cmd2 = cd_cmd + f'mv {self.version.version_name}/{proj_short_name}-Method.csv {self.version.version_name}_backup'
            run_cmd(mv_cmd2)
            mv_cmd3 = cd_cmd + f'mv {self.version.version_name}/sourcemeter/temp/{proj_short_name}-PMD.xml {self.version.version_name}_backup/sourcemeter/temp'
            run_cmd(mv_cmd3)
            # 删除原文件夹
            del_cmd = cd_cmd + f'rm -rf {self.version.version_name}'
            run_cmd(del_cmd)
            # 重命名
            ren_cmd = cd_cmd + f'mv {self.version.version_name}_backup {self.version.version_name}'
            run_cmd(ren_cmd)
        return target


if __name__ == '__main__':
    # calc_indicators(r'D:\Desktop\hwCQ\projs\ExoPlayerResults\ExoPlayer\java\tag0_r1.0.10', 'ExoPlayer')
    # project = Project('google/ExoPlayer', '', '')
    # version = Version(project, 'r1.0.10')
    # cs = CodeScanner(version)
    # cs.checkout()
    # cs.scan()
    pass
