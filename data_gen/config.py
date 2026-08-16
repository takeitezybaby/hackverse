from datetime import datetime

# Global Constants
START_DATE = datetime(2023, 9, 1)
NUM_DAYS = 30
NUM_USERS = 1500
RANDOM_SEED = 42
DEMO_NOW = datetime(2023, 9, 12, 8, 0, 0)  # Reference clock for live demo (8:00 AM Tuesday morning)

# Checkin Generation Constants
REROUTE_THRESHOLD_PCT = 90
SKIP_PROBABILITY = 0.15          # lowered from 0.20 so more visits happen
UNPLANNED_PROBABILITY = 0.12     # slightly higher spontaneous visits
BUCKET_MINUTES = 15

# Resource Capacities (lowered for smaller venues to create realistic congestion)
RESOURCE_CAPACITIES = {
    'Main Library': 200,
    'Science Library': 80,
    'Central Cafeteria': 180,
    'Food Court': 120,
    'Gymnasium': 50,
    'Indoor Sports Complex': 60,
    'Student Center': 100,
    'Computer Lab A': 35,
    'Computer Lab B': 35,
    'WiFi Zone - Academic Block': 400,
    'WiFi Zone - Library': 150,
    'WiFi Zone - Cafeteria': 200
}

# Venue Operating Hours (used by Digital Twin state and RAG engine)
OPERATING_HOURS = {
    'Main Library':               {'open': '08:00', 'close': '23:00'},
    'Science Library':            {'open': '08:00', 'close': '22:00'},
    'Central Cafeteria':          {'open': '07:30', 'close': '21:30'},
    'Food Court':                 {'open': '08:00', 'close': '22:00'},
    'Gymnasium':                  {'open': '06:00', 'close': '21:00'},
    'Indoor Sports Complex':      {'open': '06:00', 'close': '21:00'},
    'Student Center':             {'open': '07:00', 'close': '23:00'},
    'Computer Lab A':             {'open': '08:00', 'close': '22:00'},
    'Computer Lab B':             {'open': '08:00', 'close': '22:00'},
    'WiFi Zone - Academic Block': {'open': '00:00', 'close': '23:59'},
    'WiFi Zone - Library':        {'open': '07:00', 'close': '23:00'},
    'WiFi Zone - Cafeteria':      {'open': '07:00', 'close': '22:00'},
}

# Anomaly Configurations
ANOMALIES = {
    'exam_week': {
        'start_date': datetime(2023, 9, 25),
        'end_date': datetime(2023, 9, 30),
        'type': 'exam_period'
    },
    'fest': {
        'start_date': datetime(2023, 9, 15),
        'end_date': datetime(2023, 9, 16),
        'type': 'cultural_fest'
    },
    'infra_incident': {
        'start_date': datetime(2023, 9, 10),
        'end_date': datetime(2023, 9, 10),
        'resource': 'Computer Lab A',
        'type': 'infra_incident'
    },
    'class_cancellation': {
        'target_date': datetime(2023, 9, 20),
        'type': 'class_cancellation'
    }
}

# Peak hour definitions (used by user_gen to concentrate patterns)
PEAK_HOURS = {
    'Library':    {'primary': [(16, 20)], 'secondary': [(10, 12)]},
    'Cafeteria':  {'primary': [(12, 13)], 'secondary': [(18, 19)]},
    'Food':       {'primary': [(12, 13)], 'secondary': [(18, 20)]},
    'Gym':        {'primary': [(17, 20)], 'secondary': [(6, 8)]},
    'Sports':     {'primary': [(17, 19)], 'secondary': [(7, 9)]},
    'Lab':        {'primary': [(14, 18)], 'secondary': [(10, 12)]},
    'Student':    {'primary': [(15, 19)], 'secondary': [(11, 13)]},
    'WiFi':       {'primary': [(10, 17)], 'secondary': [(18, 21)]},
}

# Popular resources (weighted selection for routine patterns)
POPULAR_RESOURCES = [
    ('Main Library', 5),
    ('Central Cafeteria', 5),
    ('Gymnasium', 4),
    ('Computer Lab A', 4),
    ('Computer Lab B', 3),
    ('Student Center', 3),
    ('Food Court', 3),
    ('Science Library', 3),
    ('Indoor Sports Complex', 2),
    ('WiFi Zone - Academic Block', 2),
    ('WiFi Zone - Library', 1),
    ('WiFi Zone - Cafeteria', 1),
]
