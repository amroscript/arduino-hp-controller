"""
    @Author: Amro Farag
    Date: March 2024
    Email: amro.farag@bregroup.com / amrihabfaraj@gmail.com
"""

import os
import sys
import csv
import time
import serial
import numpy as np
from collections import deque
from datetime import datetime, timedelta
from filelock import FileLock
from matplotlib.dates import DateFormatter, date2num
from bamLoadBasedTesting.twoMassModel import CalcParameters
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QPushButton, \
    QLineEdit, QGridLayout, QGroupBox, QHBoxLayout, QFrame, QPlainTextEdit, \
    QTabWidget, QTableWidget, QTableWidgetItem, QFileDialog, QProgressBar, QSplashScreen
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap, QIcon
from PyQt5.QtCore import QTimer, Qt, QSize

# Constants for Arduino connection
ARDUINO_PORT = 'COM4'
BAUD_RATE = 115200

def applyOneDarkProTheme(app):
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(37, 37, 38))
    palette.setColor(QPalette.WindowText, QColor(212, 212, 212))
    palette.setColor(QPalette.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.AlternateBase, QColor(45, 45, 48))
    palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
    palette.setColor(QPalette.ToolTipText, QColor(212, 212, 212))
    palette.setColor(QPalette.Text, QColor(212, 212, 212))
    palette.setColor(QPalette.Button, QColor(37, 37, 38))
    palette.setColor(QPalette.ButtonText, QColor(212, 212, 212))
    palette.setColor(QPalette.BrightText, QColor(255, 255, 255))
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
    app.setPalette(palette)

    app.setStyleSheet("""
    QMainWindow, QWidget {
        background-color: #282C34;
    }
    QLineEdit, QLabel, QGroupBox {
        color: #ABB2BF;
        font-family: 'Verdana';
    }
    QLineEdit {
        border: 1px solid #3B4048;
        padding: 5px;
        background-color: #282C34;
        margin: 2px;
    }
    QPushButton {
        background-color: #3B4048;
        color: white;
        border: 2px solid #3B4048;
        border-radius: 5px;
        padding: 5px;
        margin: 2px;
    }
    QPushButton:hover {
        background-color: #4B5263;
    }
    QTabBar::tab {
        min-width: 120px;
        padding: 10px;
    }
    QGroupBox {
        border: 2px solid #3B4048;
        margin-top: 20px;
        padding: 5px;
        border-radius: 5px;
        background-color: #282C34;
    }
    """)
    
# Function to display the splash screen
def show_splash_screen():
    splash_pix = QPixmap('C:/Users/hvaclab/Desktop/GUI Testing/Splash-Screen.jpg')
    splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
    splash.setMask(splash_pix.mask())
    font = QFont("Verdana", 12, QFont.Bold)
    splash.setFont(font)
    splash.show()

    return splash

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.arduinoSerial = None
        self.currentAmbientTemperature = 0  
        self.currentMassFlow = 0.0 
        self.currentDesignHeatingPower = 0  
        self.currentFlowTemperatureDesign = 0 
        self.boostHeatPower = 6000 

        self.t_sup_history = []  
        self.t_ret_mea_history = []
        self.t_ret_history = [] 

        self.lastDACVoltage = '0.00'
        self.lastSPtemp = '0.00'
        self.lastFlowRate = '0.00'
        self.lastreturnTemperature = '0.00'
        
        self.hasBeenInitialized = False

        self.model_initialized = False
        self.boost_heater_on = False
        self.initialization_time = None

        self.logoLabel = None
        self.timer = None
        self.time_data = []
        self.temperature_data = []
        self.flow_rate_data = []
        self.return_temperature_data = []
        self.stopButton = None
        self.measurementGroup = None       
        self.exportCSVButton = None
        self.controlGroup = None
        self.flowRateLabel = None
        self.dacVoltageLabel = None
        self.updateButton = None
        self.projectNumberInput = None
        self.temperatureLabel = None
        self.clientNameInput = None
        self.initButton = None
        self.dateInput = None
        self.terminal = None
        self.tableWidget = None
        self.currentBuildingModel = None

        self.dacVoltageInput = QtWidgets.QLineEdit()
        self.targetTempInput = QtWidgets.QLineEdit()
        self.toleranceInput = QtWidgets.QLineEdit()

        self.headers_written = False
        self.simulated_time = datetime.now()  # Initialize simulated time
        self.data_storage = [] 
        self.csv_buffer = deque()  # Buffer for batch writing to CSV
        self.batch_size = 100  # Define batch size for writing to CSV
        
        self.csv_file_path = None  
        self.csv_lock_path = None 
        self.csv_writer = None  # CSV writer object
    
        self.setWindowTitle("ArduinoUI")
        self.setWindowIcon(QIcon('C:/Users/hvaclab/Desktop/GUI Testing/icon.ico'))
        self.setupUI()
        applyOneDarkProTheme(QApplication.instance())

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateDisplay)
        self.timer.start(100)

        self.loadingTimer = QTimer(self)
        self.loadingTimer.timeout.connect(self.updateLoadingBar)
        self.loadingStep = 0  

        self.graphUpdateTimer = QTimer(self)
        self.graphUpdateTimer.timeout.connect(self.updateGraph)
        self.graphUpdateTimer.start(1000)

        self.initSerialConnection()
        self.updateButton.setEnabled(False)
        self.stopButton.setEnabled(False)
        self.virtualHeaterButton.setEnabled(False)
        self.dacVoltageInput.setEnabled(False)
        self.targetTempInput.setEnabled(False)
        self.toleranceInput.setEnabled(False)

    def initSerialConnection(self): 
        try:
            self.arduinoSerial = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
            self.logToTerminal("> Serial connection established. System initialized.")
        except serial.SerialException as e:
            self.logToTerminal(f"> Error connecting to Arduino: {e}", messageType="error")
            QTimer.singleShot(2000, lambda: self.retrySerialConnection(retries=5, delay=2))

    def retrySerialConnection(self, retries=5, delay=2):
        if retries > 0:
            try:
                self.arduinoSerial = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
                self.logToTerminal("> Serial connection re-established.")
            except serial.SerialException as e:
                self.logToTerminal(f"> Retry {6 - retries} failed: {e}", messageType="error")
                QTimer.singleShot(delay * 1000, lambda: self.retrySerialConnection(retries - 1, delay))
        else:
            self.logToTerminal("> Failed to establish serial connection after multiple attempts.", messageType="error")

    def updateLoadingBar(self):
        if self.loadingStep < 100:
            self.loadingStep += 7
            self.progressBar.setValue(self.loadingStep)
            self.progressBar.setVisible(True)
        else:
            self.loadingTimer.stop()
            self.progressBar.setVisible(False)
            self.loadingStep = 0  # Reset for next use

    def startLoadingBar(self):
        self.loadingStep = 9
        self.progressBar.setValue(self.loadingStep)
        self.progressBar.setVisible(True)
        self.loadingTimer.start(100)  # Adjust the interval as needed

    def setupUI(self):
        self.setFont(QFont("Verdana", 12))
        tabWidget = QTabWidget(self)

        # Set a larger window size to accommodate the graphs
        self.setMinimumSize(1500, 950)

        # Logo Setup
        self.logoLabel = QLabel()
        logoPixmap = QPixmap("/Users/hvaclab/Desktop/GUI Testing/Arduino-Controller.png")
        scaledLogoPixmap = logoPixmap.scaled(700, 500, Qt.KeepAspectRatio)
        self.logoLabel.setPixmap(scaledLogoPixmap)
        self.logoLabel.setAlignment(Qt.AlignCenter)

        # Create QProgressBar
        self.progressBar = QProgressBar(self)
        self.progressBar.setGeometry(200, 80, 250, 20)
        self.progressBar.setMaximum(100)
        self.progressBar.setVisible(False)
        self.progressBar.setTextVisible(False)  

        controlsTab = QWidget()
        controlsLayout = QVBoxLayout()
        controlsLayout.addWidget(self.logoLabel)
        controlsLayout.addWidget(self.progressBar) 
        self.measurementGroup = self.createMeasurementGroup()
        self.controlGroup = self.createControlGroup()
        self.terminal = self.createTerminal()
        controlsLayout.addWidget(self.measurementGroup)
        controlsLayout.addWidget(self.controlGroup)
        controlsLayout.addWidget(self.terminal, 1)
        controlsTab.setLayout(controlsLayout)
        
        # Add signature label
        signatureLabel = QLabel("Developed by Amro Farag for Building Research Establishment")
        signatureLabel.setAlignment(Qt.AlignRight)
        signatureLabel.setFont(QFont("Satoshi", 6))
        signatureLabel.setStyleSheet("color: #ABB2BF;")

        controlsLayout.addWidget(signatureLabel)

        spreadsheetTab = QWidget()
        spreadsheetLayout = QVBoxLayout(spreadsheetTab)

        tableFrame = QFrame()
        tableLayout = QVBoxLayout()
        tableFrame.setLayout(tableLayout)

        headerLayout = QHBoxLayout()
        self.projectNumberInput = QLineEdit()
        self.projectNumberInput.setPlaceholderText("Project Number")
        self.projectNumberInput.setMaximumWidth(300)
        self.clientNameInput = QLineEdit()
        self.clientNameInput.setPlaceholderText("Client Name")
        self.clientNameInput.setMaximumWidth(300)
        self.dateInput = QLineEdit()
        self.dateInput.setPlaceholderText("Date (YYYY-MM-DD)")
        self.dateInput.setMaximumWidth(300)
        self.exportCSVButton = QPushButton("Export to CSV")
        self.exportCSVButton.clicked.connect(self.exportToCSV)
        self.exportCSVButton.setStyleSheet("font-size: 10pt;")
        
        headerLayout.addWidget(self.projectNumberInput)
        headerLayout.addWidget(self.clientNameInput)
        headerLayout.addWidget(self.dateInput)
        headerLayout.addWidget(self.exportCSVButton)

        tableLayout.addLayout(headerLayout)

        # Adjust the table to include all necessary columns
        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(12)  # Updated count according to the new columns
        self.tableWidget.setHorizontalHeaderLabels([
            "Time", "Supply Temperature", "DAC Voltage", "SP Temperature", "Flow Rate", 
            "Return Temperature", "Heat Flow HB", "Heat Flow BA", "Heat Flow HP", 
            "HF Internal Gains", "HF Booster Heater", "Building Temperature"
        ])

        # Adjust column widths to ensure proper display
        for i in range(12):
            self.tableWidget.setColumnWidth(i, 151)  # Adjust width as needed

        self.tableWidget.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: #282C34;
                color: #ABB2BF;
                gridline-color: #3B4048;
                selection-background-color: #3E4451;
                selection-color: #ABB2BF;
                font-size: 9pt;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #3B4048;
                color: #ABB2BF;
                padding: 5px;
                border: 1px solid #282C34;
                font-size: 9pt;
                font-family: 'Verdana';
            }
        """)
        
        self.progressBar.setStyleSheet("""
            QProgressBar {
                border: 1px solid grey;
                border-radius: 3px;
                text-align: center;
                font: bold 14px;
                color: #282C34;
                background-color: #282C34;
            }
            QProgressBar::chunk {
                background-color: #98C379;
                width: 15px;
                margin: 1px;
            }
        """)


        tableLayout.addWidget(self.tableWidget)
        spreadsheetLayout.addWidget(tableFrame)
        spreadsheetTab.setLayout(spreadsheetLayout)

        self.graphTab = QWidget()
        self.graphLayout = QVBoxLayout()
        self.graphTab.setLayout(self.graphLayout)

        self.figure = Figure(facecolor='#282C34')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("QWidget {background-color: #282C34; color: #ABB2BF;}")

        self.setupGraph()
        self.updateGraph()

        self.graphLayout.addWidget(self.canvas)
        tabWidget.addTab(controlsTab, "Controls Monitor")
        tabWidget.addTab(spreadsheetTab, "Data Spreadsheet")
        tabWidget.addTab(self.graphTab, "Temperature Graph")
        
        self.setCentralWidget(tabWidget)
        applyOneDarkProTheme(QApplication.instance())
        

    def createMeasurementGroup(self):
        group = QGroupBox("Instructions and Real-time Measurements")
        group.setFont(QFont("Verdana", 11, QFont.Bold))

        mainLayout = QHBoxLayout(group)

        instructionsLayout = QVBoxLayout()
        instructionsLabel = QLabel("""
        <p>
        1. The <span style='color: #98C379;'>Initialize</span> button must be clicked to activate building model parameters or if operations are stopped.<br>
        2. The building model control parameters are initialized & updated when the <span style='color: #61AFEF;'>Update Settings</span> button is clicked.<br>
        3. The <span style='color: #E06C75;'>Stop</span> button will halt all operations. Re-initialization is required if testing to be resumed.<br><br>
        For clarification please consult the github repo documentation: github.com/amroscript/arduino-hp-controller.
        </p>
        """)
        instructionsLabel.setFont(QFont("Verdana", 11))
        instructionsLayout.addWidget(instructionsLabel)

        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("""
            QFrame {
                color: #3B4048;
                border: 5px solid #3B4048;
                margin: 1px;
            }
        """)

        mainLayout.addLayout(instructionsLayout)
        mainLayout.addWidget(line)

        dataLayout = QGridLayout()

        uniform_font = QFont("Verdana", 11)
        uniform_font.setBold(True)

        temperatureLabel = QLabel("↻ Supply Temperature:")
        dacVoltageLabel = QLabel("⇈ DAC Output Voltage:")
        SPVoltageLabel = QLabel("Set Point Temperature:")
        flowRateLabel = QLabel("Flow Rate:")
        returnTemperatureLabel = QLabel("↺ Return Temperature:")

        for label in [temperatureLabel, dacVoltageLabel, SPVoltageLabel, flowRateLabel, returnTemperatureLabel]:
            label.setFont(uniform_font)
            label.setStyleSheet("padding-left: 20px;")  # Adjust the padding as needed

        self.temperatureLabel = QLabel("0°C")
        self.dacVoltageLabel = QLabel("0V")
        self.SPVoltageLabel = QLabel("0°C")
        self.flowRateLabel = QLabel("0L/s")
        self.returnTemperatureLabel = QLabel("0°C")

        for data_label in [self.temperatureLabel, self.dacVoltageLabel, self.SPVoltageLabel, self.flowRateLabel, self.returnTemperatureLabel]:
            data_label.setFont(uniform_font)

        dataLayout.addWidget(temperatureLabel, 1, 0)
        dataLayout.addWidget(self.temperatureLabel, 1, 1)
        dataLayout.addWidget(returnTemperatureLabel, 2, 0)
        dataLayout.addWidget(self.returnTemperatureLabel, 2, 1)
        dataLayout.addWidget(SPVoltageLabel, 3, 0)
        dataLayout.addWidget(self.SPVoltageLabel, 3, 1)
        dataLayout.addWidget(flowRateLabel, 4, 0)
        dataLayout.addWidget(self.flowRateLabel, 4, 1)
        dataLayout.addWidget(dacVoltageLabel, 5, 0)
        dataLayout.addWidget(self.dacVoltageLabel, 5, 1)

        mainLayout.addLayout(dataLayout)
        
        return group

    def createControlGroup(self):
        group = QGroupBox("Two Mass Model Settings")
        group.setFont(QFont("Verdana", 11, QFont.Bold))
        layout = QVBoxLayout(group)

        heaterButtonLayout = QHBoxLayout()
        self.virtualHeaterButton = QPushButton("MODIFY SETTINGS")

        for btn in [self.virtualHeaterButton]:
            btn.setCheckable(True)
            btn.setFixedHeight(31)
            btn.setFont(QFont("Satoshi", 8, QFont.Bold))
            btn.toggled.connect(self.updateHeaterButtonState)
            heaterButtonLayout.addWidget(btn)
            btn.setChecked(False)
            
        self.virtualHeaterSettingsGroup = self.createVirtualHeaterSettingsGroup()

        self.updateHeaterButtonState()

        settingsLayout = QHBoxLayout()
        settingsLayout.addWidget(self.virtualHeaterSettingsGroup)

        buttonLayout = QHBoxLayout()
        self.initButton = QPushButton("Initialize")
        self.stopButton = QPushButton("Stop")
        self.updateButton = QPushButton("Update Settings")
        
        for btn in [self.initButton, self.updateButton, self.stopButton]:
            btn.setFixedHeight(31)
            buttonLayout.addWidget(btn)

        layout.addLayout(heaterButtonLayout)
        layout.addLayout(settingsLayout)
        layout.addLayout(buttonLayout)

        self.applyButtonStyles()
        self.initButton.clicked.connect(lambda: self.initButtonClicked(retry_count=3))
        self.stopButton.clicked.connect(self.stopOperations)
        self.updateButton.clicked.connect(self.updateSettings)

        group.setLayout(layout)
        return group
    
    def validateVirtualHeaterSettings(self):
        try:
            ambient_temp = float(self.ambientTempInput.text())
            q_design_e = float(self.designHeatingPowerInput.text())
            t_start_h = float(self.initialReturnTempInput.text())

            if not -40 <= ambient_temp <= 40:
                self.logToTerminal("Ambient temperature out of expected range: -40 to 40°C", messageType="warning")
                return False
            if q_design_e <= 0:
                self.logToTerminal("Design heating power must be greater than 0.", messageType="warning")
                return False
            if not 10 <= t_start_h <= 90:
                self.logToTerminal("Initial return temperature out of expected range: 10 to 90°C", messageType="warning")
                return False

            return True
        except ValueError:
            self.logToTerminal("Invalid input: Please check that all fields contain numeric values.", messageType="warning")
            return False

    def updateHeaterButtonState(self):
        activeStyle = "QGroupBox { font: 8pt; font-weight: bold; color: #98C379; }"
        inactiveStyle = "QGroupBox { font: 8pt; font-weight: bold; color: #E06C75; }"
        
        if self.virtualHeaterButton.isChecked():
            self.virtualHeaterSettingsGroup.setTitle("Two Mass Model: Activated")
            self.virtualHeaterSettingsGroup.setStyleSheet(activeStyle)
        else:
            self.virtualHeaterSettingsGroup.setTitle("Two Mass Model: Off")
            self.virtualHeaterSettingsGroup.setStyleSheet(inactiveStyle)
        
        self.virtualHeaterSettingsGroup.style().unpolish(self.virtualHeaterSettingsGroup)
        self.virtualHeaterSettingsGroup.style().polish(self.virtualHeaterSettingsGroup)

    def createVirtualHeaterSettingsGroup(self):
        group = QGroupBox("Virtual Heater Settings")
        group.setFont(QFont("Verdana", 10, QFont.Bold))
        layout = QGridLayout()

        line_edit_style = """
            QLineEdit {
                border: 1px solid #3B4048;
                border-radius: 1px;
                padding: 5px;
                background-color: #282C34;
                color: #ABB2BF;
            }
            QLineEdit:focus {
                border: 1px solid #61AFEF;
            }
        """

        self.ambientTempInput = QLineEdit("7")
        self.ambientTempInput.setStyleSheet(line_edit_style)
        self.addSettingWithButtons(layout, "██████████████████████████▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒  Ambient Temperature:", self.ambientTempInput, 0, font_size=10.5)

        self.designHeatingPowerInput = QLineEdit("3750")
        self.designHeatingPowerInput.setStyleSheet(line_edit_style)
        self.addSettingWithButtons(layout, "██████████████████████████▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒  Design Heating Power:", self.designHeatingPowerInput, 1, font_size=10.5)

        self.initialReturnTempInput = QLineEdit("25")
        self.initialReturnTempInput.setStyleSheet(line_edit_style)
        self.addSettingWithButtons(layout, "██████████████████████████▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒  Initial SP Temperature:", self.initialReturnTempInput, 2, font_size=10.5)

        group.setLayout(layout)
        return group
    
    def applyButtonStyles(self):
        buttonFontSize = "8pt" 

        self.initButton.setStyleSheet(f"""
            QPushButton {{
                background-color: #98C379;
                color: white;
                border: 2px solid #98C379;
                font-size: {buttonFontSize};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #A8D989;
            }}
        """)

        self.updateButton.setStyleSheet(f"""
            QPushButton {{
                background-color: #61AFEF;
                color: white;
                border: 2px solid #61AFEF;
                font-size: {buttonFontSize};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #72BFF7;
            }}
        """)

        self.stopButton.setStyleSheet(f"""
            QPushButton {{
                background-color: #E06C75;
                color: white;
                border: 2px solid #E06C75;
                font-size: {buttonFontSize};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #EF7A85;
            }}
        """)

    def updateHeaterButtonState(self):
        activeStyle = "QGroupBox { font: 8pt; font-weight: bold; color: #98C379; }"
        inactiveStyle = "QGroupBox { font: 8pt; font-weight: bold; color: #E06C75; }"
    
        if self.virtualHeaterButton.isChecked():
            self.virtualHeaterSettingsGroup.setTitle("PARAMETERS READY TO MODIFY")
            self.virtualHeaterSettingsGroup.setStyleSheet(activeStyle)
            self.ambientTempInput.setEnabled(True)
            self.designHeatingPowerInput.setEnabled(True)
            self.initialReturnTempInput.setEnabled(True)
        else:
            self.virtualHeaterSettingsGroup.setTitle("PARAMETERS READ-ONLY")
            self.virtualHeaterSettingsGroup.setStyleSheet(inactiveStyle)
            self.ambientTempInput.setEnabled(False)
            self.designHeatingPowerInput.setEnabled(False)
            self.initialReturnTempInput.setEnabled(False)
        
        self.virtualHeaterSettingsGroup.style().unpolish(self.virtualHeaterSettingsGroup)
        self.virtualHeaterSettingsGroup.style().polish(self.virtualHeaterSettingsGroup)

    def addSettingWithButtons(self, layout, labelText, lineEdit, row, font_size=10):
        label = QLabel(labelText)
        label.setFont(QFont("Verdana", int(font_size)))
        layout.addWidget(label, row, 0)

        upButton = QPushButton("+")
        downButton = QPushButton("-")
        upButton.setFont(QFont("Verdana", int(font_size), QFont.Bold))
        downButton.setFont(QFont("Verdana", int(font_size), QFont.Bold))

        buttonSize = QSize(60, 30)
        upButton.setFixedSize(buttonSize)
        downButton.setFixedSize(buttonSize)

        upButton.clicked.connect(lambda: self.adjustValue(lineEdit, 1))
        downButton.clicked.connect(lambda: self.adjustValue(lineEdit, -1))

        lineEdit.setMinimumSize(QSize(100, 30))
        lineEdit.setFont(QFont("Verdana", int(font_size)))
        lineEdit.setEnabled(True)

        controlLayout = QHBoxLayout()
        controlLayout.addWidget(lineEdit)
        controlLayout.addWidget(upButton)
        controlLayout.addWidget(downButton)

        controlContainer = QWidget()
        controlContainer.setLayout(controlLayout)
        layout.addWidget(controlContainer, row, 1, 1, 2)

    def adjustValue(self, lineEdit, increment):
        try:
            currentValue = float(lineEdit.text())
            newValue = currentValue + increment
            lineEdit.setText(f"{newValue:.2f}")
        except ValueError:
            lineEdit.setText("0.0")

    def addControlWithButtons(self, layout, lineEdit, row, columnSpan):
        upButton = QPushButton("+")
        downButton = QPushButton("–")

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        upButton.setSizePolicy(sizePolicy)
        downButton.setSizePolicy(sizePolicy)

        upButton.setFixedSize(30, 25)
        downButton.setFixedSize(30, 25)

        def increment():
            lineEdit.setText(str(float(lineEdit.text()) + 1))

        def decrement():
            lineEdit.setText(str(float(lineEdit.text()) - 1))

        upButton.clicked.connect(increment)
        downButton.clicked.connect(decrement)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(upButton)
        buttonLayout.addWidget(downButton)

        container = QWidget()
        container.setLayout(buttonLayout)
        layout.addWidget(container, row, columnSpan)

    def initializeBuildingModel(self):
        """
        Initializes the building model with the current parameters from the UI inputs.
        
        This function validates the virtual heater settings and initializes the building model
        using the CalcParameters class. It also initializes temperature histories and logs the
        initialization status to the terminal.
        """
        if not self.validateVirtualHeaterSettings():
            self.logToTerminal("> Invalid virtual heater settings. Please check your inputs.", messageType="warning")
            return

        try:
            ambient_temp = float(self.ambientTempInput.text())
            default_q_design_e = 5500  # Default design heat power at -10°C
            q_design_e, t_flow_design, boostHeat = self.adjustDesignParameters(ambient_temp, default_q_design_e)
            mass_flow = max(self.currentMassFlow / 3600.0, 0.001)  # Convert from l/h to kg/s, ensure non-zero

            # Proper initialization of CalcParameters
            calc_params = CalcParameters(
                t_a=ambient_temp,
                q_design=q_design_e,
                t_flow_design=t_flow_design,
                mass_flow=mass_flow,
                boostHeat=boostHeat,
                maxPowBooHea=self.boostHeatPower,
                const_flow=True,  
                tau_b=209125, 
                tau_h=1957,
                t_b=20 
            )
            self.currentBuildingModel = calc_params.createBuilding()
            
            # Initialize temperature histories
            self.t_sup_history = []
            self.t_ret_history = [float(self.initialReturnTempInput.text())]  # Start with the initial return temperature

            self.startLoadingBar()
        except Exception as e:
            self.logToTerminal(f"> Failed to initialize building model: {e}", messageType="error")

    def tempToVoltage(self, temp):
        min_temp = 0
        max_temp = 100
        min_voltage = 0
        max_voltage = 5

        voltage = ((temp - min_temp) / (max_temp - min_temp)) * (max_voltage - min_voltage) + min_voltage

        correction_factor = 1
        corrected_voltage = voltage * correction_factor

        corrected_voltage = max(min(corrected_voltage, max_voltage), min_voltage)

        return corrected_voltage

    def adjustDesignParameters(self, ambient_temp, default_q_design_e):
        heat_pump_sizes = {
            -10: (1.0, 5500, 55),
            -7: (0.885, 5000, 52),
            2: (0.538, 7000, 42),
            7: (0.346, 10800, 36),
            12: (0.154, 24300, 30)
        }

        closest_temp = None
        for temp in sorted(heat_pump_sizes.keys()):
            if ambient_temp >= temp:
                closest_temp = temp
            else:
                break

        if closest_temp is None:
            closest_temp = min(heat_pump_sizes.keys())

        partLoadR, q_design, t_flow_design = heat_pump_sizes[closest_temp]

        new_q_design_e = q_design * partLoadR
        boostHeat = ambient_temp <= -10

        print(f"Ambient Temp: {ambient_temp}, Part Load Ratio: {partLoadR}, Default Design Heating Power: {new_q_design_e}, Target Flow Temp: {t_flow_design}")

        return new_q_design_e, t_flow_design, boostHeat

    def updateDisplay(self):
        try:
            if self.arduinoSerial and self.arduinoSerial.in_waiting:
                serialData = self.arduinoSerial.readline().decode('utf-8').strip()
                print(f"Received serial data: {serialData}")

                if ':' in serialData:
                    dataFields = serialData.split(',')
                    dataDict = {}
                    for field in dataFields:
                        if ':' in field:
                            key, value = field.split(':')
                            dataDict[key.strip()] = value.strip()

                    if 'STemp' in dataDict:
                        try:
                            t_sup = float(dataDict['STemp'])
                            self.updateBuildingModel(t_sup)
                            self.temperatureLabel.setText(f"{t_sup:.2f}°C")
                        except ValueError as e:
                            print(f"Error converting temperature: {e}")

                    if 'RTemp' in dataDict:
                        try:
                            t_ret_mea = float(dataDict['RTemp'])
                            self.t_ret_mea_history.append(t_ret_mea)
                            self.returnTemperatureLabel.setText(f"{t_ret_mea:.2f}°C")
                        except ValueError as e:
                            print(f"Error converting return temperature: {e}")

                    dacVoltage = dataDict.get('DACVolt', self.lastDACVoltage)
                    self.dacVoltageLabel.setText(f"{dacVoltage} V")
                    self.lastDACVoltage = dacVoltage
                    
                    if self.currentBuildingModel:
                        model_return_temp = self.currentBuildingModel.t_ret
                        if model_return_temp >= 0:
                            self.SPVoltageLabel.setText(f"{model_return_temp:.2f} °C")
                            self.lastSPtemp = model_return_temp
                        else:
                            self.SPVoltageLabel.setText("")
                    else:
                        model_return_temp = None  # Ensure model_return_temp is always defined

                    flowRate = dataDict.get('FlowRate', self.lastFlowRate)
                    self.flowRateLabel.setText(f"{flowRate} L/s")
                    self.lastFlowRate = flowRate

                    if 'FlowRate' in dataDict:
                        flowRateLPS = float(dataDict['FlowRate'])
                        self.currentMassFlow = flowRateLPS * 3600
                        self.flowRateLabel.setText(f"{flowRateLPS:.3f} L/s")

                        if self.currentBuildingModel:
                            q_hb = self.currentBuildingModel.q_dot_hb
                            q_ba = self.currentBuildingModel.q_dot_ba
                            q_hp = self.currentBuildingModel.q_dot_hp
                            q_int = self.currentBuildingModel.q_dot_int
                            q_bh = self.currentBuildingModel.q_dot_bh
                            t_b = self.currentBuildingModel.MassB.T

                        if self.currentBuildingModel:
                            self.addToSpreadsheet(
                                self.simulated_time.strftime('%H:%M:%S'), 
                                dataDict['STemp'], 
                                dacVoltage, 
                                model_return_temp if model_return_temp is not None else "N/A", 
                                flowRate, 
                                dataDict.get('RTemp', 'N/A'), 
                                q_hb, q_ba, q_hp, q_int, q_bh, t_b
                            )

                        self.simulated_time += timedelta(seconds=1)  # Increment simulated time by one second

                    self.updateGraph()

        except serial.SerialException as e:
            self.logToTerminal(f"> Error reading from serial: {e}", messageType="error")

    def updateSettings(self):
        """
        Validates and updates the virtual heater settings only when explicitly invoked by the user interaction with
        the 'Update Settings' button. This method checks the input validity, recalculates the necessary parameters,
        and updates the building model accordingly.
        """
        if not self.validateVirtualHeaterSettings():
            self.logToTerminal("> Validation of virtual heater settings failed.", messageType="warning")
            return

        try:
            ambient_temp = float(self.ambientTempInput.text())
            default_q_design_e = 5500  # Default design heat power at -10°C
            q_design_e, t_flow_design, boostHeat = self.adjustDesignParameters(ambient_temp, default_q_design_e)
            mass_flow = max(self.currentMassFlow / 3600.0, 0.001)  # Convert from L/h to kg/s to ensure non-zero mass flow

            # Recalculate parameters and update the building model
            calc_params = CalcParameters(
                t_a=ambient_temp,
                q_design=q_design_e,
                t_flow_design=t_flow_design,
                mass_flow=mass_flow,
                boostHeat=boostHeat,
                maxPowBooHea=self.boostHeatPower,
                const_flow=True,  
                tau_b=209125, 
                tau_h=1957,
                t_b=20 
            )
            self.currentBuildingModel = calc_params.createBuilding()

            # Log updated settings
            self.logToTerminal("> Settings updated successfully.", messageType="info")
        except Exception as e:
            self.logToTerminal(f"> Failed to update settings: {e}", messageType="error")

    def updateBuildingModel(self, new_t_sup, retry_count=3):
        if not hasattr(self, 't_sup_history'):
            self.t_sup_history = []
        if not hasattr(self, 't_ret_history'):
            self.t_ret_history = []
        if not hasattr(self, 't_ret_mea_history'):
            self.t_ret_mea_history = []

        self.t_sup_history.append(new_t_sup)

        # Use the latest measured return temperature if available
        last_t_ret_mea = self.t_ret_mea_history[-1] if self.t_ret_mea_history else new_t_sup - 5

        if self.currentBuildingModel is None:
            return

        try:
            mass_flow = max(self.currentMassFlow / 3600.0, 0.001)

            self.currentBuildingModel.doStep(
                t_sup=new_t_sup, 
                t_ret_mea=last_t_ret_mea, 
                m_dot=mass_flow, 
                stepSize=1, 
                q_dot_int=0 
            )

            new_t_ret = self.currentBuildingModel.t_ret

            if new_t_ret < 0:
                raise ValueError(f"Calculated return temperature is negative ({new_t_ret:.2f}°C).")

            self.t_ret_history.append(new_t_ret)

            dac_voltage = self.tempToVoltage(new_t_ret)
            self.sendSerialCommand(f"setVoltage {dac_voltage:.2f}")

        except Exception as e:
            self.logToTerminal(f"Failed to update building model: {e}", messageType="error")
            if retry_count > 0:
                self.logToTerminal(f"Retrying building model initialization... {retry_count} retries left", messageType="warning")
                # Avoid prompting for CSV save again during retries
                self.initializeBuildingModel()
                self.initButtonClicked(retry_count - 1)
            else:
                self.logToTerminal("Exceeded maximum retries for building model initialization.", messageType="error")
            
    def sendSerialCommand(self, command):
        if self.arduinoSerial and self.arduinoSerial.isOpen():
            self.arduinoSerial.write((command + '\n').encode()) 
        else:
            self.logToTerminal("> Error: Serial connection not established.", messageType="error")

    def sendArduinoCommand(self, commandType, value=None):
        if commandType in ['setVoltage', 'setTemp', 'setTolerance']:
            if value is not None:
                command = f"{commandType} {value}"
            else:
                print(f"Value required for command type: {commandType}")
                return
        elif commandType in ['activateVirtualHeater']:
            command = commandType
        else:
            print(f"Unknown command type: {commandType}")
            return
        
        self.sendSerialCommand(command)

    def initButtonClicked(self, retry_count):
        """
        Handles the initialization button click event.

        This function establishes the serial connection, starts the update timer,
        initializes the building model, and enables relevant UI components.
        """
        if self.arduinoSerial is None or not self.arduinoSerial.isOpen():
            try:
                self.arduinoSerial = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
                if self.hasBeenInitialized:
                    self.logToTerminal("> Serial connection re-established. System re-initialized.")
                else:
                    self.logToTerminal("> Serial connection established. System initialized.")
                    self.hasBeenInitialized = True
            except serial.SerialException as e:
                self.logToTerminal(f"> Error connecting to Arduino: {e}", messageType="error")
                return

        if not self.timer.isActive():
            self.timer.start(100)

        self.stopButton.setEnabled(True)
        self.virtualHeaterButton.setEnabled(True)
        self.dacVoltageInput.setEnabled(True)
        self.targetTempInput.setEnabled(True)
        self.toleranceInput.setEnabled(True)

        # Check if the CSV file path is already set before calling saveCSVFileDialog
        if not self.csv_file_path:
            self.saveCSVFileDialog()

        self.initializeBuildingModel()

        if retry_count < 3:
            self.logToTerminal(f"Retry successful.", messageType="info")

    def stopOperations(self):
        dacVoltage = 0
        self.sendSerialCommand(f"setVoltage {dacVoltage}")

        if self.timer.isActive():
            self.timer.stop()

        if self.arduinoSerial and self.arduinoSerial.isOpen():
            self.arduinoSerial.close()
            self.logToTerminal("> Serial connection closed.")

        self.updateButton.setEnabled(True)
        self.stopButton.setEnabled(True)
        self.virtualHeaterButton.setEnabled(False)
        self.dacVoltageInput.setEnabled(False)
        self.targetTempInput.setEnabled(False)
        self.toleranceInput.setEnabled(False)

    def createTerminal(self):
        terminal = QPlainTextEdit()
        terminal.setStyleSheet("""
            background-color: #1E1E1E; 
            color: #D4D4D4; 
            font-family: 'Verdana', monospace;
            font-size: 10pt;
            padding: 1px;
        """)
        terminal.setReadOnly(True)
        return terminal

    def logToTerminal(self, message, messageType="info"):
        messageStyles = {
            "info": "color: #FFFFFF;",
            "warning": "color: #E5C07B;",
            "error": "color: #E06C75;",
            "update": "color: #61AFEF;",
            "init": "color: #98C379;"
        }
        style = messageStyles.get(messageType, "color: #ABB2BF;")
        formattedMessage = f"<p style='{style}'>{message}</p>"
        self.terminal.appendHtml(formattedMessage)

    def saveCSVFileDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filePath, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv);;All Files (*)", options=options)
        
        # Ensure the file has a .csv extension
        if filePath and not filePath.endswith('.csv'):
            filePath += '.csv'

        if filePath:
            self.setCSVFilePath(filePath)
            self.logToTerminal(f"> CSV file set to save at: {filePath}")
            self.initCSVFile()  # Initialize CSV file with headers
        else:
            self.logToTerminal("> CSV file save canceled.", messageType="warning")

    def setCSVFilePath(self, file_path):
        self.csv_file_path = file_path
        self.csv_lock_path = file_path + ".lock"
        self.headers_written = False

    def initCSVFile(self):
        if not self.csv_file_path:
            self.logToTerminal("CSV file path not set.", messageType="error")
            return

        # Lock the file and open it in append mode
        self.csv_lock = FileLock(self.csv_lock_path)
        self.csv_lock.acquire()
        self.csv_file = open(self.csv_file_path, 'a', newline='', encoding='utf-8')
        self.csv_writer = csv.writer(self.csv_file)

        # Write headers if not already written
        if not self.headers_written:
            self.csv_writer.writerow(['Project Number', self.projectNumberInput.text()])
            self.csv_writer.writerow(['Client Name', self.clientNameInput.text()])
            self.csv_writer.writerow(['Date', self.dateInput.text()])
            self.csv_writer.writerow([])  # Empty row to separate the metadata from the column headers
            self.csv_writer.writerow([
                'Time', 'Supply Temperature', 'DAC Voltage', 'SP Temperature', 'Flow Rate',
                'Return Temperature', 'Heat Flow HB', 'Heat Flow BA', 'Heat Flow HP',
                'HF Internal Gains', 'HF Booster Heater', 'Building Temperature'
            ])
            self.headers_written = True

    def addToSpreadsheet(self, timestamp, temperature, dacVoltage, model_return_temp, flowRate, returnTemperature, q_hb, q_ba, q_hp, q_int, q_bh, t_b):
        try:
            temperature = float(temperature) if temperature != 'N/A' else None
            dacVoltage = float(dacVoltage) if dacVoltage != 'N/A' else None
            model_return_temp = float(model_return_temp) if model_return_temp != 'N/A' else None
            flowRate = float(flowRate) if flowRate != 'N/A' else None
            returnTemperature = float(returnTemperature) if returnTemperature != 'N/A' else None
            q_hb = float(q_hb) if q_hb != 'N/A' else None
            q_ba = float(q_ba) if q_ba != 'N/A' else None
            q_hp = float(q_hp) if q_hp != 'N/A' else None
            q_int = float(q_int) if q_int != 'N/A' else None
            q_bh = float(q_bh) if q_bh != 'N/A' else None
            t_b = float(t_b) if t_b != 'N/A' else None

            new_entry = [
                timestamp, temperature, dacVoltage, model_return_temp, flowRate, returnTemperature,
                q_hb, q_ba, q_hp, q_int, q_bh, t_b
            ]

            self.data_storage.append(new_entry)

            self.tableWidget.setRowCount(len(self.data_storage))
            for row, data in enumerate(self.data_storage):
                for col, value in enumerate(data):
                    if col == 0:  # Time column
                        item = QTableWidgetItem(value)
                    else:
                        item = QTableWidgetItem(f"{float(value):.3f}" if value is not None else 'N/A')
                    self.tableWidget.setItem(row, col, item)

            if self.csv_file_path:
                self.csv_buffer.append(new_entry)
                if len(self.csv_buffer) >= self.batch_size:
                    self.flushCSVBuffer()

            last_row_index = self.tableWidget.rowCount() - 1
            last_item = self.tableWidget.item(last_row_index, 0)
            if last_item:
                self.tableWidget.scrollToItem(last_item)

        except ValueError as e:
            self.logToTerminal(f"Error processing data for spreadsheet: {e}", messageType="error")

    def flushCSVBuffer(self):
        if not self.csv_file_path:
            self.logToTerminal("CSV file path not set.", messageType="error")
            return

        if not self.csv_lock_path:
            self.logToTerminal("CSV lock file path not set.", messageType="error")
            return

        if self.csv_writer:
            while self.csv_buffer:
                self.csv_writer.writerow(self.csv_buffer.popleft())
            self.csv_file.flush()

    def exportToCSV(self):
        if not self.csv_file_path:
            self.saveCSVFileDialog()

        if self.csv_file_path:
            try:
                self.finalizeLogging()
                if not self.headers_written:
                    self.csv_writer.writerow(['Project Number', self.projectNumberInput.text()])
                    self.csv_writer.writerow(['Client Name', self.clientNameInput.text()])
                    self.csv_writer.writerow(['Date', self.dateInput.text()])
                    self.csv_writer.writerow([])
                    headers = [self.tableWidget.horizontalHeaderItem(i).text() for i in range(self.tableWidget.columnCount())]
                    self.csv_writer.writerow(headers)
                    self.headers_written = True

                self.flushCSVBuffer()
                self.logToTerminal("> Data exported to CSV successfully.")
            except Exception as e:
                self.logToTerminal(f"> Failed to export data to CSV: {e}", messageType="error")
        else:
            self.logToTerminal("> CSV export canceled.", messageType="warning")

    def setupGraph(self):
        """
        Sets up the graph layout and axes.
        """
        # Increase the figure size (width, height)
        self.figure = Figure(figsize=(10, 18), facecolor='#282C34')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("QWidget {background-color: #282C34; color: #ABB2BF;}")

        # Create a 3-row subplot layout for different graphs with larger height and increased spacing
        gs = self.figure.add_gridspec(3, 1, height_ratios=[1, 1, 1], hspace=0.15, wspace=0.2)

        self.ax_temp = self.figure.add_subplot(gs[0, 0])  # Temperature graph
        self.ax_heat_flow = self.figure.add_subplot(gs[1, 0])  # Heat flow graph
        self.ax_building_temp = self.figure.add_subplot(gs[2, 0])  # Building temperature graph

        # Temperature graph
        self.ax_temp.set_title('Temperature Profile Over Time', color='#ABB2BF')
        self.ax_temp.set_xlabel('Time [hours]', color='#ABB2BF')
        self.ax_temp.set_ylabel('Temperature [°C]', color='#ABB2BF')
        self.ax_temp.tick_params(axis='x', colors='white')
        self.ax_temp.tick_params(axis='y', colors='white')
        self.ax_temp.grid(True, color='#4B4B4B')

        # Heat flow graph
        self.ax_heat_flow.set_title('Heat Flow Profile Over Time', color='#ABB2BF')
        self.ax_heat_flow.set_xlabel('Time [hours]', color='#ABB2BF')
        self.ax_heat_flow.set_ylabel('Heat Flow [W]', color='#ABB2BF')
        self.ax_heat_flow.tick_params(axis='x', colors='white')
        self.ax_heat_flow.tick_params(axis='y', colors='white')
        self.ax_heat_flow.grid(True, color='#4B4B4B')

        # Building temperature graph
        self.ax_building_temp.set_title('Building Temperature Over Time', color='#ABB2BF')
        self.ax_building_temp.set_xlabel('Time [hours]', color='#ABB2BF')
        self.ax_building_temp.set_ylabel('Temperature [°C]', color='#ABB2BF')
        self.ax_building_temp.tick_params(axis='x', colors='white')
        self.ax_building_temp.tick_params(axis='y', colors='white')
        self.ax_building_temp.grid(True, color='#4B4B4B')

        # Adding the canvas to the layout
        self.graphLayout.addWidget(self.canvas)
    
    def updateGraph(self):
        """
        Update the graphs with new data from the table widget.
        """
        # Clear previous plots
        self.ax_temp.clear()
        self.ax_heat_flow.clear()
        self.ax_building_temp.clear()

        # Set font properties for bold and larger text
        title_font = {'size': 20, 'weight': 'bold'}
        label_font = {'size': 12}
        tick_font = {'size': 10}
        legend_font = {'size': 10}

        # Set titles and labels with updated styles
        self.ax_temp.set_title('Two Mass Model Graph Outputs', color='white', fontdict=title_font)
        self.ax_temp.set_ylabel('Temperature [°C]', color='white', fontdict=label_font)
        self.ax_temp.tick_params(axis='x', colors='white', labelsize=tick_font['size'], width=2)
        self.ax_temp.tick_params(axis='y', colors='white', labelsize=tick_font['size'], width=2)
        self.ax_temp.grid(True, color='#ABB2BF')

        self.ax_heat_flow.set_ylabel('Heat Flow [W]', color='white', fontdict=label_font)
        self.ax_heat_flow.tick_params(axis='x', colors='white', labelsize=tick_font['size'], width=2)
        self.ax_heat_flow.tick_params(axis='y', colors='white', labelsize=tick_font['size'], width=2)
        self.ax_heat_flow.grid(True, color='#ABB2BF')

        self.ax_building_temp.set_xlabel('Time [hours]', color='white', fontdict=label_font)
        self.ax_building_temp.set_ylabel('Temperature [°C]', color='white', fontdict=label_font)
        self.ax_building_temp.tick_params(axis='x', colors='white', labelsize=tick_font['size'], width=2)
        self.ax_building_temp.tick_params(axis='y', colors='white', labelsize=tick_font['size'], width=2)
        self.ax_building_temp.grid(True, color='#ABB2BF')

        # Initialize data lists
        time_data, t_sup_data, t_ret_mea_data, t_b_data = [], [], [], []
        q_flow_hp_data, q_flow_hb_data, q_flow_ba_data, q_flow_int_data, q_flow_bh_data = [], [], [], [], []

        # Process each row in the table widget
        for row in range(self.tableWidget.rowCount()):
            time_item = self.tableWidget.item(row, 0)
            t_sup_item = self.tableWidget.item(row, 1)
            model_return_temp_item = self.tableWidget.item(row, 3)
            t_ret_mea_item = self.tableWidget.item(row, 5)
            q_flow_hb_item = self.tableWidget.item(row, 6)
            q_flow_ba_item = self.tableWidget.item(row, 7)
            q_flow_hp_item = self.tableWidget.item(row, 8)
            q_flow_int_item = self.tableWidget.item(row, 9)
            q_flow_bh_item = self.tableWidget.item(row, 10)
            t_b_item = self.tableWidget.item(row, 11)

            # Ensure items are not None before accessing text
            if all(item is not None for item in [time_item, t_sup_item, model_return_temp_item, t_ret_mea_item, q_flow_hb_item, q_flow_ba_item, q_flow_hp_item, q_flow_int_item, q_flow_bh_item, t_b_item]):
                try:
                    time_str = time_item.text()
                    # Ensure the time format includes milliseconds
                    if '.' in time_str:
                        time_data.append(date2num(datetime.strptime(time_str, '%H:%M:%S.%f')))
                    else:
                        time_data.append(date2num(datetime.strptime(time_str, '%H:%M:%S')))

                    t_sup_data.append(float(t_sup_item.text()))
                    t_ret_mea_data.append(float(t_ret_mea_item.text()))
                    q_flow_hp_data.append(float(q_flow_hp_item.text()))
                    q_flow_hb_data.append(float(q_flow_hb_item.text()))
                    q_flow_ba_data.append(float(q_flow_ba_item.text()))
                    q_flow_int_data.append(float(q_flow_int_item.text()))
                    q_flow_bh_data.append(float(q_flow_bh_item.text()))
                    t_b_data.append(float(t_b_item.text()))
                except ValueError as e:
                    print(f"Error converting table data: {e}")

        # Plot temperature data
        self.ax_temp.plot(time_data, t_sup_data, label='Supply Temperature (t_sup)', linestyle='-', color='tab:blue')
        self.ax_temp.plot(time_data, t_ret_mea_data, label='Return Temperature (t_ret_mea)', linestyle='--', color='tab:red')
        self.ax_temp.legend(loc='upper right', prop=legend_font)
        self.ax_temp.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))

        # Plot heat flow data
        self.ax_heat_flow.plot(time_data, q_flow_hp_data, label='Heat Flow HP to Transfer System (q_hp)', linestyle='-', color='tab:green')
        self.ax_heat_flow.plot(time_data, q_flow_hb_data, label='Heat Flow to Building (q_hb)', linestyle='-', color='tab:orange')
        self.ax_heat_flow.plot(time_data, q_flow_ba_data, label='Heat Flow Building to Ambient (q_ba)', linestyle='-', color='tab:purple')
        self.ax_heat_flow.plot(time_data, q_flow_int_data, label='Heat Flow Internal Gains to Building (q_int)', linestyle='-', color='tab:pink')
        self.ax_heat_flow.plot(time_data, q_flow_bh_data, label='Heat Flow Booster Heater to Heating System (q_bh)', linestyle='-', color='tab:brown')
        self.ax_heat_flow.legend(loc='upper right', prop=legend_font)
        self.ax_heat_flow.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))

        # Plot building temperature data
        self.ax_building_temp.plot(time_data, t_b_data, label='Building Temperature (t_b)', linestyle='-', color='tab:gray')
        self.ax_building_temp.legend(loc='upper right', prop=legend_font)
        self.ax_building_temp.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))

        # Update canvas
        self.canvas.draw()
        self.canvas.flush_events()
    
    def closeEvent(self, event):
        try:
            # Flush any remaining data to the CSV
            self.flushCSVBuffer()

            # Set DAC voltage to 0
            dacVoltage = 0
            self.sendSerialCommand(f"setVoltage {dacVoltage}")

            # Stop the timer if active
            if self.timer.isActive():
                self.timer.stop()

            # Close the serial connection if open
            if self.arduinoSerial and self.arduinoSerial.isOpen():
                self.arduinoSerial.close()
                self.logToTerminal("> Serial connection closed.")

            # Release the lock and close the file
            if hasattr(self, 'csv_lock') and self.csv_lock:
                self.csv_lock.release()
                self.csv_file.close()
                # Delete the lock file if it exists
                if os.path.exists(self.csv_lock_path):
                    os.remove(self.csv_lock_path)
                    self.logToTerminal("> CSV lock file deleted.")

            # Confirm application close with the user
            reply = QtWidgets.QMessageBox.question(
                self, 'Terminate Window', 'Are you sure you want to close the window?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No
            )

            if reply == QtWidgets.QMessageBox.Yes:
                event.accept()
            else:
                event.ignore()

        except Exception as e:
            self.logToTerminal(f"Error during close event: {e}", messageType="error")
            event.ignore()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    splash = show_splash_screen()
    applyOneDarkProTheme(app)
    mainWindow = MainWindow()
    mainWindow.show()
    splash.finish(mainWindow)
    sys.exit(app.exec_())
