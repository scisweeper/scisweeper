import unittest
import os
from scisweeper.scisweeper import SciSweeperJob, SciSweeper


file_location = os.path.dirname(os.path.abspath(__file__))


def job_name(input_dict, counter):
    return 'job_' + str(counter) + '_' + str(input_dict['value_1'])


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


class BashSciSweeper2(SciSweeperJob):
    @staticmethod
    def collect_output(working_directory='.'):
        import os
        with open(os.path.join(working_directory, 'output.log'), 'r') as f:
            output = f.readlines()
        return {'result': int(output[0])}


class TestSciSweeper(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        for j, d in zip(['job_0_1', 'job_0'], ['calc_test_sweeper', 'calc_test_collect']):
            os.remove(os.path.join(file_location, d, j, 'input_file'))
            os.remove(os.path.join(file_location, d, j, 'output.log'))
            os.remove(os.path.join(file_location, d, j, 'scisweeper.h5'))
            os.removedirs(os.path.join(file_location, d, j))

    def test_sweeper(self):
        self.ssw = SciSweeper(working_directory='calc_test_sweeper')
        self.ssw.job_class = BashSciSweeper
        self.ssw.job_name_function = job_name
        self.ssw.run_jobs_in_parallel(input_dict_lst=[{'value_1': 1, 'value_2': 2, 'value_3': 3}], cores=1)
        self.ssw.collect()
        self.assertEqual(self.ssw.results.result.values[0][0], 7)
        self.assertEqual(self.ssw.results.result.values[0][1], 1)
        self.assertEqual(self.ssw.results.value_1.values[0], 1)
        self.assertEqual(self.ssw.results.value_2.values[0], 2)
        self.assertEqual(self.ssw.results.value_3.values[0], 3)
        self.assertEqual(self.ssw.results.dir.values[0], 'job_0_1')

    def test_collect_again(self):
        self.ssw = SciSweeper(working_directory='calc_test_collect')
        self.ssw.job_class = BashSciSweeper
        self.ssw.run_jobs_in_parallel(input_dict_lst=[{'value_1': 1, 'value_2': 2, 'value_3': 3}], cores=1)
        self.ssw.collect()
        self.assertEqual(self.ssw.results.result.values[0][0], 7)
        self.assertEqual(self.ssw.results.result.values[0][1], 1)
        self.assertEqual(self.ssw.results.value_1.values[0], 1)
        self.assertEqual(self.ssw.results.value_2.values[0], 2)
        self.assertEqual(self.ssw.results.value_3.values[0], 3)
        self.assertEqual(self.ssw.results.dir.values[0], 'job_0')
        self.ssw.job_class = BashSciSweeper2
        self.ssw.run_collect_output()
        self.assertEqual(self.ssw.results.result.values[0], 7)
        self.assertEqual(self.ssw.results.value_1.values[0], 1)
        self.assertEqual(self.ssw.results.value_2.values[0], 2)
        self.assertEqual(self.ssw.results.value_3.values[0], 3)
        self.assertEqual(self.ssw.results.dir.values[0], 'job_0')
