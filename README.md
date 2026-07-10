NOTE: This application utilizes Android Debug Bridge (ADB) to mirror and control your Android device. ADB is fully integrated and pre-packaged directly inside the application for a secure, 100% offline experience.

GlideCast is a fast, lightweight, and high-performance desktop utility designed to mirror your Android screen directly to your Windows 10/11 PC. Stream video, forward device audio, and gain full control of your mobile apps using your computer's mouse and keyboard.

Running 100% locally on your machine with no external accounts or cloud subscriptions required, GlideCast delivers a private, secure, and lag-free experience over a simple USB or local Wi-Fi connection.

Key Features:
• Real-time, low-latency screen mirroring at native resolutions.
• Audio forwarding to play mobile games or video sound directly on your PC speakers.
• PC Keyboard & Mouse emulation to interact with your phone smoothly.
• Single-instance network locking for stable connection sessions.
• Complete privacy: Runs entirely offline on your local network.



This application is a screen mirroring and control assistant for Android devices. 

VM Testing / Demo Simulation Instructions:
If testing inside a Virtual Machine, sandboxed PC, or without a physical Android device connected:
1. Select "Demo Simulation (virtual)" from the "Android Device" dropdown selection menu on the left side of the app.
2. Click "START MIRRORING" to open the interactive simulation screen.
3. You can click inside the simulation screen to verify mouse touch capture (triggers visual ripple feedback) and press keys on your keyboard to verify input capture.
4. If testing with a real physical device, ensure USB Debugging is turned ON on the device.

Restricted Capability Declaration:
This is a packaged Win32 desktop application that requires the "runFullTrust" capability to launch the local adb and scrcpy processes, write engine binaries to Local AppData, and bind to a local socket for single-instance locking.
