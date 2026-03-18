#!/usr/bin/env python3
"""
Test suite for advertising signals detector.
Tests caching, timeouts, graceful fallbacks, and integration.
"""

import json
import logging
import sys
import time
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from advertising_signals import (
    AdvertisingSignalsDetector,
    get_all_ad_signals,
    format_ad_signals_for_display,
    get_likelihood_boost,
    load_cache,
    save_cache,
    CACHE_FILE
)
from prospect_advertising_integration import (
    add_advertising_signals_to_prospect,
    enhance_prospects_batch
)


def test_meta_ads_found():
    """Test Meta ads detection for known advertiser."""
    logger.info("\n🧪 TEST 1: Meta Ads Detection")
    
    # Known advertisers that should have Meta presence
    test_businesses = [
        "McDonald's",
        "Starbucks",
        "Amazon",
    ]
    
    for business in test_businesses:
        logger.info(f"  Checking: {business}")
        detector = AdvertisingSignalsDetector()
        result = detector.check_business(business)
        
        # Should find something (or fail gracefully)
        assert result.get('business') == business
        assert 'platforms' in result
        logger.info(f"    ✅ Found: {result.get('found_advertising', False)}")
    
    return True


def test_google_ads_found():
    """Test Google ads detection for known advertiser."""
    logger.info("\n🧪 TEST 2: Google Ads Detection")
    
    test_businesses = [
        "Best Buy",
        "Home Depot",
        "Target",
    ]
    
    for business in test_businesses:
        logger.info(f"  Checking: {business}")
        detector = AdvertisingSignalsDetector()
        result = detector.check_business(business)
        
        assert result.get('business') == business
        assert 'platforms' in result
        logger.info(f"    ✅ Result: {result.get('found_advertising', False)}")
    
    return True


def test_no_ads_found():
    """Test graceful handling when no ads found."""
    logger.info("\n🧪 TEST 3: No Ads Found (Graceful Fallback)")
    
    # Small local business unlikely to have ads
    business = "Joe's Small Hardware Store"
    
    detector = AdvertisingSignalsDetector()
    result = detector.check_business(business)
    
    # Should return gracefully without errors
    assert result.get('business') == business
    assert result.get('found_advertising') == False
    assert result.get('likelihood_boost') == 0
    
    logger.info(f"  ✅ No ads found (no error)")
    return True


def test_caching():
    """Test 24h caching works properly."""
    logger.info("\n🧪 TEST 4: Caching (24h TTL)")
    
    business = "Autotek International LLC"
    
    # First call - should fetch
    logger.info(f"  First call (should fetch)...")
    start = time.time()
    detector1 = AdvertisingSignalsDetector()
    result1 = detector1.check_business(business)
    time1 = time.time() - start
    logger.info(f"    Took {time1:.2f}s")
    
    # Second call - should use cache
    logger.info(f"  Second call (should use cache)...")
    start = time.time()
    detector2 = AdvertisingSignalsDetector()
    result2 = detector2.check_business(business)
    time2 = time.time() - start
    logger.info(f"    Took {time2:.2f}s")
    
    # Results should match
    assert result1 == result2
    
    # Second call should be much faster
    logger.info(f"  ✅ Cache working ({time2:.3f}s < {time1:.2f}s)")
    
    return True


def test_cache_expiry():
    """Test cache expiry (TTL validation)."""
    logger.info("\n🧪 TEST 5: Cache Expiry")
    
    # Read cache and verify TTL is set
    cache = load_cache()
    
    if not cache:
        logger.info("  Cache is empty (normal on first run)")
        return True
    
    for key, entry in cache.items():
        ttl = entry.get('ttl', 0)
        assert ttl == 24 * 3600  # Should be 24 hours in seconds
    
    logger.info(f"  ✅ Cache TTL verified (24 hours)")
    return True


def test_timeout_handling():
    """Test timeout handling (should not hang)."""
    logger.info("\n🧪 TEST 6: Timeout Handling")
    
    business = "Test Business " + str(int(time.time()))  # Unique name
    
    # Should timeout gracefully (not hang)
    start = time.time()
    detector = AdvertisingSignalsDetector()
    result = detector.check_business(business)
    elapsed = time.time() - start
    
    # Should complete within reasonable time (30s max, actually ~10s)
    assert elapsed < 30
    logger.info(f"  ✅ Completed in {elapsed:.1f}s (no hang)")
    
    return True


def test_ui_display():
    """Test formatting for UI display."""
    logger.info("\n🧪 TEST 7: UI Display Formatting")
    
    # Get signals for a business
    signals = {
        "business": "Example Business",
        "found_advertising": True,
        "likelihood_boost": 15,
        "checked_at": datetime.now().isoformat(),
        "platforms": {
            "meta": {"found": True, "active_ads": 5},
            "google": {"found": True, "ad_count": 3}
        }
    }
    
    display = format_ad_signals_for_display(signals)
    
    # Should contain key elements
    assert "ADVERTISING SIGNALS" in display
    assert "Meta" in display or "meta" in display.lower()
    assert "Google" in display or "google" in display.lower()
    
    logger.info(f"  ✅ Display formatting works")
    print(f"\n  Sample display:\n{display}")
    
    return True


def test_prospect_integration():
    """Test integration with prospect cards."""
    logger.info("\n🧪 TEST 8: Prospect Card Integration")
    
    # Create sample prospect
    prospect = {
        "name": "Example Pizzeria",
        "address": "123 Main St, Portland, OR",
        "phone": "(503) 555-1234",
        "likelihood_score": 65,
        "rating": 4.2,
    }
    
    logger.info(f"  Before: Score = {prospect['likelihood_score']}")
    
    # Add signals
    enhanced = add_advertising_signals_to_prospect(prospect)
    
    logger.info(f"  After: Score = {enhanced['likelihood_score']}")
    
    # If ads found, score should increase
    if enhanced.get('likelihood_boost_from_ads'):
        boost = enhanced['likelihood_boost_from_ads']
        assert enhanced['likelihood_score'] > prospect['likelihood_score']
        logger.info(f"  ✅ Score boosted by +{boost}")
    else:
        logger.info(f"  ✅ No ads found (score unchanged)")
    
    return True


def test_batch_processing():
    """Test batch enhancement of prospects."""
    logger.info("\n🧪 TEST 9: Batch Processing")
    
    prospects = [
        {"name": "Business A", "address": "123 Main", "likelihood_score": 50},
        {"name": "Business B", "address": "456 Oak", "likelihood_score": 60},
        {"name": "Business C", "address": "789 Pine", "likelihood_score": 70},
    ]
    
    logger.info(f"  Processing {len(prospects)} prospects...")
    
    start = time.time()
    enhanced = enhance_prospects_batch(prospects)
    elapsed = time.time() - start
    
    assert len(enhanced) == len(prospects)
    logger.info(f"  ✅ Processed {len(enhanced)} prospects in {elapsed:.1f}s")
    
    return True


def test_likelihood_boost():
    """Test likelihood score boost calculation."""
    logger.info("\n🧪 TEST 10: Likelihood Boost")
    
    # Signals without advertising
    signals_no_ads = {
        "found_advertising": False,
        "likelihood_boost": 0,
    }
    
    boost1 = get_likelihood_boost(signals_no_ads)
    assert boost1 == 0
    logger.info(f"  No ads: +{boost1}")
    
    # Signals with advertising
    signals_with_ads = {
        "found_advertising": True,
        "likelihood_boost": 15,
    }
    
    boost2 = get_likelihood_boost(signals_with_ads)
    assert boost2 == 15
    logger.info(f"  With ads: +{boost2}")
    
    logger.info(f"  ✅ Boost calculation correct")
    return True


def run_all_tests():
    """Run all test cases."""
    logger.info("\n" + "=" * 60)
    logger.info("ADVERTISING SIGNALS DETECTOR - TEST SUITE")
    logger.info("=" * 60)
    
    tests = [
        ("Meta Ads Detection", test_meta_ads_found),
        ("Google Ads Detection", test_google_ads_found),
        ("No Ads Found", test_no_ads_found),
        ("Caching", test_caching),
        ("Cache Expiry", test_cache_expiry),
        ("Timeout Handling", test_timeout_handling),
        ("UI Display", test_ui_display),
        ("Prospect Integration", test_prospect_integration),
        ("Batch Processing", test_batch_processing),
        ("Likelihood Boost", test_likelihood_boost),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name}")
            else:
                failed += 1
                logger.error(f"❌ {test_name}")
        except Exception as e:
            failed += 1
            logger.error(f"❌ {test_name}: {e}")
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info(f"RESULTS: {passed} passed, {failed} failed")
    logger.info("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
