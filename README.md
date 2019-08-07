# scisweeper
scisweeper - scientific parameter sweeper

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/caa562772b6944a2bcc3bd4d33ec62b0)](https://www.codacy.com/app/jan-janssen/scisweeper?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=scisweeper/scisweeper&amp;utm_campaign=Badge_Grade)
[![Build Status](https://travis-ci.org/scisweeper/scisweeper.svg?branch=master)](https://travis-ci.org/scisweeper/scisweeper)
[![Coverage Status](https://coveralls.io/repos/github/scisweeper/scisweeper/badge.svg?branch=master)](https://coveralls.io/github/scisweeper/scisweeper?branch=master)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/scisweeper/scisweeper/master?filepath=notebooks%2Fdemo.ipynb)

scisweeper is a utility for parameter sweeps in a scientific environment. By defining the `write_input` and 
`collect_output` function, as well as a link to the `executable` the users can link scisweeper to their own code. 
Afterwards scisweeper can execute the parameter sweep either locally using a given number of parallel threads or submit 
the individual calculations to a queuing system like `LFS`, `MOAB`, `SGE`, `SLURM`, or `TORQUE` using the built-in 
interface to `pysqa`. After the calculations are finished the results are summarized in a `pandas.DataFrame`, which makes 
them easily accessible for machine learning tools like `tensorflow` or `pytorch`. Coming from a scientific environment 
scisweeper was develop with a focus on debugging. Broken jobs can be identified, executed again manually or deleted and 
in case you need to update the `collect_output` function there is no need to execute the calculations again, the output 
can be parsed separatly to update the results in the `pandas.DataFrame`. 

# Installation
The scisweeper can either be installed via pip using:

    pip install scisweeper

Or via anaconda from the conda-forge channel

    conda install -c conda-forge scisweeper


# Usage 
For a simple executable like:

    #!/bin/bash
    awk '{ print $1+$2*$3 }1{print 1}' input_file > output.log

Which is located in your home directory as `~/test.sh` a parameter sweep can be conducted using the following steps. 
Start with importing `scisweeper` : 

    from scisweeper import SciSweeper
    ssw = SciSweeper()
    
Define your `write_input` and `collect_output` function in a derived class. The important part about these `write_input` and `collect_output` function is that all the necessary import statements have to be nested within the function. This might be counterintuitive in the beginning, but is essential as it allows scisweeper to transfer the function to the compute node where the code is going to be executed: 

    class BashSciSweeper(ssw.job):
        @property
        def executable(self): 
            return 'bash ~/test.sh'
        
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
            return {'result': int(output[1])}

And apply this function to our `scisweeper` instance: 

    ssw.job_class = BashSciSweeper 

Afterwards we build a list of dictionaries with the input values we want to iterate over:

    input_lst = []
    for i in range(10):
        for j in range(10):
            for k in range(10):
                input_lst.append({'value_1': i, 'value_2': j, 'value_3': k}) 

Optionally we can define a function to generate custom job names for the individual calculations. This can help 
identifying broken calculation: 

    def job_name(input_dict, counter):
        return 'job_' + str(counter) + '_' + str(input_dict['value_1'])
    
    ssw.job_name_function = job_name
    
Then we execute the caluclation in parallel using twenty cores:
    
    ssw.run_jobs_in_parallel(input_dict_lst=input_lst, cores=20)

And collect the results: 

    ssw.collect()
    ssw.results
    
If we want to update our output parser, because we want to parse more quantities, we can do so by replacing the 
interface:

    class BashSciSweeper2(ssw.job):
        @staticmethod
        def collect_output(working_directory='.'):
            with open(os.path.join(working_directory, 'output.log'), 'r') as f:
                output = f.readlines()
            return {'result': int(output[0])}
            
And repeat the steps from above:

    ssw.job_class = BashSciSweeper2
    ssw.run_collect_output()
    ssw.collect()
    ssw.results
    
Or we can identify broken calculations using: 

    ssw.broken_jobs
    
For more information feel free to look at the unit tests and the example notebooks.
https://github.com/scisweeper/scisweeper/blob/master/notebooks/demo.ipynb 

# Queuing system
To interface with the queuing system we use pysqa - https://github.com/pyiron/pysqa - which is constructed around the idea that even though modern queuing systems allow for an wide range of different configuration, most users submit the majority of their jobs with very similar parameters. Sample configurations for the specific queuing systems are availabe in the pysqa tests:

* lsf - https://github.com/pyiron/pysqa/tree/master/tests/config/lsf
* moab - https://github.com/pyiron/pysqa/tree/master/tests/config/moab
* SGE - https://github.com/pyiron/pysqa/tree/master/tests/config/sge
* slurm - https://github.com/pyiron/pysqa/tree/master/tests/config/slurm
* torque - https://github.com/pyiron/pysqa/tree/master/tests/config/torque

# License
The scisweeper is released under the BSD license https://github.com/scisweeper/scisweeper/blob/master/LICENSE . 
It is a spin-off of the pyiron project https://github.com/pyiron/pyiron therefore if you use the scisweeper for your 
publication, please cite: 

    @article{pyiron-paper,
      title = {pyiron: An integrated development environment for computational materials science},
      journal = {Computational Materials Science},
      volume = {163},
      pages = {24 - 36},
      year = {2019},
      issn = {0927-0256},
      doi = {https://doi.org/10.1016/j.commatsci.2018.07.043},
      url = {http://www.sciencedirect.com/science/article/pii/S0927025618304786},
      author = {Jan Janssen and Sudarsan Surendralal and Yury Lysogorskiy and Mira Todorova and Tilmann Hickel and Ralf Drautz and Jörg Neugebauer},
      keywords = {Modelling workflow, Integrated development environment, Complex simulation protocols},
    }
