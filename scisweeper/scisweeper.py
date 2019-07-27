import h5io
import inspect
from multiprocessing.pool import ThreadPool
import numpy as np
import os
import pandas
from pyfileindex import PyFileIndex
from pysqa import QueueAdapter
import subprocess
import sys
from tqdm import tqdm
import textwrap


def filter_function(file_name):
    """
    Internal function to check if the file_name contains 'scisweeper.h5'

    Args:
        file_name (str): name of the current file

    Returns:
        bool: [True/ False]
    """
    return 'scisweeper.h5' in file_name


def run_parallel(scisweeper, working_directory, input_dict):
    """
    Internal function to execute SciSweeperJobs in parallel

    Args:
        ssw (SciSweeper): SciSweeper Instance
        working_directory (str): working directory where the calculation should be executed
        input_dict (dict): Dictionary with input parameters
    """
    return scisweeper.job_class(working_directory=working_directory,
                                input_dict=input_dict).run()


class SciSweeperJob(object):
    def __init__(self, working_directory=None, input_dict=None, pysqa_config=None, cores=1):
        self._working_directory = None
        self.working_directory = working_directory
        if input_dict is not None:
            self._input_dict = input_dict
        else:
            self._input_dict = {}
        self._output_dict = {}
        self._executable = None
        self._write_input_source = None
        self._collect_output_source = None
        self._pysqa = None
        self.pysqa = pysqa_config
        self._cores = cores

    @property
    def pysqa(self):
        return self._pysqa

    @pysqa.setter
    def pysqa(self, pysqa_config):
        if isinstance(pysqa_config, str):
            self._pysqa = QueueAdapter(pysqa_config)
        else:
            self._pysqa = pysqa_config

    @property
    def cores(self):
        return self._cores

    @cores.setter
    def cores(self, cores):
        self._cores = cores

    @property
    def working_directory(self):
        return self._working_directory

    @working_directory.setter
    def working_directory(self, working_directory):
        self._working_directory = os.path.abspath(working_directory)
        if sys.version_info[0] >= 3:
            os.makedirs(self._working_directory, exist_ok=True)
        else:
            if not os.path.exists(self._working_directory):
                os.makedirs(self._working_directory)

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
    def _obj_to_str(obj):
        """
        Convert a function to a string for storing in the HDF5 file

        Args:
            obj(function): function object

        Returns:
            str: function source code
        """
        return inspect.getsource(obj)

    @staticmethod
    def _str_to_obj(obj_str):
        """
        Convert function source code to a function

        Args:
            obj_str (str): function source code

        Returns:
            function: resulting function
        """
        function_dedent_str = textwrap.dedent(obj_str)
        function_dedent_str = function_dedent_str.replace('@staticmethod', '')
        exec(function_dedent_str)
        return eval(function_dedent_str.split("(")[0][4:])

    @staticmethod
    def write_input(input_dict, working_directory='.'):
        """
        Write the input to files in the current working directory - This functions has to be implemented by the user.

        Args:
            input_dict (dict): Dictionary with input parameters
            working_directory (str): path to the working directory
        """
        raise NotImplementedError

    @staticmethod
    def collect_output(working_directory='.'):
        """
        Parse output to dictionary - This functions has to be implemented by the user.

        Args:
            working_directory (str): path to the working directory

        Returns:
            dict: Output dictionary
        """
        raise NotImplementedError

    def to_hdf(self):
        """
        Store input, output and the class definition in an HDF5 file - to maintain orthogonal persistence.
        """
        if self._write_input_source is None:
            self._write_input_source = self._obj_to_str(self.write_input)
        if self._collect_output_source is None:
            self._collect_output_source = self._obj_to_str(self.collect_output)
        job_dict = {'input': self._input_dict,
                    'settings': {'executable': self.executable,
                                 'working_directory': os.path.abspath(self._working_directory),
                                 'write_input': self._write_input_source,
                                 'collect_output': self._collect_output_source}}
        if len(self.output_dict) != 0:
            job_dict['output'] = self.output_dict
        h5io.write_hdf5(os.path.join(self._working_directory, 'scisweeper.h5'), job_dict, overwrite="update")

    def from_hdf(self):
        """
        Restore input, output and the class definition from an HDF5 file - to maintain orthogonal persistence.
        """
        job_dict = h5io.read_hdf5(os.path.join(self._working_directory, 'scisweeper.h5'))
        if 'input' in job_dict.keys():
            self.input_dict = job_dict['input']
        if 'settings' in job_dict.keys():
            self._executable = job_dict['settings']['executable']
            self._working_directory = job_dict['settings']['working_directory']
            if 'NotImplementedError' in inspect.getsource(self.write_input):
                self._write_input_source = job_dict['settings']['write_input']
                self.write_input = self._str_to_obj(self._write_input_source)
            if 'NotImplementedError' in inspect.getsource(self.collect_output):
                self._collect_output_source = job_dict['settings']['collect_output']
                self.collect_output = self._str_to_obj(self._collect_output_source)
        if 'output' in job_dict.keys():
            self.output_dict = job_dict['output']

    def run(self, run_again=False):
        """
        Execute the calculation by writing the input files, running the executable and storing the output
        
        Args:
            run_again (bool): If the calculation already exists it is commonly skipped, but with this option 
                              you can force to execute the calculation again. 

        Returns:
            int/ None: If the job is submitted to a queuing system the queue id is returned, else it is None.
            
        """
        if not os.path.exists(os.path.join(self._working_directory, 'scisweeper.h5')) or run_again:
            if self._pysqa is None:
                self.write_input(input_dict=self.input_dict, working_directory=self._working_directory)
                if self._executable is None:
                    self._executable = self.executable
                subprocess.check_output(self._executable,
                                        cwd=self._working_directory,
                                        universal_newlines=True,
                                        shell=True)
                self.output_dict = self.collect_output(working_directory=self._working_directory)
                self.to_hdf()
            else:
                self.to_hdf()
                return self._pysqa.submit_job(command='python -m scisweeper.cli -p ' + self._working_directory,
                                              working_directory=self._working_directory,
                                              job_name=os.path.basename(self._working_directory), cores=self.cores)

    def run_broken_again(self):
        """
        Recalcualte the job if it has no information stored in the output dictionary - this commonly means the
        calculation failed previously.
        """
        self.from_hdf()
        self.output_dict = self.collect_output(working_directory=self._working_directory)
        if len(self.output_dict) == 0:
            self.run()

    def run_collect_output(self):
        """
        Parse the output files again without executing the calculation again. Use this function after updating the
        collect_output function.
        """
        self.from_hdf()
        self.output_dict = self.collect_output(working_directory=self._working_directory)
        self.to_hdf()


class SciSweeper(object):
    def __init__(self, working_directory='.', job_class=None, cores=1, pysqa_config=None):
        self.working_directory = os.path.abspath(working_directory)
        if sys.version_info[0] >= 3:
            os.makedirs(self.working_directory, exist_ok=True)
        else:
            if not os.path.exists(self.working_directory):
                os.makedirs(self.working_directory)
        self._fileindex = PyFileIndex(path=self.working_directory, filter_function=filter_function)
        self._job_class = job_class
        self._results_df = None
        self._broken_jobs = []
        self._cores = cores
        self._job_name_function = None
        self.job = SciSweeperJob
        self._pysqa = None
        self.pysqa = pysqa_config
        self._job_id_lst = []

    @property
    def pysqa(self):
        return self._pysqa

    @pysqa.setter
    def pysqa(self, pysqa_config):
        if isinstance(pysqa_config, str):
            self._pysqa = QueueAdapter(pysqa_config)
        else:
            self._pysqa = pysqa_config

    @property
    def cores(self):
        return self._cores

    @cores.setter
    def cores(self, cores):
        self._cores = cores

    @property
    def job_name_function(self):
        return self._job_name_function

    @job_name_function.setter
    def job_name_function(self, job_name_function):
        self._job_name_function = job_name_function

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
        Check status of the calculations and update the results table.
        """
        self._fileindex.update()
        dict_lst, broken_jobs = self._check_jobs()
        self._results_df = pandas.DataFrame(dict_lst)
        self._broken_jobs = np.array([self._fileindex.dataframe[(~self._fileindex.dataframe.is_directory)
                                                                & self._fileindex.dataframe.path.str.contains(
            '/' + s + '/')].dirname.values
                                      for s in broken_jobs]).flatten().tolist()

    def delete_jobs_from_queue(self):
        """
        Delete jobs from queuing system
        """
        if self._pysqa is not None:
            _ = [self.pysqa.delete_job(process_id=j[0]) for j in self._job_id_lst]

    def get_job_status(self):
        """
        Get job status from queuing system

        Returns:
            pandas.Dataframe/ None: Status table
        """
        if self._pysqa is not None:
            status_lst = self.pysqa.get_status_of_jobs(process_id_lst=[j[0] for j in self._job_id_lst])
            return pandas.DataFrame([{'queue_id': j[0],
                                      'job_name': j[1],
                                      'status': s} for s, j in zip(status_lst, self._job_id_lst)])

    def run_jobs_in_parallel(self, input_dict_lst, cores=None, job_name_function=None):
        """
        Execute multiple SciSweeperJobs in parallel using multiprocessing.ThreadPool

        Args:
            input_dict_lst (list): List of dictionaries with input parametern
            cores (int/ None): number of cores to use = number of parallel threads.
            job_name_function (function/ None): Function which takes the input_dict and a counter as input to return the
                                                job_name as string. This can be defined by the user to have recognizable
                                                job names.
        """
        if cores is None:
            cores = self._cores
        if job_name_function is None:
            job_name_function = self.job_name_function
        if self._pysqa is None:
            tp = ThreadPool(cores)
        else:
            tp = None
        for counter, input_dict in enumerate(tqdm(input_dict_lst)):
            if job_name_function is not None:
                job_name = job_name_function(input_dict=input_dict, counter=counter)
                working_directory = os.path.abspath(os.path.join(self.working_directory, job_name))
            else:
                working_directory = os.path.abspath(os.path.join(self.working_directory, 'job_' + str(counter)))
            if self._pysqa is None:
                tp.apply_async(run_parallel, (self, working_directory, input_dict,))
            else:
                self._job_id_lst.append([self.job_class(working_directory=working_directory,
                                                        input_dict=input_dict,
                                                        pysqa_config=self.pysqa,
                                                        cores=cores).run(), os.path.basename(working_directory)])
        if self._pysqa is None:
            tp.close()
            tp.join()

    def run_job(self, job_working_directory, input_dict):
        """
        Run individual calculation.

        Args:
            job_working_directory (str): path to working directory
            input_dict (dict): dictionary with input parameters

        Returns:
            int/ None: If the job is submitted to a queuing system the queue id is returned, else it is None.
        """
        return self._job_class(working_directory=job_working_directory,
                               input_dict=input_dict,
                               pysqa_config=self.pysqa).run()

    def run_collect_output(self):
        """
        For each job in this directory and all sub directories collect the output again. Use this function after
        updating the collect_output function.
        """
        for path in tqdm(self._fileindex.dataframe[~self._fileindex.dataframe.is_directory].dirname.values):
            self._job_class(working_directory=path).run_collect_output()
        self.collect()

    def _check_jobs(self):
        """
        Internal helper function to check the jobs and build the results table.
        """
        dict_lst, all_keys_lst, broken_jobs = [], [], []
        for path in tqdm(self._fileindex.dataframe[~self._fileindex.dataframe.is_directory].dirname.values):
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
