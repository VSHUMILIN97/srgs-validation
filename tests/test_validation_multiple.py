import os
import subprocess
import stat


def test_bash_script_is_present_in_the_system(command):
    """ Checks: Bash script is located in the bin/ """
    assert os.path.exists(command) is True
    assert os.path.getsize(command) > 0
    assert os.path.isfile(command) is True


def test_smoke(testdir, command):
    """ Checks: Executable is working well with examples """
    # Some bicycles over here please
    st = os.stat(command)
    os.chmod(command, st.st_mode | stat.S_IEXEC)
    exit_code = subprocess.call(
        [command, '-d', testdir],
    )
    assert exit_code == 0
