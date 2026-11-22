# Games Statisticians Play (Volume 1)

The internal Kivy build runs offline. Choose solo or pass-and-play, select a level, then enter any whole number from 1 to 20. The default is 10 questions per player, with ten seconds per question. The internal build uses its own Android package ID so it can be installed alongside a future release.

Open the [browser phone preview](preview/index.html) to play and compare screen sizes, backgrounds, and launcher icons offline. See the [project handoff](HANDOFF.md) for verification and the remaining Android work.

## How rounds are drawn

- Level 100 draws entirely from its own bank. In every higher level, about 80% of the questions come from the selected level and 20% come from one combined pool of all earlier levels. The review share rounds to the nearest whole question. A ten-question round uses 8 current and 2 review questions. A twenty-question round uses 16 and 4.
- **AI/ML Bonus** draws only from the AI and machine learning bank. **Pro · Bring It All** draws about 70% from Level 400, Final Year and Graduate Mix combined, 20% from AI/ML and 10% from Levels 100–300 combined. A 10-question Pro round draws 7, 2 and 1 respectively. Other lengths round randomly so all three pools have a chance even in a one-question round.
- Each round draws fresh questions without repeating an item within that round. Each question keeps its five fixed choices, and their display order is shuffled when it appears.
- In pass-and-play, both players receive the same mix of source levels. Each pair uses different concepts from the same level, difficulty and clue type. A clue type is how the prompt presents the concept. It can describe it directly, give a short scenario, or show a formula to recognize. Tied matches can use up to three reserved pairs from the selected level, or from the higher-year pool in Pro.
- The solo year ladder starts at Level 100. A score of at least 60% unlocks the next year. AI/ML and Pro are available from the start in both modes, with separate solo best scores. In pass-and-play, all years are available from the start.

## Run on Windows

Use the existing `appdev-conda` environment, which has Kivy 2.3.1 and pytest.

```powershell
conda activate appdev-conda
python -m pytest -q
python app/main.py
```

The tests exercise every round length from 1 to 20 at all six years and in AI/ML and Pro using the bundled questions. They also check answer shuffling, tiebreaks, timeouts, and progress saved by older versions.

## Android phone check

Run **Android prototype** in GitHub Actions on a standard Ubuntu runner with included build capacity. Download the workflow artifact, extract the debug APK and transfer it privately to the test phone. The workflow has no publish step. [Android packaging for Kivy](https://kivy.org/doc/stable/guide/packaging-android.html) · [GitHub Actions billing and usage](https://docs.github.com/en/actions/concepts/billing-and-usage)

Record the APK version, phone model, Android version, font size and TalkBack version for each run.

1. Install the APK and launch it in airplane mode. Finish one round in each mode.
2. With TalkBack on, swipe through the title, clue and choices. Confirm it reads the formulas and gives all five answers meaningful names, and that a double tap submits the focused answer once.
3. Set the system font and display size to their largest settings. Test the formula questions in both orientations. Check for missing glyphs, clipping, and answer wrapping that singles out the correct choice. On Android 16, check that the timer and controls clear the system bars with both gesture and three-button navigation.
4. Rotate while a question is active. Briefly switch away and return after ten seconds. Confirm the deadline continues and only the timeout is recorded.
5. On the handover screen, confirm the previous question and choices are absent visually and from TalkBack. Wait more than ten seconds before tapping **Ready** and confirm the next player receives the full time.

Kivy's standard widgets have an open accessibility support issue. Treat the phone check as pending until there is direct evidence. If a focused Kivy fix fails, switch to the approved TypeScript and Capacitor approach and rerun the same device checks. [Kivy accessibility issue](https://github.com/kivy/kivy/issues/8596) · [Android TalkBack testing](https://developer.android.com/guide/topics/ui/accessibility/testing) · [Capacitor Android](https://capacitorjs.com/docs/android)

## Curriculum

The [coverage map](curriculum/coverage.v1.json) links the six years and AI/ML outcomes to the questions by ID. The expanded bank is a draft for internal play. Use the printed page number and dictionary entry for statistics references when available. Cite relevant textbooks, papers or courses for AI/ML questions. Record conventions when they affect the answer. Review the questions for correctness, a single best answer and clues from length, wording or notation. [Waterloo multiple-choice design guide](https://uwaterloo.ca/centre-for-teaching-excellence/catalogs/tip-sheets/designing-multiple-choice-questions)

| Level | Questions authored for this level | Curriculum sources |
| --- | ---: | --- |
| 100 | 100 | [UC Berkeley STAT 2](https://stat2.berkeley.edu/fall-2024/) |
| 200 | 84 | [MIT 18.05](https://ocw.mit.edu/courses/18-05-introduction-to-probability-and-statistics-spring-2022/pages/syllabus/), [UC Berkeley STAT 2](https://stat2.berkeley.edu/fall-2024/) |
| 300 | 84 | [Open University M248](https://www.open.ac.uk/courses/qualifications/details/m248/), [UC Berkeley STAT 2](https://stat2.berkeley.edu/fall-2024/) |
| 400 | 92 | [Open University M348](https://www.open.ac.uk/courses/modules/m348/), [Penn State STAT 502](https://online.stat.psu.edu/stat502/Lesson03) |
| Final Year | 84 | [Wharton statistics courses](https://statistics.wharton.upenn.edu/programs/undergraduate/course-descriptions/), [Penn EPID 702](https://www.med.upenn.edu/bgs/assets/user-content/documents/spring-2021-courses/21a-epid-702-syllabus.pdf), [Maryland SURV 701](https://jpsm.umd.edu/sites/jpsm.umd.edu/files/syllabi/SURV701_Online_Winter2018_v1.pdf), [UC Berkeley STAT C245C](https://www.stat.berkeley.edu/~sandrine/Teaching/syllabus_PHC240C_F18.pdf) |
| Graduate Mix | 84 | [Open University M347](https://css2.open.ac.uk/outis/descs/courses/M347.htm), [Ohio State STAT 6570](https://stat.osu.edu/sites/default/files/2024-02/Spring%202024%20STAT%206570%20syllabus%20for%20insructor%20Chkrebtii.pdf) |
| AI/ML Bonus | 48 | [UC Berkeley CS 188](https://inst.eecs.berkeley.edu/~cs188/textbook/), [An Introduction to Statistical Learning](https://www.statlearning.com/), [Speech and Language Processing](https://web.stanford.edu/~jurafsky/slp3/), [Attention Is All You Need](https://arxiv.org/abs/1706.03762) |
| **Total** | **576** | |

After independent statistics review, record the reviewed bank's fingerprint in the coverage map and run the release check. The fingerprint combines the filenames and SHA-256 checksums of all bundled question files. Any edit to those files requires a new review of the changes and an updated fingerprint.

```powershell
python -m curriculum.check_release app/assets curriculum/coverage.v1.json
```

## Release status

The Windows build and tests are available. The Android build still needs a GitHub repository with a working login or another Ubuntu runner. Independent review of the draft question bank and handset checks remain pending. The public download follows internal testing, including Android 8, recent Android, 16 KB page compatibility and a signed update that preserves progress. Keep the release signing key and encrypted backup outside this workspace. [Android page-size checks](https://developer.android.com/guide/practices/page-sizes) · [Android app signing](https://developer.android.com/studio/publish/app-signing)
