#!/usr/bin/env python3
"""
b2bappointments.net Web Automation
Handles contact creation, updates, and status tracking in City/Store Number folder structure.
Uses Playwright for reliable web automation.
"""

import os
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from dotenv import load_dotenv

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright")
    exit(1)

# Load environment variables
load_dotenv(".env.local")
B2B_USERNAME = os.getenv("B2B_USERNAME")
B2B_PASSWORD = os.getenv("B2B_PASSWORD")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/b2b_automation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Cache file for session persistence
CACHE_FILE = "data/b2b_session_cache.json"

class B2BAutomation:
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.session_cache = self._load_cache()

    def _load_cache(self) -> Dict:
        """Load persistent session cache."""
        if Path(CACHE_FILE).exists():
            try:
                with open(CACHE_FILE, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_cache(self):
        """Save session cache to disk."""
        Path("data").mkdir(exist_ok=True)
        with open(CACHE_FILE, "w") as f:
            json.dump(self.session_cache, f, indent=2)

    async def launch_browser(self):
        """Launch Playwright browser."""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()
            logger.info("Browser launched successfully")
        except Exception as e:
            logger.error(f"Failed to launch browser: {e}")
            raise

    async def close_browser(self):
        """Close Playwright browser."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        logger.info("Browser closed")

    async def login(self) -> bool:
        """Login to b2bappointments.net"""
        if not self.page:
            await self.launch_browser()

        try:
            logger.info("Navigating to b2bappointments.net login...")
            await self.page.goto("https://www.b2bappointments.net/login")
            
            # Wait for login form
            await self.page.wait_for_selector("input[type='email']", timeout=10000)
            
            # Enter credentials
            await self.page.fill("input[type='email']", B2B_USERNAME)
            await self.page.fill("input[type='password']", B2B_PASSWORD)
            
            # Click login button
            await self.page.click("button[type='submit']")
            
            # Wait for navigation to dashboard
            await self.page.wait_for_url("**/dashboard", timeout=15000)
            logger.info("Login successful")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    async def ensure_folder_exists(self, city: str, store_number: str) -> bool:
        """
        Ensure the City/Store Number folder exists in Leads section.
        Creates folder if it doesn't exist.
        """
        folder_path = f"{city}/{store_number}"
        
        try:
            logger.info(f"Checking folder: {folder_path}")
            
            # Navigate to leads section
            await self.page.goto("https://www.b2bappointments.net/leads/folders")
            await self.page.wait_for_load_state("networkidle")
            
            # Check if folder exists
            folder_selector = f"text={folder_path}"
            try:
                await self.page.locator(folder_selector).first.wait_for(timeout=2000)
                logger.info(f"Folder exists: {folder_path}")
                return True
            except:
                pass
            
            # Create folder if it doesn't exist
            logger.info(f"Creating folder: {folder_path}")
            await self.page.click("button:has-text('New Folder')")
            await self.page.wait_for_selector("input[placeholder*='Folder']")
            await self.page.fill("input[placeholder*='Folder']", folder_path)
            await self.page.click("button:has-text('Create')")
            
            await self.page.wait_for_load_state("networkidle")
            logger.info(f"Folder created: {folder_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error ensuring folder {folder_path}: {e}")
            return False

    async def create_contact(
        self,
        city: str,
        store_number: str,
        business_name: str,
        phone: str,
        email: str,
        likelihood_score: int = 50,
        category: str = "Prospect"
    ) -> bool:
        """
        Create a new contact in b2bappointments within City/Store Number folder.
        """
        try:
            if not self.page:
                await self.launch_browser()
            
            # Ensure logged in
            try:
                await self.page.goto("https://www.b2bappointments.net/dashboard")
                await self.page.wait_for_load_state("networkidle", timeout=5000)
            except:
                if not await self.login():
                    return False
            
            # Ensure folder exists
            if not await self.ensure_folder_exists(city, store_number):
                logger.error(f"Failed to ensure folder for {city}/{store_number}")
                return False
            
            # Check if contact already exists
            if await self.contact_exists(city, store_number, business_name):
                logger.info(f"Contact already exists: {business_name}")
                return True
            
            # Navigate to add contact in folder
            folder_path = f"{city}/{store_number}"
            logger.info(f"Adding contact to folder: {folder_path}")
            
            await self.page.goto(f"https://www.b2bappointments.net/leads/folders")
            await self.page.wait_for_load_state("networkidle")
            
            # Click on folder
            await self.page.click(f"text={folder_path}")
            await self.page.wait_for_load_state("networkidle")
            
            # Click Add Contact button
            await self.page.click("button:has-text('Add Contact')")
            
            # Fill contact form
            await self.page.fill("input[name='business_name']", business_name)
            await self.page.fill("input[name='phone']", phone)
            await self.page.fill("input[name='email']", email)
            
            # Add notes with score and category
            notes = f"Likelihood: {likelihood_score}/100 | Category: {category} | Added: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            await self.page.fill("textarea[name='notes']", notes)
            
            # Save contact
            await self.page.click("button:has-text('Save')")
            await self.page.wait_for_load_state("networkidle")
            
            logger.info(f"Contact created: {business_name} in {folder_path}")
            
            # Update cache
            cache_key = f"{city}/{store_number}/{business_name}"
            self.session_cache[cache_key] = {
                "created": datetime.now().isoformat(),
                "phone": phone,
                "email": email,
                "score": likelihood_score,
                "status": "New"
            }
            self._save_cache()
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating contact {business_name}: {e}")
            return False

    async def contact_exists(
        self,
        city: str,
        store_number: str,
        business_name: str
    ) -> bool:
        """Check if contact already exists in folder."""
        cache_key = f"{city}/{store_number}/{business_name}"
        
        # Quick cache check
        if cache_key in self.session_cache:
            return True
        
        try:
            folder_path = f"{city}/{store_number}"
            await self.page.goto("https://www.b2bappointments.net/leads/folders")
            await self.page.wait_for_load_state("networkidle")
            
            # Navigate to folder
            await self.page.click(f"text={folder_path}")
            await self.page.wait_for_load_state("networkidle")
            
            # Check for contact
            contact_selector = f"text={business_name}"
            try:
                await self.page.locator(contact_selector).first.wait_for(timeout=2000)
                return True
            except:
                return False
                
        except Exception as e:
            logger.warning(f"Error checking contact existence: {e}")
            return False

    async def update_contact_status(
        self,
        city: str,
        store_number: str,
        business_name: str,
        status: str
    ) -> bool:
        """
        Update contact status (Contacted, Interested, Appointment Booked, etc.)
        """
        try:
            if not self.page:
                await self.launch_browser()
            
            # Ensure logged in
            try:
                await self.page.goto("https://www.b2bappointments.net/dashboard")
                await self.page.wait_for_load_state("networkidle", timeout=5000)
            except:
                if not await self.login():
                    return False
            
            folder_path = f"{city}/{store_number}"
            logger.info(f"Updating contact status: {business_name} -> {status}")
            
            # Navigate to folder
            await self.page.goto("https://www.b2bappointments.net/leads/folders")
            await self.page.wait_for_load_state("networkidle")
            
            await self.page.click(f"text={folder_path}")
            await self.page.wait_for_load_state("networkidle")
            
            # Click on contact
            await self.page.click(f"text={business_name}")
            await self.page.wait_for_load_state("networkidle")
            
            # Update status field
            await self.page.select_option("select[name='status']", status)
            
            # Save
            await self.page.click("button:has-text('Save')")
            await self.page.wait_for_load_state("networkidle")
            
            # Update cache
            cache_key = f"{city}/{store_number}/{business_name}"
            if cache_key in self.session_cache:
                self.session_cache[cache_key]["status"] = status
                self._save_cache()
            
            logger.info(f"Contact status updated: {business_name} -> {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating contact status: {e}")
            return False


async def main():
    """CLI interface for testing."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python b2bappointments_automation.py [command] [args]")
        print("Commands:")
        print("  create <city> <store_num> <business> <phone> <email> [score] [category]")
        print("  exists <city> <store_num> <business>")
        print("  update <city> <store_num> <business> <status>")
        return
    
    automation = B2BAutomation()
    await automation.launch_browser()
    
    try:
        if sys.argv[1] == "create":
            city, store_num, business, phone, email = sys.argv[2:7]
            score = int(sys.argv[7]) if len(sys.argv) > 7 else 50
            category = sys.argv[8] if len(sys.argv) > 8 else "Prospect"
            await automation.create_contact(city, store_num, business, phone, email, score, category)
        
        elif sys.argv[1] == "exists":
            city, store_num, business = sys.argv[2:5]
            exists = await automation.contact_exists(city, store_num, business)
            print(f"Exists: {exists}")
        
        elif sys.argv[1] == "update":
            city, store_num, business, status = sys.argv[2:6]
            await automation.update_contact_status(city, store_num, business, status)
    
    finally:
        await automation.close_browser()


if __name__ == "__main__":
    asyncio.run(main())
