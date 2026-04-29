# Smart Locker System (Face Recognition + Raspberry Pi + piCamera)

This project is a simple smart locker system using face recognition. It runs on Raspberry Pi with a camera and provides a basic GUI for user registration and access control.

Only registered faces can unlock the door. Admin access is protected by a PIN.

---

## Features

* Face recognition based access
* Live camera preview
* Admin login using 6-digit PIN
* Register users with camera capture
* On-screen keyboard for name input
* User list with delete option
* Door lock control using GPIO
* Auto unlock for 5 seconds
* Fullscreen GUI
* Press ESC to exit

---

## Hardware Required

* Raspberry Pi (Pi 4 recommended)
* Raspberry Pi Camera Module
* Relay or MOSFET module
* Electronic door lock
* External power supply for lock 12V

---

## Software Requirements

* Python 3
* Raspberry Pi OS

Install dependencies:

```bash
pip install PyQt5 opencv-python face_recognition numpy picamera2
```

---

## Project Structure

```
smart-locker/
├── main.py
├── faces/
└── README.md
```

---

## Setup

1. Clone the repository:

```bash
git clone https://github.com/yourusername/smart-locker.git
cd smart-locker
```

2. Enable camera:

```bash
sudo raspi-config
```

Enable Camera from Interface options.

Test camera:

```bash
libcamera-hello
```

3. Run the project:

```bash
python3 main.py
```

---

## Usage

### Home Screen
* Shows live camera feed
* Detects face automatically
* If face matches → door unlocks
* Otherwise → access denied

### Admin Access
* Click settings icon
* Enter 6-digit PIN

### Admin Panel
* Click Add button
* Enter name using keyboard
* Save to register face
* User appears in list
* Select user and delete if needed

## GPIO Configuration

* GPIO 23 → Door Lock Control

Behavior:

* HIGH → Unlock
* LOW → Lock
* Auto lock after 5 seconds

## Notes
* Keep good lighting for better detection
* One face per image is recommended
* Do not power lock directly from Raspberry Pi
* Use external power for relay/lock


## License
MIT License


## More update or customization
[DigitalMonk](https://digitalmonk.biz/smart-jukebox-rfid-based-interactive-music-system/)

