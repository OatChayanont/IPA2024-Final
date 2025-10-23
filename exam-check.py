#######################################################################################
# Yourname:
# Your student ID:
# Your GitHub Repo: 

#######################################################################################
# 1. Import libraries for API requests, JSON formatting, time, os, (restconf_final or netconf_final), netmiko_final, and ansible_final.

import requests
import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv
import random
from google.genai import Client 
from google.genai.types import GenerateContentConfig

#######################################################################################
# 2. Assign the Webex access token to the variable ACCESS_TOKEN using environment variables.

# Load .env in current folder (same dir as this script) without extra dependencies

# env_file = Path(__file__).parent / ".env"
# if env_file.exists():
#     with env_file.open() as f:
#         for line in f:
#             line = line.strip()
#             if not line or line.startswith("#") or "=" not in line:
#                 continue
#             k, v = line.split("=", 1)
#             os.environ.setdefault(k.strip(), v.strip())

load_dotenv()
ACCESS_TOKEN = os.getenv("WEBEX_ACCESS_TOKEN")
#######################################################################################
# 3. Prepare parameters get the latest message for messages API.

# Defines a variable that will hold the roomId
roomIdToGetMessages = os.getenv("WEBEX_ROOM_ID")

#########################################################################################
def send_webex_message(text):
    WEBEX_BOT_TOKEN = os.getenv("WEBEX_BOT_TOKEN")
    WEBEX_ROOM_ID = os.getenv("WEBEX_ROOM_ID")
    try:
        requests.post(
            "https://webexapis.com/v1/messages",
            headers={
                "Authorization": f"Bearer {WEBEX_BOT_TOKEN}",
                "Content-Type": "application/json"
            },
            json={"roomId": WEBEX_ROOM_ID, "markdown": text},
            timeout=10
        )
        print("Successfully sent message to Webex")
    except Exception as e:
        print(f"Webex post failed: {e}")

def send_webex_file(filename):
    print(f"Sending file {filename} to Webex")
    WEBEX_BOT_TOKEN = os.getenv("WEBEX_BOT_TOKEN") or os.getenv("WEBEX_ACCESS_TOKEN")
    WEBEX_ROOM_ID = os.getenv("WEBEX_ROOM_ID")
    if not WEBEX_BOT_TOKEN or not WEBEX_ROOM_ID:
        print("Missing WEBEX_BOT_TOKEN/WEBEX_ACCESS_TOKEN or WEBEX_ROOM_ID")
        return
    try:
        file_path = Path("backups") / Path(filename).name
        if not file_path.is_file():
            print(f"File not found: {file_path}")
            return
        with file_path.open('rb') as f:
            resp = requests.post(
                "https://webexapis.com/v1/messages",
                headers={
                    "Authorization": f"Bearer {WEBEX_BOT_TOKEN}"
                },
                data={"roomId": WEBEX_ROOM_ID, "text": "show running config"},
                files={"files": (file_path.name, f, "text/plain")},
                timeout=10
            )
            if resp.status_code != 200:
                print(f"Webex file post failed: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"Webex file post failed: {e}")

def ipa_create():
    from netconf_final import create
    responseMessage = create()
    print(responseMessage)
    send_webex_message(responseMessage)
    return responseMessage

def ipa_delete():
    from netconf_final import delete
    responseMessage = delete()
    print(responseMessage)
    send_webex_message(responseMessage)
    return responseMessage

def ipa_enable():
    from netconf_final import enable
    responseMessage = enable()
    print(responseMessage)
    send_webex_message(responseMessage)
    return responseMessage

def ipa_disable():
    from netconf_final import disable
    responseMessage = disable()
    print(responseMessage)
    send_webex_message(responseMessage)
    return responseMessage

def ipa_status():
    from netconf_final import status
    responseMessage = status()
    print(responseMessage)
    send_webex_message(responseMessage)
    return responseMessage

def ipa_gigabit_status():
    from netmiko_final import gigabit_status
    responseMessage = gigabit_status()
    print(responseMessage)
    send_webex_message(responseMessage)
    return responseMessage

def ipa_showrun():
    from ansible_final import showrun
    responseMessage = showrun()
    if responseMessage:
        send_webex_file("router1-running-config.txt")
    print(responseMessage)
    return responseMessage

def check_commands(user):
    commands = [
    "create",
    "status",
    "enable",
    "gigabit_status",
    "showrun",
    "disable",
    "delete",
    ]
    command_count = random.randrange(7, 10)
    result = []
    for _ in range(command_count):
        command_execute = random.randrange(0, len(commands))
        send_webex_message(f"/{user} {commands[command_execute]}")
        result.append(f"/{user} {commands[command_execute]}")
        while True:
            time.sleep(1)
            json_data = get_message_from_webex()
            messages = json_data["items"]
            message = messages[0]["text"]
            print("Received message: " + message)
            if message.startswith(f"/{user}"):
                continue
            elif message.startswith("/cancel"):
                result.append("Cancelled by user.")
                send_webex_message(f"Command checking for user {user} cancelled. \n --------------------------------------------------")
                return 
            else:
                result.append(message)
                break
    send_webex_message(f"User {user} check commands completed. \n --------------------------------------------------")
    
    script_dir = Path(__file__).resolve().parent
    try:
        log_dir = script_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        file_path = log_dir / f"{user}.txt"
    except OSError as e:
        print(f"Warning: Could not create directory {log_dir}: {e}. Saving to script directory.")
        file_path = script_dir / f"{user}.txt"
    print(file_path)
    print(result)
    with open(file_path, "w") as f:
        f.write("\n".join(result))
    print(f"Results for {user} saved to {file_path}")

def get_message_from_webex():
    getParameters = {"roomId": roomIdToGetMessages, "max": 1}

    # the Webex Teams HTTP header, including the Authoriztion
    getHTTPHeader = {"Authorization": "Bearer " + ACCESS_TOKEN}

# 4. Provide the URL to the Webex Teams messages API, and extract location from the received message.
    
    # Send a GET request to the Webex Teams messages API.
    # - Use the GetParameters to get only the latest message.
    # - Store the message in the "r" variable.
    r = requests.get(
        "https://webexapis.com/v1/messages",
        params=getParameters,
        headers=getHTTPHeader,
    )
    # verify if the retuned HTTP status code is 200/OK
    if not r.status_code == 200:
        raise Exception(
            "Incorrect reply from Webex Teams API. Status code: {}".format(r.status_code)
        )

    # get the JSON formatted returned data
    json_data = r.json()

    # check if there are any messages in the "items" array
    if len(json_data["items"]) == 0:
        raise Exception("There are no messages in the room.")
    return json_data
def connect_to_gemini(question):
    client = Client(api_key=os.getenv("GOOGLE_API_KEY"))
    model = "gemini-2.5-flash"
    resp = client.models.generate_content(
        model=model,
        contents=question,
        config=GenerateContentConfig(temperature=0.3),
        )
    print("Gemini Response:", resp.text)
    return resp.text
#########################################################################################

while True:
    # always add 1 second of delay to the loop to not go over a rate limit of API calls
    time.sleep(1)

    json_data = get_message_from_webex()
    # the Webex Teams GET parameters
    #  "roomId" is the ID of the selected room
    #  "max": 1  limits to get only the very last message in the room
    

    # store the array of messages
    messages = json_data["items"]
    
    # store the text of the first message in the array
    message = messages[0]["text"]
    sender = messages[0]["personEmail"]
    admins = ["64070017", "chotipat.po"]
    print("Received message: " + message)

    # check if the text of the message starts with the magic character "/" followed by your studentID and a space and followed by a command name
    #  e.g.  "/66070123 create"
    if message.startswith("/64070017"):

        # extract the command
        command = message.split(" ")[1]
        print(command)

# 5. Complete the logic for each command

        if command == "create":
            ipa_create()
        elif command == "delete":
            ipa_delete()
        elif command == "enable":
            ipa_enable()
        elif command == "disable":
            ipa_disable()
        elif command == "status":
            ipa_status()
        elif command == "gigabit_status":
            ipa_gigabit_status()
        elif command == "showrun":
            ipa_showrun()
        else:
            responseMessage = "Error: No command or unknown command"
            send_webex_message(responseMessage)
    elif message.startswith("/help"):
        responseMessage = (
                "สิ่งที่ต้องทำ ทำใน Router IP 10.0.15.61:\n"
                "/66070xxx create\n"
                "/66070xxx delete\n"
                "/66070xxx enable\n"
                "/66070xxx disable\n"
                "/66070xxx status\n"
                "/66070xxx gigabit_status\n"
                "/66070xxx showrun\n"
        )
        send_webex_message(responseMessage)
        #################################################
    elif message.startswith("/check"):
        user = message.split(" ")[1]
        print(user)
        send_webex_message(f"--------------------------------------------------\n Hello! {user}: Checking Student ID commands...")
        if sender.split("@")[0] == user:
            send_webex_message(f"User: {user} checked in. Starting checking commands...")
            check_commands(user)
        elif sender.split("@")[0] in admins:
            send_webex_message(f"Admin User: Starting checking commands...")
            check_commands(user)
        else:
            send_webex_message(f"You are not allowed to check for user {user}.")
        #################################################
    elif message.startswith("/ask"):
        question = message.split(" ")[1:]
        question = " ".join(question)
        print("Question: " + question)
        ans = connect_to_gemini(question)
        send_webex_message(ans)
        
# 6. Complete the code to post the message to the Webex Teams room.

        # The Webex Teams POST JSON data for command showrun
        # - "roomId" is is ID of the selected room
        # - "text": is always "show running config"
        # - "files": is a tuple of filename, fileobject, and filetype.

        # the Webex Teams HTTP headers, including the Authoriztion and Content-Type
        
        # Prepare postData and HTTPHeaders for command showrun
        # Need to attach file if responseMessage is 'ok'; 
        # Read Send a Message with Attachments Local File Attachments
        # https://developer.webex.com/docs/basics for more detail
        #################################################
        # if command == "showrun" and responseMessage == 'ok':
        #     filename = "<!!!REPLACEME with show run filename and path!!!>"
        #     fileobject = <!!!REPLACEME with open file!!!>
        #     filetype = "<!!!REPLACEME with Content-type of the file!!!>"
        #     postData = {
        #         "roomId": <!!!REPLACEME!!!>,
        #         "text": "show running config",
        #         "files": (<!!!REPLACEME!!!>, <!!!REPLACEME!!!>, <!!!REPLACEME!!!>),
        #     }
        #     postData = MultipartEncoder(<!!!REPLACEME!!!>)
        #     HTTPHeaders = {
        #     "Authorization": ACCESS_TOKEN,
        #     "Content-Type": <!!!REPLACEME with postData Content-Type!!!>,
        #     }
        # # other commands only send text, or no attached file.
        # else:
        #     postData = {"roomId": <!!!REPLACEME!!!>, "text": <!!!REPLACEME!!!>}
        #     postData = json.dumps(postData)

        #     # the Webex Teams HTTP headers, including the Authoriztion and Content-Type
        #     HTTPHeaders = {"Authorization": <!!!REPLACEME!!!>, "Content-Type": <!!!REPLACEME!!!>}   

        # # Post the call to the Webex Teams message API.
        # r = requests.post(
        #     "<!!!REPLACEME with URL of Webex Teams Messages API!!!>",
        #     data=<!!!REPLACEME!!!>,
        #     headers=<!!!REPLACEME!!!>,
        # )
        # if not r.status_code == 200:
        #     raise Exception(
        #         "Incorrect reply from Webex Teams API. Status code: {}".format(r.status_code)
        #     )


