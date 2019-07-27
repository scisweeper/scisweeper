import sys
import getopt
from .scisweeper import SciSweeperJob


def command_line(argv):
    """
    Parse the command line arguments.

    Args:
        argv: Command line arguments

    """
    path = None
    try:
        opts, args = getopt.getopt(argv, "p:h", ["project_path=", "help"])
    except getopt.GetoptError:
        print('cli.py --p <path>')
        sys.exit()
    else:
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                print('cli.py --p <path>')
                sys.exit()
            elif opt in ("-p", "--_path"):
                path = arg
        ssw_job = SciSweeperJob(working_directory=path)
        ssw_job.from_hdf()
        ssw_job.run(run_again=True)
        sys.exit()


if __name__ == "__main__":
    command_line(sys.argv[1:])
