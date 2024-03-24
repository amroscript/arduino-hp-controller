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
    QLineEdit, QGridLayout, QGroupBox, QHBoxLayout, QFrame, QSizePolicy, QPlainTextEdit, \
    QTabWidget, QTableWidget, QTableWidgetItem
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap
from PyQt5.QtCore import QTimer, Qt


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
        font-size: 12pt;
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
    QPushButton#initButton {
        background-color: #98C379;
    }
    QPushButton#initButton:hover {
        background-color: #A8D989; /* Lighter shade for hover on initButton */
    }
    QPushButton#updateButton {
        background-color: #61AFEF; /* Specific color for update button */
    }
    QPushButton#updateButton:hover {
        background-color: #72BFF7; /* Lighter shade for hover on update button */
    }
    QPushButton#stopButton {
        background-color: #E06C75; /* Specific color for stop button */
    }
    QPushButton#stopButton:hover {
        background-color: #EF7A85; /* Lighter shade for hover on stop button */
    }
    QTabBar::tab {
        min-width: 120px; 
        font-size: 10pt; /* Set the desired font size */
        font-family: 'Verdana'; 
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
        self.dacVoltageInput = None
        self.updateButton = None
        self.toleranceInput = None
        self.projectNumberInput = None
        self.temperatureLabel = None
        self.clientNameInput = None
        self.initButton = None
        self.dateInput = None
        self.terminal = None
        self.targetTempInput = None
        self.tableWidget = None

        self.setWindowTitle("")
        self.setGeometry(200, 200, 1000, 600)
        self.setupUI()
        applyOneDarkProTheme(QApplication.instance())

        self.arduinoSerial = None  # Initialize arduinoSerial attribute to None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateDisplay)
        self.timer.start(1000)  # Refresh rate in milliseconds
        self.initSerialConnection() # Initialize serial connection with Arduino

        self.updateButton.setEnabled(False)
        self.stopButton.setEnabled(False)
        self.virtualHeaterButton.setEnabled(False)
        self.ssrHeaterButton.setEnabled(False)
        self.dacVoltageInput.setEnabled(False)
        self.targetTempInput.setEnabled(False)
        self.toleranceInput.setEnabled(False)
        


    def initSerialConnection(self): 
            try:
                self.arduinoSerial = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
                self.logToTerminal("> Serial connection established.")
            except serial.SerialException as e:
                self.logToTerminal(f"> Error connecting to Arduino: {e}", messageType="error")
    
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
        For further clarification please consult the github repository documentation: https://github.com/amroscript/arduino-hp-controller.
        </p>
        """)
        instructionsLabel.setFont(QFont("Verdana", 12))
        instructionsLayout.addWidget(instructionsLabel)
        instructionsContainer = QWidget()
        instructionsContainer.setLayout(instructionsLayout)

        # Vertical line for separation
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #3B4048")

        mainLayout.addWidget(line)
        mainLayout.setStretchFactor(line, 2)
        line.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)

        # Right side layout for real-time data
        dataLayout = QGridLayout()
        self.temperatureLabel = QLabel("0°C")
        self.resistanceLabel = QLabel("0Ω")
        self.dacVoltageLabel = QLabel("0V")
        self.sensorVoltageLabel = QLabel("0V")
        self.flowRateLabel = QLabel("0L/s")

        bold_font = QFont()
        bold_font.setBold(True)
        self.temperatureLabel.setFont(bold_font)
        self.resistanceLabel.setFont(bold_font)
        self.dacVoltageLabel.setFont(bold_font)
        self.sensorVoltageLabel.setFont(bold_font)
        self.flowRateLabel.setFont(bold_font)

        dataLayout.addWidget(QLabel("↻ Temperature:"), 1, 0)
        dataLayout.addWidget(self.temperatureLabel, 1, 1)
        dataLayout.addWidget(QLabel("Resistance:"), 0, 0)
        dataLayout.addWidget(self.resistanceLabel, 0, 1)
        dataLayout.addWidget(QLabel("Sensor Voltage:"), 2, 0)
        dataLayout.addWidget(self.sensorVoltageLabel, 2, 1)
        dataLayout.addWidget(QLabel("↻ Flow Rate:"), 3, 0)
        dataLayout.addWidget(self.flowRateLabel, 3, 1)
        dataLayout.addWidget(QLabel("⇈ DAC Voltage:"), 4, 0)
        dataLayout.addWidget(self.dacVoltageLabel, 4, 1)
        dataContainer = QWidget()
        dataContainer.setLayout(dataLayout)

        # Add instructions container, vertical line, and data container to the main layout
        mainLayout.addWidget(instructionsContainer)
        mainLayout.addWidget(line)  # Adding the line here for separation
        mainLayout.addWidget(dataContainer)

        return group

    def createControlGroup(self):
        group = QGroupBox("Control Settings")
        group.setFont(QFont("Verdana", 12, QFont.Bold))

        layout = QGridLayout(group)

        # Heater Mode Buttons Setup
        self.heaterButtonGroup = QtWidgets.QButtonGroup(group)  # Group buttons logically
        self.virtualHeaterButton = QPushButton("Virtual Heater")
        self.ssrHeaterButton = QPushButton("SSR Heater")

        for btn in [self.virtualHeaterButton, self.ssrHeaterButton]:
            btn.setCheckable(True)
            self.heaterButtonGroup.addButton(btn)
            btn.setMaximumHeight(40)  # Set a fixed height

        self.virtualHeaterButton.setChecked(True)  # Default selection

        # Connect buttons to the toggle function
        self.virtualHeaterButton.clicked.connect(lambda: self.toggleHeaterMode(True))
        self.ssrHeaterButton.clicked.connect(lambda: self.toggleHeaterMode(False))

        # Adjust button layout to remove gaps
        heaterButtonLayout = QHBoxLayout()
        heaterButtonLayout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        heaterButtonLayout.setSpacing(0)  # Remove spacing
        heaterButtonLayout.addWidget(self.virtualHeaterButton)
        heaterButtonLayout.addWidget(self.ssrHeaterButton)

        # Add layout to a container widget for proper alignment
        buttonContainer = QWidget()
        buttonContainer.setLayout(heaterButtonLayout)
        layout.addWidget(QLabel("Select Heater Mode:"), 0, 0)
        layout.addWidget(buttonContainer, 0, 1)

        # Update styling based on the initial state
        self.updateHeaterButtons(True)

        # Target Temperature Controls
        layout.addWidget(QLabel("Target Temperature (°C):"), 1, 0)
        self.targetTempInput = QLineEdit("25")
        layout.addWidget(self.targetTempInput, 1, 1)
        self.addControlWithButtons(layout, self.targetTempInput, 1, 2)

        # Temperature Tolerance Controls
        layout.addWidget(QLabel("Temperature Tolerance (±°C):"), 2, 0)
        self.toleranceInput = QLineEdit("0.1")
        layout.addWidget(self.toleranceInput, 2, 1)
        self.addControlWithButtons(layout, self.toleranceInput, 2, 2)

        # DAC Voltage Output Controls
        layout.addWidget(QLabel("DAC Voltage Output (V):"), 3, 0)
        self.dacVoltageInput = QLineEdit("0.0")
        layout.addWidget(self.dacVoltageInput, 3, 1)
        self.addControlWithButtons(layout, self.dacVoltageInput, 3, 2)

        # Initialize, Stop, and Update Settings Buttons
        self.initButton = QPushButton("Initialize")
        self.stopButton = QPushButton("Stop")
        self.updateButton = QPushButton("Update Settings")
        layout.addWidget(self.initButton, 4, 0, 1, 2)
        layout.addWidget(self.updateButton, 5, 0, 1, 2)
        layout.addWidget(self.stopButton, 6, 0, 1, 2)
        self.initButton.clicked.connect(self.initButtonClicked)
        self.stopButton.clicked.connect(self.stopOperations)
        self.updateButton.clicked.connect(self.updateSettings)

        group.setLayout(layout)
        return group

    def applyButtonStyles(self):
        # Updated styles with font-size property
        buttonFontSize = "10pt"  # Example font size, adjust as needed
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

    def addSettingWithButtons(self, layout, labelText, lineEdit, increment):
        rowLayout = QHBoxLayout()
        label = QLabel(labelText)
        upButton = QPushButton("+")
        downButton = QPushButton("−")
        
        # Connect buttons to increment/decrement actions
        upButton.clicked.connect(lambda: self.adjustValue(lineEdit, increment))
        downButton.clicked.connect(lambda: self.adjustValue(lineEdit, -increment))

        # Add widgets to row layout
        rowLayout.addWidget(label)
        rowLayout.addWidget(lineEdit)
        rowLayout.addWidget(upButton)
        rowLayout.addWidget(downButton)

        # Add row layout to the main settings layout
        layout.addLayout(rowLayout)

    def adjustValue(self, lineEdit, increment):
        try:
            currentValue = float(lineEdit.text())
            newValue = currentValue + increment
            lineEdit.setText(f"{newValue:.2f}")
        except ValueError:
            # Handle error if the line edit does not contain a valid number
            lineEdit.setText("0.0")

    def toggleHeaterMode(self, isVirtualHeaterActive):
        self.virtualHeaterButton.setChecked(isVirtualHeaterActive)
        self.ssrHeaterButton.setChecked(not isVirtualHeaterActive)
        self.updateHeaterButtons(isVirtualHeaterActive)
        
        # Enable "Update Settings" only if SSR Heater is active
        self.updateButton.setEnabled(not isVirtualHeaterActive)
        
        if isVirtualHeaterActive:
            # Example of reinitializing the building model with boost heat enabled
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
            # Reinitialize without boost heat if needed
            print("Boost heat deactivated.")
        

    def updateHeaterButtons(self, virtualHeaterActive):
        activeStyle = """
            QPushButton {
                background-color: #E5C07B; /* Black for activated button */
                color: white;
                border: 2px solid #E5C07B;
            }
        """
        inactiveStyle = """
            QPushButton {
                background-color: #5C6370; /* Grey for unactivated button */
                color: white;
                border: 2px solid #5C6370;
            }
            QPushButton:hover {
                background-color: #666666; /* Slightly lighter grey for hover */
            }
        """

        if virtualHeaterActive:
            self.virtualHeaterButton.setStyleSheet(activeStyle)
            self.ssrHeaterButton.setStyleSheet(inactiveStyle)
        else:
            self.virtualHeaterButton.setStyleSheet(inactiveStyle)
            self.ssrHeaterButton.setStyleSheet(activeStyle)


    def addControlWithButtons(self, layout, lineEdit, row, columnSpan):
        upButton = QPushButton("+")
        downButton = QPushButton("–")

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
                                self.temperatureLabel.setText(f"{value}°C")
                                temperature = float(value)
                            elif key.strip() == 'Res':
                                self.resistanceLabel.setText(f"{value}Ω")
                                resistance = float(value)  # Assuming you want to plot or use this later
                            elif key.strip() == 'DACVolt':
                                self.dacVoltageLabel.setText(f"{value}V")
                                dacVoltage = float(value)
                            elif key.strip() == 'SensorVolt':
                                self.sensorVoltageLabel.setText(f"{value}V")
                                sensorVoltage = float(value)  # Assuming you want to plot or use this later
                            elif key.strip() == 'FlowRate':
                                self.flowRateLabel.setText(f"{value}L/s")
                                flowRate = float(value)
                        except ValueError as ve:
                            print(f"Error parsing field: {field}. Error: {ve}")

                    # Ensure there's valid temperature and flowRate data before appending
                    if temperature is not None and flowRate is not None:
                        self.time_data.append(currentTime)
                        self.temperature_data.append(temperature)
                        self.flow_rate_data.append(flowRate)
                        self.updateGraph()  # Update the graph with new data
                        self.addToSpreadsheet(currentTime, temperature, resistance, dacVoltage, sensorVoltage, flowRate)  # Pass currentTime as the first argument
                else:
                    # Handle or log non-key:value messages if necessary
                    print(f"Non-data message received: {serialData}")
        except serial.SerialException as e:
            self.logToTerminal(f"> Error reading from serial: {e}", messageType="error")

    def handleNewData(self, time, temperature, flowRate):
        self.time_data.append(time)
        self.temperature_data.append(temperature)
        self.flow_rate_data.append(flowRate)

    def initButtonClicked(self):
        # Optionally, re-open the serial connection if it was closed
        if self.arduinoSerial is None or not self.arduinoSerial.isOpen():
            try:
                self.arduinoSerial = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
                self.logToTerminal("> Serial connection re-established.")
            except serial.SerialException as e:
                self.logToTerminal(f"> Error reconnecting to Arduino: {e}", messageType="error")
                return  # Early return if connection fails

        # Restart the QTimer
        if not self.timer.isActive():
            self.timer.start(1000)  # Adjust the interval as necessary
            self.logToTerminal("> Timer restarted.")

        self.logToTerminal("> System (re-)initialized.")

        # Enable buttons upon initialization
        self.stopButton.setEnabled(True)
        self.virtualHeaterButton.setEnabled(True)
        self.ssrHeaterButton.setEnabled(True)
        self.dacVoltageInput.setEnabled(True)
        self.targetTempInput.setEnabled(True)
        self.toleranceInput.setEnabled(True)

    def updateSettings(self):
        # Retrieve the values from the input fields
        temp = self.targetTempInput.text()
        tol = self.toleranceInput.text()
        dacV = self.dacVoltageInput.text()

        # Construct command strings for each setting
        tempCommand = f"setTemp {temp}\n"
        tolCommand = f"setTolerance {tol}\n"
        dacVCommand = f"setVoltage {dacV}\n"

        # Check if the serial connection is established
        if self.arduinoSerial and self.arduinoSerial.isOpen():
            try:
                # Sending the temperature setting command
                self.arduinoSerial.write(tempCommand.encode('utf-8'))
                self.logToTerminal(f"> Temperature setting command sent: {tempCommand.strip()}")

                # Sending the tolerance setting command
                self.arduinoSerial.write(tolCommand.encode('utf-8'))
                self.logToTerminal(f"> Tolerance setting command sent: {tolCommand.strip()}")

                # Sending the DAC voltage setting command
                self.arduinoSerial.write(dacVCommand.encode('utf-8'))
                self.logToTerminal(f"> DAC Voltage setting command sent: {dacVCommand.strip()}")
            except serial.SerialException as e:
                self.logToTerminal(f"> Error sending settings to Arduino: {e}", messageType="error")
        else:
            self.logToTerminal("> Serial connection not established. Unable to send settings.", messageType="error")

    def stopOperations(self):
        # Stop the QTimer
        if self.timer.isActive():
            self.timer.stop()
            self.logToTerminal("> Timer stopped.")
        
        # Optionally, close the serial connection
        if self.arduinoSerial and self.arduinoSerial.isOpen():
            self.arduinoSerial.close()
            self.logToTerminal("> Serial connection closed.")
        
        self.logToTerminal("> Operations halted.")

        # Disable buttons to require re-initialization
        self.updateButton.setEnabled(False)
        self.stopButton.setEnabled(False)
        self.virtualHeaterButton.setEnabled(False)
        self.ssrHeaterButton.setEnabled(False)
        self.dacVoltageInput.setEnabled(False)
        self.targetTempInput.setEnabled(False)
        self.toleranceInput.setEnabled(False)


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

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    applyOneDarkProTheme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
