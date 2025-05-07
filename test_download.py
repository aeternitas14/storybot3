import asyncio
import logging
import os
from instagram_monitor import InstagramMonitor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_download_story(username: str):
    """Test downloading a story from a specific username."""
    logger.info(f"Testing story download for @{username}...")
    monitor = InstagramMonitor()
    
    try:
        # Login to Instagram
        if not await monitor.login_to_instagram():
            logger.error("❌ Failed to login to Instagram")
            return False
            
        # Navigate to profile
        logger.info(f"Navigating to @{username}'s profile...")
        await monitor.page.goto(f"https://www.instagram.com/{username}/")
        await monitor.page.wait_for_selector('header', timeout=10000)
        
        # Check for story ring
        logger.info("Looking for story ring...")
        story_ring = await monitor.page.query_selector('div[role="button"] canvas')
        if not story_ring:
            logger.info(f"😴 No active stories found for @{username}")
            return False
            
        # Click story ring and wait for story viewer
        logger.info("Clicking story ring...")
        await story_ring.click()
        
        # Wait for story viewer with more specific selectors
        logger.info("Waiting for story viewer...")
        try:
            # Try multiple selectors that could indicate story viewer is ready
            selectors = [
                'div[role="dialog"] img[decoding="auto"]',  # Image story
                'div[role="dialog"] video source',  # Video story
                'div[role="dialog"] video',  # Video element
                'div[role="dialog"] article'  # General story container
            ]
            
            for selector in selectors:
                try:
                    logger.info(f"Trying selector: {selector}")
                    element = await monitor.page.wait_for_selector(selector, timeout=5000)
                    if element:
                        logger.info(f"Found story element with selector: {selector}")
                        break
                except Exception as e:
                    logger.warning(f"Selector {selector} not found: {e}")
            else:
                raise TimeoutError("No story selectors found")
            
            # Take a screenshot of the current state
            await monitor.page.screenshot(path=f"debug_{username}_found.png")
            
            # Get story container
            logger.info("Getting story container...")
            story_element = await monitor.page.query_selector('div[role="dialog"]')
            if not story_element:
                logger.error(f"❌ Could not find story container for @{username}")
                return False
                
            # Process story content
            logger.info("Processing story content...")
            story_content = await monitor.get_story_content(story_element)
            if not story_content:
                logger.error(f"❌ Could not download story content for @{username}")
                return False
                
            # Log success
            logger.info(f"✅ Successfully downloaded story from @{username}")
            logger.info(f"  Type: {story_content['type']}")
            logger.info(f"  Screenshot Hash: {story_content['screenshot_hash'][:8]}...")
            if story_content.get('media_hash'):
                logger.info(f"  Media Hash: {story_content['media_hash'][:8]}...")
                
            # Save content to test directory
            test_dir = "test_downloads"
            os.makedirs(test_dir, exist_ok=True)
            
            # Save screenshot
            screenshot_path = os.path.join(test_dir, f"{username}_screenshot.png")
            with open(screenshot_path, "wb") as f:
                f.write(story_content['screenshot'])
            logger.info(f"  Saved screenshot to {screenshot_path}")
            
            # Save media content
            if story_content['type'] == 'video':
                media_path = os.path.join(test_dir, f"{username}_video.mp4")
            else:
                media_path = os.path.join(test_dir, f"{username}_image.jpg")
                
            with open(media_path, "wb") as f:
                f.write(story_content['media_content'])
            logger.info(f"  Saved media to {media_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error waiting for story viewer: {e}")
            # Take a screenshot for debugging
            await monitor.page.screenshot(path=f"debug_{username}_error.png")
            logger.info(f"Saved debug screenshot to debug_{username}_error.png")
            # Log page content for debugging
            content = await monitor.page.content()
            with open(f"debug_{username}_content.html", "w") as f:
                f.write(content)
            logger.info(f"Saved page content to debug_{username}_content.html")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error downloading story: {e}")
        # Take a screenshot for debugging
        try:
            await monitor.page.screenshot(path=f"debug_{username}_error.png")
            logger.info(f"Saved debug screenshot to debug_{username}_error.png")
        except:
            pass
        return False
    finally:
        await monitor.cleanup_browser()

async def main():
    """Run the download test."""
    # Test with a known account that usually has stories
    test_accounts = ["instagram", "kimkardashian", "cristiano"]
    
    for account in test_accounts:
        logger.info(f"\n🔍 Testing with @{account}...")
        success = await test_download_story(account)
        if success:
            logger.info(f"✅ Test passed for @{account}")
        else:
            logger.info(f"❌ Test failed for @{account}")
        await asyncio.sleep(2)  # Small delay between tests

if __name__ == "__main__":
    asyncio.run(main()) 