#!/usr/bin/env python3
"""
Example script demonstrating the new multi-token functionality.

This script shows how to:
1. Submit a download request with multi-token support
2. List available files 
3. Mint additional tokens
4. Use the enhanced endpoints

Requirements:
- Railway yt-dlp service running locally
- requests library: pip install requests
"""

import json
import time
import requests

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = None  # Set this if your instance requires API key

def make_headers():
    """Create headers with optional API key."""
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    return headers

def submit_download_with_multi_tokens():
    """Submit a download request with multi-token support."""
    print("🎬 Submitting download with multi-token support...")
    
    payload = {
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll for testing
        "tag": "example_multi_token",
        "expected_name": "rick_roll.mp4",
        "quality": "BEST_MP4",
        "dest": "LOCAL",
        "separate_audio_video": True,  # Download separate audio/video
        "audio_format": "m4a",
        "token_count": 2,  # Create 2 tokens per artifact
        "custom_ttl": 7200  # 2 hours TTL
    }
    
    response = requests.post(f"{BASE_URL}/download", json=payload, headers=make_headers())
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Download submitted: {result['tag']}")
        return result['tag']
    else:
        print(f"❌ Download failed: {response.status_code} - {response.text}")
        return None

def check_job_status(tag):
    """Check the status of a download job."""
    print(f"🔍 Checking status for job: {tag}")
    
    response = requests.get(f"{BASE_URL}/status?tag={tag}", headers=make_headers())
    
    if response.status_code == 200:
        result = response.json()
        print(f"📊 Status: {result['status']}")
        return result['status']
    else:
        print(f"❌ Status check failed: {response.status_code}")
        return None

def get_job_result(tag):
    """Get the result of a completed job."""
    print(f"📥 Getting result for job: {tag}")
    
    response = requests.get(f"{BASE_URL}/result?tag={tag}", headers=make_headers())
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Job completed!")
        
        if "artifacts" in result:
            print("🎭 Multi-artifact result:")
            for artifact in result["artifacts"]:
                print(f"  📁 {artifact['type'].upper()}: {artifact['filename']}")
                print(f"     🔗 {len(artifact['urls'])} URLs available")
        else:
            print("📁 Single file result:")
            print(f"  🔗 {len(result.get('once_urls', [result.get('once_url', '')]))} URLs available")
        
        return result
    else:
        print(f"❌ Result fetch failed: {response.status_code}")
        return None

def list_available_files():
    """List files available for token minting."""
    print("📋 Listing available files...")
    
    response = requests.get(f"{BASE_URL}/files", headers=make_headers())
    
    if response.status_code == 200:
        result = response.json()
        print(f"📊 Found {result['total_files']} files:")
        
        for file_info in result['files']:
            print(f"  📄 {file_info['filename']} (ID: {file_info['file_id']})")
            print(f"     💾 Size: {file_info['size']} bytes")
            print(f"     🎫 Active tokens: {file_info['active_tokens']}")
            print(f"     📅 Created: {file_info['created_at']}")
        
        return result['files']
    else:
        print(f"❌ File listing failed: {response.status_code}")
        return []

def mint_additional_tokens(file_id, count=3):
    """Mint additional tokens for a file."""
    print(f"🎟️  Minting {count} additional tokens for file: {file_id}")
    
    payload = {
        "file_id": file_id,
        "count": count,
        "ttl_sec": 3600,  # 1 hour
        "tag": "example_minted_tokens"
    }
    
    response = requests.post(f"{BASE_URL}/mint", json=payload, headers=make_headers())
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Minted {result['tokens_created']} tokens!")
        print(f"⏰ Expires in: {result['expires_in_sec']} seconds")
        
        for i, url in enumerate(result['urls'], 1):
            print(f"  🎫 Token {i}: {BASE_URL}{url}")
        
        return result
    else:
        print(f"❌ Token minting failed: {response.status_code} - {response.text}")
        return None

def demonstrate_range_request(token_url):
    """Demonstrate range request support."""
    print(f"🔢 Testing range request on: {token_url}")
    
    # Request first 1KB
    headers = make_headers()
    headers["Range"] = "bytes=0-1023"
    
    response = requests.get(token_url, headers=headers)
    
    if response.status_code == 206:  # Partial Content
        print("✅ Range request successful!")
        print(f"📊 Content-Range: {response.headers.get('Content-Range')}")
        print(f"📦 Content-Length: {response.headers.get('Content-Length')}")
    else:
        print(f"❌ Range request failed: {response.status_code}")

def main():
    """Run the complete demonstration."""
    print("🚀 Multi-Token Railway yt-dlp Service Demo")
    print("=" * 50)
    
    # Check if service is running
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code != 200:
            print("❌ Service not responding correctly")
            return
        print("✅ Service is running")
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to service: {e}")
        print(f"Make sure the service is running at {BASE_URL}")
        return
    
    print("\n" + "=" * 50)
    
    # For demonstration, let's work with existing files instead of downloading
    # since we don't want to actually download videos in the demo
    
    # 1. List existing files
    files = list_available_files()
    
    if files:
        # Use the first available file
        file_info = files[0]
        file_id = file_info['file_id']
        
        print(f"\n📁 Working with file: {file_info['filename']}")
        
        # 2. Mint additional tokens
        mint_result = mint_additional_tokens(file_id, count=2)
        
        if mint_result:
            # 3. Demonstrate range request (on first minted token)
            token_url = f"{BASE_URL}{mint_result['urls'][0]}"
            demonstrate_range_request(token_url)
        
        # 4. List files again to see updated token count
        print("\n📋 Updated file listing:")
        list_available_files()
    
    else:
        print("\n💡 No files available for demonstration.")
        print("   You can submit a download job first:")
        print(f"   curl -X POST {BASE_URL}/download \\")
        print('     -H "Content-Type: application/json" \\')
        print('     -d \'{"url": "https://example.com/video", "tag": "demo"}\'')
    
    print("\n🎉 Demo completed!")
    print("\n📚 API Documentation available at:")
    print(f"   🌐 {BASE_URL}/docs")
    print(f"   📖 {BASE_URL}/redoc")

if __name__ == "__main__":
    main()