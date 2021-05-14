"""
通过计算指标与代码度量相关性进行方案验证
"""
import os
import openpyxl
import pandas as pd
from flask_pymongo import PyMongo

from app.cq_calc import ISO25010, RU2000, Readability, Complexity, Inheritance
from app.models import Project, Version


def remove_dup(series):
    return series[~series.index.duplicated()]


def add_sheet(data, excel_writer, sheet_name):
    """
    不改变原有Excel的数据，新增sheet。
    注：
    使用openpyxl操作Excel时Excel必需存在，因此要新建空sheet
    无论如何sheet页都会被新建，只是当sheet_name已经存在时会新建一个以1结尾的sheet，如：test已经存在时，新建sheet为test1，以此类推
    :param data: DataFrame数据
    :param excel_writer: 文件路径
    :param sheet_name: 新增的sheet名称
    :return: None
    """
    book = openpyxl.load_workbook(excel_writer.path)
    excel_writer.book = book
    # 保留索引和列名
    data.to_excel(excel_writer=excel_writer, sheet_name=sheet_name)

    excel_writer.close()


def cq_validator(version_scan_results_directory, project_name):
    params = [version_scan_results_directory, project_name]
    complexity_calculator = Complexity(*params)
    complexity, index = complexity_calculator.complexity, complexity_calculator.index

    maintainability_calculator = ISO25010(*params)
    maintainability = maintainability_calculator.maintainability
    testablility = maintainability_calculator.testability
    loc = maintainability_calculator.class_file['LOC']
    size2 = (maintainability_calculator.class_file['NA'] + maintainability_calculator.class_file['NM'])
    size2.name = 'SIZE2'
    nom = maintainability_calculator.class_file['NLM']
    noc = maintainability_calculator.class_file['NOC']
    wmc = maintainability_calculator.class_file['WMC']
    rfc = maintainability_calculator.class_file['RFC']
    dit = maintainability_calculator.class_file['DIT']
    cbo = maintainability_calculator.class_file['CBO']
    ce = maintainability_calculator.class_file['NOI']
    ca = maintainability_calculator.class_file['NII']
    lcom = maintainability_calculator.class_file['LCOM5']

    readability = Readability(*params).readability
    reusability = RU2000(*params).reusability
    inheritance = Inheritance(*params).inheritance

    # 合并该版本的计算结果，readability少，会被自动补充为nan
    df = pd.concat([remove_dup(maintainability),
                    remove_dup(testablility),
                    remove_dup(readability),
                    remove_dup(reusability),
                    remove_dup(inheritance),
                    remove_dup(complexity),
                    remove_dup(loc),
                    remove_dup(size2),
                    remove_dup(nom),
                    remove_dup(noc),
                    remove_dup(wmc),
                    remove_dup(rfc),
                    remove_dup(dit),
                    remove_dup(cbo),
                    remove_dup(ce),
                    remove_dup(ca),
                    remove_dup(lcom),

                    ], axis=1)

    df.fillna(1, inplace=True)
    df.to_excel(f'./ValidationResults/{project_name}.xlsx', sheet_name='code quality and metrics')

    excel_writer = pd.ExcelWriter(f'./ValidationResults/{project_name}.xlsx', engine='openpyxl')
    add_sheet(df.corr(method='spearman'), excel_writer, 'relativity')
    return df


if __name__ == '__main__':
    mongodb_url = os.getenv('MONGODB_URL')
    mongo = PyMongo('', uri=f'{mongodb_url}/run')
    project = Project('alibaba/metrics', '', '')
    version = Version(project, 't1', '', '', '')
    # cs = CodeScanner(version)
    # cs.scan()
    cq_validator(version.version_scan_results_dir, 'metrics')
