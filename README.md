GlideCast is a fast, lightweight, and high-performance desktop utility designed to mirror your Android screen directly to your Windows 10/11 PC. Stream video, forward device audio, and gain full control of your mobile apps using your computer's mouse and keyboard.

Running 100% locally on your machine with no external accounts or cloud subscriptions required, GlideCast delivers a private, secure, and lag-free experience over a simple USB or local Wi-Fi connection.

Key Features:
• Real-time, low-latency screen mirroring at native resolutions.
• Audio forwarding to play mobile games or video sound directly on your PC speakers.
• PC Keyboard & Mouse emulation to interact with your phone smoothly.
• Single-instance network locking for stable connection sessions.
• Complete privacy: Runs entirely offline on your local network.


GlideCast Privacy Policy
Last updated: July 2026

We respect your privacy. This privacy policy applies to the GlideCast application (the "App").

1. No Personal Data Collection: The App does not collect, record, store, or transmit any personal data, personal information, or user identifiers.

2. Local Processing: All screen mirroring, audio forwarding, and device control processing are executed entirely locally on your Windows PC and your connected Android device over your USB cable or local Wi-Fi. No video, audio, or input data is ever transmitted to us or any third-party servers.

3. Internet Access: The App uses your internet connection solely on the first launch to download the necessary open-source engine dependencies (scrcpy and ADB) directly from their official repositories on GitHub. No analytics, tracking, or telemetry is gathered during this process.

4. Compliance: We fully comply with the Microsoft Store Developer policies regarding user privacy.

This application is a screen mirroring and control assistant for Android devices. 

Testing instructions:
1. To fully test screen mirroring, a physical Android device must be connected to the PC via USB with USB Debugging enabled.
2. On the first launch, the app automatically downloads the open-source mirroring engine dependencies (scrcpy and ADB binaries) directly from GitHub and saves them to the user's Local AppData directory (%LOCALAPPDATA%\GlideCast).
3. If no physical Android device is connected, the app will run successfully, complete the dependency download, and show the "No active devices found" message in the status logs. This is the expected and correct behavior.

Restricted Capability Declaration:
This is a packaged Win32 desktop application that requires the "runFullTrust" capability to launch the local adb and scrcpy processes, write downloaded engine binaries to Local AppData, and bind to a local socket for single-instance locking.
