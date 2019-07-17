import h5io
import inspect
import numpy as np
import os
import pandas
from pyfileindex import PyFileIndex
import subprocess
import textwrap


def filter_function(file_name):
    return 'scisweeper.h5' in file_name


class SciSweeperJob(object):
    def __init__(self, working_directory=None, input_dict=None):
        self._working_directory = working_directory
        if input_dict is not None:
            self._input_dict = input_dict
        else:
            self._input_dict = {}
        self._output_dict = {}
        self._executable = None
        self._write_input_source = None
        self._collect_output_source = None
        self._pysqa = None
        self._run_mode = 'local'

    @property
    def pysqa(self):
        return self._pysqa

    @pysqa.setter
    def pysqa(self, pysqa):
        self._pysqa = pysqa
        self._run_mode = 'pysqa'

    @property
    def working_directory(self):
        return self._working_directory

    @working_directory.setter
    def working_directory(self, working_directory):
        self._working_directory = working_directory

    @property
    def input_dict(self):
        return self._input_dict

    @input_dict.setter
    def input_dict(self, input_dict):
        self._input_dict = input_dict

    @property
    def output_dict(self):
        return self._output_dict

    @output_dict.setter
    def output_dict(self, output_dict):
        self._output_dict = output_dict

    @property
    def executable(self):
        if self._executable is not None:
            return self._executable
        raise NotImplementedError

    @staticmethod
    def obj_to_str(obj):
        """

        Args:
            obj:

        Returns:

        """
        return inspect.getsource(obj)

    @staticmethod
    def str_to_obj(obj_str):
        """

        Args:
            obj_str:

        Returns:

        """
        function_dedent_str = textwrap.dedent(obj_str)
        function_dedent_str = function_dedent_str.replace('@staticmethod', '')
        exec function_dedent_str
        return eval(function_dedent_str.split("(")[0][4:])

    @staticmethod
    def write_input(input_dict, working_directory='.'):
        """

        Args:
            input_dict:
            working_directory:

        Returns:

        """
        raise NotImplementedError

    @staticmethod
    def collect_output(working_directory='.'):
        """

        Args:
            working_directory:

        Returns:

        """
        raise NotImplementedError

    def to_hdf(self):
        """

        Returns:

        """
        if self._write_input_source is None:
            self._write_input_source = self.obj_to_str(self.write_input)
        if self._collect_output_source is None:
            self._collect_output_source = self.obj_to_str(self.collect_output)
        job_dict = {'input': self._input_dict,
                    'settings': {'executable': self.executable,
                                 'working_directory': self._working_directory,
                                 'write_input': self._write_input_source,
                                 'collect_output': self._collect_output_source}}
        if len(self.output_dict) != 0:
            job_dict['output'] = self.output_dict
        h5io.write_hdf5(os.path.join(self._working_directory, 'scisweeper.h5'), job_dict, overwrite="update")

    def from_hdf(self):
        """

        Returns:

        """
        job_dict = h5io.read_hdf5(os.path.join(self._working_directory, 'scisweeper.h5'))
        if 'input' in job_dict.keys():
            self.input_dict = job_dict['input']
        if 'settings' in job_dict.keys():
            self._executable = job_dict['settings']['executable']
            self._working_directory = job_dict['settings']['working_directory']
            if 'NotImplementedError' in inspect.getsource(self.write_input):
                self._write_input_source = job_dict['settings']['write_input']
                self.write_input = self.str_to_obj(self._write_input_source)
            if 'NotImplementedError' in inspect.getsource(self.collect_output):
                self._collect_output_source = job_dict['settings']['collect_output']
                self.collect_output = self.str_to_obj(self._collect_output_source)
        if 'output' in job_dict.keys():
            self.output_dict = job_dict['output']

    def run(self):
        """

        Returns:

        """
        os.makedirs(self._working_directory, exist_ok=True)
        self.write_input(input_dict=self.input_dict, working_directory=self._working_directory)
        if self._executable is None:
            self._executable = self.executable
        self._execute_process(executable=self._executable,
                              working_directory=os.path.abspath(self._working_directory),
                              mode=self._run_mode)
        self.output_dict = self.collect_output(working_directory=self._working_directory)
        self.to_hdf()

    def _execute_process(self, executable, working_directory, mode='local'):
        """

        Args:
            executable:
            working_directory:
            mode:

        Returns:

        """
        if mode == 'local':
            subprocess.check_output(executable,
                                    cwd=working_directory,
                                    universal_newlines=True,
                                    shell=True)
        elif mode == 'pysqa':
            self._pysqa.submit_job(command=executable, working_directory=working_directory)
        else:
            raise ValueError

    def run_broken_again(self):
        """

        Returns:

        """
        self.from_hdf()
        self.output_dict = self.collect_output(working_directory=self._working_directory)
        if len(self.output_dict) == 0:
            self.run()

    def run_collect_output(self):
        """

        Returns:

        """
        self.from_hdf()
        self.output_dict = self.collect_output(working_directory=self._working_directory)
        self.to_hdf()


class SciSweeper(object):
    def __init__(self, working_directory='.', job_class=None):
        self._fileindex = PyFileIndex(path=working_directory, filter_function=filter_function)
        self._job_class = job_class
        self._results_df = None
        self._broken_jobs = []

    @property
    def job_class(self):
        return self._job_class

    @job_class.setter
    def job_class(self, job_class):
        self._job_class = job_class

    @property
    def results(self):
        return self._results_df

    @property
    def broken_jobs(self):
        return self._broken_jobs

    def collect(self):
        """

        Returns:

        """
        self._fileindex.update()
        dict_lst, broken_jobs = self._check_jobs()
        self._results_df = pandas.DataFrame(dict_lst)
        self._broken_jobs = np.array([self._fileindex.dataframe[(~self._fileindex.dataframe.is_directory)
                                                                & self._fileindex.dataframe.path.str.contains(
            '/' + s + '/')].dirname.values
                                      for s in broken_jobs]).flatten().tolist()

    def run_job(self, working_directory, input_dict):
        """

        Args:
            working_directory:
            input_dict:

        Returns:

        """
        self._job_class(working_directory=working_directory, input_dict=input_dict).run()

    def run_collect_output(self):
        """

        Returns:

        """
        for path in self._fileindex.dataframe[~self._fileindex.dataframe.is_directory].dirname.values:
            self._job_class(working_directory=path).run_collect_output()

    def _check_jobs(self):
        """

        Returns:

        """
        dict_lst, all_keys_lst, broken_jobs = [], [], []
        for path in self._fileindex.dataframe[~self._fileindex.dataframe.is_directory].dirname.values:
            job_dict = {}
            job_dict['dir'] = os.path.basename(path)
            job = self._job_class(working_directory=path)
            job.from_hdf()
            for k, v in job.input_dict.items():
                job_dict[k] = v
            for k, v in job.output_dict.items():
                job_dict[k] = v
            for k in job_dict.keys():
                all_keys_lst.append(k)
            dict_lst.append(job_dict)
        final_keys = list(set(all_keys_lst))
        for d in dict_lst:
            for k in final_keys:
                broken_flag = False
                if k not in d.keys():
                    d[k] = np.nan
                    broken_flag = True
                if broken_flag:
                    broken_jobs.append(d['dir'])
        return dict_lst, broken_jobs
