# 🇩🇪 German Personal Tutor (A1 → B2)

A free, open-source German coach that runs in your browser. It teaches you from **complete beginner (A1)
to upper-intermediate (B2)**, with lessons, exercises and grading by Google's Gemini AI. All your
progress is saved in your own database.

You run your own copy with **your own free accounts**. Nobody else sees your data, and nobody else
uses your AI quota. Setup takes about 15 minutes, and you don't need any programming.

▶️ **Video guide:** [docs/setup-guide.mp4](docs/setup-guide.mp4). It walks through every step below.
<sub>Narration: AI clone of the creator's own voice.</sub>

---

## What it does

| | |
|---|---|
| 📈 **8 stages, A1 → B2** | Each stage has its own topics for **Grammar, Vocabulary, Listening, Reading, Writing and Speaking**. |
| 🇬🇧 **English help for beginners** | At **A1 and A2**, every explanation, instruction and correction is in **English**, with German examples and translations. At **B1** it switches to German with English hints. **B2** is German only. |
| 🧑‍🏫 **Lesson first, then practice** | "Teach me a concept first" explains a topic, then the coach gives exercises and grades them. |
| 🚀 **Moves up by itself** | 8+ exercises in a stage with an 85%+ average unlocks the next stage. You can also pick your level yourself. |
| 📚 **Study Hub** | A week-by-week plan, a grammar checklist for each level that ticks itself as you improve, and progress by topic. |
| 🗂️ **Vocabulary** | Gemini builds the word list for your level (e.g. "A2: 312 words"). A daily vocab check counts how many you know. |
| 📖 **Grammar tables** | 46 reference tables behind toggle switches: pronouns, articles, modal verbs, Konjunktiv II, prepositions, adjective endings … |

| Stage | Level | Focus |
|---|---|---|
| 1 | A1 | German basics: sein/haben, present tense, questions, articles, nicht/kein |
| 2 | A2 | Everyday German: Perfekt, modal verbs, separable verbs, Dativ, prepositions |
| 3 | A2.2 → B1 | Core consolidation: word order, subordinate clauses, Akkusativ/Dativ |
| 4 | B1 | Everyday communication: appointments, housing, work, opinions |
| 5 | B1+ | Complex grammar: relative clauses, Konjunktiv II, passive |
| 6 | B1+ → B2 | Transition: connectors, nominalisation, formal language |
| 7 | B2 | Production: formal emails, reports, presentations, debates |
| 8 | B2 | Goethe-style exam practice and fluency |

---

## What you need (all free)

| Account | What for | Cost |
|---|---|---|
| [GitHub](https://github.com/signup) | Your copy of the code | Free |
| [Google AI Studio](https://aistudio.google.com) | The Gemini API key (the AI teacher) | Free tier |
| [Supabase](https://supabase.com) | The database that saves your progress | Free tier |
| [Streamlit Community Cloud](https://share.streamlit.io) | Runs the app on the internet | Free |

> The free tiers have limits, e.g. a number of Gemini requests per minute and per day. For one learner
> that is normally plenty. Check each provider's current terms; Google's free Gemini tier may use your
> prompts to improve its products.

---

## Setup

### Step 1: Get your own copy (GitHub)
1. Create a GitHub account at **https://github.com/signup** (skip this if you have one).
2. Open this repository and click **Fork** (top right) → **Create fork**.
   You now have your own copy at `github.com/<your-name>/german-personal-tutor-A1-B2`.

### Step 2: Get a Gemini API key (Google AI Studio)
1. Go to **https://aistudio.google.com** and sign in with your Google account.
2. Click **Get API key** → **Create API key**.
3. Copy the key and keep it somewhere safe.
   ⚠️ Never share it and never paste it into a file on GitHub. It only goes into Streamlit's **Secrets** (Step 4).

### Step 3: Create the database (Supabase)
1. Go to **https://supabase.com** → **Start your project**, and sign up (you can use GitHub).
2. Click **New project**. Choose a name, **save the database password**, and pick a region close to you.
   Wait ~2 minutes until the project is ready.
3. In the left menu open **SQL Editor** → **New query**.
4. Open [`schema.sql`](schema.sql) in this repository, copy **all** of it, paste it into the editor and click **Run**.
   You should see "Success. No rows returned". This creates all the tables the app needs.
5. Open **Project Settings** (⚙️) → **API Keys** and copy:
   - the **Project URL** (looks like `https://abcdefgh.supabase.co`; also shown under *Data API*),
   - the **Secret key** (starts with `sb_secret_…`).
   If the app later says *Invalid API key*, use the **`service_role`** key from the **Legacy API keys**
   tab instead.
   ⚠️ The secret key gives full access to your database. Only put it into Streamlit's Secrets.

### Step 4: Run the app (Streamlit Community Cloud)
1. Go to **https://share.streamlit.io** and **sign in with GitHub**.
2. Click **Create app** → **Deploy a public app from GitHub**, then choose:
   - **Repository:** your fork (`<your-name>/german-personal-tutor-A1-B2`)
   - **Branch:** `main`
   - **Main file path:** `app.py`
3. Click **Advanced settings**. In **Secrets**, paste this and fill in your values
   (it's the same as [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example)):
   ```toml
   GEMINI_API_KEY = "your-gemini-key"
   SUPABASE_URL = "https://your-project-id.supabase.co"
   SUPABASE_KEY = "your-supabase-secret-key"
   APP_PASSWORD = "choose-a-password"
   GEMINI_MODEL = "gemini-3.8-flash"
   LEARNER_ID = "me"
   ```
   `APP_PASSWORD` is optional but **recommended**. Your app's address is public, and without a
   password anyone who finds it could use your Gemini quota.
4. Click **Deploy** and wait 1–2 minutes. 🎉 Your coach is running.

You can change secrets later under your app → **⋮ → Settings → Secrets**. The app restarts by itself.

---

## First steps in the app
1. **Pick your level** in the sidebar under *Choose my level*. Complete beginners stay at **Stage 1 (A1)**.
2. Under **Today's adaptive lesson**, choose a skill (or *Auto*) and click **📘 Teach me a concept first**.
3. Read the lesson, click **I understand, give me an exercise**, answer, and submit. You get a score,
   a correction and an explanation.
4. Scroll down to the **📚 Study Hub**:
   - **Syllabus → Vocabulary:** click **✨ Build my word list with Gemini** once per level, then do the
     10-word **vocab check** every day.
   - **Syllabus → Grammar:** the grammar points of your level tick themselves as you master them.
   - **Plan:** your week-by-week sessions.
5. At the very bottom, switch on **📖 German grammar tables** whenever you need to look something up.

**Tip:** short and often beats long and rare. 15–20 minutes a day, every day.

---

## Run it on your own computer (optional)
```bash
git clone https://github.com/<your-name>/german-personal-tutor-A1-B2.git
cd german-personal-tutor-A1-B2
pip install -r requirements.txt
```
Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, fill in your keys, then:
```bash
streamlit run app.py
```
(On Windows, if `streamlit` isn't found, use `python -m streamlit run app.py`.)

---

## Troubleshooting

| Problem | Fix |
|---|---|
| "Missing GEMINI_API_KEY / SUPABASE_URL …" | A secret is missing or misspelled. Check your app → Settings → Secrets. |
| "Cannot connect" or connection errors after a break | Supabase **pauses free projects after about a week without use**. Open supabase.com → your project → **Restore project**, wait 2 minutes, reload the app. |
| *Invalid API key* (Supabase) | Use the **Legacy API keys → `service_role`** key as `SUPABASE_KEY`. |
| "…only last for this browser session" | The tables don't exist yet. Run [`schema.sql`](schema.sql) in the Supabase SQL Editor (Step 3). |
| Gemini "busy", 503 or rate limit | The app automatically tries other Gemini models. If all are busy, wait a minute; the free tier has per-minute limits. |
| Wrong password | Check `APP_PASSWORD` in your secrets. It's case-sensitive. |

---

## Privacy and security
- Your keys live only in **Streamlit Secrets**, never in the code. `.gitignore` blocks `secrets.toml`.
- `schema.sql` switches on **Row Level Security**, so Supabase's public key can't read your data. Only
  your app, using the secret key, can.
- One deployment is meant for **one learner**. Each person makes their own fork with their own keys.

## License
[GNU AGPL-3.0](LICENSE). You can use, study, change and share this app for free. If you run a
modified version as a service for others, you must publish your changes under the same license.
