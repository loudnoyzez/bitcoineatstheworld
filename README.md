# bitcoineatstheworld.com

A one-page hub: links to the social accounts, a Beehiiv email signup, the latest clips, a "start here" list and a privacy notice. Plain HTML/CSS with no build step, so it costs $0 to host.

## Files
- `index.html`: the page. Edit `CLIPS` near the bottom to change which Shorts appear (`paid: true` adds the "Paid campaign" label).
- `privacy.html`: the privacy notice. Update the date if you change it.
- `styles.css`, `favicon.svg`, `CNAME` (the custom domain for GitHub Pages).

## Preview locally
```bash
cd ~/dev/bitcoineatstheworld && python3 -m http.server 8765
```
Then open http://localhost:8765

## Launch checklist
1. **Beehiiv**: create a free account and a publication called "Bitcoin Eats the World". Go to Grow → Subscribe Forms → New form, and copy the embed code. Paste it at the `BEEHIIV EMBED` comment in `index.html`, then delete the fallback div.
2. **Hosting (GitHub Pages)**: push this repo and turn on Pages (main branch, root).
3. **DNS at GoDaddy** for bitcoineatstheworld.com:
   - 4 × `A` records on `@`: 185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153
   - `CNAME` record on `www`: `loudnoyzez.github.io`
   - Delete any old `A`/`CNAME` records on `@` and `www` that point at the GoDaddy builder site.
   - When the domain shows as verified in Pages settings, tick "Enforce HTTPS".
4. **bitcoinsavestheworld.com**: in GoDaddy, set up Forwarding to `https://bitcoineatstheworld.com` (permanent 301).
5. **Bios**: put `bitcoineatstheworld.com` in the YouTube, Instagram, TikTok and X bios.
6. **GoDaddy billing**: cancel any Website Builder plan on these domains. Keep the domain registrations.

## Rules
- No investment advice and no price predictions written as promises.
- Affiliate links need the disclosure line that's already in the "Start here" section.
- Embed posted clips only. Never re-upload campaign footage to this site.
