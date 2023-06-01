"""
By Aaron Ng (@localghost)

## Future Filesystems
A proof-of-concept way to process and organize files using GPT-4. This illustrates GPT-4's ability
to manipulate your file system in one directory, but consider a future operating system just sorts 
and presents files in whatever form you need them, whether that's based on relevance to your task, 
the contents, or so-on. 

## Disclaimer
You assume all liability for running this.
"""

import os
import json
import openai
import pkg_resources
import argparse


# Configure
openai_key = os.environ.get("OPENAI_API_KEY")
if not openai_key:
    raise Exception("Set your OPENAI_API_KEY")
openai.api_key = openai_key
preview_code = False  # Set to True if you want to preview the code.

# Chat History
assistant_chat_history = [
    {
        "role": "system",
        "content": "Explain how the code will change the files and get a confirmation or rejection from the user.",
    }
]
programmer_chat_history = [
    {
        "role": "system",
        "content": "You write processes with python code and never include markdown, comments, or formatting that cannot be directly run.",
    }
]


def process_files(directory):
    """
    Call process files to perform an action on a given directory.
    """
    print_system("What would you like to do with the files in the directory?")
    action = input("\033[1mAction: \033[0m")
    print("")

    # Get the filenames in the directory.
    print_system("Checking the directory...")
    files = get_filenames(directory)

    # Generate python with an understanding of the files.
    python_code = generate_python(action, programmer_chat_history, files)
    if not python_code:
        print_system(
            "Couldn't generate valid Python code for your command. Operation halted."
        )
        return

    # Preview code.
    if preview_code:
        print("Code Preview Start -------------------")
        print(python_code)
        print("Code Preview End -------------------")

    # Generate assistant response for confirmation.
    response = generate_response(python_code, files, assistant_chat_history)
    response_payload = json.loads(response)

    processing = True
    while processing:
        if "action" in response_payload:
            # User performed an action.
            if response_payload["action"] == "confirm":
                execute_python_code(python_code)
                print_system("Your files have been processed.")
            elif response_payload["action"] == "reject":
                print_system("Process stopped. Please run me again with a new command.")
            processing = False
        elif "text" in response_payload:
            # Print out a response to the user.
            print_system(response_payload["text"])
            user_input = input("\033[1mPlease confirm: \033[0m")
            print("")

            # Generate a response.
            response = generate_response(
                python_code,
                files,
                assistant_chat_history,
                user_input=user_input,
            )
            response_payload = json.loads(response)
        else:
            print("Unexpected response. Operation halted.")


def generate_response(code, files, assistant_chat_history, user_input=None):
    """
    This will generate responses so that you get a preview of what will happen.
    """
    assistant_chat_history.append(
        {
            "role": "user",
            "content": f"""You can provide one of three types of responses, all three of which are 
            json. Text responses look like this, where the value is your resonse: 
            {{"text": "value"}}. The other two responses are action types, which look like this: 
            {{"action": "confirm"}}, {{"action": "reject"}}. Visually explain the changes that the 
            following code will do to these files in the directory, with specific using the files 
            below. If the user says they would like to proceed send the confirm action: 
            {{"action": "confirm"}}, if they reject, use the reject action: {{"action": "reject"}}. 
            If you have something to say that is neither, or about further clarification, use the 
            text type. Code: \n {code}\n Files: \n {files}\n Latest User Input: {user_input}\n 
            Assistant JSON response:""",
        }
    )
    completion = openai.ChatCompletion.create(
        model="gpt-4", messages=assistant_chat_history, temperature=0
    )
    response = completion.choices[0].message.content
    assistant_chat_history.append({"role": "assistant", "content": response})
    return response


def generate_python(action, programmer_chat_history, files):
    """
    Generates python based on a user-provided action.
    """
    programmer_chat_history.append(
        {
            "role": "user",
            "content": f"""Generate Python code that accomplishes the following request from a user. 
            Request: {action}.\nThis task should be applied to all files in the current working 
            directory and its subdirectories.The Python code should not include hardcoded file paths, 
            instead, it should dynamically explore the directory structure using the os.walk() 
            function.\nNote: The file paths should be relative to the current working directory: 
            {os.getcwd()}.\n For understanding the file structure, here's a representation of the 
            files: {files}.\n Only use functions from the Python standard library or packages 
            included in this list: {get_packages_list()}. \n Include imports when relevant. Remove 
            all formatting, comments, or markdown syntax. Double check your work and ensure it is 
            valid python with no errors and achieves the user's stated request.""",
        }
    )
    completion = openai.ChatCompletion.create(
        model="gpt-4", messages=programmer_chat_history, temperature=0
    )
    response = completion.choices[0].message.content
    programmer_chat_history.append({"role": "assistant", "content": response})
    return response


def get_filenames(directory):
    return [
        os.path.join(dirpath, file)
        for dirpath, dirnames, files in os.walk(directory)
        for file in files
    ]


def get_packages_list():
    installed_packages = pkg_resources.working_set
    installed_packages_list = sorted(
        ["%s==%s" % (i.key, i.version) for i in installed_packages]
    )
    return installed_packages_list


def execute_python_code(code):
    if not args.RELIABILITY_GUARD_DISABLED:
        reliability_guard()
    try:
        exec(code, globals())
    except Exception as e:
        print("Error executing code: ", e)
        
        if args.SAVE_FAILED_TO:
            with open(f"{args.SAVE_FAILED_TO}", "w") as f:
                f.write(code)



def print_system(text):
    print(f"\033[1m\033[92m{text}\033[0m\n")


def print_user(text):
    print(f"\033[1m{text}\033[0m\n")


def print_status(text):
    print(f"\033[1m\033[96m{text}\033[0m\n")

def print_warn(text):
    print(f"\033[1m\033[93m{text}\033[0m\n")

## Reliability guard code from OpenAI Human Eval
# https://github.com/openai/human-eval/blob/master/human_eval/execution.py
# Add this by default to limit destrucive behavior.
# This feature can be disabled by invoking with --unsafe
def reliability_guard(maximum_memory_bytes: int = None):
    import platform
    """
    This disables various destructive functions and prevents the generated code
    from interfering with the test (e.g. fork bomb, killing other processes,
    removing filesystem files, etc.)

    WARNING
    This function is NOT a security sandbox. Untrusted code, including, model-
    generated code, should not be blindly executed outside of one. See the 
    Codex paper for more information about OpenAI's code sandbox, and proceed
    with caution.
    """

    if maximum_memory_bytes is not None:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (maximum_memory_bytes, maximum_memory_bytes))
        resource.setrlimit(resource.RLIMIT_DATA, (maximum_memory_bytes, maximum_memory_bytes))
        if not platform.uname().system == 'Darwin':
            resource.setrlimit(resource.RLIMIT_STACK, (maximum_memory_bytes, maximum_memory_bytes))


    import builtins
    builtins.exit = None
    builtins.quit = None

    import os
    os.environ['OMP_NUM_THREADS'] = '1'

    os.kill = None
    os.system = None
    os.putenv = None
    os.remove = None
    os.removedirs = None
    os.rmdir = None
    os.fchdir = None
    os.setuid = None
    os.fork = None
    os.forkpty = None
    os.killpg = None
    os.rename = None
    os.renames = None
    os.truncate = None
    os.replace = None
    os.unlink = None
    os.fchmod = None
    os.fchown = None
    os.chmod = None
    os.chown = None
    os.chroot = None
    os.fchdir = None
    os.lchflags = None
    os.lchmod = None
    os.lchown = None

    # Removing these restrictions for basic functionality
    #os.getcwd = None
    #os.chdir = None

    import shutil
    shutil.rmtree = None
    shutil.move = None
    shutil.chown = None

    import subprocess
    subprocess.Popen = None  # type: ignore

    import sys
    sys.modules['ipdb'] = None
    sys.modules['joblib'] = None
    sys.modules['resource'] = None
    sys.modules['psutil'] = None
    sys.modules['tkinter'] = None

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Interact with files using an LLM interface.')
    
    parser.add_argument('--unsafe', dest='RELIABILITY_GUARD_DISABLED', action='store_true', help='Disable reliability guard, such as os.* functions. Use at your own risk.')
    
    # Specify file to save failed code to.
    parser.add_argument('--save-failed', dest='SAVE_FAILED_TO', action='store', help='Filepath to save failed code to.')
   
    args = parser.parse_args()

    if args.RELIABILITY_GUARD_DISABLED:
        print_warn("WARNING: Reliability guard disabled. Use at your own risk.")
        
    process_files(os.getcwd())
