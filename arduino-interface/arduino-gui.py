"""
    @Author: Amro Farag
    Date: March 2024
    Email: amro.farag@bregroup.com / amrihabfaraj@gmail.com
"""

import sys
import serial
import csv
import time
from bamLoadBasedTesting.twoMassModel import CalcParameters
from bamLoadBasedTesting.twoMassModel import TwoMassBuilding
from matplotlib.backends.backend_qt import MainWindow
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QPushButton, \
    QLineEdit, QGridLayout, QGroupBox, QHBoxLayout, QFrame, QPlainTextEdit, \
    QTabWidget, QTableWidget, QTableWidgetItem, QFileDialog
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap    
from PyQt5.QtCore import QTimer, Qt, QSize

# Arduino serial connection set-up
ARDUINO_PORT = 'COM4' # Hard-coded 
BAUD_RATE = 115200

# User-interface theme customization
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

# Serial connection initialization and pop-up window set-up
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.arduinoSerial = serial.Serial('COM4', 115200, timeout=1)
        
        # Define initial values for attributes used in the model
        self.currentAmbientTemperature = 0  
        self.currentMassFlow = 0.0 
        self.currentDesignHeatingPower = 0  
        self.currentFlowTemperatureDesign = 0 
        self.boostHeatPower = 6000  
        
        self.lastResistance = '0.00'
        self.lastDACVoltage = '0.00'
        self.lastSensorVoltage = '0.00'
        self.lastFlowRate = '0.00'

        # Initialize the update timer
        self.updateTimer = QTimer(self)
        self.updateTimer.timeout.connect(self.updateSettings)
        self.updateTimer.setInterval(1000)
        self.updateTimer.start() 

        self.logoLabel = None
        self.arduinoSerial = None
        self.timer = None
        self.time_data = []
        self.temperature_data = []
        self.flow_rate_data = []
        self.stopButton = None
        self.resistanceLabel = None
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

        # Create and initialize widgets
        self.dacVoltageInput = QtWidgets.QLineEdit()
        self.targetTempInput = QtWidgets.QLineEdit()
        self.toleranceInput = QtWidgets.QLineEdit()

        self.setWindowTitle("ArduinoUI")
        self.setupUI()
        applyOneDarkProTheme(QApplication.instance())

        self.arduinoSerial = None  # Initialize arduinoSerial attribute to None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateDisplay)
        self.timer.start(100)  # Refresh rate in milliseconds
        self.initSerialConnection() # Initialize serial connection with Arduino

        self.updateButton.setEnabled(True)
        self.stopButton.setEnabled(True)
        self.virtualHeaterButton.setEnabled(True)
        self.ssrHeaterButton.setEnabled(True)
        self.dacVoltageInput.setEnabled(False)
        self.targetTempInput.setEnabled(False)
        self.toleranceInput.setEnabled(False)

        self.updateTimer = QTimer(self)
        self.updateTimer.timeout.connect(self.handleNewData)
        self.hasBeenInitialized = False

    def initSerialConnection(self): 
            try:
                self.arduinoSerial = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
                self.logToTerminal("> Serial connection established. System initialized.")
            except serial.SerialException as e:
                self.logToTerminal(f"> Error connecting to Arduino: {e}", messageType="error")

    def setupUI(self):
        self.setFont(QFont("Verdana", 12))
        tabWidget = QTabWidget(self)  # Ensure the tab widget is properly parented to the main window

        self.setMinimumSize(1000, 1000)  # Set a minimum size to avoid resizing issues

        # Logo Setup
        self.logoLabel = QLabel()
        logoPixmap = QPixmap("Arduino Controller.png")
        scaledLogoPixmap = logoPixmap.scaled(700, 500, Qt.KeepAspectRatio)
        self.logoLabel.setPixmap(scaledLogoPixmap)
        self.logoLabel.setAlignment(Qt.AlignCenter)

        # Controls Tab
        controlsTab = QWidget()
        controlsLayout = QVBoxLayout()
        controlsLayout.addWidget(self.logoLabel)
        self.measurementGroup = self.createMeasurementGroup()
        self.controlGroup = self.createControlGroup()
        self.terminal = self.createTerminal()
        controlsLayout.addWidget(self.measurementGroup)
        controlsLayout.addWidget(self.controlGroup)
        controlsLayout.addWidget(self.terminal, 1)  # Give terminal some stretch factor
        controlsTab.setLayout(controlsLayout)

        # Data Spreadsheet Tab
        spreadsheetTab = QWidget()
        spreadsheetLayout = QVBoxLayout(spreadsheetTab)  # Parent the layout to the tab

        # Frame for the table
        tableFrame = QFrame()
        tableLayout = QVBoxLayout()
        tableFrame.setLayout(tableLayout)

        # Header Section for Spreadsheet Tab
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
        self.exportCSVButton.setStyleSheet("font-size: 11pt;")
        
        headerLayout.addWidget(self.projectNumberInput)
        headerLayout.addWidget(self.clientNameInput)
        headerLayout.addWidget(self.dateInput)
        headerLayout.addWidget(self.exportCSVButton)

        tableLayout.addLayout(headerLayout)

        # Table Widget for Spreadsheet Tab
        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(7)
        self.tableWidget.setHorizontalHeaderLabels(["Time", "Temperature", "Resistance", "DAC Voltage", "Sensor Voltage", "Flow Rate", "Return Temperature"])

        # Table Widget for Spreadsheet Tab
        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(7)
        self.tableWidget.setHorizontalHeaderLabels(["Time", "Temperature", "Resistance", "DAC Voltage", "Sensor Voltage", "Flow Rate", "Return Temperature"])

        # Set the width of each column in the table
        self.tableWidget.setColumnWidth(0, 200)  # Time
        self.tableWidget.setColumnWidth(1, 200)  # Temperature
        self.tableWidget.setColumnWidth(2, 200)  # Resistance
        self.tableWidget.setColumnWidth(3, 200)  # DAC Voltage
        self.tableWidget.setColumnWidth(4, 200)  # Sensor Voltage
        self.tableWidget.setColumnWidth(5, 200)  # Flow Rate
        self.tableWidget.setColumnWidth(6, 200) 


        self.tableWidget.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: #282C34;
                color: #ABB2BF;
                gridline-color: #3B4048;
                selection-background-color: #3E4451;
                selection-color: #ABB2BF;
                font-size: 12pt; /* Increase font size */
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #3B4048;
                color: #ABB2BF;
                padding: 5px;
                border: 1px solid #282C34;
                font-size: 11pt;
                font-family: 'Verdana';
            }
        """)

        tableLayout.addWidget(self.tableWidget)
        spreadsheetLayout.addWidget(tableFrame)
        spreadsheetTab.setLayout(spreadsheetLayout)

        # Graph Tab
        graphTab = QWidget()
        graphLayout = QVBoxLayout(graphTab)

        # Set up the matplotlib Figure and its background
        self.figure = Figure(facecolor='#282C34')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("QWidget {background-color: #282C34; color: #ABB2BF;}")

        graphLayout.addWidget(self.canvas)
        tabWidget.addTab(controlsTab, "Controls Monitor")
        tabWidget.addTab(spreadsheetTab, "Data Spreadsheet")
        tabWidget.addTab(graphTab, "Temperature Graph")

        self.setCentralWidget(tabWidget)

        # Reapply the One Dark Pro theme to ensure it covers all elements
        applyOneDarkProTheme(QApplication.instance())

    def createMeasurementGroup(self):
        group = QGroupBox("Instructions and Real-time Measurements")
        group.setFont(QFont("Verdana", 11, QFont.Bold))

        # Main horizontal layout for the group
        mainLayout = QHBoxLayout(group)

        # Left side layout for instructions
        instructionsLayout = QVBoxLayout()
        instructionsLabel = QLabel("""
        <p>
        1. The <span style='color: #98C379;'>Initialize</span> button must be clicked to re-activate all Arduino components if operations are stopped.<br>
        2. The control parameters and building model are initialized & updated when the <span style='color: #61AFEF;'>Update Settings</span> button is clicked.<br>
        3. The <span style='color: #E06C75;'>Stop</span> button will halt all operations. Re-initialization is required if testing to be resumed.<br><br>
        For clarification please consult the github repo documentation: github.com/amroscript/arduino-hp-controller.
        </p>
        """)
        instructionsLabel.setFont(QFont("Verdana", 11))
        instructionsLayout.addWidget(instructionsLabel)

        # Vertical line for separation
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #3B4048")

        mainLayout.addLayout(instructionsLayout)
        mainLayout.addWidget(line)

        # Right side layout for real-time data
        dataLayout = QGridLayout()

        # Define a uniform font for all labels and data labels
        uniform_font = QFont("Verdana", 11)
        uniform_font.setBold(True)

        # Create labels for the data categories
        temperatureLabel = QLabel("↻ Temperature:")
        resistanceLabel = QLabel("Resistance:")
        dacVoltageLabel = QLabel("⇈ DAC Voltage:")
        sensorVoltageLabel = QLabel("Sensor Voltage:")
        flowRateLabel = QLabel("↻ Flow Rate:")

        # Apply the uniform font to the category labels
        for label in [temperatureLabel, resistanceLabel, dacVoltageLabel, sensorVoltageLabel, flowRateLabel]:
            label.setFont(uniform_font)

        # Initialize the data labels with default values
        self.temperatureLabel = QLabel("0°C")
        self.resistanceLabel = QLabel("0Ω")
        self.dacVoltageLabel = QLabel("0V")
        self.sensorVoltageLabel = QLabel("0V")
        self.flowRateLabel = QLabel("0L/s")

        # Apply the uniform font to the data labels
        for data_label in [self.temperatureLabel, self.resistanceLabel, self.dacVoltageLabel, self.sensorVoltageLabel, self.flowRateLabel]:
            data_label.setFont(uniform_font)

        # Add the labels and data labels to the layout
        dataLayout.addWidget(temperatureLabel, 1, 0)
        dataLayout.addWidget(self.temperatureLabel, 1, 1)
        dataLayout.addWidget(resistanceLabel, 0, 0)
        dataLayout.addWidget(self.resistanceLabel, 0, 1)
        dataLayout.addWidget(sensorVoltageLabel, 2, 0)
        dataLayout.addWidget(self.sensorVoltageLabel, 2, 1)
        dataLayout.addWidget(flowRateLabel, 3, 0)
        dataLayout.addWidget(self.flowRateLabel, 3, 1)
        dataLayout.addWidget(dacVoltageLabel, 4, 0)
        dataLayout.addWidget(self.dacVoltageLabel, 4, 1)

        mainLayout.addLayout(dataLayout)

        return group

    def createControlGroup(self):
            group = QGroupBox("Heater Mode Settings")
            group.setFont(QFont("Verdana", 11, QFont.Bold))
            layout = QVBoxLayout(group)

            # Heater Mode Buttons Setup 
            heaterButtonLayout = QHBoxLayout()
            self.ssrHeaterButton = QPushButton("Solid State Relay Heater")
            self.virtualHeaterButton = QPushButton("BAM Two Mass Model")

            for btn in [self.ssrHeaterButton, self.virtualHeaterButton]:
                btn.setCheckable(True)
                btn.setFixedHeight(31)  # Set a fixed height for a consistent look
                self.ssrHeaterButton.toggled.connect(self.updateHeaterButtonState)
                self.virtualHeaterButton.toggled.connect(self.updateHeaterButtonState)
                heaterButtonLayout.addWidget(btn)

            # Initial Button States
            self.ssrHeaterButton.setChecked(False)
            self.virtualHeaterButton.setChecked(False)

            self.ssrSettingsGroup = self.createSSRSettingsGroup()
            self.virtualHeaterSettingsGroup = self.createVirtualHeaterSettingsGroup()

            self.updateHeaterButtonState()  # Initialize the button states

            settingsLayout = QHBoxLayout()
            settingsLayout.addWidget(self.ssrSettingsGroup)
            settingsLayout.addWidget(self.virtualHeaterSettingsGroup)

            # Initialize, Stop, and Update Settings Buttons setup
            buttonLayout = QHBoxLayout()
            self.initButton = QPushButton("Initialize")
            self.stopButton = QPushButton("Stop")
            self.updateButton = QPushButton("Update Settings")
            
            for btn in [self.initButton, self.updateButton, self.stopButton]:
                btn.setFixedHeight(31)
                buttonLayout.addWidget(btn)

            # Compose the final layout
            layout.addLayout(heaterButtonLayout)
            layout.addLayout(settingsLayout)
            layout.addLayout(buttonLayout)

            # Apply button styles and connect signals
            self.applyButtonStyles()
            self.initButton.clicked.connect(self.initButtonClicked)
            self.stopButton.clicked.connect(self.stopOperations)
            self.updateButton.clicked.connect(self.updateSettings)

            group.setLayout(layout)
            return group
    
    def validateVirtualHeaterSettings(self):
        """
        Validates the input settings for the virtual heater to ensure they are within acceptable ranges.
        Returns True if all settings are valid, False otherwise.
        """
        try:
            ambient_temp = float(self.ambientTempInput.text())  # Get ambient temperature from user input
            q_design_e = float(self.designHeatingPowerInput.text())  # Get design heating power from user input
            t_start_h = float(self.initialReturnTempInput.text())  # Get initial return temperature from user input

            # Validate the converted values are within expected ranges
            if not -40 <= ambient_temp <= 40:
                self.logToTerminal("Ambient temperature out of expected range: -40 to 40°C", messageType="warning")
                return False
            if q_design_e <= 0:
                self.logToTerminal("Design heating power must be greater than 0.", messageType="warning")
                return False
            if not 10 <= t_start_h <= 90:  # Adjusted upper limit to 90°C
                self.logToTerminal("Initial return temperature out of expected range: 10 to 90°C", messageType="warning")
                return False

            return True  # If all checks pass, the settings are valid
        except ValueError:
            # If any conversion fails, log the failure and return False
            self.logToTerminal("Invalid input: Please check that all fields contain numeric values.", messageType="warning")
            return False

    def updateHeaterButtonState(self):
        # Define active and inactive styles for cleaner code
        activeStyle = "QGroupBox { font: 8pt; font-weight: bold; color: #98C379; }"  # Green
        inactiveStyle = "QGroupBox { font: 8pt; font-weight: bold; color: #E06C75; }"  # Red
        
        # Update SSR Heater group box
        if self.ssrHeaterButton.isChecked():
            self.ssrSettingsGroup.setTitle("SSR Heater: Activated")
            self.ssrSettingsGroup.setStyleSheet(activeStyle)
        else:
            self.ssrSettingsGroup.setTitle("SSR Heater: Off")
            self.ssrSettingsGroup.setStyleSheet(inactiveStyle)
        
        # Update Virtual Heater group box
        if self.virtualHeaterButton.isChecked():
            self.virtualHeaterSettingsGroup.setTitle("BAM Model: Activated")
            self.virtualHeaterSettingsGroup.setStyleSheet(activeStyle)
        else:
            self.virtualHeaterSettingsGroup.setTitle("Virtual Heater: Off")
            self.virtualHeaterSettingsGroup.setStyleSheet(inactiveStyle)
        
        # Refresh UI components to apply styles immediately
        self.ssrSettingsGroup.style().unpolish(self.ssrSettingsGroup)
        self.ssrSettingsGroup.style().polish(self.ssrSettingsGroup)
        self.virtualHeaterSettingsGroup.style().unpolish(self.virtualHeaterSettingsGroup)
        self.virtualHeaterSettingsGroup.style().polish(self.virtualHeaterSettingsGroup)
            
    def createSSRSettingsGroup(self):
        group = QGroupBox("SSR Heater Settings")
        group.setFont(QFont("Verdana", 10, QFont.Bold))
        layout = QGridLayout()

        self.targetTempInput = QLineEdit("23")
        self.addSettingWithButtons(layout, "Target Temperature (°C):", self.targetTempInput, 0, font_size= 10.5)

        self.toleranceInput = QLineEdit("0.2")
        self.addSettingWithButtons(layout, "Temperature Tolerance (±°C):", self.toleranceInput, 1, font_size= 10.5)

        self.dacVoltageInput = QLineEdit("2.5")
        self.addSettingWithButtons(layout, "DAC Voltage Output (V):", self.dacVoltageInput, 2, font_size= 10.5)

        group.setLayout(layout)
        return group

    def createVirtualHeaterSettingsGroup(self):
        """
        Create a group box for Virtual Heater settings with inputs for ambient temperature,
        design heating power, and initial return temperature including increment/decrement buttons.
        """
        group = QGroupBox("Virtual Heater Settings")
        group.setFont(QFont("Verdana", 10, QFont.Bold))
        layout = QGridLayout()

        # Inputs
        self.ambientTempInput = QLineEdit("7")
        self.addSettingWithButtons(layout, "Ambient Temperature (°C):", self.ambientTempInput, 0, font_size=10.5)
        
        self.designHeatingPowerInput = QLineEdit("3750")
        self.addSettingWithButtons(layout, "Design Heating Power (W):", self.designHeatingPowerInput, 1, font_size=10.5)

        self.initialReturnTempInput = QLineEdit("30.0")  
        self.addSettingWithButtons(layout, "Initial Return Temperature (°C):", self.initialReturnTempInput, 2, font_size=10.5)

        group.setLayout(layout)
        return group
    
    def applyButtonStyles(self):
        buttonFontSize = "8pt" 

        # Initialize, Update, and Stop Buttons
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
        # Define active and inactive styles for cleaner code
        activeStyle = "QGroupBox { font: 8pt; font-weight: bold; color: #98C379; }"  # Green
        inactiveStyle = "QGroupBox { font: 8pt; font-weight: bold; color: #E06C75; }"  # Red
        
        # Update SSR Heater group box
        if self.ssrHeaterButton.isChecked():
            self.ssrSettingsGroup.setTitle("SSR HEATER ACTIVATED")
            self.ssrSettingsGroup.setStyleSheet(activeStyle)
            # Enable the QLineEdit widgets for SSR Heater settings
            self.targetTempInput.setEnabled(True)
            self.toleranceInput.setEnabled(True)
            self.dacVoltageInput.setEnabled(True)
        else:
            self.ssrSettingsGroup.setTitle("SSR HEATER OFF")
            self.ssrSettingsGroup.setStyleSheet(inactiveStyle)
            # Disable the QLineEdit widgets when SSR Heater is off
            self.targetTempInput.setEnabled(False)
            self.toleranceInput.setEnabled(False)
            self.dacVoltageInput.setEnabled(False)
            # Reset DAC Voltage Input to 0 when the heater is turned off
            self.dacVoltageInput.setText("0")

        # Update Virtual Heater group box
        if self.virtualHeaterButton.isChecked():
            self.virtualHeaterSettingsGroup.setTitle("BAM MODEL ACTIVATED")
            self.virtualHeaterSettingsGroup.setStyleSheet(activeStyle)
            # Enable the QLineEdit widgets for Virtual Heater settings
            self.ambientTempInput.setEnabled(True)
            self.designHeatingPowerInput.setEnabled(True)
            self.initialReturnTempInput.setEnabled(True)
        else:
            self.virtualHeaterSettingsGroup.setTitle("BAM MODEL OFF")
            self.virtualHeaterSettingsGroup.setStyleSheet(inactiveStyle)
            # Disable the QLineEdit widgets when Virtual Heater is off
            self.ambientTempInput.setEnabled(False)
            self.designHeatingPowerInput.setEnabled(False)
            self.initialReturnTempInput.setEnabled(False)
        
        # Refresh UI components to apply styles immediately
        self.ssrSettingsGroup.style().unpolish(self.ssrSettingsGroup)
        self.ssrSettingsGroup.style().polish(self.ssrSettingsGroup)
        self.virtualHeaterSettingsGroup.style().unpolish(self.virtualHeaterSettingsGroup)
        self.virtualHeaterSettingsGroup.style().polish(self.virtualHeaterSettingsGroup)

    def addSettingWithButtons(self, layout, labelText, lineEdit, row, font_size=10):
        label = QLabel(labelText)
        label.setFont(QFont("Verdana", int(font_size)))
        layout.addWidget(label, row, 0)

        # Increment/Decrement buttons
        upButton = QPushButton("+")
        downButton = QPushButton("-")
        upButton.setFont(QFont("Verdana", int(font_size)))
        downButton.setFont(QFont("Verdana", int(font_size)))

        # Set a fixed size for the buttons
        buttonSize = QSize(30, 30)
        upButton.setFixedSize(buttonSize)
        downButton.setFixedSize(buttonSize)

        # Connect buttons to increment/decrement actions
        upButton.clicked.connect(lambda: self.adjustValue(lineEdit, 1))
        downButton.clicked.connect(lambda: self.adjustValue(lineEdit, -1))

        lineEdit.setMinimumSize(QSize(100, 30))  # Adjusted size to make room for buttons
        lineEdit.setFont(QFont("Verdana", int(font_size)))
        lineEdit.setEnabled(True)  # Ensure the line edit is enabled

        # Create a layout for buttons and line edit
        controlLayout = QHBoxLayout()
        controlLayout.addWidget(lineEdit)
        controlLayout.addWidget(upButton)
        controlLayout.addWidget(downButton)

        # Set alignment and add the container to the grid layout
        controlContainer = QWidget()
        controlContainer.setLayout(controlLayout)
        layout.addWidget(controlContainer, row, 1, 1, 2)  # Span 2 columns

    def adjustValue(self, lineEdit, increment):
        try:
            currentValue = float(lineEdit.text())
            newValue = currentValue + increment
            lineEdit.setText(f"{newValue:.2f}")
        except ValueError:
            # Handle error if the line edit does not contain a valid number
            lineEdit.setText("0.0")

    def toggleHeaterMode(self, isSSRHeaterActive):
        self.ssrHeaterButton.setChecked(isSSRHeaterActive)
        self.virtualHeaterButton.setChecked(not isSSRHeaterActive)
        self.updateHeaterButtons(isSSRHeaterActive)

        if isSSRHeaterActive:
            # SSR Heater is activated
            self.ssrSettingsGroup.setTitle("ACTIVATED")
            self.ssrSettingsGroup.setStyleSheet("QGroupBox { font: 10pt; font-weight: bold; color: #98C379; }")  
        else:
            # SSR Heater is off, meaning Virtual Heater is activated
            self.ssrSettingsGroup.setTitle("                                                                                                                                                                                                                            OFF")
            self.ssrSettingsGroup.setStyleSheet("QGroupBox { font: 10pt; font-weight: bold; color: #E06C75; }")  

        # Ensure currentMassFlow is not zero before initializing CalcParameters
        if self.currentMassFlow > 0:  # Check to ensure we have a valid mass flow
            if not isSSRHeaterActive:
                # Proceed with creating the building model only if we have valid data
                self.currentBuildingModel = CalcParameters(
                    t_a=self.currentAmbientTemperature, 
                    q_design=self.currentDesignHeatingPower,
                    t_flow_design=self.currentFlowTemperatureDesign,
                    mass_flow=self.currentMassFlow,
                    boostHeat=True, 
                    maxPowBooHea=self.boostHeatPower
                ).createBuilding()
                print("Virtual heater activated.")
            else:
                print("Virtual heater deactivated.")
        else:
            print("Mass flow data is not yet available. Delaying model initialization.")

    def addControlWithButtons(self, layout, lineEdit, row, columnSpan):
        upButton = QPushButton("+")
        downButton = QPushButton("–")

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        upButton.setSizePolicy(sizePolicy)
        downButton.setSizePolicy(sizePolicy)

        # Set fixed sizes for buttons
        upButton.setFixedSize(30, 25)  # Adjust width and height
        downButton.setFixedSize(30, 25)  # Adjust width and height


        def increment():
            lineEdit.setText(str(float(lineEdit.text()) + 1))

        def decrement():
            lineEdit.setText(str(float(lineEdit.text()) - 1))

        upButton.clicked.connect(increment)
        downButton.clicked.connect(decrement)

        # Button layout adjustment
        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(upButton)
        buttonLayout.addWidget(downButton)

        container = QWidget()
        container.setLayout(buttonLayout)
        layout.addWidget(container, row, columnSpan)

    def initializeBuildingModel(self):
        if not self.validateVirtualHeaterSettings():
            self.logToTerminal("> Invalid virtual heater settings. Please check your inputs.", messageType="warning")
            return

        try:
            ambient_temp = float(self.ambientTempInput.text())
            default_q_design_e = 3750  # Default design heat power at -10°C
            q_design_e, t_flow_design, boostHeat = self.adjustDesignParameters(ambient_temp, default_q_design_e)
            mass_flow = max(self.currentMassFlow / 3600.0, 0.001)  # Convert from l/h to kg/s, ensure non-zero
            print(f"Initializing Building Model with Ambient Temp: {ambient_temp}, Design Heating Power: {q_design_e}, Mass Flow: {mass_flow:.3f} kg/s")
        except ValueError as ve:
            self.logToTerminal(f"> Error in input conversion: {ve}", messageType="error")
            return

        if mass_flow <= 0.001:
            self.logToTerminal("> Mass flow is zero or negative, which is invalid.", messageType="error")
            return

        boostHeat = self.boostHeatPower
        tau_b = 209125 
        tau_h = 1957
        t_b = 20

        try:
            calc_params = CalcParameters(
                t_a=ambient_temp,
                q_design=q_design_e,
                t_flow_design=t_flow_design,
                mass_flow=mass_flow,
                boostHeat=boostHeat,
                maxPowBooHea=self.boostHeatPower,
                const_flow=True,  
                t_b=t_b,
                tau_b=tau_b,  
                tau_h=tau_h   
            )
            self.currentBuildingModel = calc_params.createBuilding()
            self.logToTerminal("> Building model initialized with current parameters.", messageType="info")
        except Exception as e:
            self.logToTerminal(f"> Failed to initialize building model: {e}", messageType="error")


    def tempToVoltage(self, temp):
        # Conversion logic parameters
        min_temp = 0
        max_temp = 100
        min_voltage = 0
        max_voltage = 5

        # Calculate the initial voltage from the temperature
        voltage = ((temp - min_temp) / (max_temp - min_temp)) * (max_voltage - min_voltage) + min_voltage

        # Apply the correction factor from Arduino script
        correction_factor = 1
        corrected_voltage = voltage * correction_factor

        # Ensure correctedVoltage is within the DAC's allowable range
        corrected_voltage = max(min(corrected_voltage, max_voltage), min_voltage)  # Clamp to range 0-5V

        return corrected_voltage

    def adjustDesignParameters(self, ambient_temp, default_q_design_e):
        # Map outside temperatures to their respective part load ratio and design sizes
        heat_pump_sizes = {
            -10: (1.0, 3750, 55),
            -7: (0.885, 4240, 52),
            2: (0.538, 7000, 42),
            7: (0.346, 10800, 36),
            12: (0.154, 24300, 30)
        }

        # Find the closest temperature threshold less than or equal to the ambient temperature
        closest_temp = None
        for temp in sorted(heat_pump_sizes.keys()):
            if ambient_temp >= temp:
                closest_temp = temp
            else:
                break

        if closest_temp is None:
            closest_temp = min(heat_pump_sizes.keys())  # Default to lowest if all thresholds are higher

        # Get settings for the closest or default temperature threshold
        partLoadR, q_design, t_flow_design = heat_pump_sizes[closest_temp]

        new_q_design_e = q_design * partLoadR
        boostHeat = ambient_temp <= -10  # Boost heating only if very cold

        print(f"Ambient Temp: {ambient_temp}, Part Load Ratio: {partLoadR}, New Design Heating Power: {new_q_design_e}, Target Flow Temp: {t_flow_design}")

        return new_q_design_e, t_flow_design, boostHeat


    def updateDisplay(self):
        try:
            if self.arduinoSerial and self.arduinoSerial.in_waiting:
                serialData = self.arduinoSerial.readline().decode('utf-8').strip()
                print(f"Received serial data: {serialData}")  # Debug print

                if ':' in serialData:
                    dataFields = serialData.split(',')
                    dataDict = {}
                    for field in dataFields:
                        key, value = field.split(':')
                        dataDict[key.strip()] = value.strip()

                    if 'Temp' in dataDict:
                        try:
                            t_sup = float(dataDict['Temp'])
                            self.updateBuildingModel(t_sup)
                            self.temperatureLabel.setText(f"{t_sup:.2f}°C")
                        except ValueError:
                            print(f"Error converting temperature to float: {dataDict['Temp']}")

                    # Update and display resistance
                    resistance = dataDict.get('Res', self.lastResistance)
                    self.lastResistance = resistance
                    self.resistanceLabel.setText(resistance + " Ω")

                    # Update and display DAC voltage
                    dacVoltage = dataDict.get('DACVolt', self.lastDACVoltage)
                    self.lastDACVoltage = dacVoltage
                    self.dacVoltageLabel.setText(dacVoltage + " V")

                    # Update and display sensor voltage
                    sensorVoltage = dataDict.get('SensorVolt', self.lastSensorVoltage)
                    self.lastSensorVoltage = sensorVoltage
                    self.sensorVoltageLabel.setText(sensorVoltage + " V")

                    # Update and display flow rate
                    flowRate = dataDict.get('FlowRate', self.lastFlowRate)
                    self.lastFlowRate = flowRate
                    self.flowRateLabel.setText(flowRate + " L/s")

                    if 'FlowRate' in dataDict:
                        try:
                            flowRateLPS = float(dataDict['FlowRate'])
                            self.currentMassFlow = flowRateLPS * 3600  # Convert to L/h
                            self.flowRateLabel.setText(f"{flowRateLPS:.3f} L/s")
                            if self.currentBuildingModel:
                                self.addToSpreadsheet(time.strftime("%H:%M:%S", time.localtime()), dataDict['Temp'], resistance, dacVoltage, sensorVoltage, flowRate, self.currentBuildingModel.t_ret)
                        except ValueError:
                            print(f"Error converting flow rate to float: {dataDict['FlowRate']}")

        except serial.SerialException as e:
            self.logToTerminal(f"> Error reading from serial: {e}", messageType="error")

    def handleNewData(self, time, temperature, flowRate):
        """
        Handles incoming new data by appending it to the respective lists.

        This method is called whenever new data points for time, temperature,
        and flow rate are received, ensuring that all relevant data is stored
        sequentially for further processing or display.

        :param time: The timestamp associated with the new data point.
        :param temperature: The temperature value of the new data point.
        :param flowRate: The flow rate value of the new data point.
        """
        self.time_data.append(time)
        self.temperature_data.append(temperature)
        self.flow_rate_data.append(flowRate)

    def initButtonClicked(self):
        if self.arduinoSerial is None or not self.arduinoSerial.isOpen():
            try:
                self.arduinoSerial = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
                # Check if the system has been initialized before
                if self.hasBeenInitialized:
                    self.logToTerminal("> Serial connection re-established. System re-initialized.")
                else:
                    self.logToTerminal("> Serial connection established. System initialized.")
                    # Set the flag to True after the first initialization
                    self.hasBeenInitialized = True
            except serial.SerialException as e:
                self.logToTerminal(f"> Error connecting to Arduino: {e}", messageType="error")
                return  # Early return if connection fails

        # Restart the QTimer for regular updates
        if not self.timer.isActive():
            self.timer.start(100)  # Adjust the interval as necessary

        # Enable buttons upon initialization
        self.stopButton.setEnabled(True)
        self.virtualHeaterButton.setEnabled(True)
        self.ssrHeaterButton.setEnabled(True)
        self.dacVoltageInput.setEnabled(True)
        self.targetTempInput.setEnabled(True)
        self.toleranceInput.setEnabled(True)

    def updateSettings(self):
        if not self.validateVirtualHeaterSettings():
            self.logToTerminal("> Validation of virtual heater settings failed.", messageType="warning")
            return

        try:
            ambient_temp = float(self.ambientTempInput.text())
            default_q_design_e = 3750  # Default design heat power at -10°C
            q_design_e, t_flow_design, boostHeat = self.adjustDesignParameters(ambient_temp, default_q_design_e)
            mass_flow = max(self.currentMassFlow / 3600.0, 0.001)  # Convert from L/h to kg/s to ensure non-zero mass flow

            # Recalculate parameters and update the building model
            self.currentBuildingModel = CalcParameters(
                t_a=ambient_temp,
                q_design=q_design_e,
                t_flow_design=t_flow_design,
                mass_flow=mass_flow,
                boostHeat=boostHeat,
                maxPowBooHea=self.boostHeatPower
            ).createBuilding()

            # Log updated settings
            print(f"Current t_ret: {self.currentBuildingModel.t_ret:.2f}°C, Mass flow: {mass_flow:.3f} kg/s")
        except Exception as e:
            self.logToTerminal(f"> Failed to update settings: {e}", messageType="error")

    def parseSerialData(self, data):
        data_fields = data.split(',')
        data_dict = {}
        for field in data_fields:
            try:
                key, value = field.split(':')
                data_dict[key.strip()] = value.strip()
            except ValueError:
                print(f"Error parsing field: {field}. Expected format 'key:value'.")
        return data_dict

                
    def updateBuildingModel(self, t_sup):
        if not self.validateVirtualHeaterSettings():
            self.logToTerminal("> Invalid settings for virtual heater. Please check your inputs.", messageType="error")
            return

        if self.currentBuildingModel is None:
            self.logToTerminal("No building model available. Please initialize the model.", messageType="warning")
            return

        try:
            # Ensure the mass flow is a valid number
            mass_flow = max(self.currentMassFlow / 3600.0, 0.001)  # Convert L/h to kg/s and ensure it's not zero

            # self.logToTerminal(f"Updating model with t_sup={t_sup:.2f}°C and mass flow={mass_flow:.3f} kg/s", messageType="update")

            # Perform model update step
            self.currentBuildingModel.doStep(
                t_sup=t_sup,
                t_ret_mea=self.currentBuildingModel.t_ret,
                m_dot=mass_flow,
                stepSize=1
            )

            # Retrieve and log the new return temperature
            new_return_temp = self.currentBuildingModel.t_ret
            self.temperatureLabel.setText(f"Updated t_ret: {new_return_temp:.2f}°C")  # UI feedback

            # Convert temperature to voltage for DAC output
            dac_voltage = self.tempToVoltage(new_return_temp)
            self.sendSerialCommand(f"setVoltage {dac_voltage:.2f}")
            # self.logToTerminal(f"Model updated: New t_ret={new_return_temp:.2f}°C, DAC Voltage set to {dac_voltage:.2f}V", messageType="info")
            
        except Exception as e:
            self.logToTerminal(f"> Failed to update building model: {e}", messageType="error")

            
    def sendSerialCommand(self, command):
        """
        Sends a command to the Arduino via the established serial connection.

        :param command: The command string to be sent to the Arduino.
        """
        if self.arduinoSerial and self.arduinoSerial.isOpen():
            # If the serial connection is open, encode and send the command with a newline character.
            self.arduinoSerial.write((command + '\n').encode()) 
        else:
            # If the serial connection is not established, log an error message.
            self.logToTerminal("> Error: Serial connection not established.", messageType="error")

    def sendArduinoCommand(self, commandType, value=None):
        """
        Send a command to the Arduino based on the command type and value.
        
        Parameters:
        - commandType: A string that specifies the type of command to send ('setVoltage', 'setTemp', 'setTolerance', 'activateVirtualHeater', 'activateSSRHeater').
        - value: The value associated with the command, if applicable. For 'setVoltage', 'setTemp', and 'setTolerance', this should be the desired setting value. For 'activateVirtualHeater' and 'activateSSRHeater', this can be omitted.
        """
        if commandType in ['setVoltage', 'setTemp', 'setTolerance']:
            if value is not None:
                command = f"{commandType} {value}"
            else:
                print(f"Value required for command type: {commandType}")
                return
        elif commandType in ['activateVirtualHeater', 'activateSSRHeater']:
            command = commandType
        else:
            print(f"Unknown command type: {commandType}")
            return
        
        self.sendSerialCommand(command)

    def stopOperations(self):
        dacVoltage = 0
        self.sendSerialCommand(f"setVoltage {dacVoltage}")

        # Stop the QTimer
        if self.timer.isActive():
            self.timer.stop()

        # Optionally, close the serial connection
        if self.arduinoSerial and self.arduinoSerial.isOpen():
            self.arduinoSerial.close()
            self.logToTerminal("> Serial connection closed.")

        # Disable buttons to require re-initialization
        self.updateButton.setEnabled(True)
        self.stopButton.setEnabled(True)
        self.virtualHeaterButton.setEnabled(False)
        self.ssrHeaterButton.setEnabled(False)
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
        # Define color codes or styles for different message types
        messageStyles = {
            "info": "color: #FFFFFF;",  # White
            "warning": "color: #D19A66;",  # Orange
            "error": "color: #E06C75;",  # Red
            "update": "color: #61AFEF;",  # Blue
            "init": "color: #C678DD;"  # Purple
        }
        style = messageStyles.get(messageType, "color: #ABB2BF;")  # Default color
        formattedMessage = f"<p style='{style}'>{message}</p>"
        self.terminal.appendHtml(formattedMessage)

    def addToSpreadsheet(self, timeData, temperature, resistance, dacVoltage, voltage, flowRate, new_return_temp):
        """
        Adds a row of data to the spreadsheet.

        This function takes various measurements and inserts them into a new row in the spreadsheet.
        It uses exception handling to catch and report any issues that might occur during the data insertion process,
        ensuring the application remains stable even if errors are encountered.

        Parameters:
        - timeData (str): The time at which the data was recorded.
        - temperature (float): The measured temperature.
        - resistance (float): The measured resistance.
        - dacVoltage (float): The DAC voltage setting.
        - voltage (float): The measured sensor voltage.
        - flowRate (float): The measured flow rate.
        - returnTemp (float): The calculated return temperature.
        """

        # Convert string representations to float
        temperature = float(temperature)
        resistance = float(resistance) if resistance != 'N/A' else 0  # Convert 'N/A' to 0
        dacVoltage = float(dacVoltage)
        voltage = float(voltage)
        flowRate = float(flowRate)
        new_return_temp = float(new_return_temp)

        # Check if any of the values are negative or zero
        if temperature <= 0 or resistance <= 0 or dacVoltage <= 0 or voltage <= 0 or flowRate <= 0 or new_return_temp <= 0:
            self.logToTerminal("Spreadsheet data logging initiating....", messageType="update")
            return

        rowPosition = self.tableWidget.rowCount()
        try:
            self.tableWidget.insertRow(rowPosition)
            self.tableWidget.setItem(rowPosition, 0, QTableWidgetItem(timeData))
            self.tableWidget.setItem(rowPosition, 1, QTableWidgetItem(str(temperature)))
            self.tableWidget.setItem(rowPosition, 2, QTableWidgetItem(str(resistance)))
            self.tableWidget.setItem(rowPosition, 3, QTableWidgetItem(str(dacVoltage)))
            
            # Ensure that voltage and flowRate can be converted to float
            formattedVoltage = f"{voltage:.2f}"
            formattedFlowRate = f"{flowRate:.4f}"
            formattedTRet = f"{new_return_temp:.2f}"  

            self.tableWidget.setItem(rowPosition, 4, QTableWidgetItem(formattedVoltage))
            self.tableWidget.setItem(rowPosition, 5, QTableWidgetItem(formattedFlowRate))
            self.tableWidget.setItem(rowPosition, 6, QTableWidgetItem(formattedTRet))
        except Exception as e:
            print(f"Error adding data to spreadsheet: {e}")
            self.logToTerminal(f"Error adding data to spreadsheet: {e}", messageType="error")

    def exportToCSV(self):
        """
        Allows user to choose a location to save the CSV file and creates the spreadsheet.
        """
        # Open a file dialog to choose where to save the CSV
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filePath, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv);;All Files (*)", options=options)

        # Check if the user gave a file name
        if filePath:
            try:
                with open(filePath, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    # Write the project details
                    writer.writerow(['Project Number', self.projectNumberInput.text()])
                    writer.writerow(['Client Name', self.clientNameInput.text()])
                    writer.writerow(['Date', self.dateInput.text()])
                    writer.writerow([])  # Add an empty row for spacing
                    # Write the table headers
                    headers = [self.tableWidget.horizontalHeaderItem(i).text() for i in range(self.tableWidget.columnCount())]
                    writer.writerow(headers)
                    # Write the data
                    for row in range(self.tableWidget.rowCount()):
                        row_data = []
                        for column in range(self.tableWidget.columnCount()):
                            item = self.tableWidget.item(row, column)
                            # Ensure the item exists before trying to access its text
                            if item is not None:
                                row_data.append(item.text())
                            else:
                                row_data.append('')
                        writer.writerow(row_data)
                self.logToTerminal("> Data exported to CSV successfully.")
            except Exception as e:
                self.logToTerminal(f"> Failed to export data to CSV: {e}", messageType="error")
        else:
            self.logToTerminal("> CSV export canceled.", messageType="warning")


    def closeEvent(self, event):
        """
        Reimplements the close event to perform cleanup before the window is closed.
        """
        # Send command to reset DAC voltage to 0
        dacVoltage = 0
        self.sendSerialCommand(f"setVoltage {dacVoltage}")

        # Stop the QTimer to halt periodic updates
        if self.timer.isActive():
            self.timer.stop()

        # Close the serial connection if it's open
        if self.arduinoSerial and self.arduinoSerial.isOpen():
            self.arduinoSerial.close()
            self.logToTerminal("> Serial connection closed.")

        # Confirm with the user before closing the window
        reply = QtWidgets.QMessageBox.question(self, 'Terminate Window', 'Are you sure you want to close the window?',
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            event.accept()  # Accept the close event and close the window
        else:
            event.ignore()  # Ignore the close event to keep the window open

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    applyOneDarkProTheme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
