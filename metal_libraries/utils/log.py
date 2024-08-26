
"""
log.py: Display subprocess error output in formatted string.
"""

import subprocess


def log(process: subprocess.CompletedProcess) -> None:
    """
    Display subprocess error output in formatted string.
    """
    def format_output(output: str) -> str:
        if not output:
            return "        None\n"
        _result = "\n".join([f"        {line}" for line in output.split("\n") if line not in ["", "\n"]])
        if not _result.endswith("\n"):
            _result += "\n"
        return _result

    output = "Subprocess failed.\n"
    output += f"    Command: {process.args}\n"
    output += f"    Return Code: {process.returncode}\n"
    output += f"    Standard Output:\n"
    if process.stdout:
        output += format_output(process.stdout)
    else:
        output += "        None\n"
    output += f"    Standard Error:\n"
    if process.stderr:
        output += format_output(process.stderr)
    else:
        output += "        None\n"
    print(output)