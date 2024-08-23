import subprocess
import os

def get_current_script_path():
    return os.path.dirname(os.path.abspath(__file__))

def check_executables():
    base_path = get_current_script_path()

    runner_path = os.path.join(base_path, 'exec\\runner.exe')
    sender_path = os.path.join(base_path, 'exec\\sender.exe')

    runner_exists = os.path.isfile(runner_path)
    sender_exists = os.path.isfile(sender_path)

    if not runner_exists:
        print(f"Error: runner.exe not found in {runner_path}")
    if not sender_exists:
        print(f"Error: sender.exe not found in {sender_path}")

    return runner_exists and sender_exists

def run_runner():
    try:
        subprocess.run(["powershell", "-Command", "Start-Process '.\\src\\exec\\runner.exe' -Verb runAs"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error while executing runner.exe: {e}")

def run_sender(com_port, file_path):
    try:
        sender_path = os.path.join(get_current_script_path(), 'exec\\sender.exe')
        command = f'& "{sender_path}" {com_port} "{file_path}"'
        subprocess.Popen(["powershell", "-Command", command])  # Popen, don't wait till the end of sender
        print("Sender started successfully.")
        return 0
    except Exception as e:
        print(f"Error while executing sender.exe: {e}")
        return 1

def start_simulation():
    try:
        exit = check_executables()

        if not exit:
            return
        
        run_runner()

        file_path = input("Please enter the path to the data file (e.g., path/to/folder/data.ubx): ")
        com_port = "COM8"
        
        if run_sender(com_port, file_path) != 0:
            print("Error in the sender data process...")
        else:
            print("Simulation executed successfully.")

    except Exception as e:
        print(f"Error during simulation: {e}")

if __name__ == "__main__":
    start_simulation()
