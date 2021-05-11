"""
一个文件运行所有的测试用例
"""
import unittest

if __name__ == '__main__':
    tests = unittest.TestLoader().discover('app/tests')
    unittest.TextTestRunner(verbosity=2).run(tests)