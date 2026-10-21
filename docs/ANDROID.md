# Android Port

The current Mark LVI is a desktop PyQt application. Porting to Android requires:

1. **UI rewrite**: Replace PyQt6 with Kivy or BeeWare (Toga). The HUD/avatar need reimplementation.
2. **Audio**: Use Android media APIs (pyjnius) instead of sounddevice.
3. **Subprocess**: Android doesn't support subprocess the same way; use pyjnius or Kivy.
4. **Build**: Use Buildozer (buildozer.spec included) or python-for-android.

## Steps
1. Install buildozer: `pip install buildozer`
2. Install Android SDK/NDK via buildozer.
3. Run `buildozer android debug` to build APK.
4. For release: `buildozer android release` then sign with jarsigner.

## Limitations
- PyQt6 HUD/avatar won't work; needs Kivy rewrite.
- System control (volume, apps) differs on Android.
- File paths differ (use Android storage APIs).

## Recommendation
Create a separate `android/` directory with a Kivy-based UI that reuses `core/` logic (gemini, memory, actions) where possible, and shares the same plugin system.
PY