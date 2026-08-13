/**
 * Google Apps Script — Deploy as Web App
 * Serves calendar events as JSON for the PWA (Option B: multi-rep, no logins)
 *
 * HOW IT WORKS (zero-login syncing):
 *   Each rep shares their personal Google Calendar with the account that owns
 *   this script (View access is enough). They never hand over a password —
 *   just Calendar → Settings → their calendar → "Share with specific people"
 *   → add THIS account's email → "See all event details".
 *
 *   This script reads EVERY calendar shared with it via getAllCalendars(),
 *   so new reps flow in automatically once they share.
 *
 * ZONE FILTERING (7X / 7Y / 7Z only):
 *   Every event is tagged with a zone parsed from the store-number pattern
 *   (e.g. "FME07Z-0236" → "07Z") found in the title/location/description.
 *   Pass ?zones=7X,7Y,7Z to only return events in your team's zones.
 *   Events with no detectable zone are included by default (set
 *   ?strictZone=1 to drop them too).
 *
 * SETUP:
 * 1. Go to https://script.google.com
 * 2. Create new project, paste this code
 * 3. Deploy → New deployment → Web app
 *    - Execute as: Me
 *    - Who has access: Anyone
 * 4. Copy the deployment URL
 * 5. Paste it into the PWA as CALENDAR_API_URL
 * 6. Have each rep share their calendar with this script's owner account.
 */

// Zones your team occupies. Requests can override with ?zones=7X,7Y,7Z
var DEFAULT_ZONES = ['7X', '7Y', '7Z'];

function doGet(e) {
  try {
    var daysAhead = parseInt(e && e.parameter && e.parameter.days) || 30;
    var now = new Date();
    var end = new Date(now.getTime() + daysAhead * 24 * 60 * 60 * 1000);

    // Which zones to keep. Normalize to uppercase 2-char zone codes (7X etc.)
    var zoneParam = (e && e.parameter && e.parameter.zones) || DEFAULT_ZONES.join(',');
    var wantZones = zoneParam.split(',')
      .map(function (z) { return z.trim().toUpperCase(); })
      .filter(function (z) { return z; });
    var strictZone = !!(e && e.parameter && e.parameter.strictZone);

    // Read EVERY calendar shared with this account (Option B: multi-rep).
    var calendars = CalendarApp.getAllCalendars();

    var result = [];
    var seen = {}; // de-dupe shared events that appear on multiple calendars

    calendars.forEach(function (calendar) {
      var calName = '';
      try { calName = calendar.getName() || ''; } catch (e2) { calName = ''; }

      var events;
      try {
        events = calendar.getEvents(now, end);
      } catch (e3) {
        return; // skip calendars we can't read
      }

      events.forEach(function (event) {
        var title = event.getTitle() || '';
        var location = '';
        var description = '';
        try { location = event.getLocation() || ''; } catch (e4) {}
        try { description = event.getDescription() || ''; } catch (e5) {}

        var zone = detectZone(title + ' ' + location + ' ' + description);

        // Zone filter: keep if zone is in wantZones, or (no zone AND not strict)
        if (zone) {
          if (wantZones.indexOf(zone) === -1) return;
        } else if (strictZone) {
          return;
        }

        var startISO = event.getStartTime().toISOString();
        var dedupeKey = title + '|' + startISO;
        if (seen[dedupeKey]) return;
        seen[dedupeKey] = true;

        var attendees = [];
        try {
          attendees = event.getGuestList().map(function (g) {
            return {
              email: g.getEmail(),
              name: g.getName(),
              status: g.getGuestStatus().toString()
            };
          });
        } catch (e6) {}

        var creators = '';
        try { creators = event.getCreators().join(', '); } catch (e7) {}

        result.push({
          event_id: event.getId(),
          title: title,
          start: startISO,
          end: event.getEndTime().toISOString(),
          location: location,
          description: description,
          zone: zone || '',
          calendar: calName,
          rep: calName, // owning calendar name is the rep's name in Option B
          attendees: attendees,
          creator: creators,
          is_prospect_visit: /visit|indoor|prospect|meeting/i.test(title)
        });
      });
    });

    return ContentService
      .createTextOutput(JSON.stringify(result))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ error: err.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Extract a zone code from free text using the store-number pattern.
 * Matches the PWA's getZoneByStoreNumber convention: two digits + a letter,
 * e.g. "FME07Z-0236" → "07Z", then normalized to "7Z".
 * Falls back to a bare "7X/7Y/7Z" mention if present.
 */
function detectZone(text) {
  if (!text) return null;
  var up = text.toUpperCase();

  // Store-number style: ##[A-Z] (07Z, 07X, 07Y, ...)
  var m = up.match(/\b\d{2}[A-Z]\b/);
  if (m) return normalizeZone(m[0]);

  // Bare zone mention: "7X", "Zone 7Z", "7 Z"
  var m2 = up.match(/\b0?7\s?([XYZ])\b/);
  if (m2) return '7' + m2[1];

  return null;
}

// "07Z" → "7Z"; leave already-short codes alone.
function normalizeZone(code) {
  var c = code.toUpperCase();
  if (/^0\d[A-Z]$/.test(c)) return c.slice(1); // 07Z -> 7Z
  return c;
}
