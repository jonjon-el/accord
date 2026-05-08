# ACCORD 📂🤖
> **A**utomated **C**alibration and **C**ontrol for **O**perational **R**adiotherapy **D**ata.

(Calibración y Control Automático para Datos de Radioterapia Operacional)

🌎 *Leer en otros idiomas: [English](README.md)*

ACCORD es una aplicación diseñada para automatizar, centralizar y optimizar el control de calidad (QC) en aceleradores lineales (LINACs). Basada en el ecosistema de Pylinac, ACCORD extiende sus capacidades integrando un motor de análisis de incertidumbres y en un futuro, la adquisición automática de datos de sensores.

## 🚀 Características principales

### Implementadas:

* CLI de Pylinac.
* Integración con Pylinac: Implementación de:
* Protocolo TRS 398 según el módulo `pylinac.calibration.trs398`
* Análisis preliminar a la calibración de la incertidumbre por:
    + Repetibilidad de lecturas
    + Temperatura
    + Presión
* Automatización de flujo: Reducción del error humano mediante el procesamiento sistemático de datos operativos.

### En proceso:

* GUI basada en Kivy para Pylinac.
* Protocolo TG 51 según el módulo `pylinac.calibration.tg51`.
* Módulos de análisis. (Winston-Lutz, VMAT, Starshot, etc)
* Análisis de incertidumbre completo.
* Sensor Sync: Lectura directa y procesamiento en tiempo real de instrumentación externa.

## 🛠️ Configuración para desarrolladores

Si usas VS Code, este proyecto incluye una configuración optimizada del debugger.
Asegúrate de tener el archivo .vscode/launch.json configurado para que los scripts actúen sobre los archivos de datos que se irán localizando en la subcarpeta tests de la carpeta raíz del proyecto.
De esta manera, se puede depurar el programa desde vscode. La opción clave para lograr esto es:

```"${workspaceFolder}/tests"```

## 🛠️ Instalación

Este programa utiliza flit para instalarse como paquete.
Se recomienda crear un entorno virtual de python para ejecutar los siguientes comandos (Se utilizó venv durante el desarrollo):
```bash
git clone https://github.com/jonjon-el/accord
cd accord
```
A partir de aquí hay dos maneras de instalarlo

1. (CLÁSICA) El programa se puede instalar como paquete local directamente con:
```bash
pip install .
```

2. (FLIT) También se puede utilizar flit para facilitar el desarrollo haciendo una instalación editable.
```bash
# (OPCIONAL) Instalar flit para permitir una instalación editable
pip install flit
# (OPCIONAL) Entonces después se puede hacer la instalación editable como paquete
flit install --symlink
```

## 🚀 Uso

Cómo ejecutarlo:
1. Abre VS Code.
2. Configura el `launch.json` (como vimos antes).
3. Presiona F5 para debugear.

## 📝 Notas del Debugger
Originalmente este programa se desarrolló en una laptop con Windows 11, CPU i3 basado en Sandy Bridge, Memoria RAM de 6GB.

## ✒️ Mantenido por
ACCORD Development Team:
* https://github.com/jonjon-el

## 🤝 Contribuciones y Soporte

Si quieres ayudar a mejorar **ACCORD** o tienes alguna duda técnica:

*   **Reportar errores:** Si algo no funciona o los cálculos de incertidumbre dan resultados inesperados, abre un [Issue](https://github.com).
*   **Sugerir mejoras:** ¿Tienes una idea para la automatización de sensores? Cuéntamelo en la sección de [Discusiones](https://github.com) o mediante un Issue.
*   **Enviar código:** Si has corregido algo o añadido una función, ¡envía un **Pull Request**! Estaré encantado de revisarlo junto a **@jonjon-el**.

## Nota histórica

**ACCORD** comenzó su vida como el script llamado **nel_calc**, un trabajo para una tesis desarrollado por **jonjon-el** para simplificar procesos de calbración específicos basados en el TRS 398, ejecutados sobre un acelerador lineal perteneciente a un Hospital Oncológico. En el transcurso del tiempo, la necesidad de integrar todo el poder de *Pylinac*, implementar cálculos de incertidumbre y la adquisición automática de datos de sensores hicieron que surgiera la idea de transformar el script original en una plataforma completa de calibración de LINACs.