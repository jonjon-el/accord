# ACCORD 📂🤖
> **A**utomated **C**alibration and **C**ontrol for **O**perational **R**adiotherapy **D**ata.

(Calibración y Control Automático para Datos de Radioterapia Operacional)

🌎 *Read this in other languages: [Español](README.es.md)*

ACCORD is an application designed to automate, centralize, and optimize Quality Control (QC) in Linear Accelerators (LINACs). Built upon the Pylinac ecosystem, ACCORD extends its capabilities by integrating an uncertainty analysis engine and, in the future, automated sensor data adquisition.

## 🚀 Key features

### Currently implemented:

* **Pylinac CLI:** A robust command-line interface for rapid workflows.
* **Pylinac Integration:** Core implementation of:
    * **TRS-398 Protocol:** Based on the `pylinac.calibration.trs398` module.
* **Pre-calibration Uncertainty Analysis:** Including:
    * Reading repeatability.
    * Temperature corrections.
    * Pressure variations.
* **Workflow Automation:** Significant reduction of human error through systematic processing of operational data.

### In Progress / Roadmap:
* **Kivy-based GUI:** A modern graphical user interface for Pylinac.
* **TG-51 Protocol:** Implementation based on the `pylinac.calibration.tg51` module.
* **Standard Analysis Modules:** (Winston-Lutz, VMAT, Starshot, etc.).
* **Comprehensive Uncertainty Analysis:** Full-scale statistical budget for calibration.
* **Sensor Sync:** Direct real-time data acquisition and processing from external instrumentation.

## 🛠️ Developer Configuration

If you use VS Code, this project includes an optimized debugger configuration.  
Ensure your `.vscode/launch.json` file is configured so that scripts act upon the data files located in the `tests` subfolder of the project's root directory.  
This allows for seamless debugging within VS Code. The key setting to achieve this is:

```json
"cwd": "\${workspaceFolder}/tests"
```

## 🛠️ Installation

This program uses **Flit** for package installation.  
It is highly recommended to create a Python virtual environment (the project was developed using `venv`):

```bash
git clone https://github.com/jonjon-el/accord
cd accord
```

There are two ways to install it:

1. **Classic (Direct):** Install as a local package using pip:
   ```bash
   pip install .
   ```

2. **Flit (Editable):** Use Flit for an editable installation, which is ideal for development:
   ```bash
   # (OPTIONAL) Install flit to enable editable mode
   pip install flit
   # Perform an editable installation as a package
   flit install --symlink
   ```

## 🚀 Usage

How to run:
1. Open the project in VS Code.
2. Configure `launch.json` (as described above).
3. Press **F5** to start debugging.

## 📝 Debugger & Development Notes
The program was originally developed on a Windows 11 laptop with an Intel i3 (Sandy Bridge) CPU and 6GB of RAM.

## ✒️ Maintained by
**ACCORD Development Team:**
* [GitHub Profile](https://github.com/jonjon-el)

## 🤝 Contributing & Support

If you want to help improve **ACCORD** or have technical questions:

* **Report Bugs:** If something isn't working or uncertainty calculations yield unexpected results, please open an [Issue](https://github.com).
* **Suggest Improvements:** Have an idea for sensor automation? Share it in the [Discussions](https://github.com) section or via an Issue.
* **Submit Code:** If you’ve fixed a bug or added a feature, send a **Pull Request**! I’ll be happy to review it alongside **@jonjon-el**.

## 📜 Historical Note

**ACCORD** began its life as the script called **nel_calc**, a work for a thesis developed by **jonjon-el** to simplify specific clinical calibration workflows based on TRS 398, performed on a LINAC located on a Oncology Hospital. Over time, the idea of transform that original script into a comprehensive platform for calibration of LINACs arose from the need to integrate the full power of *Pylinac*, implement rigorous uncertainty analysis, and automate sensor data acquisition.
