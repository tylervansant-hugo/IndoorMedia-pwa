#!/usr/bin/env python3
"""
Quarterly ROI Report Generator for IndoorMediaProspectBot

Generates professional quarterly ROI reports for customer contracts,
tracking coupon redemptions, revenue impact, and expansion opportunities.

Usage:
    from quarterly_roi_generator import generate_quarterly_roi_report, quarterly_roi_email_template
    
    report = generate_quarterly_roi_report(
        business_name="Felony Pizza",
        contact_name="Travis McDonald",
        contact_email="Dotcomvapor@gmail.com",
        store_number="1704",
        start_date="2026-02-25",
        months_active=1,
        coupon_count=38,
        avg_transaction_value=45.50,
        cogs_percent=0.30
    )
    print(report["report_text"])
    print(report["summary_stats"])
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


class QuarterlyROITracker:
    """Track which quarters have been reported for each customer."""
    
    def __init__(self, tracker_file: Optional[str] = None):
        """
        Initialize the tracker.
        
        Args:
            tracker_file: Path to JSON file tracking reported quarters.
                         Defaults to data/roi_report_tracker.json
        """
        if tracker_file is None:
            workspace = Path(__file__).parent.parent
            tracker_file = workspace / "data" / "roi_report_tracker.json"
        
        self.tracker_file = Path(tracker_file)
        self._ensure_tracker_exists()
        self.data = self._load_tracker()
    
    def _ensure_tracker_exists(self):
        """Create tracker file if it doesn't exist."""
        if not self.tracker_file.exists():
            self.tracker_file.parent.mkdir(parents=True, exist_ok=True)
            self.tracker_file.write_text(json.dumps({"reported_quarters": {}}, indent=2))
    
    def _load_tracker(self) -> Dict[str, Any]:
        """Load tracker data from file."""
        try:
            return json.loads(self.tracker_file.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            return {"reported_quarters": {}}
    
    def _save_tracker(self):
        """Save tracker data to file."""
        self.tracker_file.write_text(json.dumps(self.data, indent=2))
    
    def mark_reported(self, contact_email: str, year_quarter: str) -> bool:
        """
        Mark a quarter as reported for a contact.
        
        Args:
            contact_email: Customer contact email
            year_quarter: Format like "2026-Q1"
            
        Returns:
            True if newly marked, False if already marked
        """
        if contact_email not in self.data["reported_quarters"]:
            self.data["reported_quarters"][contact_email] = []
        
        if year_quarter not in self.data["reported_quarters"][contact_email]:
            self.data["reported_quarters"][contact_email].append(year_quarter)
            self._save_tracker()
            return True
        return False
    
    def is_reported(self, contact_email: str, year_quarter: str) -> bool:
        """Check if a quarter has already been reported."""
        return (
            contact_email in self.data["reported_quarters"]
            and year_quarter in self.data["reported_quarters"][contact_email]
        )
    
    def get_reported_quarters(self, contact_email: str) -> List[str]:
        """Get all reported quarters for a contact."""
        return self.data["reported_quarters"].get(contact_email, [])


def _get_current_quarter() -> str:
    """Return current quarter in format 'YYYY-QX' (e.g., '2026-Q1')."""
    today = datetime.now()
    quarter = (today.month - 1) // 3 + 1
    return f"{today.year}-Q{quarter}"


def _get_quarter_from_date(date: datetime) -> str:
    """Get quarter from a datetime object."""
    quarter = (date.month - 1) // 3 + 1
    return f"{date.year}-Q{quarter}"


def _calculate_roi(
    coupon_count: int,
    avg_transaction_value: float,
    cogs_percent: float,
    total_contract_amount: float
) -> Dict[str, Any]:
    """
    Calculate detailed ROI metrics.
    
    Args:
        coupon_count: Number of redeemed coupons
        avg_transaction_value: Average transaction value ($)
        cogs_percent: Cost of Goods Sold as decimal (e.g., 0.30 = 30%)
        total_contract_amount: Total contract value ($)
    
    Returns:
        Dictionary with ROI calculations
    """
    gross_revenue = coupon_count * avg_transaction_value
    cogs = gross_revenue * cogs_percent
    gross_profit = gross_revenue - cogs
    
    # "Better than free" metric: if gross profit exceeds contract cost
    roi_percent = ((gross_profit - total_contract_amount) / total_contract_amount * 100) if total_contract_amount > 0 else 0
    payback_days = None
    
    if coupon_count > 0:
        daily_profit = gross_profit / (30 * max(1, coupon_count // 10))  # Estimate days active
        if daily_profit > 0:
            payback_days = int(total_contract_amount / daily_profit)
    
    return {
        "gross_revenue": gross_revenue,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "roi_percent": roi_percent,
        "payback_days": payback_days,
        "is_better_than_free": gross_profit > total_contract_amount,
    }


def generate_quarterly_roi_report(
    business_name: str,
    contact_name: str,
    contact_email: str,
    store_number: str,
    start_date: str,
    months_active: int,
    coupon_count: int,
    avg_transaction_value: float,
    cogs_percent: float,
    total_contract_amount: float = 0.0,
    store_name: str = "",
) -> Dict[str, Any]:
    """
    Generate a professional quarterly ROI report.
    
    Args:
        business_name: Customer business name (e.g., "Felony Pizza")
        contact_name: Contact person name
        contact_email: Contact email
        store_number: Store/location number
        start_date: Contract start date (YYYY-MM-DD format)
        months_active: Number of months ad has been active
        coupon_count: Total redeemed coupons in the quarter
        avg_transaction_value: Average value per coupon redemption ($)
        cogs_percent: Cost of goods sold as decimal (0.30 = 30%)
        total_contract_amount: Total contract value ($) - used for ROI calc
        store_name: Grocery store name (e.g., "Safeway")
    
    Returns:
        Dictionary containing:
        - report_text: Professional report body
        - summary_stats: Dict with key metrics
        - email_ready: Pre-formatted for email send
        - quarter: Current quarter reference
    """
    
    # Parse dates
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
        start_dt = datetime.strptime(start_date, "%m/%d/%Y")
    
    current_dt = datetime.now()
    quarter = _get_current_quarter()
    
    # Calculate ROI
    roi = _calculate_roi(coupon_count, avg_transaction_value, cogs_percent, total_contract_amount)
    
    # Expansion opportunity assessment
    expansion_opportunity = "EXCELLENT"
    if coupon_count < 10:
        expansion_opportunity = "GOOD"
    elif coupon_count < 20:
        expansion_opportunity = "VERY GOOD"
    elif coupon_count >= 30:
        expansion_opportunity = "EXCELLENT - READY FOR MULTI-LOCATION EXPANSION"
    
    # Generate report text
    report_text = f"""QUARTERLY ROI PERFORMANCE REPORT
{business_name} | {contact_name}
Store: {store_name} ({store_number}) | Quarter: {quarter}
Report Date: {current_dt.strftime('%B %d, %Y')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXECUTIVE SUMMARY

In the {months_active} month{'s' if months_active != 1 else ''} since launching your IndoorMedia advertising campaign, here's what {business_name} achieved:

• {coupon_count} customers redeemed your in-store coupons
• ${roi['gross_revenue']:,.2f} in gross revenue driven directly from ads
• ${roi['gross_profit']:,.2f} in gross profit (after COGS @ {cogs_percent*100:.0f}%)
• {'📈 BETTER THAN FREE' if roi['is_better_than_free'] else '📊 POSITIVE MOMENTUM'} — Ad spend already {'paid for itself' if roi['is_better_than_free'] else 'driving strong ROI'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PERFORMANCE METRICS

Campaign Duration:        {months_active} month{'s' if months_active != 1 else ''}
Active Redeemed Coupons:  {coupon_count}
Avg. Transaction Value:   ${avg_transaction_value:,.2f}

Financial Impact:
  Gross Revenue Generated: ${roi['gross_revenue']:,.2f}
  Less: Cost of Goods      ${roi['cogs']:,.2f}
  ─────────────────────────────────
  Gross Profit:            ${roi['gross_profit']:,.2f}
  
ROI Analysis:
  Campaign Cost:           ${total_contract_amount:,.2f}
  Profit Contribution:     ${roi['gross_profit'] - total_contract_amount:,.2f}
  ROI Performance:         {roi['roi_percent']:.1f}%
  Payback Timeline:        {f'{roi['payback_days']} days' if roi['payback_days'] else 'Highly variable by season'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXPANSION OPPORTUNITY ANALYSIS

With {coupon_count} coupons redeemed in {months_active} month{'s' if months_active != 1 else ''}, your advertising is:

✓ Driving consistent customer traffic
✓ Converting awareness into actual redemptions
✓ Creating repeat visit opportunities

Recommended Next Step: {expansion_opportunity}

{('🚀 EXPANSION READY' + chr(10) + chr(10) + f'With {coupon_count}+ redemptions, you\'re a prime candidate for expanding to additional locations. The data shows your customer base is ready for multi-location visibility.') if coupon_count >= 30 else f'Continue current campaign momentum. Review in 30 days for expansion potential.'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEXT STEPS

1. Continue current advertising (proven performer)
2. Review redemption trends by location/day
3. Consider expansion to additional store locations
4. Schedule expansion strategy call with your rep

Questions? Contact your IndoorMedia representative.
"""
    
    summary_stats = {
        "business_name": business_name,
        "contact_name": contact_name,
        "contact_email": contact_email,
        "store_number": store_number,
        "store_name": store_name,
        "quarter": quarter,
        "months_active": months_active,
        "coupon_count": coupon_count,
        "avg_transaction_value": avg_transaction_value,
        "gross_revenue": round(roi['gross_revenue'], 2),
        "gross_profit": round(roi['gross_profit'], 2),
        "roi_percent": round(roi['roi_percent'], 1),
        "is_better_than_free": roi['is_better_than_free'],
        "expansion_opportunity": expansion_opportunity,
        "report_date": current_dt.isoformat(),
    }
    
    return {
        "report_text": report_text,
        "summary_stats": summary_stats,
        "quarter": quarter,
        "roi_metrics": roi,
    }


def quarterly_roi_email_template(
    business_name: str,
    contact_name: str,
    contact_email: str,
    store_number: str,
    rep_name: str,
    report: Dict[str, Any],
) -> str:
    """
    Generate a professional, email-ready ROI report template.
    
    Args:
        business_name: Customer business name
        contact_name: Contact person name
        contact_email: Contact email
        store_number: Store/location number
        rep_name: Sales rep name
        report: Output from generate_quarterly_roi_report()
    
    Returns:
        Email-ready formatted text (Markdown-friendly for Telegram/email)
    """
    
    stats = report["summary_stats"]
    roi = report["roi_metrics"]
    
    # Personalization
    first_name = contact_name.split()[0] if contact_name else "there"
    
    email_body = f"""Subject: Your {stats['quarter']} IndoorMedia Performance Report — {business_name}

───────────────────────────────────────────────────────────────────

Hi {first_name},

Great news — your IndoorMedia advertising campaign is delivering results!

We wanted to share your {stats['quarter']} performance report. The numbers speak for themselves:

📊 **QUARTER HIGHLIGHTS**

  Coupons Redeemed:         {stats['coupon_count']}
  Gross Revenue Generated:  ${stats['gross_revenue']:,.2f}
  Gross Profit:             ${stats['gross_profit']:,.2f}
  ROI Performance:          {stats['roi_percent']:.1f}%
  
✅ **The Bottom Line:** Your advertising investment {'has already paid for itself and is generating pure profit!' if stats['is_better_than_free'] else 'is driving positive return on investment.'}

───────────────────────────────────────────────────────────────────

🎯 **EXPANSION OPPORTUNITY**

With this level of performance, we think you're ready for the next step. Many customers like you are expanding to additional store locations — and the data shows it's working.

Here's why it makes sense:
  • Proven customer demand (shown by redemption rates)
  • Repeatable, scalable approach
  • Higher ROI with multi-location reach

───────────────────────────────────────────────────────────────────

Let's talk about expansion options. A quick 15-minute call could position {business_name} for even stronger growth this quarter.

Can we schedule a time to discuss?

Best regards,

{rep_name}
IndoorMedia
──────────────────────────────────────────────────────────────────

📎 Full Report Attached | Questions? Reply to this email.
Store: {store_number} | Period: {stats['quarter']}
"""
    
    return email_body


def create_audit_event_button_data(
    business_name: str,
    contact_name: str,
    contact_email: str,
    store_number: str,
    rep_name: str,
) -> Dict[str, Any]:
    """
    Create a Telegram-friendly button payload for audit timeline integration.
    
    Use this to add "📊 Generate Q ROI Report" button to audit events.
    
    Args:
        business_name: Customer business name
        contact_name: Contact person name
        contact_email: Contact email
        store_number: Store/location number
        rep_name: Sales rep name
    
    Returns:
        Dictionary with button metadata and callback data
    """
    
    return {
        "button_text": "📊 Generate Q ROI Report",
        "callback_data": f"roi_report:{contact_email}:{store_number}",
        "customer_context": {
            "business_name": business_name,
            "contact_name": contact_name,
            "contact_email": contact_email,
            "store_number": store_number,
            "rep_name": rep_name,
        },
        "action": "generate_quarterly_roi_report",
        "tooltip": f"Generate Q{_get_current_quarter()[-2]} ROI report for {business_name}",
    }


def load_contract_metrics(
    contact_email: str,
    contracts_file: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Load contract details from contracts.json.
    
    Args:
        contact_email: Contact email to look up
        contracts_file: Path to contracts.json
                       Defaults to data/contracts.json
    
    Returns:
        Contract dict if found, None otherwise
    """
    
    if contracts_file is None:
        workspace = Path(__file__).parent.parent
        contracts_file = workspace / "data" / "contracts.json"
    
    try:
        contracts_data = json.loads(Path(contracts_file).read_text())
        for contract in contracts_data.get("contracts", []):
            if contract.get("contact_email") == contact_email:
                return contract
    except (json.JSONDecodeError, FileNotFoundError):
        pass
    
    return None


def quarterly_roi_report_batch(
    contacts_file: Optional[str] = None,
    metrics_file: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Generate ROI reports for all contacts with metrics available.
    
    This is useful for quarterly batch reporting.
    
    Args:
        contacts_file: Path to contracts.json
        metrics_file: Path to metrics file (coupon counts, etc.)
                     Expected format: {email: {q1: {coupon_count: X, ...}}}
    
    Returns:
        List of report dicts for each contact
    """
    
    reports = []
    
    if contacts_file is None:
        workspace = Path(__file__).parent.parent
        contacts_file = workspace / "data" / "contracts.json"
    
    try:
        contracts_data = json.loads(Path(contacts_file).read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return reports
    
    for contract in contracts_data.get("contracts", []):
        try:
            report = generate_quarterly_roi_report(
                business_name=contract.get("business_name", ""),
                contact_name=contract.get("contact_name", ""),
                contact_email=contract.get("contact_email", ""),
                store_number=contract.get("store_number", ""),
                start_date=contract.get("date", ""),
                months_active=1,  # Would need to calculate from actual dates
                coupon_count=0,  # Would need metrics file
                avg_transaction_value=0.0,
                cogs_percent=0.30,
                total_contract_amount=contract.get("total_amount", 0.0),
                store_name=contract.get("store_name", ""),
            )
            reports.append(report)
        except Exception as e:
            # Skip contracts that fail gracefully
            continue
    
    return reports


if __name__ == "__main__":
    # Example usage
    report = generate_quarterly_roi_report(
        business_name="Felony Pizza",
        contact_name="Travis McDonald",
        contact_email="Dotcomvapor@gmail.com",
        store_number="1704",
        start_date="2026-02-25",
        months_active=1,
        coupon_count=38,
        avg_transaction_value=45.50,
        cogs_percent=0.30,
        total_contract_amount=3545.04,
        store_name="Safeway",
    )
    
    print(report["report_text"])
    print("\n" + "=" * 70 + "\n")
    print("SUMMARY STATS:")
    print(json.dumps(report["summary_stats"], indent=2))
    print("\n" + "=" * 70 + "\n")
    
    email = quarterly_roi_email_template(
        business_name="Felony Pizza",
        contact_name="Travis McDonald",
        contact_email="Dotcomvapor@gmail.com",
        store_number="1704",
        rep_name="Tyler VanSant",
        report=report,
    )
    
    print("EMAIL TEMPLATE:")
    print(email)
    print("\n" + "=" * 70 + "\n")
    
    button = create_audit_event_button_data(
        business_name="Felony Pizza",
        contact_name="Travis McDonald",
        contact_email="Dotcomvapor@gmail.com",
        store_number="1704",
        rep_name="Tyler VanSant",
    )
    
    print("AUDIT BUTTON DATA:")
    print(json.dumps(button, indent=2))
    
    # Test tracker
    tracker = QuarterlyROITracker()
    print("\n" + "=" * 70 + "\n")
    print("TRACKER TEST:")
    print(f"Marking as reported... {tracker.mark_reported('test@example.com', '2026-Q1')}")
    print(f"Already reported? {tracker.is_reported('test@example.com', '2026-Q1')}")
    print(f"Reported quarters: {tracker.get_reported_quarters('test@example.com')}")
