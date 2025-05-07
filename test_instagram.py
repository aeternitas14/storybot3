import logging
import sys
import asyncio
from instagram_monitor import InstagramMonitor
from playwright.async_api import async_playwright

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

async def test_instagram_login():
    """Test Instagram login functionality."""
    logger.info("Testing Instagram login...")
    monitor = InstagramMonitor()
    
    try:
        # Attempt to login
        success = await monitor.login_to_instagram()
        if success:
            logger.info("✅ Instagram login successful!")
        else:
            logger.error("❌ Instagram login failed!")
        
        # Clean up
        await monitor.cleanup_browser()
        return success
    except Exception as e:
        logger.error(f"❌ Error during login test: {e}")
        return False

async def test_story_checking(username: str):
    """Test story checking functionality."""
    logger.info(f"Testing story checking for @{username}...")
    monitor = InstagramMonitor()
    
    try:
        # First ensure we're logged in
        if not await monitor.login_to_instagram():
            logger.error("❌ Cannot check stories: Login failed")
            return False
        
        # Check stories
        await monitor.check_story(username)
        logger.info("✅ Story checking completed")
        
        # Clean up
        await monitor.cleanup_browser()
        return True
    except Exception as e:
        logger.error(f"❌ Error during story checking: {e}")
        return False

async def test_content_processing(username: str):
    """Test story content processing functionality."""
    logger.info(f"Testing story content processing for @{username}...")
    monitor = InstagramMonitor()
    
    try:
        # First ensure we're logged in
        if not await monitor.login_to_instagram():
            logger.error("❌ Cannot process content: Login failed")
            return False
        
        # Navigate to profile and open story
        await monitor.page.goto(f"https://www.instagram.com/{username}/")
        await monitor.page.wait_for_selector('header', timeout=10000)
        
        story_ring = await monitor.page.query_selector('div[role="button"] canvas')
        if story_ring:
            await story_ring.click()
            await monitor.page.wait_for_selector('div[role="dialog"]', timeout=5000)
            
            # Get story container
            story_element = await monitor.page.query_selector('div[role="dialog"]')
            if story_element:
                # Process content
                content = await monitor.get_story_content(story_element)
                if content:
                    logger.info("✅ Successfully processed story content:")
                    logger.info(f"  Type: {content['type']}")
                    logger.info(f"  Screenshot Hash: {content['screenshot_hash'][:8]}...")
                    if content.get('media_hash'):
                        logger.info(f"  Media Hash: {content['media_hash'][:8]}...")
                    return True
        
        logger.info("No stories available for content processing test")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during content processing test: {e}")
        return False
    finally:
        await monitor.cleanup_browser()

async def main():
    """Run all tests."""
    logger.info("Starting Instagram monitor tests...")
    
    # Test login
    login_success = await test_instagram_login()
    if not login_success:
        logger.error("❌ Login test failed, aborting further tests")
        return
    
    # Test story checking with a known account
    test_account = "instagram"  # Using Instagram's official account for testing
    story_success = await test_story_checking(test_account)
    
    # Test content processing
    content_success = await test_content_processing(test_account)
    
    if story_success and content_success:
        logger.info("✅ All tests passed successfully!")
    else:
        logger.error("❌ Some tests failed")

if __name__ == "__main__":
    asyncio.run(main()) 