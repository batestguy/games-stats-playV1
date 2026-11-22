# Repository Guidelines

## Project Structure

Start with [Stats Game andriod.txt](Stats%20Game%20andriod.txt), the design brief for a
statistics quiz with solo progression and two-player pass-and-play. The project is at the
design stage. The brief proposes Kotlin, Jetpack Compose, and Room.

When the Android app is scaffolded, organize Kotlin packages under `app/src/main/java/`.
Use `data/` for Room and repositories, `domain/` for scoring and question pairing, and
`ui/` for Compose screens and ViewModels. Place bundled question data and formula assets
under `app/src/main/assets/` and Android resources under `app/src/main/res/`.

## Build, Test, and Run

The current checkout has no Android scaffold or Gradle wrapper. Once both exist, use these
commands from the project root in PowerShell and use Android Studio to run the app on an
emulator or device.

- `./gradlew.bat assembleDebug` builds a debug APK.
- `./gradlew.bat testDebugUnitTest` runs local unit tests.
- `./gradlew.bat connectedDebugAndroidTest` runs instrumented tests on a connected device or emulator.
- `./gradlew.bat lintDebug` checks the debug build with Android Lint.

## Coding Style and Content

Use four spaces for Kotlin indentation, PascalCase for classes and composable functions
that produce UI, camelCase for other functions and properties, and UPPER_SNAKE_CASE for
enum entries. Keep scoring and pairing rules in the domain layer. Give each quiz item a
stable ID, level, difficulty, one correct answer, four plausible distractors, and a short
explanation. Review formula notation and formatting for clues that give away the answer.

## Testing Guidelines

When adding tests, place JUnit tests in `app/src/test/` and instrumented Android tests in
`app/src/androidTest/`. Use names such as `QuestionPairingStrategyTest`. Cover timeouts,
scoring, level unlocking, and same-level, same-difficulty pairing without repeats. On a
device or emulator, check that rotation preserves the countdown and the handover screen
hides each player's question.

## Commits and Pull Requests

Use short, imperative commit subjects such as `Add question pairing rules`. In pull
requests, describe the change, link the issue if one exists, and list the checks you ran.
Include screenshots or a short recording for visible changes. Keep signing keys and
passwords outside the workspace.
