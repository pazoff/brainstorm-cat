from cat.mad_hatter.decorators import tool, hook, plugin
from cat.log import log
import threading
from pydantic import BaseModel

# Settings

# Default values
default_brainStorm_interval_seconds = 30


class BrainStormCatSettings(BaseModel):
    brainStorm_interval_seconds: int = default_brainStorm_interval_seconds
    

# Give your settings schema to the Cat.
@plugin
def settings_schema():
    return BrainStormCatSettings.schema()


alert_thread = None
stop_flag = threading.Event()

def stop_checking():
    global stop_flag
    try:
        stop_flag.set()
        return True
    except Exception as e:
        print("Error while stopping checking:", e)
        return False

def do_brainstorming(cat, interval_seconds, brainstorm_on):
    global stop_flag, alert_thread
    related_on = brainstorm_on
    
    while not stop_flag.is_set():
        try:
           cat.send_ws_message(content=f'Brainstorming on {related_on} ...', msg_type='chat_token')
           branestorm_result = cat.llm(f'Brainstorm great ideas based on {related_on}') 
           cat.send_ws_message(content=f'<b>BrainStorm Cat</b><br>Brainstorming on <b>{related_on}</b><br><br>{branestorm_result}', msg_type='chat')
           related_on = cat.llm(f'Write 1 question related to {related_on}.')
            
        except Exception as e:
            print("BrainStorm Cat: ERROR: ", e)
        
    
        stop_flag.wait(interval_seconds)

    stop_flag.clear()
    
    cat.send_ws_message(content='<b>BrainStorm Cat:</b> Brainstorming STOPPED', msg_type='chat')

@hook
def agent_fast_reply(fast_reply, cat):
    return_direct = True
    global alert_thread

    # Get user message from the working memory
    message = cat.working_memory["user_message_json"]["text"]

    if message.startswith('@brainstorm') or message.startswith('@brainstorm stop'):
        # Load settings
        settings = cat.mad_hatter.get_plugin().load_settings()
        brainStorm_interval_seconds = settings.get("brainStorm_interval_seconds")
        
        # Set default value for missing or invalid setting
        if (brainStorm_interval_seconds is None) or (brainStorm_interval_seconds < 30):
            brainStorm_interval_seconds = default_brainStorm_interval_seconds
    
        if message.startswith('@brainstorm stop'):
            if alert_thread is not None and alert_thread.is_alive():
                if stop_checking():
                    more_info = "<br><br>To start brainstorming again, type <b>@brainstorm your-topic</b>"
                    return {"output": "Brainstorming <b>OFF</b>" + more_info}
                else:
                    return {"output": "Error stopping Brainstorming."}
            else:
                return {"output": "Cannot stop. Brainstorming is <b>already OFF</b><br>To start brainstorming, type <b>@brainstorm your-topic</b>"}

        if message.startswith('@brainstorm'):
            if alert_thread is not None and alert_thread.is_alive():
                return {"output": "Cannot start. Brainstorming is <b>already ON</b><br>To stop brainstorming, type <b>@brainstorm stop</b> in the chat"}

            if alert_thread is None or not alert_thread.is_alive():
                brainstorm_on = message[len("@brainstorm "):] 
                if brainstorm_on != "":
                    alert_thread = threading.Thread(target=do_brainstorming, args=(cat, brainStorm_interval_seconds, brainstorm_on))
                    alert_thread.start()
                    more_info = "<br><br>To stop Brainstorming, type <b>@brainstorm stop</b> in the chat."
                    return {"output": f"Brainstorming <b>ON</b><br>New ideas based on <b>{brainstorm_on}</b> are comming every {brainStorm_interval_seconds} seconds." + more_info}
                else:
                    more_info = "<br> - To start brainstorming, type <b>@brainstorm your-topic</b><br><br> - To stop brainstorming, type <b>@brainstorm stop</b> in the chat"
                    return {"output": "<b>How to use BrainStorm Cat?</b><br>" + more_info}

    return None
