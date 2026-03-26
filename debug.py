#!/usr/bin/env python3
import os
import json

print("=== Railway Debug Script ===")

# Check environment variables
required_vars = ['DISCORD_TOKEN', 'MOD_CHANNEL_ID', 'FIREBASE_PROJECT_ID', 'OPENAI_API_KEY', 'FIREBASE_CRED_JSON']
missing_vars = []

for var in required_vars:
    value = os.getenv(var)
    if value:
        print(f"✅ {var}: Set")
    else:
        print(f"❌ {var}: Missing")
        missing_vars.append(var)

# Check Firebase JSON
firebase_json = os.getenv('FIREBASE_CRED_JSON')
if firebase_json:
    try:
        parsed = json.loads(firebase_json)
        print("✅ FIREBASE_CRED_JSON: Valid JSON")
        required_keys = ['type', 'project_id', 'private_key', 'client_email']
        for key in required_keys:
            if key in parsed:
                print(f"  ✅ Contains {key}")
            else:
                print(f"  ❌ Missing {key}")
    except json.JSONDecodeError as e:
        print(f"❌ FIREBASE_CRED_JSON: Invalid JSON - {e}")
else:
    print("❌ FIREBASE_CRED_JSON: Not set")

if missing_vars:
    print(f"\n❌ Missing required environment variables: {', '.join(missing_vars)}")
    exit(1)
else:
    print("\n✅ All required environment variables are set")

print("\n=== Testing Imports ===")
try:
    import discord
    print("✅ discord: OK")
except ImportError as e:
    print(f"❌ discord: {e}")

try:
    import firebase_admin
    print("✅ firebase_admin: OK")
except ImportError as e:
    print(f"❌ firebase_admin: {e}")

try:
    import openai
    print("✅ openai: OK")
except ImportError as e:
    print(f"❌ openai: {e}")

# Test Firebase initialization and connectivity
firebase_json = os.getenv('FIREBASE_CRED_JSON')
firebase_project = os.getenv('FIREBASE_PROJECT_ID')

if firebase_json and firebase_project:
    try:
        import json
        from firebase_admin import credentials, firestore
        cred_dict = json.loads(firebase_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred, {
            'projectId': firebase_project
        })
        db = firestore.client()
        print("✅ Firebase initialized successfully")
        
        # Test a simple write
        test_ref = db.collection('test').document('connection_test')
        test_ref.set({'test': True, 'timestamp': firestore.SERVER_TIMESTAMP})
        print("✅ Firebase write test successful")
        
        # Clean up test
        test_ref.delete()
        print("✅ Firebase delete test successful")
        
    except Exception as e:
        print(f"❌ Firebase test failed: {e}")
else:
    print("❌ Firebase credentials not available for testing")

print("\n=== Debug Complete ===")