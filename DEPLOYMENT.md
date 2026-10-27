# Put your finished portfolio online

The ZIP contains all six pages, the Admin Panel, the server, the starting content, and the images. Changes you save in the Admin Panel live on the server and are visible to everyone, including visitors using another device.

## First: choose the right hosting

Use hosting that supports **Python web applications and permanent storage**, such as Render with a persistent disk, or a Python-capable hosting control panel. A static-only host, including GitHub Pages, cannot run the login, save content, or accept image uploads. Uploading these files to GitHub Pages alone will not produce the finished website.

You do not need to edit website code. Your hosting needs to run the included server. Ask your host to follow the settings below if it manages the server for you.

## Recommended route: Render

1. Download the ZIP and unzip it. Open the `Washma-Amjad-Portfolio` folder.
2. Put the **contents of that folder** in a GitHub repository. On GitHub, use **Add file → Upload files**, and drag in the unpacked files and folders. Keep `app.py`, `requirements.txt`, `render.yaml`, `seed.json`, `templates`, `admin`, and `assets` together at the top level. Include the CSS and JavaScript files too. Do not upload a real `data` folder or a `.venv` folder.
3. In Render, choose **New → Blueprint** and connect that repository. Render reads the included `render.yaml`. Review the plan and charges before creating it: this setup uses a persistent disk, which requires a paid service. Permanent storage is necessary so your edits and images survive restarts and deployments.
4. Create the service and let the build finish. The supplied configuration installs the software, starts the website, and attaches permanent storage. It also enables secure login cookies for HTTPS.
5. Open the website address Render gives you. Add `/admin` to the end to open the Admin Panel.
6. **Change the default login before sharing the website publicly**, following the next section.
7. You can connect your own domain in the host’s domain settings. Keep HTTPS enabled.

The supplied Render configuration is prepared, but this project has not been deployed to your hosting account. No hosting purchase, account change, or deployment has been performed for you.

## Change your password the first time you log in

1. Visit `https://your-website-address/admin`.
2. Enter **Username: `admin`** and **Password: `Admin@123`**.
3. Click **Enter the Studio**.
4. Click **Open Login & Security** in the orange reminder, or choose **Login & Security** in the menu.
5. Enter `Admin@123` in **Current password**.
6. Enter a new, unique password of **at least 12 characters** in **New password** and repeat it in **Confirm new password**. You may change the username too.
7. Click **Update Login Securely**. This saves the new login immediately. You do not need to click Save & Publish for the password.
8. Log out and log back in with your new details. Store them in your password manager. Other existing sessions are signed out when you change your password.

**`Admin@123` is for testing only. Change it before the site goes live.** A new installation starts with the dummy login; a website with existing permanent storage keeps the login you already changed.

## How to update the site

- **Page Content:** choose Home, About, Portfolio, Services, Awards, or Contact. Search for the wording you want and open its section to edit it.
- **Services & Pricing:** add or remove services, edit the description and included features, set the price, and move services up or down. Enter prices exactly as you want them displayed, such as `Starting at $150 per project`. The Home preview shows the first three services.
- **Portfolio Projects:** add or remove projects, choose their categories, edit the short and full descriptions, and choose or upload thumbnails.
- **Home Featured Work:** manage the Home gallery independently. Every image and expanded description is editable.
- **Awards & Achievements:** add or remove entries, edit the year, organizer, and explanation. Leave the sample checkbox on for fictional entries. Replace the sample notice in Awards page content when all the examples have been replaced with real achievements.
- **Image Library:** replace your profile photo or any gallery image. The profile photo updates on Home and About together. Use JPG, PNG, or WebP files up to 10 MB. Uploaded SVG files are not accepted. Add an image description so visitors using screen readers can understand it.
- **Contact & Social Links:** update your email, optional WhatsApp number, and social URLs. Include the country code in WhatsApp, like `+923001234567`. Instagram and YouTube remain pending until you add their actual links.
- **Save & Publish:** click this after changing content or images. The save updates all relevant pages. People already viewing the website receive the update automatically; refreshing also shows it immediately.
- **Color Themes:** click a theme to publish it immediately across all pages. This publishes only the theme and does not publish your other unfinished edits.
- **Reload Saved:** reload the server’s last saved content. It asks before discarding your unpublished edits. If two editors work at once, the Admin Panel prevents an older draft from overwriting a newer save.

## Keep your changes safe

Your permanent storage contains `portfolio.sqlite3`, `uploads`, and `.session-secret`. **Back up the entire permanent-storage folder through your host** before moving the website. Restore the whole folder on the new server to preserve your content, login, and images. Never upload it to a public repository or place it in a public downloads folder.

The dashboard’s **Download Content Backup** also exports the current content and referenced uploaded images. It intentionally excludes your login and private session secret. This is a content export, not a one-click account restore. Full hosting migrations should use the permanent-storage folder backup.

The starting ZIP intentionally excludes private runtime data. Uploading the ZIP to another new server starts a fresh site with the supplied example content and dummy login. It does not include changes you made later on a running server.

## Other Python hosting / hosting control panel

Upload all unpacked project files together. Ask your host to use:

- Python **3.12 or newer**.
- Installation command: `pip install -r requirements.txt`.
- Application: `app:app` (the file is `app.py`).
- Start command: `gunicorn --workers 1 --threads 32 --timeout 60 --bind 0.0.0.0:$PORT app:app`.
- `DATA_DIR`: the absolute path of a **private, permanently writable folder**. It must survive deployments. It must not be a public web folder.
- `SECURE_COOKIES=1` when the website uses HTTPS. Always use HTTPS on the public site.
- Route **all website requests** to the application, not just `/admin`. Do not serve the template files directly.
- Keep a single application worker as supplied; the server uses threaded connections and SQLite. Disable response caching and proxy buffering for `/api/events` so open pages can receive updates promptly. A periodic revision check also reconnects clients when needed.

If your hosting only offers `public_html` uploads without a Python app option, ask the host to enable Python applications or choose a compatible host. Simply copying templates into `public_html` will not run this website.

## Try it on a computer before uploading

Install Python 3.12+, then open a terminal in the unzipped folder:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py
```

On Windows, activate the environment using `.venv\Scripts\activate` instead. Open `http://localhost:8080` for the website and `http://localhost:8080/admin` for the login. This local command is for testing; use the supplied production start command on hosting.

A Dockerfile is included for Docker-capable hosts. Attach permanent storage at `/app/data`, expose the configured `PORT` (8080 by default), and set `SECURE_COOKIES=1` behind HTTPS.

If you forget the password, your host can run `python app.py reset-password` using the same `DATA_DIR`. It privately prompts for a new password and invalidates existing sessions.

## Contact form

The Contact form still prepares an email draft for the visitor to review and send from their email app. It does not claim to send messages automatically. Changing the contact email in the Admin Panel updates the destination. Automatic email delivery would require a separate email service configuration; it is not silently simulated here.
