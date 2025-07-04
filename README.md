# OutRun Arcade Graphics Atlas Tool

A Python script for extracting, decoding, and visualizing graphics (sprites, tiles, palettes) from the legendary SEGA **OutRun** arcade ROMs.  
This tool is created for arcade preservation, reverse engineering, and educational research.

---

## 🚗 About

This project generates a “graphics atlas” — a single PNG sheet showing all decoded sprite/tile graphics as used in the classic SEGA arcade title **OutRun**.  
It is useful for researching arcade graphics formats, creating documentation, or visualizing the raw assets from classic 1980s arcade games.

**Features:**
- Decodes and plots sprite/tile graphics from OutRun ROMs
- Palette extraction and application
- Output as indexed or RGBA PNG for easy viewing
- Customizable output (palettes, tile size, etc.)

---

## 🕹 Requirements

- **Python 3.7+**
- **Pillow** (`pip install pillow`)
- The original OutRun arcade ROMs (see Legal Disclaimer below)

---

## ⚡ Usage

1. **Obtain the original OutRun arcade ROM set**  
   *This script does not include or provide any copyrighted ROM data.*

2. **Extract the required ROM files** to a "Rom" folder as the batch file uses this to combine the data.

3. **Run the script: **  
   ```bash
   Run the dos batch command make-all.bat
   
-   

   ## ⚖️ Legal / Copyright Disclaimer

## **Disclaimer**

This project is intended **solely for educational, research, and preservation purposes**.
- No original OutRun game code or copyrighted graphic data is included or distributed.
 - To use this tool, **you must provide your own legally-obtained OutRun ROM files**.
 - **OutRun**, its graphics, and all related intellectual property are owned by **SEGA**.
 - This project and its contributors are **not affiliated with or endorsed by SEGA**.
 - **Do not redistribute ROM images or copyrighted data.**

 If you are a rights holder and have concerns, please open a GitHub issue or contact the maintainer. Content will be removed or modified as required.
 

