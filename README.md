# Color Under Pressure for Android

The Windows game (`color_rush.py`, Man Studio) built into an Android APK with Buildozer.

- `app/` - the game as it is on the computer, plus `main.py` (starts it) and `android_shim.py`
  (full screen, joystick + action button where the game wants WASD, Back = ESC, phone keyboard,
  Hebrew font, links, HTTPS).
- `tools/patch_game.py` - two exact changes made only in the build (screen size from the phone,
  saves in the app's private folder so updates keep them).
- `sync.ps1` - copies the latest `color_rush.py` and music from the ManStudio folder. Never copies
  saves, logs or account files.
- GitHub Actions builds, signs (secret `CUP_SIGNING`, key backed up in OneDrive\cup-signing) and
  publishes a release with `ColorUnderPressure.apk`.

Update: run `sync.ps1`, commit, push.
