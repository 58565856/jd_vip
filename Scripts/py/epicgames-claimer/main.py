import importlib
import time

import schedule
import update_check
from pyppeteer.errors import BrowserError

import epicgames_claimer

args = epicgames_claimer.get_args(include_auto_update=True)
interactive = True if args.username == None else False
data_dir = "User_Data/Default" if interactive else None

def is_up_to_date() -> bool:
    try:
        up_to_date = update_check.isUpToDate("epicgames_claimer.py", "https://raw.githubusercontent.com/luminoleon/epicgames-claimer/master/epicgames_claimer.py")
        return up_to_date
    except Exception as e:
        epicgames_claimer.epicgames_claimer.log("Failed to check for update. {}: {}".format(e.__class__.__name__, e), level="warning")
        return True

def update() -> None:
    try:
        update_check.update("epicgames_claimer.py", "https://raw.githubusercontent.com/luminoleon/epicgames-claimer/master/epicgames_claimer.py")
        importlib.reload(epicgames_claimer)
        epicgames_claimer.epicgames_claimer.log("\"epicgames_claimer.py\" has been updated.")
    except Exception as e:
        epicgames_claimer.epicgames_claimer.log("Failed to update \"epicgames_claimer.py\". {}: {}".format(e.__class__.__name__, e), level="warning")

def run() -> None:
    if args.auto_update and not is_up_to_date():
        update()
    for i in range(3):
        try:
            claimer = epicgames_claimer.epicgames_claimer(data_dir, headless=not args.no_headless, chromium_path=args.chromium_path)
            claimer.add_quit_signal()
            claimer.run_once(interactive, args.username, args.password)
            break
        except BrowserError as e:
            epicgames_claimer.epicgames_claimer.log(str(e).replace("\n", " "), "warning")
            if i == 2:
                epicgames_claimer.epicgames_claimer.log("Failed to open the browser.", "error")
                return

def scheduled_run(at: str):
    schedule.every().day.at(at).do(run)
    while True:
        schedule.run_pending()
        time.sleep(1)

def main() -> None:
    epicgames_claimer.epicgames_claimer.log("Claimer is starting...")
    if args.auto_update and not is_up_to_date():
        update()
    claimer = epicgames_claimer.epicgames_claimer(data_dir, headless=not args.no_headless, chromium_path=args.chromium_path)
    if args.once == True:
        epicgames_claimer.epicgames_claimer.log("Claimer started.")
        claimer.run_once(interactive, args.username, args.password)
        epicgames_claimer.epicgames_claimer.log("Claim completed.")
    else:
        epicgames_claimer.epicgames_claimer.log("Claimer started. Run at {} everyday.".format(args.run_at))
        claimer.run_once(interactive, args.username, args.password)
        claimer.add_quit_signal()
        scheduled_run(args.run_at)

if __name__ == "__main__":
    main()
