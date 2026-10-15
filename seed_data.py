"""
Root compatibility wrapper for Lucas Garage dummy data seeder.
Delegates directly to dummy_data/seed_data.py.
"""
from dummy_data.seed_data import seed_database

if __name__ == '__main__':
    seed_database()
