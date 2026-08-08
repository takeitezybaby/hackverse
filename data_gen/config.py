from datetime import datetime

# Global Constants
START_DATE = datetime(2023, 9, 1)
NUM_DAYS = 30
NUM_USERS = 200
RANDOM_SEED = 42

# Checkin Generation Constants
REROUTE_THRESHOLD_PCT = 90
SKIP_PROBABILITY = 0.20
UNPLANNED_PROBABILITY = 0.10

# Resource Capacities
RESOURCE_CAPACITIES = {
    'Main Library': 300,
    'Science Library': 120,
    'Central Cafeteria': 250,
    'Food Court': 200,
    'Gymnasium': 80,
    'Indoor Sports Complex': 100,
    'Student Center': 150,
    'Computer Lab A': 60,
    'Computer Lab B': 60,
    'WiFi Zone - Academic Block': 500,
    'WiFi Zone - Library': 200,
    'WiFi Zone - Cafeteria': 300
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
