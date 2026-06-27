#!/usr/bin/env python3
"""
Database seeding script for ThutoPele EduLearn
Run this script after starting your FastAPI server to populate the database with sample data.
"""

import asyncio
import sys
import httpx
import random
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = "http://localhost:8000/api/v1"

# Sample courses with the new categories
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
    
    # Robotics Courses
    {
        "title": "Robotics Fundamentals with Arduino",
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
    {
        "title": "Industrial Robotics and Automation",
        "description": "Program industrial robots, PLCs, and automation systems. Learn robotic arm control and manufacturing automation.",
        "category": "Robotics",
        "level": "Advanced",
        "price": 79,
        "is_published": True
    },
    
    # Artificial Intelligence Courses
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
    {
        "title": "Natural Language Processing with AI",
        "description": "Build NLP applications using transformers, BERT, and GPT. Learn text classification, sentiment analysis, and language generation.",
        "category": "Artificial Intelligence",
        "level": "Intermediate",
        "price": 59,
        "is_published": True
    },
    
    # Machine Learning Courses
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
    {
        "title": "MLOps: Machine Learning Operations",
        "description": "Learn to deploy, monitor, and maintain ML models in production. Docker, Kubernetes, and CI/CD for ML.",
        "category": "Machine Learning",
        "level": "Advanced",
        "price": 79,
        "is_published": True
    },
    
    # Networking Courses
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
    {
        "title": "Cloud Networking with AWS",
        "description": "Design and implement cloud networks on AWS. VPC, subnets, load balancers, and hybrid networking.",
        "category": "Networking",
        "level": "Advanced",
        "price": 69,
        "is_published": True
    },
    
    # Cyber Security Courses
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
    },
    {
        "title": "Security Operations Center (SOC) Analyst",
        "description": "Learn SIEM, threat hunting, incident response, and security monitoring. Become a SOC analyst.",
        "category": "Cyber Security",
        "level": "Intermediate",
        "price": 59,
        "is_published": True
    }
]

async def create_user(client, email, password, username, full_name, is_instructor=False):
    """Create a user through the API"""
    print(f"Creating user: {email}...")
    
    try:
        response = await client.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": email,
                "password": password,
                "username": username,
                "full_name": full_name
            }
        )
        
        if response.status_code == 200:
            user_data = response.json()
            print(f" Created user: {email}")
            
            # Login to get token
            login_response = await client.post(
                f"{BASE_URL}/auth/login",
                data={
                    "username": email,
                    "password": password
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if login_response.status_code == 200:
                token_data = login_response.json()
                print(f" Logged in: {email}")
                
                # Note: You'll need to manually set is_instructor in Supabase dashboard
                if is_instructor:
                    print(f"      Remember to set {email} as instructor in Supabase dashboard")
                
                return token_data["access_token"]
            else:
                print(f"  Failed to login: {email}")
                return None
        else:
            print(f"  Failed to create user: {email} - {response.text}")
            return None
            
    except Exception as e:
        print(f"  Error creating user {email}: {e}")
        return None

async def create_course(client, token, course_data):
    """Create a course through the API"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = await client.post(
            f"{BASE_URL}/courses/",
            json=course_data,
            headers=headers
        )
        
        if response.status_code == 200:
            print(f" Created course: {course_data['title']}")
            return response.json()
        else:
            print(f"  Failed to create course: {course_data['title']}")
            print(f"   Status: {response.status_code}, Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"  Error creating course {course_data['title']}: {e}")
        return None

async def main():
    """Seed the database with sample data"""
    print("=" * 60)
    print("  Seeding Database with Sample Data")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Create instructor
        print("\n  Creating Instructor Account...")
        instructor_token = await create_user(
            client,
            "instructor@example.com",
            "password123",
            "instructor1",
            "John Instructor",
            is_instructor=True
        )
        
        # Create student
        print("\n  Creating Student Account...")
        student_token = await create_user(
            client,
            "student@example.com",
            "password123",
            "student1",
            "Jane Student"
        )
        
        if instructor_token:
            print("\n  Creating Sample Courses...")
            
            # Create courses
            created_courses = []
            for course_data in SAMPLE_COURSES:
                course = await create_course(client, instructor_token, course_data)
                if course:
                    created_courses.append(course)
            
            print(f"\n Created {len(created_courses)} courses successfully!")
            
            # Show statistics by category
            print("\n📊 Course Statistics by Category:")
            categories = {}
            for course in created_courses:
                cat = course.get('category')
                categories[cat] = categories.get(cat, 0) + 1
            
            for category, count in categories.items():
                print(f"   {category}: {count} courses")
        
        print("\n" + "=" * 60)
        print(" Seeding Complete!")
        print("=" * 60)
        print("\n  Login Credentials:")
        print("   Instructor: instructor@example.com / password123")
        print("   Student: student@example.com / password123")
        print("\n   Important Notes:")
        print("   1. Make sure your FastAPI server is running on http://localhost:8000")
        print("   2. Set instructor@example.com as instructor in Supabase dashboard")
        print("   3. You can now browse courses at http://localhost:8000/courses")
        print("\n  Categories added:")
        for category in ['Programming', 'Robotics', 'Artificial Intelligence', 'Machine Learning', 'Networking', 'Cyber Security']:
            print(f"   • {category}")

if __name__ == "__main__":
    # Check if server is running
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 8000))
    
    if result != 0:
        print("  Error: FastAPI server is not running on http://localhost:8000")
        print("   Please start your server first with: uvicorn app.main:app --reload")
        sys.exit(1)
    
    asyncio.run(main())