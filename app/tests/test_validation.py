import time
import unittest
from utils import UtilsTestCase


class ValidationTestCase(UtilsTestCase):
    def test_right_token(self):
        token = self.login({'username': 'mql', 'password': 'python'})
        response = self.client.get('/api/resource', headers=UtilsTestCase.get_api_headers(token))
        self.assertTrue(response.status_code == 200)
        self.assertIn('Hello', response.get_data(as_text=True))

    def test_no_user(self):
        name_passwd = {'username': 'lml', 'password': 'python'}
        response = self.client.post('api/token', json=name_passwd)
        self.assertTrue(response.status_code == 404)
        self.assertIn('no user', response.get_data(as_text=True))

    def test_wrong_passwd(self):
        name_passwd = {'username': 'mql', 'password': 'java'}
        response = self.client.post('api/token', json=name_passwd)
        self.assertTrue(response.status_code == 401)
        self.assertIn('wrong passwd', response.get_data(as_text=True))

    def test_wrong_token(self):
        response = self.client.get('/api/resource', headers=UtilsTestCase.get_api_headers('qwer'))
        self.assertIn('invalid token', response.get_data(as_text=True))

    def test_outdated_token(self):
        token = self.login({'username': 'mql', 'password': 'python', 'valid_time': 10})
        time.sleep(11)
        response = self.client.get('/api/resource', headers=UtilsTestCase.get_api_headers(token))
        self.assertIn('invalid token', response.get_data(as_text=True))


if __name__ == '__main__':
    # unittest.main(verbosity=3)
    suite = unittest.TestSuite()
    suite.addTest(ValidationTestCase("test_right_token"))
    suite.addTest(ValidationTestCase("test_no_user"))
    suite.addTest(ValidationTestCase("test_wrong_passwd"))
    suite.addTest(ValidationTestCase("test_wrong_token"))
    suite.addTest(ValidationTestCase("test_outdated_token"))
    unittest.TextTestRunner(verbosity=3).run(suite)
