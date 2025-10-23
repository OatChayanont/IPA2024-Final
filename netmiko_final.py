from netmiko import ConnectHandler
from pprint import pprint
from dotenv import load_dotenv
import os
import time

load_dotenv()

device_ip = os.getenv("ROUTER_IP")
username = os.getenv("ROUTER_USERNAME")
password = os.getenv("ROUTER_PASSWORD")

device_params = {
    "device_type": "cisco_ios",
    "ip": device_ip,
    "username": username,
    "password": password,
}


def gigabit_status():
    ans = ""
    max_retries = 3
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            with ConnectHandler(**device_params) as ssh:
                up = 0
                down = 0
                admin_down = 0
                # Use TextFSM to get structured data
                result = ssh.send_command("show ip interface brief", use_textfsm=True)
                if not isinstance(result, list):
                    ans = "Failed to parse interface data."
                    pprint(ans)
                    return ans
                print(result)
                for status in result:
                    if status.get("interface", "").startswith("GigabitEthernet"):
                        iface_state = status.get("status", "").lower()
                        if iface_state == "up":
                            up += 1
                        elif iface_state == "down":
                            down += 1
                        elif iface_state == "administratively down":
                            admin_down += 1
                ans = f"GigabitEthernet interfaces -> up: {up}, down: {down}, administratively down: {admin_down}"
                pprint(ans)
                return ans  # Success, exit the function
        except Exception as e:
            print(f"Attempt {attempt + 1} of {max_retries} failed: {e}")
            if attempt + 1 < max_retries:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("All attempts failed.")
    
    ans = "Failed to connect to the device after multiple attempts."
    pprint(ans)
    return ans
