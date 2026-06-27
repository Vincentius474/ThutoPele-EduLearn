#!/usr/bin/env python3
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8000/api/v1"
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

async def create_user(email, password, username, full_name, is_instructor=False, is_admin=False):
    """Create a user with specified role"""
    print(f"Creating {username}...")
    
    async with httpx.AsyncClient() as client:
        # Register user
        response = await client.post(
            f"{BASE_URL}/auth/register/student",
            json={
                "email": email,
                "password": password,
                "username": username,
                "full_name": full_name,
                "role": "student"
            }
        )
        
        if response.status_code == 200:
            print(f" Created: {email}")
            
            # Update role if needed
            if is_instructor or is_admin:
                headers = {
                    "apikey": SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                    "Content-Type": "application/json"
                }
                
                # Get user ID
                user_resp = await client.get(
                    f"{SUPABASE_URL}/auth/v1/admin/users",
                    headers=headers
                )
                
                if user_resp.status_code == 200:
                    users = user_resp.json().get('users', [])
                    user_id = None
                    for u in users:
                        if u.get('email') == email:
                            user_id = u.get('id')
                            break
                    
                    if user_id:
                        # Update profile
                        await client.patch(
                            f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}",
                            headers=headers,
                            json={
                                "is_instructor": is_instructor,
                                "is_admin": is_admin
                            }
                        )
                        print(f"   Role updated: {'Admin' if is_admin else 'Instructor' if is_instructor else 'Student'}")
            return True
        else:
            print(f"  Failed: {response.text}")
            return False

async def main():
    print("=" * 50)
    print("Creating Test Accounts")
    print("=" * 50)
    
    # Create Student
    await create_user(
        "student@example.com",
        "password123",
        "student1",
        "Jane Student",
        is_instructor=False,
        is_admin=False
    )
    
    # Create Instructor
    await create_user(
        "instructor@example.com",
        "password123",
        "instructor1",
        "John Instructor",
        is_instructor=True,
        is_admin=False
    )
    
    # Create Admin
    await create_user(
        "admin@example.com",
        "password123",
        "admin1",
        "Admin User",
        is_instructor=False,
        is_admin=True
    )
    
    print("\n" + "=" * 50)
    print("Test Accounts Created Successfully!")
    print("=" * 50)
    print("\n  Login Credentials:")
    print("   Student:  student@example.com / password123")
    print("   Instructor: instructor@example.com / password123")
    print("   Admin:    admin@example.com / password123")
    print("\n  Access dashboards:")
    print("   http://localhost:8000/dashboard")

if __name__ == "__main__":
    asyncio.run(main())