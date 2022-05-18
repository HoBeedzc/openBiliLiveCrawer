import datetime


# Logs
def log(level="INFO", msg=""):
    now = str(datetime.datetime.now()).split('.')[0]
    if level == "ERROR":
        color = "\033[0;31m"
    elif level == "WARNING":
        color = "\033[0;33m"
    elif level == "INFO":
        color = "\033[0;32m"
    else:
        color = "\033[0;37m"
    print(f"{color}[{now}] {level} : {msg}\033[0m")


def log_info(msg=""):
    log("INFO", msg)


def log_warn(msg=""):
    log("WARNING", msg)


def log_error(msg=""):
    log("ERROR", msg)
