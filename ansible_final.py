import os
import shlex
import subprocess

def _win_to_wsl_path(path: str) -> str:
    path = os.path.abspath(path)
    drive = path[0].lower()
    rest = path[2:].replace('\\', '/')
    return f"/mnt/{drive}/{rest}"

def showrun(playbook='ansible-playbook.yml',
            inventory='hosts.ini',
            use_wsl=True,
            wsl_workdir='/tmp/ansible_run'):
    """
    If use_wsl is True:
      1. Copy playbook + inventory into WSL (to wsl_workdir)
      2. Run ansible-playbook inside WSL
    Else: run natively (original behavior).
    Returns stdout on success, otherwise diagnostic string.
    """
    if not use_wsl:
        cmd = ['ansible-playbook', '-i', inventory, playbook]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        stdout = proc.stdout
        if proc.returncode == 0 and 'PLAY RECAP' in stdout:
            return stdout
        return f"Playbook failed (rc={proc.returncode}).\nSTDOUT:\n{stdout}\nSTDERR:\n{proc.stderr}"

    # WSL mode
    if not os.path.exists(playbook):
        return f"Missing playbook: {playbook}"
    if not os.path.exists(inventory):
        return f"Missing inventory: {inventory}"

    wsl_playbook_src = _win_to_wsl_path(playbook)
    wsl_inventory_src = _win_to_wsl_path(inventory)

    playbook_basename = os.path.basename(playbook)
    inventory_basename = os.path.basename(inventory)

    q = shlex.quote
    script = (
        f"set -e;"
        f"mkdir -p {q(wsl_workdir)};"
        f"cp {q(wsl_playbook_src)} {q(wsl_workdir)}/;"
        f"cp {q(wsl_inventory_src)} {q(wsl_workdir)}/;"
        f"cd {q(wsl_workdir)};"
        f"mkdir -p {q(wsl_workdir)}/backups;"  # avoid warnings
        f"ansible-playbook -i {q(inventory_basename)} {q(playbook_basename)}"
    )

    cmd = ['wsl', 'bash', '-lc', script]
    proc = subprocess.run(cmd, capture_output=True, text=True)

    stdout = proc.stdout
    if proc.returncode == 0 and 'PLAY RECAP' in stdout:
        try:
            # Copy backup files from WSL backups dir to current Windows working directory
            dest_wsl = _win_to_wsl_path(os.getcwd()+"/backups")
            q = shlex.quote
            copy_script = (
                f"shopt -s nullglob; "
                f"if [ -d {q(wsl_workdir)}/backups ]; then "
                f"cp -a {q(wsl_workdir)}/backups/* {q(dest_wsl)}/ 2>/dev/null || true; "
                f"fi"
            )
            subprocess.run(['wsl', 'bash', '-lc', copy_script], capture_output=True, text=True)
        except Exception:
            pass
        return True
    return (
        "Playbook failed inside WSL "
        f"(rc={proc.returncode}).\nSTDOUT:\n{stdout}\nSTDERR:\n{proc.stderr}"
    )

if __name__ == "__main__":
    print(showrun())
