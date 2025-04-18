import subprocess


def execute(command: str) -> str:
    """
    Executes a shell command and returns its standard output.

    Args:
        command (str): The shell command to execute.

    Raises:
        TypeError: If the provided command is not a string.

    Returns:
        str: The standard output of the command if successful,
             or an error message with the return code and stderr if the command fails.
    """
    if not isinstance(command, str):
        raise TypeError("command must be a string.")

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Command failed with code {e.returncode}:\n{e.stderr.strip()}"
