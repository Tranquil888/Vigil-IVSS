#!/usr/bin/env python3
"""
Setup script to create first admin user for Vigil surveillance system.
Run this script if no users exist in the database.
"""

import sys
import os
import hashlib

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vigil.database.manager import AuthenticationDatabase
from vigil.utils.logging_config import get_auth_logger

def create_admin_user():
    """Create the first admin user."""
    logger = get_auth_logger()
    
    print("=== Vigil Admin User Setup ===")
    print("This script will create the first administrator user.")
    print()
    
    try:
        # Initialize database
        auth_db = AuthenticationDatabase()
        
        # Check if users already exist
        users = auth_db.get_all_users()
        if users:
            print(f"Found {len(users)} existing users:")
            for user in users:
                print(f"  - {user['username']} ({user['role']})")
            print()
            
            response = input("Users already exist. Do you want to create another admin user? (y/n): ")
            if response.lower() != 'y':
                print("Setup cancelled.")
                return
        
        # Get admin credentials
        print("Create Administrator Account")
        print("-" * 30)
        
        while True:
            username = input("Enter admin username: ").strip()
            if username:
                if len(username) < 3:
                    print("Username must be at least 3 characters long.")
                    continue
                if len(username) > 50:
                    print("Username must be less than 50 characters.")
                    continue
                break
            print("Username is required.")
        
        while True:
            password = input("Enter admin password: ")
            if password:
                if len(password) < 6:
                    print("Password must be at least 6 characters long.")
                    continue
                confirm_password = input("Confirm password: ")
                if password == confirm_password:
                    break
                print("Passwords do not match.")
            else:
                print("Password is required.")
        
        # Hash password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Create admin user
        success = auth_db.create_user(username, password_hash, 'admin')
        
        if success:
            print()
            print("✅ Admin user created successfully!")
            print(f"Username: {username}")
            print("Role: Administrator")
            print()
            print("You can now login to the Vigil application using these credentials.")
            print("Run: python main_new.py")
            
            logger.info(f"Admin user '{username}' created via setup script")
            
        else:
            print("❌ Failed to create admin user.")
            print("Please check the logs for more information.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Admin setup error: {e}")

if __name__ == "__main__":
    create_admin_user()
