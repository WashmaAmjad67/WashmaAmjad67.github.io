# Washma Amjad — Complete Portfolio & Studio Admin

A six-page portfolio with a real, password-protected content management system.

**Read [DEPLOYMENT.md](DEPLOYMENT.md) for the step-by-step hosting and first-login guide.**

## First login

- Admin address: `/admin`
- Username: `admin`
- Temporary password: `Admin@123`

**Change this temporary password in Login & Security before going live.** New installations create this account once. Existing installations keep their saved credentials.

## What works

- Home, About, Portfolio, Services, Awards & Achievements, and Contact pages, linked through working navigation and footers.
- Real login, logout, username/password changes, hashed passwords, private session cookies, CSRF protection, rate-limited login, and stale-session invalidation after a password change.
- Editable wording across all six pages, including headings, body copy, buttons, form labels, page titles, and search descriptions.
- Add, remove, reorder, and edit services, prices, portfolio projects, Home featured work, and awards.
- Shared contact email, WhatsApp number, Instagram, YouTube, TikTok, Fiverr, LinkedIn, and Behance settings.
- Image library and real uploads for all photos and project thumbnails. The profile photo is shared by Home and About. Images are decoded and re-encoded as WebP to validate their contents and remove embedded metadata. JPEG, PNG, and WebP uploads are accepted; uploaded SVG is rejected.
- Four complete themes: Charcoal Orange, Midnight Blue, Slate Purple, and Emerald Dark. Theme selection saves immediately; other content uses Save & Publish.
- Server-rendered pages update immediately after saving. Open visitor tabs receive server-sent update notifications and reload automatically; a revision check provides a fallback. A contact enquiry in progress is preserved across a content-update reload.
- SQLite stores published content and credentials. Uploaded images and the session secret are kept in a private persistent data folder. Changes survive application restarts and appear to other browsers; browser-local mock storage is not used as the CMS.
- Content export ZIP (content and referenced uploaded images, excluding credentials).

## Start locally

Python 3.12+ is required. In this folder:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py
```

On Windows use `.venv\Scripts\activate` to activate the environment.

Open `http://localhost:8080` and `http://localhost:8080/admin`. The local development server is for testing. Use the supplied Gunicorn configuration on hosting.

## Hosting

This is now a **Python web application**, not a static-only website. GitHub Pages alone cannot run the Admin Panel. All requests must reach the application; the HTML templates are not meant to be opened directly as files.

The included `render.yaml`, `Dockerfile`, and `Procfile` support deployment. Configure permanent storage and HTTPS as described in DEPLOYMENT.md. `DATA_DIR` selects the private persistent directory (defaults to `data` next to `app.py`). On HTTPS hosting set `SECURE_COOKIES=1`. Never publish the private data folder. The final source ZIP excludes it and starts from `seed.json` on a new installation.

Use the supplied single-worker Gunicorn configuration with threads. SQLite provides atomic saves and optimistic revision checking; stale drafts return a conflict instead of overwriting newer work.

## Content notes

The portrait, project artwork, testimonials, and award examples are illustrative placeholders. Sample award names, years, and organizations are fictional, as clearly disclosed on the page. Replace them with verified material before presenting them as real endorsements or recognition. The owner’s provided experience, client count, and rating are retained.

Graphic-design and web-development services start with Custom quote because no prices for these services were provided. The Admin Panel can set any starting price text without editing code. Home previews the first three saved services.

Email defaults to `muskanamjad671@gmail.com`. WhatsApp is initially available on request. TikTok uses `@Senu_Graphics`, and Fiverr uses the supplied `senu_graphics` handle. Instagram and YouTube remain pending until their actual links are entered in the Admin Panel. Profile ownership and external link availability were not independently verified.

The Contact form prepares an encoded email draft for visitors to review and send through their email app. It does not claim automatic delivery or store public enquiries on the server. Changing the contact email in the Admin Panel updates the draft destination.

## Design

Manrope headings and DM Sans body copy, charcoal backgrounds, orange and electric-blue accents by default, gentle blurred ambient movement, staggered reveals, image hover lifts, and reduced-motion support. The Manrope and DM Sans variable fonts are included locally, with their SIL Open Font License files. All pages and the Admin Panel use the same bundled fonts without third-party font requests; system fonts remain as fallbacks. No scanning or sweeping effects are used.

## Tests

```sh
python -m unittest discover -s tests -v
```

Tests use an isolated temporary database and cover access protection, CSRF, six-page text edits, HTML escaping, collection add/remove behavior, pricing, contact settings, themes, revision conflicts, image uploads/rejection, password/session changes, login rate limiting, and persistence from a separate process.

Browser validation also exercises the actual dashboard, publishing, public-page updates, file upload controls, mobile layouts, portfolio filtering, lightboxes, and the contact form.
