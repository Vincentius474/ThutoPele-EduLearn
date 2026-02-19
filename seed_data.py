#!/usr/bin/env python3
import asyncio
import httpx
import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
BASE_URL = "http://localhost:8000/api/v1"

SAMPLE_COURSES = [
    # Programming Courses
    {
        "title": "Python Programming Masterclass",
        "description": "Complete Python programming course from beginner to advanced. Learn variables, functions, OOP, file handling, and more with practical projects.",
        "category": "Programming",
        "level": "Beginner",
        "price": 0,
        "is_published": True
    },
    {
        "title": "Advanced Java Development with Spring Boot",
        "description": "Master Java development with Spring Boot, Hibernate, microservices, and REST APIs. Build enterprise-grade applications.",
        "category": "Programming",
        "level": "Advanced",
        "price": 49,
        "is_published": True
    },
    {
        "title": "JavaScript: The Complete Guide",
        "description": "Modern JavaScript from ES6 to advanced concepts. Includes async programming, promises, and DOM manipulation.",
        "category": "Programming",
        "level": "Intermediate",
        "price": 39,
        "is_published": True
    },
    # Robotics
    {
        "title": "Robotics with Arduino",
        "description": "Learn robotics basics with Arduino. Build and program your own robots, work with sensors, motors, and microcontrollers.",
        "category": "Robotics",
        "level": "Beginner",
        "price": 39,
        "is_published": True
    },
    {
        "title": "ROS (Robot Operating System) for Beginners",
        "description": "Master Robot Operating System (ROS) for advanced robotics applications. Learn simulation, navigation, and robot control.",
        "category": "Robotics",
        "level": "Intermediate",
        "price": 59,
        "is_published": True
    },
    # AI
    {
        "title": "Artificial Intelligence Fundamentals",
        "description": "Learn AI concepts, search algorithms, knowledge representation, and expert systems. Build intelligent agents.",
        "category": "Artificial Intelligence",
        "level": "Beginner",
        "price": 45,
        "is_published": True
    },
    {
        "title": "Deep Learning and Neural Networks",
        "description": "Master neural networks, CNN, RNN, and transformers for AI applications. Implement using PyTorch and TensorFlow.",
        "category": "Artificial Intelligence",
        "level": "Advanced",
        "price": 69,
        "is_published": True
    },
    # Machine Learning
    {
        "title": "Machine Learning with Python",
        "description": "Comprehensive ML course covering regression, classification, clustering, and model evaluation. Use scikit-learn and pandas.",
        "category": "Machine Learning",
        "level": "Intermediate",
        "price": 55,
        "is_published": True
    },
    {
        "title": "TensorFlow 2.0 Deep Learning",
        "description": "Build and deploy deep learning models with TensorFlow and Keras. Cover CNN, RNN, and model deployment.",
        "category": "Machine Learning",
        "level": "Advanced",
        "price": 65,
        "is_published": True
    },
    # Networking
    {
        "title": "Computer Networking Fundamentals",
        "description": "Learn TCP/IP, OSI model, routing, switching, and network protocols. Perfect for beginners.",
        "category": "Networking",
        "level": "Beginner",
        "price": 35,
        "is_published": True
    },
    {
        "title": "CCNA Certification Course",
        "description": "Complete preparation for Cisco CCNA certification exam. Includes labs and practice tests.",
        "category": "Networking",
        "level": "Intermediate",
        "price": 79,
        "is_published": True
    },
    # Cyber Security
    {
        "title": "Cyber Security Fundamentals",
        "description": "Learn security fundamentals, cryptography, and network security. Understand threats and defense mechanisms.",
        "category": "Cyber Security",
        "level": "Beginner",
        "price": 45,
        "is_published": True
    },
    {
        "title": "Ethical Hacking and Penetration Testing",
        "description": "Master ethical hacking techniques, vulnerability assessment, and penetration testing methodologies.",
        "category": "Cyber Security",
        "level": "Advanced",
        "price": 89,
        "is_published": True
    }
]

async def wait_for_server(max_retries=5, delay=2):
    """Wait for FastAPI server to be ready"""
    print("Checking if FastAPI server is running...")
    
    for i in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:8000/health")
                if response.status_code == 200:
                    print("✅ FastAPI server is running")
                    return True
        except:
            print(f"⏳ Waiting for server (attempt {i+1}/{max_retries})...")
            time.sleep(delay)
    
    print("❌ FastAPI server is not responding")
    print("Please run: uvicorn app.main:app --reload")
    return False

async def create_user_with_service_role(email, password, username, full_name, is_instructor=False):
    """Create user using service role key"""
    print(f"Creating user: {email}...")
    
    if not SUPABASE_SERVICE_KEY:
        print("❌ SUPABASE_SERVICE_KEY not found in .env file")
        return None
    
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Check if user already exists
            check_response = await client.get(
                f"{SUPABASE_URL}/auth/v1/admin/users",
                headers=headers
            )
            
            if check_response.status_code == 200:
                users = check_response.json().get('users', [])
                for user in users:
                    if user.get('email') == email:
                        print(f"⚠️ User {email} already exists with ID: {user['id']}")
                        
                        # Still try to create/update profile
                        profile_response = await client.post(
                            f"{SUPABASE_URL}/rest/v1/users",
                            headers={
                                **headers,
                                "Prefer": "return=representation"
                            },
                            json={
                                "id": user['id'],
                                "email": email,
                                "username": username,
                                "full_name": full_name,
                                "is_instructor": is_instructor
                            }
                        )
                        
                        if profile_response.status_code in [200, 201]:
                            print(f"✅ Profile updated for {email}")
                            return user['id']
                        else:
                            print(f"⚠️ Could not update profile: {profile_response.text}")
                            return user['id']
            
            # Create new user if doesn't exist
            print(f"   Creating new auth user...")
            auth_response = await client.post(
                f"{SUPABASE_URL}/auth/v1/admin/users",
                headers=headers,
                json={
                    "email": email,
                    "password": password,
                    "email_confirm": True,
                    "user_metadata": {
                        "full_name": full_name,
                        "username": username
                    }
                }
            )
            
            if auth_response.status_code != 200:
                print(f"❌ Failed to create auth user: {auth_response.text}")
                return None
            
            user_data = auth_response.json()
            user_id = user_data['id']
            print(f"   ✅ Auth user created with ID: {user_id}")
            
            # Create profile
            print(f"   Creating user profile...")
            profile_response = await client.post(
                f"{SUPABASE_URL}/rest/v1/users",
                headers={
                    **headers,
                    "Prefer": "return=representation"
                },
                json={
                    "id": user_id,
                    "email": email,
                    "username": username,
                    "full_name": full_name,
                    "is_instructor": is_instructor,
                    "is_admin": False
                }
            )
            
            if profile_response.status_code in [200, 201]:
                print(f"   ✅ Profile created successfully")
                return user_id
            else:
                print(f"❌ Failed to create profile: {profile_response.text}")
                return None
                
        except httpx.TimeoutException:
            print(f"❌ Timeout while creating user {email}")
            return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

async def login_with_retry(client, email, password, max_retries=3):
    """Login with retry logic"""
    for attempt in range(max_retries):
        try:
            response = await client.post(
                f"{BASE_URL}/auth/login",
                data={
                    "username": email,
                    "password": password
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.json()["access_token"]
            elif response.status_code == 401:
                print(f"   Invalid credentials for {email}")
                return None
            else:
                print(f"   Attempt {attempt + 1}: Status {response.status_code}")
                
        except httpx.TimeoutException:
            print(f"   Attempt {attempt + 1}: Timeout")
        except Exception as e:
            print(f"   Attempt {attempt + 1}: {e}")
        
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt
            print(f"   Waiting {wait_time} seconds...")
            time.sleep(wait_time)
    
    return None

async def create_courses_with_api(instructor_email, password):
    """Create courses by logging in as instructor"""
    print("\n📚 Creating Courses...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Login as instructor with retry
        print(f"Logging in as {instructor_email}...")
        token = await login_with_retry(client, instructor_email, password)
        
        if not token:
            print("❌ Could not login as instructor")
            print("\nTroubleshooting tips:")
            print("1. Make sure your FastAPI server is running")
            print("2. Check if the user exists in Supabase")
            print("3. Try logging in manually at http://localhost:8000/login")
            return False
        
        print("✅ Logged in successfully")
        
        # Create courses
        headers = {"Authorization": f"Bearer {token}"}
        created_count = 0
        skipped_count = 0
        
        for course in SAMPLE_COURSES:
            try:
                # Check if course already exists (optional - you might want to skip duplicates)
                response = await client.post(
                    f"{BASE_URL}/courses/",
                    json=course,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    created_count += 1
                    print(f"   ✅ Created: {course['title']}")
                elif response.status_code == 403:
                    print(f"   ⚠️ Need instructor privileges for: {course['title']}")
                    print("\n📝 To fix this:")
                    print("   1. Go to Supabase Dashboard → Table Editor → users")
                    print("   2. Find instructor@example.com")
                    print("   3. Set 'is_instructor' to true")
                    print("   4. Click Save")
                    print("   5. Run this script again")
                    return False
                else:
                    skipped_count += 1
                    print(f"   ❌ Failed: {course['title']} - {response.status_code}")
                    
            except httpx.TimeoutException:
                print(f"   ⏳ Timeout creating: {course['title']}")
                skipped_count += 1
            except Exception as e:
                print(f"   ❌ Error creating {course['title']}: {e}")
                skipped_count += 1
        
        print(f"\n✅ Created {created_count} courses")
        if skipped_count > 0:
            print(f"⚠️ Skipped {skipped_count} courses due to errors")
        
        return True

async def main():
    print("=" * 60)
    print("🚀 Seeding Database with Service Role")
    print("=" * 60)
    
    # Check if server is running
    if not await wait_for_server():
        return
    
    # Check for service key
    if not SUPABASE_SERVICE_KEY:
        print("\n❌ ERROR: SUPABASE_SERVICE_KEY not found in .env file")
        print("\nTo fix this:")
        print("1. Go to Supabase Dashboard → Project Settings → API")
        print("2. Copy the 'service_role' key")
        print("3. Add it to your .env file:")
        print("   SUPABASE_SERVICE_KEY=your-service-role-key-here")
        return
    
    # Create instructor
    print("\n📝 Creating Instructor Account...")
    instructor_id = await create_user_with_service_role(
        "instructor@example.com",
        "password123",
        "instructor1",
        "John Instructor",
        is_instructor=True
    )
    
    # Create student (if needed)
    print("\n📝 Creating Student Account...")
    student_id = await create_user_with_service_role(
        "student@example.com",
        "password123",
        "student1",
        "Jane Student",
        is_instructor=False
    )
    
    if instructor_id:
        # Create courses
        success = await create_courses_with_api("instructor@example.com", "password123")
        
        if not success:
            print("\n⚠️ Course creation incomplete. Please follow the instructions above.")
    else:
        print("\n❌ Failed to create instructor account")
    
    print("\n" + "=" * 60)
    print("✅ Seeding Process Complete!")
    print("=" * 60)
    print("\n🔑 Login Credentials:")
    print("   Instructor: instructor@example.com / password123")
    print("   Student: student@example.com / password123")
    print("\n📚 Categories added:")
    for category in ['Programming', 'Robotics', 'Artificial Intelligence', 
                    'Machine Learning', 'Networking', 'Cyber Security']:
        print(f"   • {category}")
    
    print("\n🌐 Visit: http://localhost:8000")
    print("📚 Browse courses: http://localhost:8000/courses")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Seeding interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")