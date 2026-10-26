# Ars Memoriae — Mobile App (iOS & Android)

The official cross-platform mobile companion for **Ars Memoriae**, featuring active recall reviews with typed responses, FSRS priority queue scheduling, and sub-second real-time progress synchronization.

---

## ⚡ Quickstart (Under 60 Seconds)

### 1. Install Expo Go on your Phone
- **iOS (iPhone/iPad)**: Download [Expo Go on the App Store](https://apps.apple.com/app/expo-go/id982107779).
- **Android**: Download [Expo Go on Google Play](https://play.google.com/store/apps/details?id=host.exp.exponent).

### 2. Start the Mobile Development Server
In your terminal, navigate to the `mobile` folder:
```bash
cd mobile
npm install
npm start
```
A QR code will appear in your terminal.

### 3. Open on your Phone
- **iOS**: Open your iPhone camera and scan the terminal QR code to open in Expo Go.
- **Android**: Open the Expo Go app, tap **Scan QR Code**, and scan the terminal QR code.

---

## 🔗 1-Click Desktop Pairing

1. On your desktop, launch Ars Memoriae (`start_windows.bat` or `./start_mac.sh`).
2. Open your desktop browser to **Settings** and scroll to **Mobile Companion & Real-Time Sync**.
3. In the mobile app, tap the **Connection Pill** (or Settings &gt; Pair) and paste the QR payload or enter the local Wi-Fi IP (e.g. `http://192.168.1.50:8000`).
4. You are paired! The top badge turns **🟢 LIVE SYNC**.

---

## 🔄 Real-Time Sync Architecture

- **Bi-directional WebSocket Hub**: Card reviews confirmed on mobile immediately broadcast to desktop, updating your daily time budget, reviewed counts, and card intervals without refreshing.
- **Offline-First Resilience**: If you lose Wi-Fi or go into Airplane mode (e.g. subway commute), reviews continue uninterrupted. They are queued locally and automatically batch-synced to `/api/sync/batch` when reconnection occurs.
- **Identical FSRS Engine**: Spaced repetition metrics (`stability`, `difficulty`, and `due`) use the exact same algorithm parameters across both desktop and mobile.
