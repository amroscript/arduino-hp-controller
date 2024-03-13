import sys, pyserial
# import random # simulation
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, \
    QLineEdit, QGridLayout, QGroupBox, QHBoxLayout, QFrame, QSizePolicy, QMessageBox, QPlainTextEdit
from PyQt5.QtGui import QFont, QColor, QPalette, QPixmap
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, Qt

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

    # Additional style sheet for further customization
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
    QGroupBox {
        border: 2px solid #3B4048; 
        margin-top: 20px; 
        padding: 5px; 
        border-radius: 5px; 
        background-color: #282C34; 
    }
    """)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("")
        self.setGeometry(200, 200, 1000, 800) 
        self.setupUI()
        applyOneDarkProTheme(QApplication.instance())
        self.initSerialConnection() # Initialize serial connection with Arduino

    def initSerialConnection(self):
        """Initialize serial connection to Arduino."""
        try:
            # Setup serial connection (Adjust 'COM3' and 9600 according to your setup)
            self.arduinoSerial = serial.Serial('COM3', 9600, timeout=1)
        except serial.SerialException as e:
            print(f"Error connecting to Arduino: {e}")

    def setupUI(self):
        self.setFont(QFont("Verdana", 12))
        mainLayout = QVBoxLayout()

        self.logoLabel = QLabel() # Logo set-up
        logoPixmap = QPixmap("Arduino Controller.png")
        scaledLogoPixmap = logoPixmap.scaled(550, 350, Qt.KeepAspectRatio)
        self.logoLabel.setPixmap(scaledLogoPixmap)
        self.logoLabel.setAlignment(Qt.AlignCenter)
        mainLayout.addWidget(self.logoLabel)

        self.measurementGroup = self.createMeasurementGroup()
        self.controlGroup = self.createControlGroup()
        self.terminal = self.createTerminal()

        # Directly add groups and terminal to the main layout
        mainLayout.addWidget(self.measurementGroup)
        mainLayout.addWidget(self.controlGroup)
        mainLayout.addWidget(self.terminal, 1)  # Give the terminal some stretch factor

        self.setCentralWidget(QWidget())
        self.centralWidget().setLayout(mainLayout)

        self.thread = MockArduinoThread()
        self.thread.updated.connect(self.updateDisplay)
        self.thread.start()

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
        For further clarification please consult documentation.
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
        self.temperatureLabel = QLabel("Temperature: 0°C")
        self.resistanceLabel = QLabel("Resistance: 0Ω")
        self.dacVoltageLabel = QLabel("DAC Voltage: 0V")
        self.flowRateLabel = QLabel("Flow Rate: 0L/s")

        bold_font = QFont()
        bold_font.setBold(True)
        self.temperatureLabel.setFont(bold_font)
        self.resistanceLabel.setFont(bold_font)
        self.dacVoltageLabel.setFont(bold_font)
        self.flowRateLabel.setFont(bold_font)

        dataLayout.addWidget(QLabel("Temperature:"), 1, 0)
        dataLayout.addWidget(self.temperatureLabel, 1, 1)
        dataLayout.addWidget(QLabel("Resistance:"), 0, 0)
        dataLayout.addWidget(self.resistanceLabel, 0, 1)
        dataLayout.addWidget(QLabel("DAC Voltage:"), 3, 0)
        dataLayout.addWidget(self.dacVoltageLabel, 3, 1)
        dataLayout.addWidget(QLabel("Flow Rate:"), 2, 0)
        dataLayout.addWidget(self.flowRateLabel, 2, 1)
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

        self.targetTempInput = QLineEdit("25")
        self.toleranceInput = QLineEdit("0.1")
        self.dacVoltageInput = QLineEdit("2.5")

        self.addControlWithButtons(layout, "Target Temperature (°C):", self.targetTempInput, 1)
        self.addControlWithButtons(layout, "Temperature Tolerance (±°C):", self.toleranceInput, 0.1)
        self.addControlWithButtons(layout, "DAC Voltage Output (V):", self.dacVoltageInput, 1)

        self.updateButton = QPushButton("Update Settings")
        self.updateButton.setObjectName("updateButton")
        self.updateButton.setStyleSheet("background-color: #61AFEF;")  # Green
        self.updateButton.clicked.connect(self.updateSettings)

        self.stopButton = QPushButton("Stop")
        self.stopButton.setObjectName("stopButton")
        self.stopButton.setStyleSheet("background-color: #E06C75;")  # Red
        self.stopButton.clicked.connect(self.stopOperations)

        self.updateButton.setEnabled(False)  # Initially disabled
        self.stopButton.setEnabled(False)  # Initially disabled

        layout.addWidget(self.updateButton, 4, 0, 1, 2)
        layout.addWidget(self.stopButton, 5, 0, 1, 2)

        self.initButton = QPushButton("Initialize")
        self.initButton.setObjectName("initButton")  # Use this name in your stylesheet if you want to apply styles
        self.initButton.clicked.connect(self.initButtonClicked)

        self.initButton.setMinimumHeight(75)  # Set a minimum height for the button.
        layout.addWidget(self.initButton, 4, 2, 2, 1)
        layout.setRowStretch(4, 1)
        layout.setRowStretch(5, 1)

        return group

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

    def addControlWithButtons(self, layout, label, lineEdit, increment):
        rowIndex = layout.rowCount()
        layout.addWidget(QLabel(label), rowIndex, 0)
        layout.addWidget(lineEdit, rowIndex, 1)

        upButton = QPushButton("+")
        downButton = QPushButton("–")
        upButton.clicked.connect(lambda: self.adjustValue(lineEdit, increment))
        downButton.clicked.connect(lambda: self.adjustValue(lineEdit, -increment))

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(upButton)
        buttonLayout.addWidget(downButton)
        container = QWidget()
        container.setLayout(buttonLayout)
        layout.addWidget(container, rowIndex, 2)

    def adjustValue(self, lineEdit, increment):
        currentValue = float(lineEdit.text())
        newValue = currentValue + increment
        lineEdit.setText(f"{newValue:.1f}" if increment < 1 else f"{newValue}")

    def updateDisplay(self, data):
        temperature, resistance, dacVoltage, flowRate = data.split(', ')
        self.temperatureLabel.setText(f"{temperature}°C")
        self.resistanceLabel.setText(f"{resistance}Ω")
        self.dacVoltageLabel.setText(f"{dacVoltage}V")
        self.flowRateLabel.setText(f"{flowRate}L/s")

    def updateSettings(self):
        temp = self.targetTempInput.text()
        tol = self.toleranceInput.text()
        dacV = self.dacVoltageInput.text()
        self.logToTerminal(f"> Control settings updated: Temp= {temp}, Tolerance= {tol}, DAC Voltage= {dacV}.")

    def stopOperations(self):
        self.thread.terminate()
        self.logToTerminal("> Operations halted.")

    def initButtonClicked(self): 
        self.thread.terminate()
        self.logToTerminal("> System initialized.")
    
        # Enable the Update Settings and Stop buttons
        self.updateButton.setEnabled(True)
        self.stopButton.setEnabled(True)

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


class MockArduinoThread(QThread):
    updated = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.timer = QTimer()
        self.timer.timeout.connect(self.generateData)
        self.timer.start(1000)

    def generateData(self):
        temperature = str(random.randint(20, 30))
        resistance = str(random.randint(100, 200))
        dacVoltage = f"{random.uniform(0, 5):.2f}"
        flowRate = f"{random.uniform(0, 1):.2f}"
        self.updated.emit(f"{temperature}, {resistance}, {dacVoltage}, {flowRate}")


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    applyOneDarkProTheme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
