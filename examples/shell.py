import subprocess


def execute(command: str) -> str:
    if not isinstance(command, str):
        raise TypeError("command must be a string.")

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Command failed with code {e.returncode}:\n{e.stderr.strip()}"
