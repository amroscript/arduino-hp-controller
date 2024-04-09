"""This model is used to calculate the return flow of a building according to the compensation load method
in project EBC0955_DBU_Testmethoden_KAP_GES
@author: Stephan Göbel, date: 2023-01"""


class ThermalMass:
    def __init__(self, mcp, T_start):
        """
        Thermal mass must have initial temperature
        :param mcp: heat capacity [J/K]
        :param T_start: initial temperature [°C / K]
        """
        self.mcp = mcp
        self.T = T_start

    def qflow(self, Q):
        """
        calculates new temperature after energy input or output
        :param Q: Energy in Joule, positiv for increasing energy
        """
        self.T = self.T + Q/self.mcp

    def setT(self, T):
        """
        Sets temperature off mass directly
        :param T: new Temperature for mass
        """
        self.T = T


class TwoMassBuilding:
    def __init__(self, ua_hb, ua_ba, mcp_h,  mcp_b, t_a, t_start_h, t_flow_design, t_start_b=20,
                 boostHeat = False, maxPowBooHea = 0):
        """
        Init function, use either °C or K but not use both
        :param ua_hb: thermal conductivity [W/K] between transfer system (H) and Building (B)
        :param ua_ba: thermal conductivity [W/K] between building and environment
        :param mcp_h: heat capacity transfer system [J/kg K]
        :param t_start_h: initial temperature transfer system (H) [°C / K]
        :param mcp_b: heat capacity building [J/ kg K]
        :param t_start_b: initial temperature building [°C / K]
        :param t_a: ambient temperature [°C / K]
        """
        self.MassH = ThermalMass(mcp_h, t_start_h)
        self.MassB = ThermalMass(mcp_b, t_start_b)
        self.ua_hb = ua_hb
        self.ua_ba = ua_ba
        self.t_a = t_a
        self.boostHeat = boostHeat
        self.q_dot_hp = 0
        self.q_dot_hb = 0
        self.q_dot_ba = 0
        self.q_dot_int = 0
        self.q_dot_bh = 0
        self.t_ret = t_start_h
        self.t_flow_design = t_flow_design
        self.maxPowBooHea = maxPowBooHea

    def calcHeatFlows(self, m_dot, t_sup, t_ret_mea):
        """
        Calculates current heat flows between heat pump -- transfer system; transfer system -- building and
        building -- environment
        :param m_dot: measured value of mass flow [kg/s]
        :param t_sup: measured value of supply temperature [°C]
        :param t_ret_mea: measured value of return temperature [°C]
        """
        if self.boostHeat and t_sup < self.t_flow_design:
            self.q_dot_bh = m_dot*4183*(self.t_flow_design-t_sup)
            if self.q_dot_bh > self.maxPowBooHea:
                self.q_dot_bh = self.maxPowBooHea
        else:
            self.q_dot_bh = 0

        self.q_dot_hp = m_dot*4183*(t_sup-t_ret_mea)
        self.q_dot_hb = self.ua_hb * ((t_sup+self.MassH.T)/2 - self.MassB.T)
        self.q_dot_ba = self.ua_ba * (self.MassB.T - self.t_a)


    def calc_return(self, t_sup):
        """
        calculates return temperature
        assumption: temperature of heat transfer system is arithmetic mean temperature of supply and return temperature
        :param t_sup: current supply temperature
        :return: return temperature
        """
        t_ret = self.MassH.T
        return t_ret

    def doStep(self, t_sup, t_ret_mea, m_dot, stepSize, q_dot_int = 0):
        """
        step of one second:
        1) calculate current heat flows
        2) calculate new temperature of thermal masses
        3) calculates return temperature
        :param t_sup: [°C / K]
        :param m_dot: [kg/s]
        :param stepSize [s]
        :param t_ret_mea: measured value of return temperature [°C]
        :param q_dot_int: internal gain heat flow directly into building mass [W]
        :param boostHeat: virtual booster heater that increases temperature to set temperature
        """
        self.q_dot_int = q_dot_int
        # calc heat flows depending on current temperatures
        self.calcHeatFlows(m_dot=m_dot, t_sup=t_sup, t_ret_mea=t_ret_mea)
        # heat flow heat pump & booster heater - heat flow H-->B
        self.MassH.qflow((self.q_dot_hp + self.q_dot_bh - self.q_dot_hb)*stepSize)
        # heat flow H-->B - heat flow B-->A + heat flow internal gain
        self.MassB.qflow((self.q_dot_hb - self.q_dot_ba + self.q_dot_int)*stepSize)
        #  calculate new return temperature
        self.t_ret = self.calc_return(t_sup)

class CalcParameters:
    def __init__(self, t_a, q_design, t_flow_design, mass_flow, delta_T_cond=5, boostHeat=False, maxPowBooHea=7000):
        """
        Initialize parameters for a two-mass building model based on the provided system characteristics.

        :param t_a: Ambient temperature [°C]
        :param q_design: Design heating power [W]
        :param t_flow_design: Design flow temperature [°C]
        :param mass_flow: Mass flow [kg/s]
        :param delta_T_cond: Temperature difference between flow and return in the heating system [°C]
        :param boostHeat: Indicates if a booster heater is used
        :param maxPowBooHea: Maximum power of the booster heater [W]
        """
        self.t_a = t_a
        self.q_design = q_design
        self.t_flow_design = t_flow_design
        self.mass_flow = mass_flow
        self.delta_T_cond = delta_T_cond
        self.boostHeat = boostHeat
        self.maxPowBooHea = maxPowBooHea

        # Calculate thermal conductivities and capacities
        self.calculate_parameters()

    def calculate_parameters(self):
        # Example constants for thermal mass (specific heat capacity * mass)
        # These should be adjusted to reflect your building and system specifics
        c_p = 4186  # Specific heat capacity of water J/(kg*K)
        volume_h = 0.1  # Volume of water in the heating system [m^3]
        volume_b = 10  # Volume of water equivalent for building thermal mass [m^3]
        density_water = 997  # Density of water [kg/m^3]

        self.mcp_h = c_p * density_water * volume_h  # Thermal mass of heating system
        self.mcp_b = c_p * density_water * volume_b  # Thermal mass of building

        # Calculate thermal conductivities
        self.ua_hb = self.q_design / (self.t_flow_design - 0.5 * self.delta_T_cond - 20)  # Example indoor temp for calculation
        self.ua_ba = self.q_design / (20 - self.t_a)  # Assuming indoor temperature of 20°C for calculation

    def createBuilding(self):
        """
        Creates and returns a TwoMassBuilding instance with calculated parameters.
        """
        return TwoMassBuilding(ua_hb=self.ua_hb, ua_ba=self.ua_ba, mcp_h=self.mcp_h, mcp_b=self.mcp_b, t_a=self.t_a,
                               t_start_h=self.t_flow_design - self.delta_T_cond, t_flow_design=self.t_flow_design,
                               boostHeat=self.boostHeat, maxPowBooHea=self.maxPowBooHea)


