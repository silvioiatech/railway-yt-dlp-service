"""
Example usage of Channel Downloads API endpoints.

This script demonstrates how to use the channel info and download endpoints
with various filtering options.
"""
import asyncio
import httpx
from datetime import datetime, timedelta


# Configuration
API_BASE_URL = "http://localhost:8080/api/v1"
API_KEY = "your-api-key-here"  # Replace with actual API key


async def get_channel_info_example():
    """
    Example: Get channel information with filters.
    """
    print("=" * 60)
    print("Example 1: Get Channel Info with Filters")
    print("=" * 60)

    # Calculate date filter (videos from last 30 days)
    date_after = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

    params = {
        "url": "https://youtube.com/@example",
        "date_after": date_after,
        "min_duration": 300,  # At least 5 minutes
        "sort_by": "view_count",  # Most viewed first
        "page": 1,
        "page_size": 20
    }

    headers = {"X-API-Key": API_KEY}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{API_BASE_URL}/channel/info",
                params=params,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()

            data = response.json()

            print(f"\nChannel: {data['channel_name']}")
            print(f"Total videos: {data['video_count']}")
            print(f"Filtered videos: {data['filtered_video_count']}")
            print(f"Page: {data['page']}/{data['total_pages']}")
            print(f"\nFilters applied: {data['filters_applied']}")

            print("\nTop videos:")
            for idx, video in enumerate(data['videos'][:5], 1):
                print(f"  {idx}. {video['title']}")
                print(f"     Views: {video.get('view_count', 'N/A')}")
                print(f"     Duration: {video.get('duration', 'N/A')}s")
                print(f"     URL: {video['url']}")
                print()

        except httpx.HTTPError as e:
            print(f"Error: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")


async def download_channel_example():
    """
    Example: Download filtered channel videos.
    """
    print("=" * 60)
    print("Example 2: Download Top 10 Popular Videos")
    print("=" * 60)

    payload = {
        "url": "https://youtube.com/@example",
        "sort_by": "view_count",
        "max_downloads": 10,
        "min_duration": 300,  # At least 5 minutes
        "quality": "1080p",
        "download_subtitles": True,
        "subtitle_languages": ["en"],
        "path_template": "channels/{uploader}/{upload_date}-{title}.{ext}"
    }

    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/channel/download",
                json=payload,
                headers=headers,
                timeout=60.0
            )
            response.raise_for_status()

            data = response.json()

            print(f"\nBatch job created: {data['batch_id']}")
            print(f"Status: {data['status']}")
            print(f"Total jobs: {data['total_jobs']}")
            print(f"Queued jobs: {data['queued_jobs']}")

            print("\nVideos queued for download:")
            for idx, job in enumerate(data['jobs'][:5], 1):
                print(f"  {idx}. {job['title']}")
                print(f"     Job ID: {job['job_id']}")
                print(f"     Status: {job['status']}")
                print()

            print(f"\nTrack progress at: /api/v1/batch/{data['batch_id']}")

        except httpx.HTTPError as e:
            print(f"Error: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")


async def download_date_range_example():
    """
    Example: Download videos from specific date range.
    """
    print("=" * 60)
    print("Example 3: Download Videos from Date Range")
    print("=" * 60)

    # Videos from January 2025
    payload = {
        "url": "https://youtube.com/@example",
        "date_after": "20250101",
        "date_before": "20250131",
        "min_views": 10000,  # At least 10k views
        "sort_by": "upload_date",  # Newest first
        "quality": "best",
        "audio_only": False,
        "path_template": "channels/{uploader}/2025-01/{upload_date}-{title}.{ext}"
    }

    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/channel/download",
                json=payload,
                headers=headers,
                timeout=60.0
            )
            response.raise_for_status()

            data = response.json()

            print(f"\nBatch job created: {data['batch_id']}")
            print(f"Videos matching criteria: {data['total_jobs']}")

            if data['total_jobs'] == 0:
                print("No videos match the specified filters!")
            else:
                print(f"\nDownload started for {data['total_jobs']} videos")
                print(f"Track progress: /api/v1/batch/{data['batch_id']}")

        except httpx.HTTPError as e:
            print(f"Error: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")


async def pagination_example():
    """
    Example: Paginate through large channel results.
    """
    print("=" * 60)
    print("Example 4: Paginate Through Channel Videos")
    print("=" * 60)

    headers = {"X-API-Key": API_KEY}

    async with httpx.AsyncClient() as client:
        page = 1
        total_pages = 1

        while page <= total_pages and page <= 3:  # Limit to 3 pages for demo
            print(f"\nFetching page {page}...")

            params = {
                "url": "https://youtube.com/@example",
                "min_duration": 600,  # 10+ minutes
                "sort_by": "upload_date",
                "page": page,
                "page_size": 10
            }

            try:
                response = await client.get(
                    f"{API_BASE_URL}/channel/info",
                    params=params,
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()

                data = response.json()
                total_pages = data['total_pages']

                print(f"Page {data['page']}/{data['total_pages']}")
                print(f"Videos on this page: {len(data['videos'])}")

                for video in data['videos']:
                    print(f"  - {video['title']}")

                if data['has_next']:
                    page += 1
                else:
                    break

            except httpx.HTTPError as e:
                print(f"Error: {e}")
                break


async def main():
    """
    Run all examples.
    """
    print("\n" + "=" * 60)
    print("Channel Downloads API Examples")
    print("=" * 60 + "\n")

    # Run examples
    await get_channel_info_example()
    print("\n")

    await download_channel_example()
    print("\n")

    await download_date_range_example()
    print("\n")

    await pagination_example()
    print("\n")

    print("=" * 60)
    print("Examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    # Note: Update API_BASE_URL and API_KEY before running
    print("\nNote: Update API_BASE_URL and API_KEY in this file before running")
    print("Current API_BASE_URL:", API_BASE_URL)
    print()

    # Uncomment to run:
    # asyncio.run(main())
