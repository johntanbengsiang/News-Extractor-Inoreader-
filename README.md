# AP-HA Bulletin RSS Feed

Self-hosted RSS feed for just the "Newsletter" (AP Hospitality Bulletin Asia
Pacific) posts from https://www.ap-ha.com/news-publications — no Publications,
Articles, or Announcements included.

## Setup

1. **Create a new GitHub repo** (public is simplest — GitHub Pages on the free
   tier requires public repos unless you're on a paid plan). Call it whatever
   you like, e.g. `ap-ha-rss-feed`.

2. **Push these files** to the repo root, keeping the folder structure:
   ```
   scraper.py
   requirements.txt
   .github/workflows/update-feed.yml
   README.md
   ```

3. **Update the self-link in `scraper.py`.** Change:
   ```python
   FEED_SELF_URL = "https://REPLACE_ME.github.io/ap-ha-rss-feed/feed.xml"
   ```
   to your actual GitHub username and repo name.

4. **Run it once manually** to generate the first `feed.xml`:
   - Go to the repo's **Actions** tab
   - Select "Update AP-HA Bulletin RSS Feed"
   - Click **Run workflow** (this uses the `workflow_dispatch` trigger)
   - This commits `feed.xml` to the repo

5. **Enable GitHub Pages:**
   - Repo **Settings → Pages**
   - Source: **Deploy from a branch**
   - Branch: `main`, folder: `/ (root)`
   - Save. GitHub will give you a URL like
     `https://yourusername.github.io/ap-ha-rss-feed/`

6. **Your feed URL** will be:
   ```
   https://yourusername.github.io/ap-ha-rss-feed/feed.xml
   ```
   Add that to any RSS reader (or your Dispatch app's feed list).

## How it works

- `scraper.py` fetches the news page, walks the HTML in document order, and
  tracks the most recent category label + month/day text it has seen. When it
  hits a `/post/...` link, it records that post along with whatever
  category/date context preceded it.
- Only posts under the **Newsletter** category are kept.
- The site doesn't print a year, so the script infers it: it starts from the
  current year and walks down the list (newest → oldest), decrementing the
  year whenever the month number goes *up* as you move down the list (a
  December → January wrap going backwards in time).
- The GitHub Action re-runs the scraper every 6 hours and commits `feed.xml`
  only if it changed.

## Notes / limitations

- This depends on the current AP-HA page markup (via Webflow). If they
  redesign the site, the category/month/day tracking logic in
  `extract_posts()` may need adjusting. Check the Action logs — the script
  prints a warning if it finds zero newsletter posts.
- Year inference is a heuristic. It's been accurate against the current
  page's ordering but worth spot-checking `feed.xml` after first run.
- Cron schedule is UTC and GitHub free-tier schedules can be delayed by
  several minutes to hours under load — fine for a monthly-cadence bulletin.
