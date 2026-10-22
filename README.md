# MissConduct.vegas → RSS → TrustyBot

This public GitHub Actions project reads MissConduct.vegas's **existing** RSS feed, extracts its article summaries and first article images, and republishes a small RSS feed suitable for TrustyBot. It checks every 30 minutes (GitHub may delay scheduled runs).

## Setup

1. In your `missconduct-rss` GitHub repository, upload `build_feed.py`, `requirements.txt`, and this README.
2. **Important:** GitHub's web uploader may not preserve `.github/workflows/`. Create `.github/workflows/update-feed.yml` separately using **Add file → Create new file**, and paste the supplied workflow contents (or upload via git).
3. In **Settings → Pages**, select **GitHub Actions** as the source.
4. In **Actions → Update MissConduct RSS**, click **Run workflow**. Open `build` logs to check how many articles and images were extracted.
5. After successful deployment, the feed should be `https://kartane25.github.io/missconduct-rss/feed.xml`.
6. Add the verified URL to TrustyBot in `#bot-testing`, then inspect tags via `;rss listtags missconduct-official #bot-testing`. Expect `$media_url01` if image metadata is recognized.

**Note:** The source has returned security challenges to some bots. If GitHub receives a CAPTCHA, the build fails rather than publishing bogus entries. In that case, this method cannot work as-is; it does not bypass security controls. No secret tokens needed.
