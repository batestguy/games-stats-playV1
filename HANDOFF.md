# Games Statisticians Play (Volume 1) handoff

As of 22 November 2026, the full internal quiz is playable on Windows. It has six
statistics levels, AI/ML Bonus, and Pro, backed by 576 draft questions. The latest Windows
suite passed all 29 tests. Independent question approval and Android handset testing are
still open. The Android packaging workflow is prepared and awaits a runnable Ubuntu job.

The original brief records the initial Android design. The approved plan chose Python and
Kivy for the internal build, with a TypeScript and Capacitor fallback if a focused fix cannot
pass the phone accessibility checks. Later decisions added variable round lengths, earlier-year
review, AI/ML Bonus, and Pro. Use the working code and README for current gameplay.
[Original design brief](Stats%20Game%20andriod.txt) · [Current README](README.md)

## Try the game

### Windows internal build

From the project root, run these commands in PowerShell with the existing `appdev-conda`
environment. It has Kivy 2.3.1 and pytest.

```powershell
conda activate appdev-conda
python app/main.py
```

Choose **Solo** or **Pass-and-play**, select a level, and set a round length from 1 to 20.
Solo saves the best accuracy on the current machine. The two-player flow uses **Player 1**
and **Player 2** and passes the same device between them. Use this build for the internal
Windows experience. [App entry point](app/main.py)

### Browser phone simulation

Open the preview file directly in a browser. Keep the files in `preview/` together
so the page can load its styles, code, and copy of the draft bank offline. It supports
both game modes. Choose a compact, standard, or large phone,
portrait or landscape, and 100%, 130%, or 160% text. Compare Graph, Solid, and Paper
backgrounds and the Histogram or Sigma icon. The formula and launcher previews are
available from the side controls. Solo best scores use browser storage when available
and stay in memory when the browser blocks storage. They are independent of the
Windows app’s saved progress. Chromium passed offline file loading and a touch-sized
browser check. All three simulated sizes passed in both orientations, with the formula
screen checked at 160% text. The checks covered both icon designs, the three
backgrounds, invalid round length, solo answers and unlocks, AI/ML timeout, a Pro
match with a private handover, and a draw after all three reserve pairs. The timer
also expired correctly while the launcher was open. The launcher, backgrounds, and icons are
browser design candidates. Android installation, native system bars, TalkBack, and
signed updates still require a native build and handset checks. [Open the phone preview](preview/index.html)

After changing the draft bank, run `python -m preview.sync_bank` from the root to
regenerate the browser copy. The generated copy includes the fields needed for play.
The browser rules were checked in Node against all 576 questions, including all
round lengths, every Pro rounding offset, distinct matched pairs, and sudden
death outcomes. [Preview bank generator](preview/sync_bank.py) ·
[Browser game rules](preview/game.js) · [Preview controls and screens](preview/preview.js)

## Gameplay and progress

| Area | Current rule |
| --- | --- |
| Question | Identify a concept from a short definition, scenario, or formula. The stored five choices stay fixed and the display order is shuffled on each appearance. |
| Round length | Any whole number from 1 to 20. The default is 10 questions in solo or 10 per player in pass-and-play. |
| Year selection | The solo ladder advances through Level 100, 200, 300, 400, Final Year, and Graduate Mix. A completed round with at least 60% correct unlocks the next year. Pass-and-play allows every year immediately. |
| Year question mix | Level 100 uses its own questions. Higher years use about 80% from the selected year and 20% from one combined pool of earlier years, rounding the review count to the nearest whole item. A 10-question round draws 8 and 2. A 20-question round draws 16 and 4. |
| AI/ML Bonus | Available immediately in both modes. Draws exclusively from the AI/ML bank and has its own solo best score. |
| Pro · Bring It All | Available immediately in both modes. Draws about 70% from Level 400, Final Year, and Graduate Mix combined, 20% from AI/ML, and 10% from Levels 100–300 combined. Ten questions draw 7, 2, and 1. Twenty draw 14, 4, and 2. Randomized rounding keeps all three pools eligible in a one-question round. Pro has its own solo best score. |
| Scoring | A correct answer earns one point. An incorrect answer or timeout earns zero. Solo shows the correct choice and explanation before **Next**. Pass-and-play reveals answers and explanations on the results screen. |
| Matched turns | Each pair uses two distinct concepts from the same source level, difficulty, and clue type. Question IDs cannot repeat within a match, including reserve pairs. Both players get the same mix of source levels. |
| Handover | The screen removes the previous clue and answers before showing the incoming player. The next 10 seconds start when that player taps **Ready**. |
| Match winner | Compare regulation points first, then faster average time on correct regulation answers. An unresolved tie uses up to three matched reserve pairs. The first pair with exactly one correct answer decides the match. If all three pairs tie, record a draw. Reserves come from the chosen year, AI/ML for that mode, or Pro’s higher-year pool. |

The deadline is checked against elapsed time, including when the app resumes. A tap at
or after 10 seconds records a timeout. Once a turn records an outcome, stale or repeated
taps have no effect. Windows uses a monotonic clock. Android code uses the platform’s
`elapsedRealtime` clock, which includes device sleep. Physical rotation and backgrounding
still need verification on a phone.

Solo writes the best accuracy as a fraction to `progress.json` under Kivy’s app data
directory. The current format is version 2. Readers also accept version 1 scores from
fixed 10-question rounds. Progress is written when the completed round improves the
player’s best. Bonus and Pro best scores affect only their own entries.
[Game logic and progress storage](app/game.py) · [Screen flow and timers](app/main.py)

## Question bank and curriculum

| Pool | Draft items | Outcomes | Available disjoint pairs |
| --- | ---: | ---: | ---: |
| Level 100 | 100 | 4 | 50 |
| Level 200 | 84 | 4 | 42 |
| Level 300 | 84 | 4 | 42 |
| Level 400 | 92 | 4 | 46 |
| Final Year | 84 | 4 | 42 |
| Graduate Mix | 84 | 5 | 42 |
| AI/ML Bonus | 48 | 5 | 24 |
| **Total** | **576** | **30** | **288** |

The 100 Level 100 items include the eight original prototype samples. The six statistics
levels account for 528 items, above the approved plan’s 525-item statistics target.
AI/ML adds 48. Pro draws from existing pools. All 576 current IDs appear in the map, and
the smallest outcome has nine linked questions. Pair capacities are calculated within each
pool by the current matching rules. [Bundled question files](app/assets) · [Coverage map](curriculum/coverage.v1.json)

The version 1 question format stores an ID, concept, level, difficulty, clue type, clue,
five choices, answer, short explanation, reference, and an optional notation convention.
Keep IDs stable. Statistics references use exact dictionary pages and entries where
available and checked university or textbook material for other topics. AI/ML uses course
notes, textbooks, and original papers. Keep the Cambridge reference PDF outside release
assets. [Sample format](app/assets/sample-bank.v1.json) · [Curriculum sources](README.md#curriculum)

The release checker currently returns only “The curriculum map has no approval for this
version of the bank.” Its draft fingerprint is
`42755fb6ae734d1ef5968ec3a4f477f6f4f4370a549995c9dc17123a1db65e68`.
The approved fingerprint remains empty. An independent reviewer must check correctness,
exactly one best answer, credible alternatives, sources, and unintended visual clues.
Record approval for the reviewed fingerprint after corrections. The checker hashes the
ordered filenames and their individual SHA-256 checksums, so a bank edit changes the
fingerprint. [Release checker](curriculum/check_release.py)

## Verification and working files

The Windows automated suite was rerun for this handoff and passed **29 tests**. It exercises
all round lengths in both modes, the draw and pairing rules, shuffled answers, timing
boundaries, ties, progression, and old saved scores. The default pytest temp and cache
folders returned Windows access errors on this machine. The commands below use a fresh
temporary directory and disable pytest’s cache. The release check exits with status 1
while approval is pending. [Automated tests](tests/test_game.py)

```powershell
conda activate appdev-conda
$testTemp = Join-Path $env:TEMP ('statsgame-test-' + [guid]::NewGuid().ToString('N'))
python -m pytest -q -p no:cacheprovider --basetemp $testTemp
python -m curriculum.check_release app/assets curriculum/coverage.v1.json
```

Earlier Windows play-throughs verified the round chooser, the Level 200 unlock, a
20-question-per-player match, and the optional sections. The earlier prototype also
passed a Windows run at doubled font scale after switching question clues and feedback
to DejaVu Sans. [Initial prototype record](.agent/20261122-android-prototype-d842/progress.md) ·
[Expanded game record](.agent/20261122-cumulative-quiz-492d/report.md) ·
[Optional modes record](.agent/20261122-optional-play-e5a7/report.md)

| File | Where to work |
| --- | --- |
| [app/game.py](app/game.py) | Bank loading, draw quotas, pair selection, turn resolution, match scoring, and progress. |
| [app/main.py](app/main.py) | Kivy screens, local game entry point, platform clock, and handover. |
| [buildozer.spec](buildozer.spec) | Internal Android package `org.gamesstatisticiansplay.volumeone.internal`, version 0.1.0, Android API 36 target, API 26 minimum, and pinned Android build settings. |
| [Android prototype workflow](.github/workflows/android-prototype.yml) | Manually triggered Ubuntu 24.04 job that runs the tests, builds a debug APK, and retains it as an internal artifact for seven days. |

The internal packaging job uses Python 3.12, Java 17, and Buildozer 1.6.0. The spec
selects Android NDK 28c, the SDL2 bootstrap, a pinned Python-for-Android revision,
and 64-bit and 32-bit ARM builds. It includes only Python and JSON files from
`app/`, so the root reference PDF and browser simulator stay outside the APK.

## Remaining release work

1. **Run the internal Android build.** The previous attempt recorded a GitHub authentication
   HTTP 401, found no matching connected repository, and did not establish an alternate
   Linux runner through WSL or Docker. Use an authorized repository with an Ubuntu runner,
   or another available Ubuntu runner, and use included build capacity. Capture a successful
   build and APK artifact, then transfer it privately to a test phone. No successful native
   build or APK artifact has been verified for this handoff.
2. **Pass the handset checks.** Record the build version, phone, Android version, TalkBack
   version, and text/display settings. Install and play both modes in airplane mode.
   Choose the icon and background after browser review, then check the implemented
   launcher icon and background in the Android build under light and dark device settings.
   Check that TalkBack can read the clue, formulas, and every choice and submit each answer
   once. Use maximum system text and display size in portrait and landscape. On Android 16,
   verify clear timer and controls under both gesture and three-button navigation. Rotate
   during a question and return after backgrounding past the deadline. Leave the handover
   on screen for more than 10 seconds, confirm the previous question is absent visually and
   with TalkBack, then tap **Ready** and verify a full countdown. If a focused Kivy fix
   cannot pass the accessibility checks, use the approved TypeScript and Capacitor
   fallback and repeat them. [Phone checklist](README.md#android-phone-check)
3. **Approve the bank.** Obtain independent question review and sign-off, update
   `approved_bank_sha256` for that exact content, and rerun the release checker.
4. **Prepare and verify the signed release.** Choose one public package ID for future
   updates. Keep the signing key and encrypted backup outside the workspace. Build the
   signed APK after internal verification. Test Android 8 and a recent Android release,
   check 16 KB memory-page compatibility, and verify that a signed update preserves
   progress. Keep the internal build’s separate package ID for private testing.
5. **Open the official download after sign-off.** The approved plan calls for a GitHub
   Pages download page and a GitHub Releases APK, with a version, size, checksum, QR code,
   install steps, and feedback link. Verify ordinary installation in several markets and
   check current Android distribution requirements before promotion. Google Play
   publication follows sponsorship, with the same release signing key imported into
   Play App Signing and a separate upload key for the Android App Bundle. The first
   30 days of the public launch are intended to track downloads and voluntarily reported
   install problems, completion, and replay interest.
