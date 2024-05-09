"""
    @Author: Amro Farag
    Date: March 2024
    Email: amro.farag@bregroup.com / amrihabfaraj@gmail.com
"""

import sys
import serial
import csv
import time
from bamLoadBasedTesting.twoMassModel import CalcParameters, TwoMassBuilding
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QPushButton, \
    QLineEdit, QGridLayout, QGroupBox, QHBoxLayout, QFrame, QPlainTextEdit, \
    QTabWidget, QTableWidget, QTableWidgetItem, QFileDialog
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap
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
        self.t_ret_history = []  
        self.lastDACVoltage = '0.00'
        self.lastSPtemp = '0.00'
        self.lastFlowRate = '0.00'
        self.lastreturnTemperature = '0.00'
        self.hasBeenInitialized = False

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

        self.setWindowTitle("ArduinoUI")
        self.setupUI()
        applyOneDarkProTheme(QApplication.instance())

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateDisplay)
        self.timer.start(100)


        self.loadingTimer = QTimer(self)
        self.loadingTimer.timeout.connect(self.updateLoadingBar)
        self.loadingStep = 0  

        self.initSerialConnection()
        self.updateButton.setEnabled(True)
        self.stopButton.setEnabled(True)
        self.virtualHeaterButton.setEnabled(True)
        self.ssrHeaterButton.setEnabled(True)
        self.dacVoltageInput.setEnabled(False)
        self.targetTempInput.setEnabled(False)
        self.toleranceInput.setEnabled(False)

    def initSerialConnection(self): 
        try:
            self.arduinoSerial = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
            self.logToTerminal("> Serial connection established. System initialized.")
        except serial.SerialException as e:
            self.logToTerminal(f"> Error connecting to Arduino: {e}", messageType="error")

    def updateLoadingBar(self):
        if self.loadingStep < 100:
            self.loadingStep += 100
            elapsed = self.loadingStep
            total = 100
            percent = (elapsed / total) * 100
            bar_length = 100  # Adjust the length of the progress bar
            filled_length = int(round(bar_length * elapsed / float(total)))
            bar = '█' * filled_length + '-' * (bar_length - filled_length)
            self.logToTerminal(f"|{bar}| {percent:.0f}%" "  Model Initialized.", messageType="init")
        else:
            self.loadingTimer.stop()
            self.loadingStep = 0  # Reset for next use

    def startLoadingBar(self):
        self.loadingTimer.start() 

    def setupUI(self):
        self.setFont(QFont("Verdana", 12))
        tabWidget = QTabWidget(self)

        self.setMinimumSize(1000, 1000)

        self.logoLabel = QLabel()
        logoPixmap = QPixmap("Arduino Controller.png")
        scaledLogoPixmap = logoPixmap.scaled(700, 500, Qt.KeepAspectRatio)
        self.logoLabel.setPixmap(scaledLogoPixmap)
        self.logoLabel.setAlignment(Qt.AlignCenter)

        controlsTab = QWidget()
        controlsLayout = QVBoxLayout()
        controlsLayout.addWidget(self.logoLabel)
        self.measurementGroup = self.createMeasurementGroup()
        self.controlGroup = self.createControlGroup()
        self.terminal = self.createTerminal()
        controlsLayout.addWidget(self.measurementGroup)
        controlsLayout.addWidget(self.controlGroup)
        controlsLayout.addWidget(self.terminal, 1)
        controlsTab.setLayout(controlsLayout)

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
        self.exportCSVButton.setStyleSheet("font-size: 11pt;")
        
        headerLayout.addWidget(self.projectNumberInput)
        headerLayout.addWidget(self.clientNameInput)
        headerLayout.addWidget(self.dateInput)
        headerLayout.addWidget(self.exportCSVButton)

        tableLayout.addLayout(headerLayout)

        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(6)
        self.tableWidget.setHorizontalHeaderLabels(["Time", "Temperature", "DAC Voltage", "SP Temperature", "Flow Rate", "Return Temperature"])

        self.tableWidget.setColumnWidth(0, 250)
        self.tableWidget.setColumnWidth(1, 250)
        self.tableWidget.setColumnWidth(2, 250)
        self.tableWidget.setColumnWidth(3, 250)
        self.tableWidget.setColumnWidth(4, 250)
        self.tableWidget.setColumnWidth(5, 250)

        self.tableWidget.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: #282C34;
                color: #ABB2BF;
                gridline-color: #3B4048;
                selection-background-color: #3E4451;
                selection-color: #ABB2BF;
                font-size: 12pt;
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

        self.graphTab = QWidget()
        self.graphLayout = QVBoxLayout()
        self.graphTab.setLayout(self.graphLayout)
        self.setupGraph()

        self.figure = Figure(facecolor='#282C34')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("QWidget {background-color: #282C34; color: #ABB2BF;}")

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
        line.setStyleSheet("color: #3B4048")

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
        group = QGroupBox("Heater Mode Settings")
        group.setFont(QFont("Verdana", 11, QFont.Bold))
        layout = QVBoxLayout(group)

        heaterButtonLayout = QHBoxLayout()
        self.ssrHeaterButton = QPushButton("Solid State Relay Heater")
        self.virtualHeaterButton = QPushButton("Two Mass Model")

        for btn in [self.ssrHeaterButton, self.virtualHeaterButton]:
            btn.setCheckable(True)
            btn.setFixedHeight(31)
            self.ssrHeaterButton.toggled.connect(self.updateHeaterButtonState)
            self.virtualHeaterButton.toggled.connect(self.updateHeaterButtonState)
            heaterButtonLayout.addWidget(btn)

        self.ssrHeaterButton.setChecked(False)
        self.virtualHeaterButton.setChecked(False)

        self.ssrSettingsGroup = self.createSSRSettingsGroup()
        self.virtualHeaterSettingsGroup = self.createVirtualHeaterSettingsGroup()

        self.updateHeaterButtonState()

        settingsLayout = QHBoxLayout()
        settingsLayout.addWidget(self.ssrSettingsGroup)
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
        self.initButton.clicked.connect(self.initButtonClicked)
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
        
        if self.ssrHeaterButton.isChecked():
            self.ssrSettingsGroup.setTitle("SSR Heater: Activated")
            self.ssrSettingsGroup.setStyleSheet(activeStyle)
        else:
            self.ssrSettingsGroup.setTitle("SSR Heater: Off")
            self.ssrSettingsGroup.setStyleSheet(inactiveStyle)
        
        if self.virtualHeaterButton.isChecked():
            self.virtualHeaterSettingsGroup.setTitle("Two Mass Model: Activated")
            self.virtualHeaterSettingsGroup.setStyleSheet(activeStyle)
        else:
            self.virtualHeaterSettingsGroup.setTitle("Two Mass Model: Off")
            self.virtualHeaterSettingsGroup.setStyleSheet(inactiveStyle)
        
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
        group = QGroupBox("Virtual Heater Settings")
        group.setFont(QFont("Verdana", 10, QFont.Bold))
        layout = QGridLayout()

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
        
        if self.ssrHeaterButton.isChecked():
            self.ssrSettingsGroup.setTitle("SSR HEATER ACTIVATED")
            self.ssrSettingsGroup.setStyleSheet(activeStyle)
            self.targetTempInput.setEnabled(True)
            self.toleranceInput.setEnabled(True)
            self.dacVoltageInput.setEnabled(True)
        else:
            self.ssrSettingsGroup.setTitle("SSR HEATER OFF")
            self.ssrSettingsGroup.setStyleSheet(inactiveStyle)
            self.targetTempInput.setEnabled(False)
            self.toleranceInput.setEnabled(False)
            self.dacVoltageInput.setEnabled(False)
            self.dacVoltageInput.setText("0")

        if self.virtualHeaterButton.isChecked():
            self.virtualHeaterSettingsGroup.setTitle("TWO MASS MODEL READY TO MODIFY")
            self.virtualHeaterSettingsGroup.setStyleSheet(activeStyle)
            self.ambientTempInput.setEnabled(True)
            self.designHeatingPowerInput.setEnabled(True)
            self.initialReturnTempInput.setEnabled(True)
        else:
            self.virtualHeaterSettingsGroup.setTitle("TWO MASS MODEL READ-ONLY")
            self.virtualHeaterSettingsGroup.setStyleSheet(inactiveStyle)
            self.ambientTempInput.setEnabled(False)
            self.designHeatingPowerInput.setEnabled(False)
            self.initialReturnTempInput.setEnabled(False)
        
        self.ssrSettingsGroup.style().unpolish(self.ssrSettingsGroup)
        self.ssrSettingsGroup.style().polish(self.ssrSettingsGroup)
        self.virtualHeaterSettingsGroup.style().unpolish(self.virtualHeaterSettingsGroup)
        self.virtualHeaterSettingsGroup.style().polish(self.virtualHeaterSettingsGroup)

    def addSettingWithButtons(self, layout, labelText, lineEdit, row, font_size=10):
        label = QLabel(labelText)
        label.setFont(QFont("Verdana", int(font_size)))
        layout.addWidget(label, row, 0)

        upButton = QPushButton("+")
        downButton = QPushButton("-")
        upButton.setFont(QFont("Verdana", int(font_size)))
        downButton.setFont(QFont("Verdana", int(font_size)))

        buttonSize = QSize(30, 30)
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

    def toggleHeaterMode(self, isSSRHeaterActive):
        self.ssrHeaterButton.setChecked(isSSRHeaterActive)
        self.virtualHeaterButton.setChecked(not isSSRHeaterActive)
        self.updateHeaterButtons(isSSRHeaterActive)

        if isSSRHeaterActive:
            self.ssrSettingsGroup.setTitle("ACTIVATED")
            self.ssrSettingsGroup.setStyleSheet("QGroupBox { font: 10pt; font-weight: bold; color: #98C379; }")
        else:
            self.ssrSettingsGroup.setTitle("                                                                                                                                                                                                                            OFF")
            self.ssrSettingsGroup.setStyleSheet("QGroupBox { font: 10pt; font-weight: bold; color: #E06C75; }")

        if self.currentMassFlow > 0:
            if not isSSRHeaterActive:
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
            default_q_design_e = 3750  # Default design heat power at -10°C
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
            -10: (1.0, 3750, 55),
            -7: (0.885, 4240, 52),
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

                    flowRate = dataDict.get('FlowRate', self.lastFlowRate)
                    self.flowRateLabel.setText(f"{flowRate} L/s")
                    self.lastFlowRate = flowRate

                    if 'FlowRate' in dataDict:
                        flowRateLPS = float(dataDict['FlowRate'])
                        self.currentMassFlow = flowRateLPS * 3600
                        self.flowRateLabel.setText(f"{flowRateLPS:.3f} L/s")

                        if self.currentBuildingModel:
                            self.addToSpreadsheet(time.strftime("%H:%M:%S", time.localtime()), dataDict['STemp'], dacVoltage, model_return_temp, flowRate, dataDict.get('RTemp', 'N/A'))
                        
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
            default_q_design_e = 3750  # Default design heat power at -10°C
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

    def updateBuildingModel(self, new_t_sup):
        if not hasattr(self, 't_sup_history'):
            self.t_sup_history = []
        if not hasattr(self, 't_ret_history'):
            self.t_ret_history = []

        self.t_sup_history.append(new_t_sup)

        last_t_ret = self.t_ret_history[-1] if self.t_ret_history else new_t_sup - 5

        if self.currentBuildingModel is None:
            return

        try:
            mass_flow = max(self.currentMassFlow / 3600.0, 0.001)

            self.currentBuildingModel.doStep(
                t_sup=new_t_sup, 
                t_ret_mea=last_t_ret, 
                m_dot=mass_flow, 
                stepSize=1, 
                q_dot_int=0 
            )

            new_t_ret = self.currentBuildingModel.t_ret

            if new_t_ret < 0:
                self.logToTerminal(f"Warning: Calculated return temperature is negative ({new_t_ret:.2f}°C). Resetting to last valid temperature.", messageType="warning")
                new_t_ret = last_t_ret

            self.t_ret_history.append(new_t_ret)

            dac_voltage = self.tempToVoltage(new_t_ret)
            self.sendSerialCommand(f"setVoltage {dac_voltage:.2f}")

        except Exception as e:
            self.logToTerminal(f"Failed to update building model: {e}", messageType="error")
            
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
        elif commandType in ['activateVirtualHeater', 'activateSSRHeater']:
            command = commandType
        else:
            print(f"Unknown command type: {commandType}")
            return
        
        self.sendSerialCommand(command)

    def initButtonClicked(self):
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
        self.ssrHeaterButton.setEnabled(True)
        self.dacVoltageInput.setEnabled(True)
        self.targetTempInput.setEnabled(True)
        self.toleranceInput.setEnabled(True)

        self.initializeBuildingModel()


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

    def addToSpreadsheet(self, timeData, temperature, dacVoltage, voltage, flowRate, returnTemperature):
        try:
            temperature = float(temperature) if temperature != 'N/A' else None
            dacVoltage = float(dacVoltage) if dacVoltage != 'N/A' else None
            voltage = float(voltage) if voltage != 'N/A' else None
            flowRate = float(flowRate) if flowRate != 'N/A' else None
            returnTemperature = float(returnTemperature) if returnTemperature != 'N/A' else None

            if any(value is None or value == 0 for value in [temperature, dacVoltage, voltage, flowRate, returnTemperature] if value is not None):
                self.logToTerminal("Skipping addition to spreadsheet due to zero or invalid value.", messageType="warning")
                return

            rowPosition = self.tableWidget.rowCount()
            self.tableWidget.insertRow(rowPosition)

            data = [timeData] + [f"{value:.2f}" if value is not None else "N/A" for value in [temperature, dacVoltage, voltage, flowRate, returnTemperature]]
            for index, item in enumerate(data):
                self.tableWidget.setItem(rowPosition, index, QTableWidgetItem(item))

            # Scroll to the newly added item for automatic scrolling
            item = self.tableWidget.item(rowPosition, 0)  # Assuming you want to scroll to the first column
            if item:
                self.tableWidget.scrollToItem(item)

        except ValueError as e:
            self.logToTerminal(f"Error processing data for spreadsheet: {e}", messageType="error")

    def exportToCSV(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filePath, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv);;All Files (*)", options=options)

        if filePath:
            try:
                with open(filePath, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(['Project Number', self.projectNumberInput.text()])
                    writer.writerow(['Client Name', self.clientNameInput.text()])
                    writer.writerow(['Date', self.dateInput.text()])
                    writer.writerow([])
                    headers = [self.tableWidget.horizontalHeaderItem(i).text() for i in range(self.tableWidget.columnCount())]
                    writer.writerow(headers)
                    for row in range(self.tableWidget.rowCount()):
                        row_data = []
                        for column in range(self.tableWidget.columnCount()):
                            item = self.tableWidget.item(row, column)
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

    def initGraphUpdateTimer(self):
        self.graphUpdateTimer = QTimer(self)
        self.graphUpdateTimer.timeout.connect(self.updateGraph)
        self.graphUpdateTimer.start(1000)

    def setupGraph(self):
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title('Temperature Profile Over Time')
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Temperature (°C)')
        self.canvas.draw()

        self.graphLayout.addWidget(self.canvas)

    def updateGraph(self):
        self.ax.clear()
        self.ax.set_title('Temperature Profile Over Time')
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Temperature (°C)')

        time_data, t_sup_data, t_ret_data = [], [], []

        for row in range(self.tableWidget.rowCount()):
            time_stamp = self.tableWidget.item(row, 0).text()
            t_sup = float(self.tableWidget.item(row, 1).text())
            t_ret_mea = float(self.tableWidget.item(row, 5).text())

            time_data.append(time_stamp)
            t_sup_data.append(t_sup)
            t_ret_data.append(t_ret_mea)

        self.ax.plot(time_data, t_sup_data, label='Supply Temp (t_sup)', marker='o', linestyle='-')
        self.ax.plot(time_data, t_ret_data, label='Return Temp Measured (t_ret_mea)', marker='x', linestyle='--')
        self.ax.legend()
        self.canvas.draw()
        self.canvas.flush_events()

    def closeEvent(self, event):
        dacVoltage = 0
        self.sendSerialCommand(f"setVoltage {dacVoltage}")

        if self.timer.isActive():
            self.timer.stop()

        if self.arduinoSerial and self.arduinoSerial.isOpen():
            self.arduinoSerial.close()
            self.logToTerminal("> Serial connection closed.")

        reply = QtWidgets.QMessageBox.question(self, 'Terminate Window', 'Are you sure you want to close the window?',
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    applyOneDarkProTheme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
