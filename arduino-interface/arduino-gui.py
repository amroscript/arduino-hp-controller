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
    QTabWidget, QTableWidget, QTableWidgetItem
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap    
from PyQt5.QtCore import QTimer, Qt, QSize

# Arduino serial connection set-up
ARDUINO_PORT = 'COM4' # Hard-coded 
BAUD_RATE = 9600

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

        self.arduinoSerial = serial.Serial('COM4', 9600, timeout=1)
        
        # Define initial values for attributes used in the model
        self.currentAmbientTemperature = 0.0  # NOT Dynamic update
        self.currentMassFlow = 0.0  # Dynamic update
        self.currentDesignHeatingPower = 5390  # design heating power
        self.currentFlowTemperatureDesign = 55  # flow temperature design
        self.boostHeatPower = 7000  # boost heat power

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
        self.timer.start(1000)  # Refresh rate in milliseconds
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

        # Set the width of each column in the table
        self.tableWidget.setColumnWidth(0, 147)
        self.tableWidget.setColumnWidth(1, 147)
        self.tableWidget.setColumnWidth(2, 147)
        self.tableWidget.setColumnWidth(3, 147)
        self.tableWidget.setColumnWidth(4, 148)
        self.tableWidget.setColumnWidth(5, 148)
        self.tableWidget.setColumnWidth(6, 148)
        self.tableWidget.setColumnWidth(7, 150)


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

    def initializeBuildingModel(self):
        if self.validateVirtualHeaterSettings():
            ambient_temp = float(self.ambientTempInput.text())  # Use ambient temperature from the GUI
            q_design_e = float(self.designHeatingPowerInput.text())
            mass_flow = self.currentMassFlow / 1000.0  # Convert L/s to kg/s

            boostHeat = self.virtualHeaterButton.isChecked()

            try:
                self.currentBuildingModel = CalcParameters(
                    t_a=ambient_temp,
                    q_design=q_design_e,
                    t_flow_design=self.currentFlowTemperatureDesign,
                    mass_flow=mass_flow,
                    boostHeat=boostHeat,
                    maxPowBooHea=self.boostHeatPower
                ).createBuilding()
                self.logToTerminal("> Building model initialized with current parameters.")
            except Exception as e:
                self.logToTerminal(f"> Failed to initialize building model: {e}", messageType="error")
        else:
            self.logToTerminal("> Invalid virtual heater settings. Please check your inputs.", messageType="warning")

    def tempToVoltage(self, temp):
        # Conversion logic parameters
        min_temp = 0
        max_temp = 100
        min_voltage = 0
        max_voltage = 10

        # Calculate the initial voltage from the temperature
        voltage = ((temp - min_temp) / (max_temp - min_temp)) * (max_voltage - min_voltage) + min_voltage

        # Apply the correction factor from your Arduino script
        correction_factor = 0.891
        corrected_voltage = voltage * correction_factor

        # Ensure correctedVoltage is within the DAC's allowable range
        corrected_voltage = max(min(corrected_voltage, max_voltage), min_voltage)  # Clamp to range 0-10V

        return corrected_voltage

    def adjustDesignParameters(self, ambient_temp, q_design_e):
        if ambient_temp <= -10:
            return q_design_e, 55
        elif -10 < ambient_temp <= -7:
            return q_design_e * 0.885, 52
        elif -7 < ambient_temp <= 2:
            return q_design_e * 0.538, 42
        elif 2 < ambient_temp <= 7:
            return q_design_e * 0.346, 36
        elif ambient_temp > 7:
            return q_design_e * 0.154, 30
        else:
            self.logToTerminal(f"> Ambient temperature {ambient_temp}°C is out of expected range.", messageType="warning")
            return q_design_e, 55  # Return default values if the temperature is out of the expected range

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
            self.virtualHeaterButton = QPushButton("Virtual Model Heater")

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
        try:
            # Ensure all required fields are filled and valid. Adapt according to your actual inputs
            float(self.ambientTempInput.text())
            float(self.initialReturnTempInput.text())
            float(self.designHeatingPowerInput.text())
            return True
        except ValueError:
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
            self.virtualHeaterSettingsGroup.setTitle("Virtual Heater: Activated")
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
        self.ambientTempInput = QLineEdit("10")
        self.addSettingWithButtons(layout, "Ambient Temperature (°C):", self.ambientTempInput, 0, font_size=10.5)
        
        self.designHeatingPowerInput = QLineEdit("5390")
        self.addSettingWithButtons(layout, "Design Heating Power (W):", self.designHeatingPowerInput, 1, font_size=10.5)

        self.initialReturnTempInput = QLineEdit("20.0")  
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
            self.virtualHeaterSettingsGroup.setTitle("VIRTUAL HEATER ACTIVATED")
            self.virtualHeaterSettingsGroup.setStyleSheet(activeStyle)
            # Enable the QLineEdit widgets for Virtual Heater settings
            self.ambientTempInput.setEnabled(True)
            self.designHeatingPowerInput.setEnabled(True)
            self.initialReturnTempInput.setEnabled(True)
        else:
            self.virtualHeaterSettingsGroup.setTitle("VIRTUAL HEATER OFF")
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

    def validateVirtualHeaterSettings(self):
        try:
            # Attempt to convert the text input from the UI to float
            ambient_temp = float(self.ambientTempInput.text())
            design_power = float(self.designHeatingPowerInput.text())
            initial_return_temp = float(self.initialReturnTempInput.text())
            
            # Validate the converted values are within expected ranges
            if not -40 <= ambient_temp <= 40:
                raise ValueError("Ambient temperature out of expected range.")
            if design_power <= 0:
                raise ValueError("Design heating power must be greater than 0.")
            if not 10 <= initial_return_temp <= 30:
                raise ValueError("Initial return temperature out of expected range.")
            
            # If all checks pass, return True
            return True
        except ValueError:
            # If any conversion fails or a check doesn't pass, return False
            return False

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

    def addToSpreadsheet(self, timeData, temperature, resistance, dacVoltage, voltage, flowRate):
        """
        Adds a row of data to the spreadsheet.

        This function takes various measurements (timeData, temperature, resistance, dacVoltage, voltage, flowRate)
        and inserts them into a new row in the spreadsheet. Each parameter corresponds to a specific column in the table.
        It uses exception handling to catch and report any issues that might occur during the data insertion process,
        ensuring the application remains stable even if errors are encountered.

        Parameters:
        - timeData (str): The time at which the data was recorded.
        - temperature (float): The measured temperature.
        - resistance (float): The measured resistance.
        - dacVoltage (float): The DAC voltage setting.
        - voltage (float): The measured sensor voltage.
        - flowRate (float): The measured flow rate.
        - t_ret (float): The calculated return temperature.
        """
        rowPosition = self.tableWidget.rowCount()
        try:
            self.tableWidget.insertRow(rowPosition)
            self.tableWidget.setItem(rowPosition, 0, QTableWidgetItem(timeData))
            self.tableWidget.setItem(rowPosition, 1, QTableWidgetItem(str(temperature)))
            self.tableWidget.setItem(rowPosition, 2, QTableWidgetItem(str(resistance)))
            self.tableWidget.setItem(rowPosition, 3, QTableWidgetItem(str(dacVoltage)))
            self.tableWidget.setItem(rowPosition, 4, QTableWidgetItem(str(voltage)))
            self.tableWidget.setItem(rowPosition, 5, QTableWidgetItem(str(flowRate)))
        except Exception as e:
            print(f"Error adding data to spreadsheet: {e}")
    
    def updateDisplay(self):
        """
        Processes incoming serial data and updates the GUI display accordingly.

        This function reads data sent from the Arduino over the serial connection. It expects the data to be in a specific format,
        with each piece of data labeled. The function parses this data, updates the display
        elements in the GUI (like temperature, resistance, etc.), and appends the data to the spreadsheet and graph.

        It incorporates error handling to manage unexpected data formats or communication issues, ensuring the application's stability.
        Debugging messages are printed to the console for troubleshooting purposes.
        """
        try:
            if self.arduinoSerial and self.arduinoSerial.in_waiting:
                serialData = self.arduinoSerial.readline().decode('utf-8').strip()
                print(f"Received serial data: {serialData}")  # Debug print

                # Check if the received data is in key-value pair format
                if ':' in serialData:
                    dataFields = serialData.split(',')
                    dataDict = {}
                    for field in dataFields:
                        parts = field.split(':')
                        if len(parts) == 2:
                            key, value = parts
                            key = key.strip()
                            try:
                                value = float(value.strip())
                            except ValueError:
                                continue  # Skip if value cannot be converted to float
                            dataDict[key] = value
                    
                    currentTime = time.strftime("%H:%M:%S", time.localtime())
                    
                    # Retrieve values from dataDict if available
                    temperature = dataDict.get('Temp', None)
                    resistance = dataDict.get('Res', None)
                    dacVoltage = dataDict.get('DACVolt', None)
                    sensorVoltage = dataDict.get('SensorVolt', None)
                    flowRate = dataDict.get('FlowRate', None)

                    # Update GUI elements only if values are present
                    if temperature is not None:
                        self.temperatureLabel.setText(f"{temperature}°C")
                    if resistance is not None:
                        self.resistanceLabel.setText(f"{resistance}Ω")
                    if dacVoltage is not None:
                        self.dacVoltageLabel.setText(f"{dacVoltage}V")
                    if sensorVoltage is not None:
                        self.sensorVoltageLabel.setText(f"{sensorVoltage}V")
                    if flowRate is not None:
                        self.flowRateLabel.setText(f"{flowRate}L/s")

                    # Append valid data to the spreadsheet and potentially to the graph
                    if temperature is not None and resistance is not None and dacVoltage is not None \
                            and sensorVoltage is not None and flowRate is not None:
                        self.addToSpreadsheet(currentTime, temperature, resistance, dacVoltage, sensorVoltage, flowRate)
                        print("Appended data to spreadsheet.")
                else:
                    # Handle or log non-key:value messages if necessary
                    print(f"Non key-value pair message received: {serialData}")
        except serial.SerialException as e:
            self.logToTerminal(f"> Error reading from serial: {e}", messageType="error")
            print(f"SerialException encountered: {e}")

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
        
    # def updateGraph(self):
    #     """Update the graph with new data."""
    #     print("Attempting to update graph...")
    #     self.figure.clear()
    #     ax = self.figure.add_subplot(111)

    #     if len(self.time_data) > 0 and len(self.t_sup_data) > 0 and len(self.t_ret_mea_data) > 0:
    #         print(f"Plotting data: {len(self.time_data)} points.")
    #         ax.plot(self.time_data, self.t_sup_data, label='Supply Temperature (°C)', marker='o', linestyle='-', color='limegreen')
    #         ax.plot(self.time_data, self.t_ret_mea_data, label='Return Temperature (°C)', marker='o', linestyle='-', color='red')

    #         ax.set_xlabel('Time (minutes)')
    #         ax.set_ylabel('Temperature (°C)')
    #         ax.set_title('Temperature Profile Over 30 Minutes')
    #         ax.legend()

    #         self.canvas.draw()
    #     else:
    #         print("No data to plot.")

    # def addTemperatureData(self, time_stamp, t_sup, t_ret_mea):
    #     try:
    #         t_sup = float(t_sup)
    #         t_ret_mea = float(t_ret_mea)
    #         print(f"Adding data: Time: {time_stamp}, Supply Temp: {t_sup}, Return Temp: {t_ret_mea}")

    #         self.t_sup_data.append(t_sup)
    #         self.t_ret_mea_data.append(t_ret_mea)
    #         self.time_data.append(time_stamp)

    #         if len(self.time_data) > 0:  # Temporarily changed for debugging
    #             self.updateGraph()
    #     except ValueError as e:
    #         print(f"Error adding data: {e}")

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
            self.timer.start(1000)  # Adjust the interval as necessary

        # Enable buttons upon initialization
        self.stopButton.setEnabled(True)
        self.virtualHeaterButton.setEnabled(True)
        self.ssrHeaterButton.setEnabled(True)
        self.dacVoltageInput.setEnabled(True)
        self.targetTempInput.setEnabled(True)
        self.toleranceInput.setEnabled(True)

    def updateSettings(self):
        """
        Initializes or updates the building model based on user inputs and real-time sensor data.
        Continuously updates the DAC voltage based on the calculated return temperature from the building model.
        """
        if self.validateVirtualHeaterSettings():
            ambient_temp = float(self.ambientTempInput.text())  # Get user input for ambient temperature
            q_design_e = float(self.designHeatingPowerInput.text())  # Get user input for design heating power

            # Assuming currentTemperature and currentFlowRate are updated by another function handling real-time Arduino data
            t_sup = float(self.temperatureLabel.text().strip('°C'))  # Real-time supply temperature
            flow_rate = float(self.flowRateLabel.text().strip('L/s'))  # Real-time flow rate

            q_design_adjusted, t_flow_design_adjusted = self.adjustDesignParameters(ambient_temp, q_design_e)

            try:
                # Initialize the building model if it doesn't exist
                if not hasattr(self, 'currentBuildingModel') or self.currentBuildingModel is None:
                    self.currentBuildingModel = TwoMassBuilding(
                        ua_hb=100, 
                        ua_ba=50,  
                        mcp_h=1000,  
                        mcp_b=1500,  
                        t_a=ambient_temp,
                        t_start_h=t_sup,
                        t_flow_design=t_flow_design_adjusted,
                        q_design_e=q_design_adjusted,
                        boostHeat=self.virtualHeaterButton.isChecked(),
                        maxPowBooHea=self.boostHeatPower
                    )

                # Perform a simulation step using the real-time data
                self.currentBuildingModel.doStep(
                    t_sup=t_sup,
                    t_ret_mea=self.currentBuildingModel.t_ret,
                    m_dot=flow_rate,
                    stepSize=1  # Step size in seconds
                )

                # Retrieve the new return temperature and update DAC voltage
                t_ret = self.currentBuildingModel.t_ret
                dacVoltage = self.tempToVoltage(t_ret)
                self.sendSerialCommand(f"setVoltage {dacVoltage:.2f}")

                self.logToTerminal("> Building model and DAC voltage updated.")
                print(f"Updated t_ret: {t_ret:.2f}°C, DAC Voltage: {dacVoltage:.2f} V")

            except Exception as e:
                self.logToTerminal(f"> Failed to update building model: {e}", messageType="error")
                print(f"Exception in building model update: {e}")

        else:
            self.logToTerminal("> Validation of virtual heater settings failed.", messageType="warning")
            print("Validation of virtual heater settings failed.")

        # Handle SSR heater settings update if the SSR heater button is toggled on
        if self.ssrHeaterButton.isChecked():
            try:
                targetTemperature = self.targetTempInput.text()
                tolerance = self.toleranceInput.text()
                dacVoltage = self.dacVoltageInput.text()

                self.sendSerialCommand(f"setTemp {targetTemperature}")
                self.sendSerialCommand(f"setTolerance {tolerance}")
                self.sendSerialCommand(f"setVoltage {dacVoltage}")

                self.logToTerminal("> SSR heater settings updated.")
            except ValueError as e:
                self.logToTerminal(f"> Error updating SSR settings: {e}", messageType="error")
                print(f"Error updating SSR settings: {e}")

    def setBoostHeat(self, activate):
        """
        Set the boost heat state.

        :param activate: A boolean indicating whether to activate (True) or deactivate (False) the boost heat.
        """
        if activate:
            # Activate the boost heater
            self.sendSerialCommand("activateBoostHeat")
            self.logToTerminal("> Virtual heater activated.")
        else:
            # Deactivate the boost heater
            self.sendSerialCommand("deactivateBoostHeat")
            self.logToTerminal("> Virtual heater deactivated.")
                
    def updateBuildingModel(self, ambient_temp):
        """
        Updates the building model with new parameters based on ambient temperature and design heating power.

        :param ambient_temp: The current ambient temperature.
        :param q_design: The initial design heating power.
        :param boostHeat: Boolean indicating whether the boost heat feature is activated.
        """
        if self.validateVirtualHeaterSettings():  # Ensure inputs are valid
                ambient_temp = float(self.ambientTempInput.text())  # Get ambient temperature from user input
                q_design_e = float(self.designHeatingPowerInput.text())  # Get design heating power from user input

                # Adjust design parameters based on user inputs
                q_design_adjusted, t_flow_design_adjusted = self.adjustDesignParameters(ambient_temp, q_design_e)

                # Initialize building model with adjusted parameters
                try:
                    self.currentBuildingModel = CalcParameters(
                        t_a=ambient_temp,
                        q_design=q_design_adjusted,
                        t_flow_design=t_flow_design_adjusted,
                        mass_flow=self.currentMassFlow / 1000.0,  # Convert from L/s to kg/s if necessary
                        boostHeat=self.virtualHeaterButton.isChecked(),
                        maxPowBooHea=self.boostHeatPower
                    ).createBuilding()
                    self.logToTerminal(f"> Building model initialized for ambient temperature {ambient_temp}°C.")
                except Exception as e:
                    self.logToTerminal(f"> Failed to initialize building model: {e}", messageType="error")
                else:
                    self.logToTerminal("> Invalid settings for virtual heater. Please check your inputs.", messageType="warning")
        
    def sendSerialCommand(self, command):
        """
        Sends a command to the Arduino via the established serial connection.

        :param command: The command string to be sent to the Arduino.
        """
        if self.arduinoSerial and self.arduinoSerial.isOpen():
            # If the serial connection is open, encode and send the command with a newline character.
            self.arduinoSerial.write((command + '\n').encode()) 
            self.logToTerminal(f"> Sent to Arduino: {command}")
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

        # Log that operations have been halted
        self.logToTerminal("> Operations halted.")

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
        
        # Format the message with HTML tags
        formattedMessage = f"<p style='{style}'>{message}</p>"
        
        # Append the formatted message to the terminal
        self.terminal.appendHtml(formattedMessage)

    def exportToCSV(self):
        filePath = r'C:\Users\hvaclab\Desktop\GUI Testing\HPData.csv' 
        with open(filePath, 'w', newline='') as file:
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

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    applyOneDarkProTheme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
