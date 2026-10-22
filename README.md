# VGK Official News → GitHub RSS → TrustyBot

Free community RSS generator for the [Vegas Golden Knights official news page](https://www.nhl.com/goldenknights/news/). Reads the latest official news page and article metadata; adds description and image tags when the NHL site supplies them. Updates every 30 minutes (GitHub Actions runs may be delayed).

## Setup
1. Create a **public** GitHub repository named `vgk-official-rss`.
2. Upload `build_feed.py`, `requirements.txt`, and this `README.md`.
3. Add `.github/workflows/update-feed.yml` separately using GitHub **Add file → Create new file** to preserve the dot folder.
4. Go to Settings → Pages and select **GitHub Actions**.
5. Actions → Update VGK Official RSS → Run workflow. Check **build** logs for article and image counts. If fetching fails, adjust the script using the error output before enabling the feed.
6. Open `https://YOUR_USERNAME.github.io/vgk-official-rss/feed.xml` and confirm it contains article `<item>` entries and `<media:content url="...">` images.
7. Test in TrustyBot: `;rss add vgk-official #bot-testing https://YOUR_USERNAME.github.io/vgk-official-rss/feed.xml`.
8. Get available tags with `;rss listtags vgk-official #bot-testing`; set the large embed image to `$media_url01` if available, and a template like `**[$title]($link)**\\n\\n$summary_detail_plaintext`. Test with `;rss force vgk-official #bot-testing`.

This script has been syntax checked but **not live-verified** against NHL.com's HTML. The first GitHub run verifies whether article metadata is accessible. If no items are found, it intentionally fails rather than publishing an empty feed.
