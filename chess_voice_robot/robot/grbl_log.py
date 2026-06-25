"""Print G-code commands sent to the Arduino."""


def log_command(cmd: str) -> None:
    line = cmd.strip()
    if line:
        print(f"[Arduino] {line}", flush=True)
