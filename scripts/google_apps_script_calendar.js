/**
 * Google Apps Script — Deploy as Web App
 * Serves calendar events as JSON for the PWA
 * 
 * SETUP:
 * 1. Go to https://script.google.com
 * 2. Create new project, paste this code
 * 3. Deploy → New deployment → Web app
 *    - Execute as: Me
 *    - Who has access: Anyone
 * 4. Copy the deployment URL
 * 5. Paste it into the PWA as CALENDAR_API_URL
 */

function doGet(e) {
  try {
    const daysAhead = parseInt(e?.parameter?.days) || 30;
    const now = new Date();
    const end = new Date(now.getTime() + daysAhead * 24 * 60 * 60 * 1000);
    
    const calendar = CalendarApp.getDefaultCalendar();
    const events = calendar.getEvents(now, end);
    
    const result = events.map(event => ({
      event_id: event.getId(),
      title: event.getTitle(),
      start: event.getStartTime().toISOString(),
      end: event.getEndTime().toISOString(),
      location: event.getLocation() || '',
      description: event.getDescription() || '',
      attendees: event.getGuestList().map(g => ({
        email: g.getEmail(),
        name: g.getName(),
        status: g.getGuestStatus().toString()
      })),
      creator: event.getCreators().join(', '),
      is_prospect_visit: /visit|indoor|prospect|meeting/i.test(event.getTitle())
    }));
    
    return ContentService
      .createTextOutput(JSON.stringify(result))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ error: err.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
