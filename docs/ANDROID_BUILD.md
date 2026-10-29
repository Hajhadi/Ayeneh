# Android build

Ayeneh uses Capacitor to package the static Next.js export as a single-user Android app.

## Local build

Install Java 21 and Android SDK packages `platform-tools`, `platforms;android-36`, and `build-tools;36.0.0`, then run:

```bash
pnpm install --frozen-lockfile
pnpm --filter ayeneh-web build
pnpm --filter ayeneh-web exec cap sync android
cd frontend/android
./gradlew assembleDebug
```

The APK is written to `frontend/android/app/build/outputs/apk/debug/app-debug.apk`.

After installing the APK, open **Settings → Backend Connection** and enter the
public URL of the Ayeneh backend (including `https://`, without a trailing slash).
The URL is stored locally on the device, so changing it does not require a new APK.

## GitHub Actions

The `Android build` workflow performs the same export, sync, and debug build on GitHub and uploads the APK as `ayeneh-debug-apk`. It can be started manually from the Actions tab.
