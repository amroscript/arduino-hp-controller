"""This model is used to calculate the return flow of a building according to the compensation load method
in project EBC0955_DBU_Testmethoden_KAP_GES
@author: Stephan Göbel, date: 2023-01"""


class ThermalMass:
    def __init__(self, mcp, T_start):
        """
        Initializes a ThermalMass object with a specific heat capacity and initial temperature.
        :param mcp: Heat capacity [J/K] (mass * specific heat capacity)
        :param T_start: Initial temperature [°C or K]
        """
        self.mcp = mcp
        self.T = T_start
        print(f"Initialized ThermalMass with mcp={self.mcp} J/K and T_start={self.T}°")

    def qflow(self, Q):
        """
        Calculates new temperature after energy input or output.
        :param Q: Energy in Joules, positive for increasing energy
        """
        old_temperature = self.T
        self.T = self.T + Q / self.mcp
        print(f"Temperature updated from {old_temperature}° to {self.T}° due to energy flow of {Q} Joules")

    def setT(self, T):
        """
        Sets the temperature of the mass directly.
        :param T: New temperature for the mass [°C or K]
        """
        print(f"Temperature set directly from {self.T}° to {T}°")
        self.T = T


class TwoMassBuilding:
    def __init__(self, ua_hb, ua_ba, mcp_h, mcp_b, t_a, t_start_h, t_flow_design, t_start_b=20,
                boostHeat=False, maxPowBooHea=0):
        """
        Initialize a two-mass building model with the given parameters.
        :param ua_hb: thermal conductivity [W/K] between transfer system (H) and Building (B)
        :param ua_ba: thermal conductivity [W/K] between building and environment
        :param mcp_h: heat capacity of the transfer system [J/kg K]
        :param mcp_b: heat capacity of the building [J/kg K]
        :param t_a: ambient temperature [°C / K]
        :param t_start_h: initial temperature of the transfer system (H) [°C / K]
        :param t_flow_design: design flow temperature [°C / K]
        :param t_start_b: initial temperature of the building (B), default 20°C
        :param boostHeat: flag to activate a virtual booster heater (True/False)
        :param maxPowBooHea: maximum power output of the booster heater [W]
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

        print("TwoMassBuilding initialized with the following parameters:")
        print("  Thermal Conductivity HB:", ua_hb, "[W/K]")
        print("  Thermal Conductivity BA:", ua_ba, "[W/K]")
        print("  MassH Heat Capacity:", mcp_h, "[J/kg K]")
        print("  MassB Heat Capacity:", mcp_b, "[J/kg K]")
        print("  Ambient Temperature:", t_a, "[°C / K]")
        print("  Initial Temp Transfer System (H):", t_start_h, "[°C / K]")
        print("  Initial Temp Building (B):", t_start_b, "[°C / K]")
        print("  Design Flow Temperature:", t_flow_design, "[°C / K]")
        print("  Boost Heat Enabled:", boostHeat)
        print("  Maximum Booster Heater Power:", maxPowBooHea, "[W]")

    def calcHeatFlows(self, m_dot, t_sup, t_ret_mea):
        """
        Calculates current heat flows between heat pump -- transfer system; transfer system -- building and
        building -- environment
        :param m_dot: measured value of mass flow [kg/s]
        :param t_sup: measured value of supply temperature [°C]
        :param t_ret_mea: measured value of return temperature [°C]
        """
        if self.boostHeat and t_sup < self.t_flow_design:
            self.q_dot_bh = m_dot * 4183 * (self.t_flow_design - t_sup)
            if self.q_dot_bh > self.maxPowBooHea:
                self.q_dot_bh = self.maxPowBooHea
        else:
            self.q_dot_bh = 0

        print("Boost Heat Calculation:")
        print("  boostHeat:", self.boostHeat)
        print("  m_dot:", m_dot)
        print("  t_sup:", t_sup)
        print("  t_flow_design:", self.t_flow_design)
        print("  q_dot_bh (Booster Heat):", self.q_dot_bh)

        self.q_dot_hp = m_dot * 4183 * (t_sup - t_ret_mea)
        self.q_dot_hb = self.ua_hb * ((t_sup + self.MassH.T) / 2 - self.MassB.T)
        self.q_dot_ba = self.ua_ba * (self.MassB.T - self.t_a)

        print("Heat Flow Calculations:")
        print("  q_dot_hp (Heat pump to transfer system):", self.q_dot_hp)
        print("  q_dot_hb (Transfer system to building):", self.q_dot_hb)
        print("    t_sup:", t_sup)
        print("    MassH.T:", self.MassH.T)
        print("    MassB.T:", self.MassB.T)
        print("  q_dot_ba (Building to ambient):", self.q_dot_ba)
        print("    MassB.T:", self.MassB.T)
        print("    t_a:", self.t_a)


    def calc_return(self, t_sup):
        """
        Calculates the return temperature.
        The assumption here is that the temperature of the heat transfer system (thermal mass H) represents the return temperature.
        :param t_sup: current supply temperature
        :return: return temperature
        """
        t_ret = self.MassH.T
        print("Calculating return temperature:")
        print("  Supply temperature (t_sup):", t_sup)
        print("  Current MassH temperature (assumed return temp):", t_ret)
        
        return t_ret

    def doStep(self, t_sup, t_ret_mea, m_dot, stepSize, q_dot_int=0):
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
        print("Step function started")
        print("Internal gains (q_dot_int):", self.q_dot_int)

        # calc heat flows depending on current temperatures
        self.calcHeatFlows(m_dot=m_dot, t_sup=t_sup, t_ret_mea=t_ret_mea)

        print("Applying energy flows for the step:")
        print("  Heat from HP & booster to transfer system (Q_in):", self.q_dot_hp + self.q_dot_bh)
        print("  Heat from transfer system to building (Q_out):", self.q_dot_hb)
        print("  Net heat into transfer system:", (self.q_dot_hp + self.q_dot_bh - self.q_dot_hb) * stepSize)
        
        # heat flow heat pump & booster heater - heat flow H-->B
        self.MassH.qflow((self.q_dot_hp + self.q_dot_bh - self.q_dot_hb) * stepSize)
        print("  Updated MassH temperature:", self.MassH.T)

        print("  Heat from building to ambient (Q_out):", self.q_dot_ba)
        print("  Net heat into building:", (self.q_dot_hb - self.q_dot_ba + self.q_dot_int) * stepSize)

        # heat flow H-->B - heat flow B-->A + heat flow internal gain
        self.MassB.qflow((self.q_dot_hb - self.q_dot_ba + self.q_dot_int) * stepSize)
        print("  Updated MassB temperature:", self.MassB.T)

        # calculate new return temperature
        self.t_ret = self.calc_return(t_sup)
        print("Updated return temperature to:", self.t_ret)


class CalcParameters:
    def __init__(self, t_a, q_design, t_flow_design, mass_flow, delta_T_cond=5, const_flow=True,  tau_b=55E6/263,
                 tau_h=505E3/258, t_b=20, boostHeat=False, maxPowBooHea=0):
        """
        Calculate parameters for a two-mass building model according to given parameters of a heat pump.
        Either a mass flow or a temperature difference on the condenser has to be provided.
        @param t_a: Nominal outdoor temperature [°C]
        @param q_design: Nominal heating power [W]
        @param t_flow_design: Nominal flow temperature [°C]
        @param t_b: Nominal building temperature (default value: 20 °C) [°C]
        @param mass_flow: Mass flow if const_flow = True [kg/s]
        @param delta_T_cond: Temperature difference t_flow-t_ret, if no constant mass flow [°C]
        @param const_flow: Calculate parameters with given mass flow (True) or given temperature difference (False)
        """
        self.t_a = t_a
        self.t_b = t_b
        self.q_design = q_design
        self.t_flow_design = t_flow_design
        self.const_flow = const_flow
        self.tau_b = tau_b
        self.tau_h = tau_h
        self.mass_flow = mass_flow
        self.delta_T_cond = delta_T_cond if not const_flow else self.q_design / (self.mass_flow * 4183)
        self.ua_ba = self.q_design / (self.t_b - self.t_a)
        self.ua_hb = self.q_design / (self.t_flow_design - 0.5 * self.delta_T_cond - self.t_b)
        self.t_start_h = self.t_flow_design - self.delta_T_cond
        self.mcp_b = self.tau_b * self.ua_ba
        self.mcp_h = self.tau_h * self.ua_hb
        self.boostHeat = boostHeat
        self.maxPowBooHea = maxPowBooHea

        print("Initialized CalcParameters with:")
        print(f"  Ambient Temperature: {self.t_a}°C")
        print(f"  Building Temperature: {self.t_b}°C")
        print(f"  Design Heating Power: {self.q_design}W")
        print(f"  Flow Temperature Design: {self.t_flow_design}°C")
        print(f"  Mass Flow: {self.mass_flow}kg/s")
        print(f"  Delta T Condenser: {self.delta_T_cond}°C")
        print(f"  UA Building-Ambient: {self.ua_ba}W/K")
        print(f"  UA Transfer-Building: {self.ua_hb}W/K")
        print(f"  Initial Temperature of Transfer System: {self.t_start_h}°C")
        print(f"  Heat Capacity of Building Mass: {self.mcp_b}J/K")
        print(f"  Heat Capacity of Transfer System: {self.mcp_h}J/K")
        print(f"  Boost Heat Enabled: {self.boostHeat}")
        print(f"  Max Power of Booster Heater: {self.maxPowBooHea}W")

    def createBuilding(self):
        building = TwoMassBuilding(ua_hb=self.ua_hb, ua_ba=self.ua_ba, mcp_h=self.mcp_h, mcp_b=self.mcp_b, t_a=self.t_a,
                                   t_start_h=self.t_start_h, t_start_b=self.t_b, t_flow_design=self.t_flow_design,
                                   boostHeat=self.boostHeat, maxPowBooHea = self.maxPowBooHea)
        print("Building created: Mass B = " + str(building.MassB.mcp) + " ua_ba = " + str(building.ua_ba) + "Mass H = "
              + str(building.MassH.mcp) + " ua_hb = " + str(building.ua_hb))
        return building
