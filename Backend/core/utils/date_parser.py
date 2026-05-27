import datetime

def try_parse_date(date_str):
    """
    Handles DD.MM.YYYY, YYYYMMDD, MM/DD/YYYY formats.
    Returns a date object or None.
    """
    if not date_str:
        return None
        
    date_str = date_str.strip()
    formats = ['%d.%m.%Y', '%Y%m%d', '%m/%d/%Y', '%Y-%m-%d']
    
    for fmt in formats:
        try:
            return datetime.datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
            
    return None
