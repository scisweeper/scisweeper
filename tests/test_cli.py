import unittest
import os
import subprocess
from scisweeper.scisweeper import SciSweeperJob


file_location = os.path.dirname(os.path.abspath(__file__))


class BashSciSweeper(SciSweeperJob):
    @property
    def executable(self):
        return 'bash ' + os.path.join(file_location, 'executable', 'test.sh')

    @staticmethod
    def write_input(input_dict, working_directory='.'):
        import os
        from jinja2 import Template
        template = Template("{{value_1}} {{value_2}} {{value_3}}")
        template_str = template.render(value_1=input_dict['value_1'],
                                       value_2=input_dict['value_2'],
                                       value_3=input_dict['value_3'])
        with open(os.path.join(working_directory, 'input_file'), 'w') as f:
            f.writelines(template_str)

    @staticmethod
    def collect_output(working_directory='.'):
        import os
        with open(os.path.join(working_directory, 'output.log'), 'r') as f:
            output = f.readlines()
        return {'result': [int(o) for o in output]}


class TestJobFileTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.makedirs('calc_test_cli', exist_ok=True)
        cls.job = BashSciSweeper(working_directory=os.path.join(os.path.abspath('calc_test_cli'), 'job'),
                                 input_dict={'value_1': 1, 'value_2': 2, 'value_3': 3})
        cls.job.to_hdf()

    @classmethod
    def tearDownClass(cls):
        os.remove(os.path.join(file_location, 'calc_test_cli', 'job', 'input_file'))
        os.remove(os.path.join(file_location, 'calc_test_cli', 'job', 'output.log'))
        os.remove(os.path.join(file_location, 'calc_test_cli', 'job', 'scisweeper.h5'))
        os.removedirs(os.path.join(file_location, 'calc_test_cli', 'job'))

    def test_cli_run(self):
        path_job = os.path.join(os.path.abspath('calc_test_cli'), 'job')
        subprocess.check_output('python -m scisweeper.cli -p ' + path_job, cwd=file_location, shell=True,
                                universal_newlines=True)
        self.job.from_hdf()
        self.assertEqual(self.job.output_dict['result'][0], 7)
        self.assertEqual(self.job.output_dict['result'][1], 1)

    def test_error(self):
        out = subprocess.check_output('python -m scisweeper.cli -x', cwd=file_location, shell=True,
                                      universal_newlines=True)
        self.assertIn('cli.py --p <path>', out)

    def test_help(self):
        out = subprocess.check_output('python -m scisweeper.cli -h', cwd=file_location, shell=True,
                                      universal_newlines=True)
        self.assertIn('cli.py --p <path>', out)
