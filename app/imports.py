"""Normalize values read from CSV and Excel for JSON storage."""
from app.quality import plain


def records(frame):
    return [{str(key): plain(value) for key, value in row.items()}
            for row in frame.to_dict('records')]
