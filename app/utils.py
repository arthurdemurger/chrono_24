from datetime import timedelta

def format_lap_duration(sec):
    try:
        sec = float(sec)
        if sec <= 0:
            return "N/A"
        return str(timedelta(seconds=int(sec)))
    except:
        return "N/A"
