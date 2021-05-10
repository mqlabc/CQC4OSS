import pandas as pd
import xml.etree.ElementTree as ET
import numpy


class Complexity:
    """
    计算代码级复杂性：the less, the better
    粒度：Version、Class、Method
    """

    def __init__(self, directory, name):
        self.dir = directory
        self.class_file = pd.read_csv(f'{directory}/{name}-Class.csv').set_index('LongName', drop=False)
        self.df = self.class_file[['WMC', 'Path', 'Name']]
        self.complexity = self.df['WMC']
        self.complexity.name = 'complexity'
        self.index = self.df['Path'].str.replace('\\', '/') + '/' + self.df['Name']


class Inheritance:
    """
    计算项继承性: the less, the better
    Version、Class
    """

    def __init__(self, directory, name):
        self.dir = directory
        self.class_file = pd.read_csv(f'{directory}/{name}-Class.csv').set_index('LongName', drop=False)
        self.noa = self.class_file['NOA']
        self.noc = self.class_file['NOC']
        self.nop = self.class_file['NOP']
        self.nod = self.class_file['NOD']
        self.dit = self.class_file['DIT']
        self.inheritance = self.get_inherirance()
        self.inheritance.name = 'inheritance'

    def get_inherirance(self):
        return (self.noa + self.noc + self.nop + self.nod + self.dit) / 5


class ISO25010:
    """
    计算ISO25010可维护性指标（借助Code Smell）：the more, the better
    粒度：Version、Class
    """

    def __init__(self, directory, name):
        self.dir = directory
        self.class_file = pd.read_csv(f'{directory}/{name}-Class.csv').set_index('LongName', drop=False)
        self.method_file = pd.read_csv(f'{directory}/{name}-Method.csv').set_index('LongName', drop=False)

        # 方法级代码度量
        self.par = self.method_file['NUMPAR']
        self.nbd = self.method_file['NL']
        self.mloc = self.method_file['LOC']
        self.mccc = self.method_file['McCC']

        # 类级代码度量
        self.cc = self.class_file['CC']
        self.cllc = self.class_file['CLLC']
        self.loc = self.class_file['LOC']
        self.loc_mean = self.class_file['LOC'].mean()
        self.nom = self.class_file['NM']
        self.wmc = self.class_file['WMC']
        self.cloc = self.class_file['LOC']
        self.cbo = self.class_file['CBO']
        self.cbo_mean = self.class_file['CBO'].mean()
        self.dit = self.class_file['DIT']

        # 代码异味指标
        self.duplicate_code = self.get_duplicate_code()
        self.long_parameter = self.get_long_parameter()
        self.long_method = self.get_long_method()
        self.lazy_class = self.get_lazy_class()
        self.large_class = self.get_large_class()

        # maintainability子指标
        self.modularity, self.reusability, self.analyzability, self.modifiability, self.testability = \
            self.get_sub_iso25010()

        # maintainability指标
        self.maintainability = self.get_maintainability()

        self.duplicate_code_V = self.duplicate_code.mean()
        self.long_parameter_V = self.long_parameter.mean()
        self.long_method_V = self.long_method.mean()
        self.lazy_class_V = self.lazy_class.mean()
        self.large_class_V = self.large_class.mean()
        self.maintainability.name = 'maintainability'
        self.testability.name = 'testability'

    @staticmethod
    def _get_duplicate_code(single_class):
        if single_class <= 0.03:
            dc = 2
        elif single_class <= 0.05:
            dc = 1
        elif single_class <= 0.1:
            dc = 0
        elif single_class <= 0.2:
            dc = -1
        else:
            dc = -2
        return dc

    def get_duplicate_code(self):
        cc = self.cc.map(self._get_duplicate_code)
        cllc = self.cllc.map(self._get_duplicate_code)
        # 先映射，再平均
        return (cc + cllc) / 2

    def find_method(self, single_class):
        """
        返回类名为class_name的method数据框
        :param single_class: 类名
        :return: 相应的method数据框
        """
        return self.method_file[self.method_file['LongName'].str.startswith(single_class)]

    @staticmethod
    def _get_long_parameter(single_method):
        if single_method <= 1:
            lp = 2
        elif single_method <= 3:
            lp = 1
        elif single_method <= 5:
            lp = 0
        elif single_method <= 7:
            lp = -1
        else:
            lp = -2
        return lp

    def get_long_parameter_class(self, single_class):
        df = self.find_method(single_class)
        if len(df) == 0:
            return 0
        return df['NUMPAR'].map(self._get_long_parameter).mean()

    def get_long_parameter(self):
        return self.class_file['LongName'].map(self.get_long_parameter_class)

    @staticmethod
    def _get_nbd(single_class):
        if single_class <= 1:
            nbd = 2
        elif single_class <= 2:
            nbd = 1
        elif single_class <= 4:
            nbd = 0
        elif single_class <= 6:
            nbd = -1
        else:
            nbd = -2
        return nbd

    @staticmethod
    def _get_mloc(single_method):
        if single_method <= 7:
            mloc = 2
        elif single_method <= 10:
            mloc = 1
        elif single_method <= 13:
            mloc = 0
        elif single_method <= 20:
            mloc = -1
        else:
            mloc = -2
        return mloc

    @staticmethod
    def _get_mccc(single_method):
        if single_method <= 1.1:
            mccc = 2
        elif single_method <= 2.0:
            mccc = 1
        elif single_method <= 3.1:
            mccc = 0
        elif single_method <= 4.7:
            mccc = -1
        else:
            mccc = -2
        return mccc

    def get_long_method_class(self, single_class):
        df = self.find_method(single_class)
        if len(df) == 0:
            return 0
        long_parameter = df['NUMPAR'].map(self._get_long_parameter)
        part1 = df['NL'].map(self._get_nbd)
        part2 = df['LOC'].map(self._get_mloc)
        part3 = df['McCC'].map(self._get_mccc)
        sum_vec = (long_parameter + part1 + part2 + part3) / 4
        return sum_vec.mean()

    def get_long_method(self):
        return self.class_file['LongName'].map(self.get_long_method_class)

    @staticmethod
    def _get_nom(single_class):
        if single_class >= 1:
            nom = 2
        else:
            nom = -2
        return nom

    def _get_lazy_class_part1(self, single_class):
        # 考虑除数为0
        if single_class['NM'] == 0:
            p1 = -2
        elif (single_class['LOC'] >= self.loc_mean) and (single_class['WMC'] / single_class['NM'] > 2):
            p1 = 2
        elif (single_class['LOC'] < self.loc_mean) and (single_class['WMC'] / single_class['NM'] <= 2):
            p1 = -2
        else:
            p1 = 0
        return p1

    def _get_lazy_class_part2(self, single_class):
        if (single_class['CBO'] >= self.cbo_mean) and (single_class['DIT'] <= 1):
            p2 = 2
        elif (single_class['CBO'] < self.cbo_mean) and (single_class['DIT'] > 1):
            p2 = -2
        else:
            p2 = 0
        return p2

    def get_lazy_class(self):
        nom = self.nom.map(self._get_nom)
        # mean会忽略NaN
        part1 = self.class_file.apply(self._get_lazy_class_part1, axis=1)
        part2 = self.class_file.apply(self._get_lazy_class_part2, axis=1)

        return (nom + part1 + part2) / 3

    @staticmethod
    def _get_large_class_nom(single_class):
        if single_class <= 4:
            nom = 2
        elif single_class <= 7:
            nom = 1
        elif single_class <= 10:
            nom = 0
        elif single_class <= 15:
            nom = -1
        else:
            nom = -2
        return nom

    @staticmethod
    def _get_large_class_wmc(single_class):
        if single_class <= 5:
            wmc = 2
        elif single_class <= 14:
            wmc = 1
        elif single_class <= 31:
            wmc = 0
        elif single_class <= 47:
            wmc = -1
        else:
            wmc = -2
        return wmc

    @staticmethod
    def _get_large_class_cloc(single_class):
        if single_class <= 28:
            cloc = 2
        elif single_class <= 70:
            cloc = 1
        elif single_class <= 130:
            cloc = 0
        elif single_class <= 195:
            cloc = -1
        else:
            cloc = -2
        return cloc

    @staticmethod
    def _get_large_class_cbo(single_class):
        if single_class <= 1:
            cbo = 2
        elif single_class <= 3:
            cbo = 1
        elif single_class <= 5:
            cbo = 0
        elif single_class <= 7:
            cbo = -1
        else:
            cbo = -2
        return cbo

    def get_large_class(self):
        part0 = self.nom.map(self._get_large_class_nom)
        part1 = self.wmc.map(self._get_large_class_wmc)
        part2 = self.cloc.map(self._get_large_class_cloc)
        part3 = self.cbo.map(self._get_large_class_cbo)
        return (part0 + part1 + part2 + part3) / 4

    def get_sub_iso25010(self):
        modularity = (self.duplicate_code + self.long_method + self.large_class) / 3
        reusability = modularity
        analyzability = (self.duplicate_code + self.long_parameter + self.long_method + self.lazy_class) / 4
        modifiability = (self.duplicate_code + self.long_parameter + self.large_class) / 3
        testablility = modularity
        return modularity, reusability, analyzability, modifiability, testablility

    def get_maintainability(self):
        return (self.modularity + self.reusability + self.analyzability + self.modifiability + self.testability) / 5


class Readability:
    """
    论文中提到的归一化方法是什么？
    计算项目粒度的可读性: the less, the better
    Version、Class
    注意：不会包括所有的类，这些类的可读性为1
    """

    def __init__(self, directory, name):
        self.pmd_file = f'{directory}/sourcemeter/temp/{name}-PMD.xml'
        self.class_file = pd.read_csv(f'{directory}/{name}-Class.csv').set_index('LongName', drop=False)
        tree = ET.parse(self.pmd_file)
        self.root = tree.getroot()
        self.violations = ['Best Practices', 'Documentation', 'Design', 'Code Style', 'Error Prone']
        self.lloc = self.class_file['LLOC'].sum()
        self.viol_per_loc = self.get_viol_per_loc()
        self.readability = self.get_readability()
        self.readability.name = 'readability'

    # 根据violation的种类和程度，获取每个逻辑行的平均violation权重
    def get_viol_per_loc(self):
        class_d = {}

        for file in self.root:
            for item in file:
                if ('class' not in item.attrib) or ('package' not in item.attrib):
                    continue
                class_name = item.attrib['package'] + '.' + item.attrib['class']
                if item.attrib['ruleset'] in self.violations:
                    if class_name not in class_d:
                        class_d[class_name] = int(item.attrib['priority'])
                        continue
                    class_d[class_name] += int(item.attrib['priority'])

        fail_objs = []
        # 遍历class_d除以各自的lloc
        for k in class_d.keys():
            try:
                lloc = self.class_file['LLOC'][k]
                if type(lloc) == pd.core.series.Series:
                    lloc = lloc.mean()
                class_d[k] = class_d[k] / lloc
            # pmd file中有一些interface被误标记为interface在class_file中找不到, 如果直接放弃也不可能造成与其他指标的不一致
            except KeyError:
                fail_objs.append(k)
        # dataframe不能直接用.name改名，要先取成series
        vio_per_loc = pd.DataFrame.from_dict(class_d, orient='index')[0]
        valid_entries = vio_per_loc.drop(fail_objs)
        return valid_entries

    @staticmethod
    def value_normalize(col):
        return 1 / (1 + numpy.exp(-1 * col))

    def get_readability(self):
        # return 1 - self.value_normalize(self.viol_per_loc)
        return self.viol_per_loc


class RU2000:
    """
    使用RU2000计算项继承性
    the more, the better
    """

    def __init__(self, directory, name):
        self.dir = directory
        self.class_file = pd.read_csv(f'{directory}/{name}-Class.csv').set_index('LongName', drop=False)
        self.method_file = pd.read_csv(f'{directory}/{name}-Method.csv').set_index('LongName', drop=False)

        self.lcom = self.class_file['LCOM5']
        self.cohesion = ((-2.26852 * self.lcom) + 103.259) / 100
        # ?什么归一化upper
        self.npm = self.value_normalize(self.class_file['NPM'])
        self.cloc_loc = self.class_file['LongName'].map(self.get_cloc_loc)
        self.ncm_nm = self.class_file['LongName'].map(self.get_ncm_nm)
        self.comments_in_definition_na_nm = self.class_file['LongName'].map(self.get_comments_in_definition_na_nm)
        # upper limit metrics
        self.na = self.value_normalize(self.class_file['NA'])
        # ?什么归一化upper
        self.loc_m = self.value_normalize(self.class_file['LongName'].map(self.get_loc_m))
        # ?什么归一化upper
        self.wmc = self.value_normalize(self.class_file['WMC'])

        # Modularity = 0.50 * Lack of Coupling + 0.50 * Cohesion
        # sourcemeter不提供计算lack of coupling的指标，所以直接使用cohesion代替
        self.Modularity = self.cohesion
        self.InterfaceSize = self.npm
        self.Documentation = (self.cloc_loc + self.ncm_nm + self.comments_in_definition_na_nm) / 3
        self.Complexity = (0.5 * (0.5 * self.na + 0.5 * self.loc_m) + 0.5 * self.wmc)
        self.reusability = self.get_reusability()
        self.reusability.name = 'reusability'

    @staticmethod
    def value_normalize(col):
        threshold = col.median()
        return 1 / (1 + (col / threshold).pow(4))

    def find_method(self, class_name):
        """
        返回类名为class_name的method数据框
        :param class_name: 类名
        :return: 相应的method数据框
        """
        return self.method_file[self.method_file['LongName'].str.startswith(class_name)]

    def get_cloc_loc(self, class_name):
        df = self.find_method(class_name)
        # 如果类中没有方法，则无方法粒度的平均值，无法计算的情况下直接返回0，以下同理
        if len(df) == 0:
            return 0
        comment_lines_per_method = df['CLOC'].mean()
        loc_per_method = df['LOC'].mean()
        return comment_lines_per_method / loc_per_method

    def get_ncm_nm(self, class_name):
        df = self.find_method(class_name)
        if len(df) == 0:
            return 0
        num_of_commented_methods = sum(df['CLOC'] > 0)
        return num_of_commented_methods / len(df)

    def get_comments_in_definition_na_nm(self, class_name):
        df = self.find_method(class_name)
        if len(df) == 0:
            return 0
        num_of_method_comments = df['CLOC'].sum()
        num_of_class_comments = self.class_file['CLOC'][class_name]
        if type(num_of_class_comments) == pd.core.series.Series:
            num_of_class_comments = num_of_class_comments.mean()
        # 类定义的comments = 所有的comments - 方法的comments
        num_of_def_comments = num_of_class_comments - num_of_method_comments
        na = self.class_file['NA'][class_name]
        nm = self.class_file['NM'][class_name]
        nam = na + nm

        if type(nam) == pd.core.series.Series:
            nam = nam.mean()

        if (type(nam) == numpy.int64) and (nam == 0):
            return 0

        return num_of_def_comments / nam

    def get_loc_m(self, class_name):
        df = self.find_method(class_name)
        if len(df) == 0:
            return 0
        loc_per_method = df['LOC'].mean()
        return loc_per_method

    def get_reusability(self):
        reusability = (self.Modularity + self.InterfaceSize + self.Documentation + self.Complexity) / 4
        return reusability


def remove_dup(series):
    return series[~series.index.duplicated()]


# 为某个version计算六项指标的工具函数
# 返回值是一个合并后的df
def cq_calculator(version_scan_results_directory, project_name):
    params = [version_scan_results_directory, project_name]
    complexity_calculator = Complexity(*params)
    complexity, index = remove_dup(complexity_calculator.complexity), remove_dup(complexity_calculator.index)
    maintainability_calculator = ISO25010(*params)
    maintainability, testablility = remove_dup(maintainability_calculator.maintainability), remove_dup(
        maintainability_calculator.testability)
    readability = remove_dup(Readability(*params).readability)
    reusability = remove_dup(RU2000(*params).reusability)
    inheritance = remove_dup(Inheritance(*params).inheritance)
    # 合并该版本的计算结果
    df = pd.concat([maintainability, testablility, readability, reusability, inheritance, complexity], axis=1)
    assert len(index) > 0, f'{version_scan_results_directory} has no classes'
    # 空项目时可能不会成立
    path0 = index[0]
    start_index = path0.find(project_name)
    df.index = [s[start_index:] for s in index]
    df.fillna(1, inplace=True)
    return df
