import datetime

def get_current_week_start_end():
    today = datetime.date.today()
    # Get the ISO week number and year
    iso_week = today.isocalendar()
    # Calculate the start of the week based on the ISO week
    week_start = today + datetime.timedelta(days=-iso_week[2] + 1)
    week_end = week_start + datetime.timedelta(days=6)
    return week_start.strftime("%d/%m/%Y"), week_end.strftime("%d/%m/%Y")

# Example usage:
start_date, end_date = get_current_week_start_end()
print("Start of the week:", start_date)
print("End of the week:", end_date)