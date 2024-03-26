#!/usr/bin/env python3.9

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
ARDUINO_PORT = 'COM3' # Hard-coded 
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

        self.arduinoSerial = serial.Serial('COM3', 9600, timeout=1)
        
        # Define initial values for attributes used in the model
        self.currentAmbientTemperature =0.0  # NOT Dynamic update
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
                self.logToTerminal("> Serial connection established.")
            except serial.SerialException as e:
                self.logToTerminal(f"> Error connecting to Arduino: {e}", messageType="error")

    # Formatting: logo and setting up controls
    def setupUI(self):
        self.setFont(QFont("Verdana", 12))
        tabWidget = QTabWidget()

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
        spreadsheetLayout = QHBoxLayout()  # Changed to QHBoxLayout to place table and graph side by side

        # Frame for the table
        tableFrame = QFrame()
        tableLayout = QVBoxLayout()
        tableFrame.setLayout(tableLayout)

        # Frame for the graph
        graphFrame = QFrame()
        graphLayout = QVBoxLayout()
        graphFrame.setLayout(graphLayout)
        graphFrame.setMaximumWidth(800)  # Adjust this value as needed

        # Header Section for Spreadsheet Tab
        headerLayout = QHBoxLayout()
        self.projectNumberInput = QLineEdit()
        self.projectNumberInput.setPlaceholderText("Project Number")
        self.projectNumberInput.setMaximumWidth(300)  # Adjust the maximum width as desired
        self.clientNameInput = QLineEdit()
        self.clientNameInput.setPlaceholderText("Client Name")
        self.clientNameInput.setMaximumWidth(300)  # Adjust the maximum width as desired
        self.dateInput = QLineEdit()
        self.dateInput.setPlaceholderText("Date (YYYY-MM-DD)")
        self.dateInput.setMaximumWidth(300)  # Adjust the maximum width as desired
        self.exportCSVButton = QPushButton("Export to CSV")
        self.exportCSVButton.clicked.connect(self.exportToCSV)
        self.exportCSVButton.setStyleSheet("font-size: 11pt;")

        # Adding widgets to the header layout
        headerLayout.addWidget(self.projectNumberInput)
        headerLayout.addWidget(self.clientNameInput)
        headerLayout.addWidget(self.dateInput)
        headerLayout.addWidget(self.exportCSVButton)

        # Add the header section to the table layout
        tableLayout.addLayout(headerLayout)

        # Table Widget for Spreadsheet Tab
        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(6)  # Columns for Temperature, Resistance, Voltage, Flow Rate
        self.tableWidget.setHorizontalHeaderLabels(["Time", "Temperature", "Resistance", "DAC Voltage", "Sensor Voltage", "Flow Rate"])

        # Set the width of each column in the table
        self.tableWidget.setColumnWidth(0, int(147.5))  # Time column width
        self.tableWidget.setColumnWidth(1, int(147.5))  # Temperature column width
        self.tableWidget.setColumnWidth(2, int(147.5))  # Resistance column width
        self.tableWidget.setColumnWidth(3, int(147.5))  # DAC Voltage column width
        self.tableWidget.setColumnWidth(4, int(148))  # Sensor Voltage column width
        self.tableWidget.setColumnWidth(5, int(148))  # Flow Rate column width

        # Adding the tableWidget to the table layout
        tableLayout.addWidget(self.tableWidget)

        # Graph setup
        self.graphFigure = Figure()
        self.graphCanvas = FigureCanvas(self.graphFigure)

        # Now adding both frames to the spreadsheetLayout to arrange them side by side
        spreadsheetLayout.addWidget(tableFrame)
        spreadsheetLayout.addWidget(graphFrame)

        spreadsheetTab.setLayout(spreadsheetLayout) 
        self.graphFigure.patch.set_facecolor('#282C34')  # Background color to match One Dark Pro theme
        self.graphCanvas = FigureCanvas(self.graphFigure)
        self.ax = self.graphFigure.add_subplot(111)
        self.ax.set_facecolor('#282C34')  # Graph background color
        self.ax.tick_params(axis='x', colors='#ABB2BF')  # Adjust to match theme
        self.ax.tick_params(axis='y', colors='#ABB2BF')
        self.ax.spines['bottom'].set_color('#ABB2BF')
        self.ax.spines['top'].set_color('#ABB2BF') 
        self.ax.spines['right'].set_color('#ABB2BF')
        self.ax.spines['left'].set_color('#ABB2BF')
        self.ax.xaxis.label.set_color('#ABB2BF')
        self.ax.yaxis.label.set_color('#ABB2BF')
        self.ax.title.set_color('#ABB2BF')

        # Apply the stylesheet for One Dark Pro theme consistency
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
        spreadsheetTab.setLayout(spreadsheetLayout)  # Set the layout for the spreadsheet tab
        graphLayout.addWidget(self.graphCanvas)

        # Add tabs to the TabWidget
        tabWidget.addTab(controlsTab, "Controls Monitor")
        tabWidget.addTab(spreadsheetTab, "Data Spreadsheet")

        # Set the TabWidget as the central widget
        self.setCentralWidget(tabWidget)
        spreadsheetLayout.addWidget(tableFrame)
        spreadsheetLayout.addWidget(graphFrame)

        spreadsheetTab.setLayout(spreadsheetLayout) 

        self.applyButtonStyles()

        # Call updateGraph to refresh the graph with the new data
        self.updateGraph()

    def initializeBuildingModel(self):
        if self.validateVirtualHeaterSettings():
            ambient_temp = float(self.ambientTempInput.text())
            q_design_e = float(self.designHeatingPowerInput.text())
            t_b = 20.0  # Assuming a default constant building temperature
            mass_flow = self.currentMassFlow / 1000.0  # Convert L/s to kg/s

            # Adjust q_design and t_flow_design based on ambient temperature
            if ambient_temp <= -10:
                q_design_adjusted = q_design_e
                t_flow_design_adjusted = 55
            elif -10 < ambient_temp <= -7:
                q_design_adjusted = q_design_e * 0.885
                t_flow_design_adjusted = 52
            elif -7 < ambient_temp <= 2:
                q_design_adjusted = q_design_e * 0.538
                t_flow_design_adjusted = 42
            elif 2 < ambient_temp <= 7:
                q_design_adjusted = q_design_e * 0.346
                t_flow_design_adjusted = 36
            elif ambient_temp > 7:
                q_design_adjusted = q_design_e * 0.154
                t_flow_design_adjusted = 30
            else:
                self.logToTerminal("> Ambient temperature out of expected range.", messageType="warning")
                return

            boostHeat = self.virtualHeaterButton.isChecked()

            try:
                self.currentBuildingModel = CalcParameters(
                    t_a=ambient_temp,
                    q_design=q_design_adjusted,
                    tau_b=209125,
                    tau_h=1957,
                    t_flow_design=t_flow_design_adjusted,
                    mass_flow=mass_flow,
                    t_b=t_b,
                    boostHeat=boostHeat,
                    maxPowBooHea=self.boostHeatPower
                ).createBuilding()
                self.logToTerminal("> Building model initialized with current parameters.")
            except Exception as e:
                self.logToTerminal(f"> Failed to initialize building model: {e}", messageType="error")
        else:
            self.logToTerminal("> Invalid virtual heater settings. Please check your inputs.", messageType="warning")


    def createMeasurementGroup(self):
        group = QGroupBox("Instructions and Real-time Measurements")
        group.setFont(QFont("Verdana", 12, QFont.Bold))

        # Main horizontal layout for the group
        mainLayout = QHBoxLayout(group)

        # Left side layout for instructions
        instructionsLayout = QVBoxLayout()
        instructionsLabel = QLabel("""
        <p>
        1. Click the <span style='color: #98C379;'>initialize</span> button to activate all Arduino components.<br>
        2. The control parameters are only updated when the <span style='color: #61AFEF;'>update settings</span> button is clicked.<br>
        3. The <span style='color: #E06C75;'>stop</span> button will halt all operations.<br><br>
        For further clarification please consult the GitHub repository documentation: <a href="https://github.com/amroscript/arduino-hp-controller">Arduino HP Controller</a>.
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
            group.setFont(QFont("Verdana", 12, QFont.Bold))
            layout = QVBoxLayout(group)

            # Heater Mode Buttons Setup (without grouping them to allow independent toggling)
            heaterButtonLayout = QHBoxLayout()
            self.ssrHeaterButton = QPushButton("Solid State Relay Heater")
            self.virtualHeaterButton = QPushButton("Virtual Model Heater")

            for btn in [self.ssrHeaterButton, self.virtualHeaterButton]:
                btn.setCheckable(True)
                btn.setFixedHeight(30)  # Set a fixed height for a consistent look
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
                btn.setFixedHeight(30)
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
        # Update settings group titles and styles based on the heater button states
        if self.ssrHeaterButton.isChecked():
            self.ssrSettingsGroup.setTitle("SSR Heater: Activated")
        else:
            self.ssrSettingsGroup.setTitle("SSR Heater: Off")

        if self.virtualHeaterButton.isChecked():
            self.virtualHeaterSettingsGroup.setTitle("Virtual Heater: Activated")
        else:
            self.virtualHeaterSettingsGroup.setTitle("Virtual Heater: Off")
            
    def createSSRSettingsGroup(self):
        group = QGroupBox("SSR Heater Settings")
        group.setFont(QFont("Verdana", 10, QFont.Bold))
        layout = QGridLayout()

        # Existing SSR Heater Settings, assuming you have similar inputs as before
        self.targetTempInput = QLineEdit("23")
        self.addSettingWithButtons(layout, "Target Temperature (°C):", self.targetTempInput, 0, font_size= 11)

        self.toleranceInput = QLineEdit("0.2")
        self.addSettingWithButtons(layout, "Temperature Tolerance (±°C):", self.toleranceInput, 1, font_size= 11)

        self.dacVoltageInput = QLineEdit("2.5")
        self.addSettingWithButtons(layout, "DAC Voltage Output (V):", self.dacVoltageInput, 2, font_size= 11)

        group.setLayout(layout)
        return group

    def createVirtualHeaterSettingsGroup(self):
        """
        Create a group box for Virtual Heater settings with inputs for ambient temperature,
        design heating power, and initial return temperature including increment/decrement buttons.
        """
        group = QGroupBox("Virtual Heater Settings")
        group.setFont(QFont("Verdana", 10, QFont.Bold))  # Adjusted font size to 10
        layout = QGridLayout()

        # Inputs
        self.ambientTempInput = QLineEdit("10")
        self.addSettingWithButtons(layout, "Ambient Temperature (°C):", self.ambientTempInput, 0, font_size=11)
        self.designHeatingPowerInput = QLineEdit("5390")
        self.addSettingWithButtons(layout, "Design Heating Power (W):", self.designHeatingPowerInput, 1, font_size=11)

        # Initial Return Temperature Input with buttons
        self.initialReturnTempInput = QLineEdit("20.0")  # Default value as an example
        self.addSettingWithButtons(layout, "Initial Return Temperature (°C):", self.initialReturnTempInput, 2, font_size=11)

        group.setLayout(layout)
        return group
    
    def applyButtonStyles(self):
        buttonFontSize = "10pt" 

        # Initialize, Update, and Stop Buttons
        self.initButton.setStyleSheet(f"""
            QPushButton {{
                background-color: #98C379;
                color: white;
                border: 2px solid #98C379;
                font-size: {buttonFontSize};
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
            }}
            QPushButton:hover {{
                background-color: #EF7A85;
            }}
        """)

    def updateHeaterButtonState(self):
        # Define styles for the buttons
        activeButtonStyle = "QPushButton { background-color: #ABB2BF; color: white; border: 2px solid #ABB2BF; font-size: 10pt; }"
        inactiveButtonStyle = "QPushButton { background-color: #5C6370; color: white; border: 2px solid #5C6370; font-size: 10pt; }"
        
        # Apply the active or inactive style to the buttons
        self.ssrHeaterButton.setStyleSheet(activeButtonStyle if self.ssrHeaterButton.isChecked() else inactiveButtonStyle)
        self.virtualHeaterButton.setStyleSheet(activeButtonStyle if self.virtualHeaterButton.isChecked() else inactiveButtonStyle)
        
        # Update the group titles and colors
        if self.ssrHeaterButton.isChecked():
            self.ssrSettingsGroup.setTitle("SSR HEATER ACTIVATED")
            self.ssrSettingsGroup.setStyleSheet("QGroupBox { font: 9pt; font-weight: bold; color: #98C379; }")  # Green for activated
        else:
            self.ssrSettingsGroup.setTitle("SSR HEATER OFF")
            self.ssrSettingsGroup.setStyleSheet("QGroupBox { font: 9pt; font-weight: bold; color: #E06C75; }")  # Red for off
        
        if self.virtualHeaterButton.isChecked():
            self.virtualHeaterSettingsGroup.setTitle("VIRTUAL HEATER ACTIVATED")
            self.virtualHeaterSettingsGroup.setStyleSheet("QGroupBox { font: 9pt; font-weight: bold; color: #98C379; }")  # Green for activated
        else:
            self.virtualHeaterSettingsGroup.setTitle("VIRTUAL HEATER OFF")
            self.virtualHeaterSettingsGroup.setStyleSheet("QGroupBox { font: 9pt; font-weight: bold; color: #E06C75; }")  # Red for off

        # Ensure UI updates are applied immediately
        self.ssrHeaterButton.style().unpolish(self.ssrHeaterButton)
        self.ssrHeaterButton.style().polish(self.ssrHeaterButton)
        self.virtualHeaterButton.style().unpolish(self.virtualHeaterButton)
        self.virtualHeaterButton.style().polish(self.virtualHeaterButton)

    def addSettingWithButtons(self, layout, labelText, lineEdit, row, font_size=12):
        label = QLabel(labelText)
        label.setFont(QFont("Verdana", font_size))
        layout.addWidget(label, row, 0)

        # Increment/Decrement buttons
        upButton = QPushButton("+")
        downButton = QPushButton("-")
        upButton.setFont(QFont("Verdana", font_size))
        downButton.setFont(QFont("Verdana", font_size))

        # Set a fixed size for the buttons
        buttonSize = QSize(30, 30)
        upButton.setFixedSize(buttonSize)
        downButton.setFixedSize(buttonSize)

        # Connect buttons to increment/decrement actions
        upButton.clicked.connect(lambda: self.adjustValue(lineEdit, 1))
        downButton.clicked.connect(lambda: self.adjustValue(lineEdit, -1))

        lineEdit.setMinimumSize(QSize(100, 30))  # Adjusted size to make room for buttons
        lineEdit.setFont(QFont("Verdana", font_size))

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
                print("Boost heat activated.")
            else:
                print("Boost heat deactivated.")
        else:
            print("Mass flow data is not yet available. Delaying model initialization.")

    def updateVirtualHeaterSettings(self):
        try:
            # Read values from input fields
            ambient_temp = float(self.ambientTempInput.text())
            design_power = float(self.designHeatingPowerInput.text())
            
            # Check if the virtual heater is on or off to set boostHeat
            boostHeat = self.virtualHeaterButton.isChecked()
            self.logToTerminal(f"> boostHeat status: {'Activated' if boostHeat else 'Deactivated'}")
            
            # Update the model
            self.currentBuildingModel = CalcParameters(
                t_a=ambient_temp,
                q_design=design_power,
                t_flow_design=self.currentFlowTemperatureDesign, # Assuming this is static or set elsewhere
                mass_flow=self.currentMassFlow, # Assuming this is dynamically updated elsewhere in your program
                boostHeat=boostHeat,
                maxPowBooHea=self.boostHeatPower # Assuming this is static or set elsewhere
            ).createBuilding()
            
            self.logToTerminal("Virtual heater settings updated successfully.")
        except ValueError as e:
            self.logToTerminal(f"Error updating virtual heater settings: {str(e)}", messageType="error")

        # Assuming you want to automatically update the model upon changing any of these settings
        self.ambientTempInput.textChanged.connect(self.updateVirtualHeaterSettings)
        self.designHeatingPowerInput.textChanged.connect(self.updateVirtualHeaterSettings)
        self.virtualHeaterButton.toggled.connect(self.updateVirtualHeaterSettings)

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
        rowPosition = self.tableWidget.rowCount()
        self.tableWidget.insertRow(rowPosition)
        self.tableWidget.setItem(rowPosition, 0, QTableWidgetItem(timeData))
        self.tableWidget.setItem(rowPosition, 1, QTableWidgetItem(str(temperature)))
        self.tableWidget.setItem(rowPosition, 2, QTableWidgetItem(str(resistance)))
        self.tableWidget.setItem(rowPosition, 3, QTableWidgetItem(str(dacVoltage)))
        self.tableWidget.setItem(rowPosition, 4, QTableWidgetItem(str(voltage)))
        self.tableWidget.setItem(rowPosition, 5, QTableWidgetItem(str(flowRate)))

    def updateDisplay(self):
        try:
            if self.arduinoSerial and self.arduinoSerial.in_waiting:
                serialData = self.arduinoSerial.readline().decode('utf-8').strip()
                print(f"Received data: {serialData}")  # Debug print

                # Check if the received data is a key-value pair
                if ':' in serialData:
                    dataFields = serialData.split(',')
                    currentTime = time.strftime("%H:%M:%S", time.localtime())  # Format current time as a string
                    temperature = resistance = dacVoltage = sensorVoltage = flowRate = None  # Initialize as None for clarity

                    for field in dataFields:
                        try:
                            key, value = field.split(':', 1)
                            if key.strip() == 'Temp':
                                temp = float(value)
                                self.temperatureLabel.setText(f"{temp}°C")
                                t_sup = temp  # Update t_sup with the actual temperature
                            elif key.strip() == 'Res':
                                self.resistanceLabel.setText(f"{value}Ω")
                                resistance = float(value)  # Assuming you want to use this later
                            elif key.strip() == 'DACVolt':
                                self.dacVoltageLabel.setText(f"{value}V")
                                dacVoltage = float(value)
                            elif key.strip() == 'SensorVolt':
                                self.sensorVoltageLabel.setText(f"{value}V")
                                sensorVoltage = float(value)  # Assuming you want to use this later
                            elif key.strip() == 'FlowRate':
                                self.flowRateLabel.setText(f"{value}L/s")
                                flowRate = float(value)
                                self.currentMassFlow = float(value) / 1000.0  # Convert L/s to kg/s
                        except ValueError as ve:
                            print(f"Error parsing field: {field}. Error: {ve}")

                    # Append valid temperature and flowRate data
                    if temperature is not None and flowRate is not None:
                        self.time_data.append(currentTime)
                        self.temperature_data.append(temperature)
                        self.flow_rate_data.append(flowRate)
                        self.updateGraph()  # Update the graph with new data
                        self.addToSpreadsheet(currentTime, temperature, resistance, dacVoltage, sensorVoltage, flowRate)
                else:
                    # Handle or log non-key:value messages if necessary
                    print(f"Message received: {serialData}")
        except serial.SerialException as e:
            self.logToTerminal(f"> Error reading from serial: {e}", messageType="error")

    def handleNewData(self, time, temperature, flowRate):
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
            self.timer.start(1000)  # Adjust the interval as necessary

        # Enable buttons upon initialization
        self.stopButton.setEnabled(True)
        self.virtualHeaterButton.setEnabled(True)
        self.ssrHeaterButton.setEnabled(True)
        self.dacVoltageInput.setEnabled(True)
        self.targetTempInput.setEnabled(True)
        self.toleranceInput.setEnabled(True)
            
    def updateSettings(self):
        if self.validateVirtualHeaterSettings():
            # Retrieve values from UI
            ambient_temp = float(self.ambientTempInput.text())
            design_power = float(self.designHeatingPowerInput.text())
            boostHeat = self.virtualHeaterButton.isChecked()

            try:
                # Correctly pass the expected number of arguments to updateBuildingModel
                self.currentBuildingModel = self.updateBuildingModel(ambient_temp, design_power, boostHeat)
                self.logToTerminal("> Building model updated with current parameters.")

                # If SSR settings are separate and need to be updated only when SSR heater is on
                if self.ssrHeaterButton.isChecked():
                    # Update SSR settings here
                    self.logToTerminal("> SSR heater settings updated.")
            except Exception as e:
                self.logToTerminal(f"> Failed to update settings: {e}", messageType="error")
        else:
            self.logToTerminal("> Invalid settings. Please check your inputs.", messageType="warning")


        # SSR settings update if SSR heater is on
        if self.ssrHeaterButton.isChecked():
            try:
                # Retrieve SSR Heater settings
                targetTemperature = self.targetTempInput.text()
                tolerance = self.toleranceInput.text()
                dacVoltage = self.dacVoltageInput.text()

                # Send serial commands to the Arduino for each SSR setting
                self.sendSerialCommand(f"setTemp {targetTemperature}")
                self.sendSerialCommand(f"setTolerance {tolerance}")
                self.sendSerialCommand(f"setVoltage {dacVoltage}")
                
                self.logToTerminal("> SSR heater settings updated.")
            except ValueError as e:
                self.logToTerminal(f"> Error updating SSR settings: {e}", messageType="error")

    def updateBuildingModel(self, t_a, q_design, boostHeat):
        try:
            # Parameters for the building model, adjust as necessary
            t_flow_design = self.currentFlowTemperatureDesign
            mass_flow = self.currentMassFlow
            # Call CalcParameters with the correct parameters
            self.currentBuildingModel = CalcParameters(
                t_a=t_a,
                q_design=q_design,
                t_flow_design=t_flow_design,
                mass_flow=mass_flow,
                delta_T_cond=5,  # Example value, adjust as necessary
                const_flow=True,  # Or False, based on your system setup
                tau_b=55E6 / 263,  # Example value, adjust as necessary
                tau_h=505E3 / 258,  # Example value, adjust as necessary
                t_b=20,  # Default or from UI
                boostHeat=boostHeat,
                maxPowBooHea=7000  # Example value, adjust as necessary
            ).createBuilding()
            self.logToTerminal("> Building model created and initialized.")
        except Exception as e:
            self.logToTerminal(f"> Failed to create/update building model: {e}", messageType="error")

    def sendSerialCommand(self, command):
        if self.arduinoSerial and self.arduinoSerial.isOpen():
            self.arduinoSerial.write((command + '\n').encode()) 
            self.logToTerminal(f"> Sent to Arduino: {command}")
        else:
            self.logToTerminal("> Error: Serial connection not established.", messageType="error")

    def setDACVoltage(self):
        """Send DAC voltage setting command to Arduino."""
        voltage = self.dacVoltageInput.text()  # Assuming dacVoltageInput is a QLineEdit
        command = f"setVoltage {voltage}"
        self.sendCommandToArduino(command)

    def setTargetTemperature(self):
        """Send target temperature setting command to Arduino."""
        temperature = self.targetTempInput.text()  # Assuming targetTempInput is a QLineEdit
        command = f"setTemp {temperature}"
        self.sendCommandToArduino(command)

    def setTolerance(self):
        """Send tolerance setting command to Arduino."""
        tolerance = self.toleranceInput.text()  # Assuming toleranceInput is a QLineEdit
        command = f"setTolerance {tolerance}"
        self.sendCommandToArduino(command)

    def activateVirtualHeater(self):
        """Send command to activate virtual heater."""
        self.sendCommandToArduino("activateVirtualHeater")

    def activateSSRHeater(self):
        """Send command to activate SSR heater."""
        self.sendCommandToArduino("activateSSRHeater")

    def stopOperations(self):
        # Stop the QTimer
        if self.timer.isActive():
            self.timer.stop()
        
        # Optionally, close the serial connection
        if self.arduinoSerial and self.arduinoSerial.isOpen():
            self.arduinoSerial.close()
            self.logToTerminal("> Serial connection closed.")
        
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
            font-size: 12pt;
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


    def updateGraph(self):
        if not self.time_data:  # Check if there's data to plot
            return

        self.ax.clear()  # Clear previous data

        # Plot temperature vs. time
        self.ax.plot(self.time_data, self.temperature_data, label='Temperature (°C)', color='#E06C75', linewidth=2)
        # Plot flow rate vs. time on a secondary y-axis
        self.ax2 = self.ax.twinx()  # Create a secondary y-axis
        self.ax2.plot(self.time_data, self.flow_rate_data, label='Flow Rate (L/s)', color='#61AFEF', linewidth=2)

        # Set the face color to match the One Dark Pro theme
        self.ax.set_facecolor('#282C34')
        self.ax2.set_facecolor('#282C34')  # Set face color for the secondary y-axis

        # Update tick parameters and spines to match the theme color
        for ax in [self.ax, self.ax2]:
            ax.tick_params(axis='x', colors='#ABB2BF', rotation=90)  # Rotate tick labels by 90 degrees for better readability
            ax.tick_params(axis='y', colors='#ABB2BF')
            for spine in ax.spines.values():
                spine.set_color('#ABB2BF')

        # Adjust the number of ticks on the x-axis (every 10th tick)
        num_ticks = len(self.time_data)
        if num_ticks > 10:
            step = num_ticks // 10
            self.ax.xaxis.set_ticks(self.time_data[::step])
        
        # Update axis labels and title
        self.ax.set_title('Temperature & Flow Rate VS Time', color='#ABB2BF')

        # Show legend
        lines, labels = self.ax.get_legend_handles_labels()
        lines2, labels2 = self.ax2.get_legend_handles_labels()
        self.ax.legend(lines + lines2, labels + labels2, loc='upper left', facecolor='#282C34', edgecolor='#282C34')

        # Redraw the graph with the new data
        self.graphCanvas.draw()

    def exportToCSV(self):
        filePath = r'C:\Users\LAB\Desktop\GUI Testing\HPData.csv' 
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
