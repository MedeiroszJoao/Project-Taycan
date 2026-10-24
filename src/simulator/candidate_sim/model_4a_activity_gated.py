from __future__ import annotations
"""Experimental strict-energy Taycan 1RC candidate, NOT approved Stage 3 model.

Derived from the isolated bidirectional candidate. This revision changes the
thermal model and charge boundary policy deliberately. The source may be tested
but MUST NOT be passed to the sealed Stage 4 runner as the frozen model.
"""
"""Etapa 3 — circuito equivalente 1RC/ramo com 168 grupos 2p e perdas térmicas.

Positivo: corrente de descarga da bateria. OCV, resistências, sensores e
perdas NÃO estão calibrados para o Porsche Taycan; são hipóteses declaradas.
A física oculta é separada das observações autorizadas.
"""
from dataclasses import dataclass, field
from typing import Optional
import math
import random
import json
from pathlib import Path

N_MODULES = 28
GROUPS_PER_MODULE = 6
N_GROUPS = N_MODULES * GROUPS_PER_MODULE
BRANCHES = 2
FAULT_IDS = ("H00", "B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09", "M01", "I01")
CATALOG = frozenset(json.loads((Path(__file__).parent / 'signal_contract.json').read_text(encoding='utf8'))['approved_ids'])


@dataclass(frozen=True)
class ModelConfig:
    seed: int = 20261011
    dt_s: float = 1.0
    steps: int = 180
    acquisition_mode: str = "independent"  # independent | shared
    sensor_noise: bool = True
    counter_source: str = "BMS_I"  # BMS_I | HVBAT_CURRENT | truth (ablation only)
    diff_motor_t_mapping: str = "winding_proxy"  # winding_proxy | uninformative
    aging_index: float = 0.15
    aging_rate_per_s: float = 1e-8
    capacity_ah_cell: float = 64.5
    r0_ohm_cell: float = 0.0006  # ASSUMIDO; Req_pack=168*r0/2=0.0504 ohm at 25C, age0
    r1_ohm_cell: float = 0.00025  # ASSUMIDO; 1RC polarization branch
    rc_tau_s: float = 75.0
    ocv_low_v: float = 3.15
    ocv_span_v: float = 0.96
    ocv_temp_coeff_v_per_K: float = 0.0002
    resistance_cold_coeff_per_K: float = 0.012
    age_capacity_loss: float = 0.12
    age_resistance_gain: float = 0.28
    group_soc_spread: float = 0.004
    branch_soc_spread: float = 0.006
    branch_r_spread: float = 0.12
    initial_soc: float = 0.74
    module_temp_variation_C: float = 0.35
    resistance_reference_C: float = 25.0
    coolant_exchange_W_per_K: float = 4000.0
    isolation_sensor_modulation_frac: float = 0.01
    driver_rpm_period_s: float = 37.0
    driver_rpm_fast_period_s: float = 9.0
    driver_torque_period_s: float = 27.0
    driver_torque_fast_period_s: float = 11.0
    b01_capacity_extra_loss: float = 0.30
    b02_r0_extra_gain: float = 1.50
    b03_local_capacity_loss: float = 0.50
    b04_leak_min_A: float = 0.05
    b04_leak_gain_A: float = 0.45
    b05_voltage_offset_V: float = 0.07
    b06_current_offset_A: float = 9.0
    b07_cooling_loss_fraction: float = 0.88
    b08_temperature_offset_C: float = 7.0
    b09_iso_loss_fraction: float = 0.96
    driver_rpm_baseline: float = 3200.0
    driver_rpm_swing: float = 650.0
    driver_rpm_fast_swing: float = 200.0
    driver_torque_baseline: float = 90.0
    driver_torque_swing: float = 24.0
    driver_torque_fast_swing: float = 9.0
    front_torque_fraction: float = 0.48
    sensor_temp_spacing_C: float = 0.075
    module_heat_j_per_K: float = 70000.0
    module_cooling_w_per_K: float = 34.0
    coolant_C: float = 25.0
    init_module_C: float = 31.0
    motor_heat_j_per_K: float = 65000.0
    motor_cooling_w_per_K: float = 85.0
    motor_init_C: float = 42.0
    motor_copper_coeff_w_per_nm2: float = 0.033
    motor_iron_coeff_w_per_krpm2: float = 40.0
    motor_loss_fault_multiplier: float = 2.0
    inverter_efficiency: float = 0.975
    inverter_fault_extra_W: float = 1600.0
    gearbox_loss_fraction: float = 0.015  # nuisance, not a new subsystem
    auxiliary_mean_W: float = 1900.0
    auxiliary_amplitude_W: float = 750.0
    auxiliary_phase_rad: float = 0.0
    # Observer ONLY reads reported group voltage/current/temperature, never latent SOC.
    soc_observer_ocv_bias_V: float = 0.005  # ASSUMIDO [−0.02, +0.02]
    soc_observer_noise_frac: float = 0.004  # ASSUMIDO [0, 0.02]
    bms_soc_bias_frac: float = 0.002  # ASSUMIDO [−0.02, +0.02]
    current_noise_A: float = 0.06
    voltage_noise_V: float = 0.001
    temperature_noise_C: float = 0.04
    nominal_isolation_kohm: float = 3000.0
    nominal_hvil_V: float = 5.0
    nominal_hvil_mA: float = 3.0
    # Experimental Stage 4 boundary inputs; zero/unity reproduce frozen model.
    external_charge_power_W: float = 0.0  # idealized power at HV DC bus; NOT grid AC power
    traction_torque_scale: float = 1.0
    regeneration_torque_scale: float = 1.0

    def __post_init__(self):
        if self.counter_source not in {"BMS_I", "HVBAT_CURRENT", "truth"}:
            raise ValueError('counter_source must be BMS_I/HVBAT_CURRENT/truth')
        if self.diff_motor_t_mapping not in {"winding_proxy", "uninformative"}:
            raise ValueError('diff_motor_t_mapping must be winding_proxy/uninformative')
        if self.acquisition_mode not in {"independent", "shared"}:
            raise ValueError('acquisition_mode must be independent/shared')
        if not (0 < self.dt_s <= 20 and 2 <= self.steps <= 50000):
            raise ValueError('dt_s or steps outside model bounds')
        if not (0 <= self.aging_index <= 1.0):
            raise ValueError('aging_index outside [0,1]')
        if min(self.coolant_exchange_W_per_K,self.driver_rpm_period_s,self.driver_rpm_fast_period_s,self.driver_torque_period_s,self.driver_torque_fast_period_s,self.capacity_ah_cell, self.r0_ohm_cell, self.r1_ohm_cell, self.rc_tau_s,
               self.module_heat_j_per_K, self.motor_heat_j_per_K, self.nominal_isolation_kohm) <= 0:
            raise ValueError('physical model denominator must be positive')
        if not (0.01 < self.initial_soc < 0.99):
            raise ValueError('initial_soc must be in (0.01,0.99)')
        if not (0.1 < self.inverter_efficiency < 1):
            raise ValueError('inverter efficiency must be in (0.1,1)')
        if not (math.isfinite(self.external_charge_power_W) and 0 <= self.external_charge_power_W <= 250000):
            raise ValueError('external_charge_power_W must be finite and within [0,250000]')
        if not all(math.isfinite(x) and 0 < x <= 3 for x in
                   (self.traction_torque_scale, self.regeneration_torque_scale)):
            raise ValueError('torque scales must be finite in (0,3]')


@dataclass(frozen=True)
class Fault:
    id: str = "H00"
    module: int = 7
    group: int = 3  # one-based, within module
    branch: str = "A"  # B04: A or B
    channel: str = "TAYCAN_BMS_I"  # B06 current channel
    temperature_sensor: int = 2
    severity: float = 1.0  # [0,1]; nominal=0; strength mapped by fault family

    def __post_init__(self):
        if self.id not in FAULT_IDS:
            raise ValueError(f'unknown fault ID {self.id}')
        if not (1 <= self.module <= N_MODULES and 1 <= self.group <= GROUPS_PER_MODULE):
            raise ValueError('module/group not in 28x6')
        if self.branch not in ('A', 'B') or self.temperature_sensor not in (1, 2, 3):
            raise ValueError('branch/sensor invalid')
        if self.channel not in ('TAYCAN_BMS_I', 'TAYCAN_HVBAT_CURRENT'):
            raise ValueError('current channel invalid')
        if not (0 <= self.severity <= 1):
            raise ValueError('severity must be in [0,1]')


@dataclass
class SimResult:
    observations: list[dict[str, float]]
    truth: list[dict]
    fault: Fault
    metadata: dict


def _ocv(z: float, t_C: float, p: ModelConfig) -> float:
    return p.ocv_low_v + p.ocv_span_v * min(1, max(0, z)) + p.ocv_temp_coeff_v_per_K * (t_C - 25)


def _driver(t: float, p: ModelConfig) -> tuple[float,float]:
    """ASSUMIDO: rotor speed [rpm] and torque [Nm] for equivalent driveline."""
    rpm = p.driver_rpm_baseline + p.driver_rpm_swing*math.sin(t/p.driver_rpm_period_s) + p.driver_rpm_fast_swing*math.sin(t/p.driver_rpm_fast_period_s)
    torque = p.driver_torque_baseline + p.driver_torque_swing*math.sin(t/p.driver_torque_period_s) + p.driver_torque_fast_swing*math.cos(t/p.driver_torque_fast_period_s)
    return rpm, torque


def _init_branches(p: ModelConfig, fault: Fault, rng: random.Random):
    z, r_mult, q_mult, polar = [], [], [], []
    for g in range(N_GROUPS):
        mean = p.initial_soc + rng.gauss(0, p.group_soc_spread)
        s = rng.gauss(0, p.branch_soc_spread)
        z.append([mean + s, mean - s])
        rd = rng.gauss(0, p.branch_r_spread)
        r_mult.append([max(0.5, 1+rd),max(0.5, 1-rd)])
        q_mult.append([1.0, 1.0])
        polar.append([0.0,0.0])
    ix=(fault.module-1)*GROUPS_PER_MODULE+fault.group-1
    if fault.id == 'B03':
        q_mult[ix] = [1-p.b03_local_capacity_loss*fault.severity,1-p.b03_local_capacity_loss*fault.severity]
    if fault.id == 'B04':
        # Deliberately asymmetric initial branches: swapping whole A/B state
        # and leakage designation must leave the measured parallel V invariant.
        pass
    return z,r_mult,q_mult,polar


def _positive_power_current(voc_v: float, r_eq_ohm: float, demand_W: float) -> float:
    disc = voc_v*voc_v - 4*r_eq_ohm*demand_W
    if disc <= 0:
        raise ValueError('requested power exceeds model steady-state feasibility')
    return 2*demand_W/(voc_v + math.sqrt(disc))  # stable form




def _rc_exact_step(v0_V: float, current_A: float, r1_ohm: float, tau_s: float, dt_s: float):
    """Exact 1RC step for constant current, resistance and time constant over dt.

    Returns (v1[V], Q_R1[J], delta_E_cap[J], input_work[J]). The identity
    input_work = Q_R1 + delta_E_cap holds without equating I*V_RC to heat.
    C= tau/R1 [F]. Aging/temperature parameter changes BETWEEN steps are not
    included in this per-step identity and require their own constitutive law.
    """
    if not all(math.isfinite(x) for x in (v0_V,current_A,r1_ohm,tau_s,dt_s)):
        raise ValueError('nonfinite RC step input')
    if min(r1_ohm,tau_s,dt_s)<=0:
        raise ValueError('RC R, tau, dt must be strictly positive')
    h=dt_s/tau_s
    one_minus_e=-math.expm1(-h)
    one_minus_e2=-math.expm1(-2*h)
    v_inf=current_A*r1_ohm
    difference=v0_V-v_inf
    v1=v_inf+difference*(1-one_minus_e)
    # Integrate V(t)^2/R1 exactly; no forward-Euler heat approximation.
    joules=(v_inf*v_inf*dt_s
        +2*v_inf*difference*tau_s*one_minus_e
        +difference*difference*tau_s*one_minus_e2/2)/r1_ohm
    capacitance_F=tau_s/r1_ohm
    delta_storage_J=capacitance_F*(v1*v1-v0_V*v0_V)/2
    work_J=current_A*(v_inf*dt_s+difference*tau_s*one_minus_e)
    # Numerical roundoff is bounded relative to energy scale, never used to
    # hide a materially negative dissipative heat prediction.
    tol=1e-9*max(1.,abs(work_J),abs(delta_storage_J),abs(joules))
    if joules < -tol or abs(work_J-joules-delta_storage_J)>tol:
        raise ArithmeticError('RC energy identity violated')
    return v1, max(0.,joules), delta_storage_J, work_J


def _integrate_soc_strict(soc: float, current_A: float, capacity_Ah: float, dt_s:float,
                          *, step:int, group:int, branch:int, mechanism:str='terminal') -> float:
    """Reject impossible charge trajectories; never discard charge via SOC clip."""
    if not (math.isfinite(soc) and math.isfinite(current_A) and math.isfinite(capacity_Ah)) or capacity_Ah<=0:
        raise ValueError(f'invalid SOC integration data step={step} group={group} branch={branch}')
    trial=soc-current_A*dt_s/(3600*capacity_Ah)
    if not (0<=trial<=1):
        raise ValueError(f'SOC_BOUNDARY_VIOLATION step={step} group={group} branch={branch} '
                         f'mechanism={mechanism} proposed_SOC={trial:.12g} '
                         f'current_A={current_A:.9g}')
    return trial

def simulate(fault: Fault = Fault(), p: ModelConfig = ModelConfig(), *,
             swap_branches: bool = False, torque_trace_nm=None, auxiliary_trace_W=None,
             rpm_trace_rpm=None, external_charge_trace_W=None) -> SimResult:
    """Execute fixed truth-injected scenario. swap_branches exchanges hidden 2p labels.

    Observations contain approved OBDb IDs only; truth contains inaccessible latent
    branch currents/SOC, true power and auxiliary loads for tests, NOT for models.
    """
    if torque_trace_nm is not None:
        if len(torque_trace_nm) != p.steps or not all(math.isfinite(x) for x in torque_trace_nm):
            raise ValueError('torque_trace_nm must contain one finite value per step')
    if auxiliary_trace_W is not None:
        if (len(auxiliary_trace_W) != p.steps or
                not all(math.isfinite(x) and x >= 0 for x in auxiliary_trace_W)):
            raise ValueError('auxiliary_trace_W must contain one finite nonnegative load per step')
    if rpm_trace_rpm is not None:
        if len(rpm_trace_rpm) != p.steps or not all(math.isfinite(x) and 0 <= x <= 20000 for x in rpm_trace_rpm):
            raise ValueError('rpm_trace_rpm must contain one finite nonnegative value <=20k per step')
    if external_charge_trace_W is not None:
        if p.external_charge_power_W != 0:
            raise ValueError('external charge trace and constant power are mutually exclusive')
        if len(external_charge_trace_W) != p.steps or not all(math.isfinite(x) and 0 <= x <= 250000 for x in external_charge_trace_W):
            raise ValueError('external_charge_trace_W must contain finite values in [0,250000]')
    rng_init = random.Random(p.seed)
    rng_meas = random.Random(p.seed + 717)
    z, r_mult, q_mult, pol = _init_branches(p, fault, rng_init)
    ix=(fault.module-1)*GROUPS_PER_MODULE + fault.group-1
    if swap_branches:
        for k in range(N_GROUPS):
            z[k].reverse();r_mult[k].reverse();q_mult[k].reverse();pol[k].reverse()
    leak_idx=0 if fault.branch=='A' else 1
    if swap_branches: leak_idx=1-leak_idx
    T=[p.init_module_C+p.module_temp_variation_C*math.sin(m) for m in range(N_MODULES)]
    motor_T=p.motor_init_C
    obs_rows=[]; truth_rows=[]
    if any(not 0<=soc<=1 for pair in z for soc in pair):
        raise ValueError('initial branch SOC outside physical [0,1]')
    # Coulomb and energy counters are sensor integrators, unless 'truth' ablation.
    chg_Ah=dchg_Ah=chg_kWh=dchg_kWh=0.0
    for step in range(p.steps):
        t=step*p.dt_s
        age=min(1.0,p.aging_index+p.aging_rate_per_s*t)
        cap_age=(1-p.age_capacity_loss*age)
        r_age=(1+p.age_resistance_gain*age)
        # B01 over and above H00: acceleration of uniformly reduced capacity.
        cap_fault=(1-p.b01_capacity_extra_loss*fault.severity) if fault.id=='B01' else 1.0
        r_fault=(1+p.b02_r0_extra_gain*fault.severity) if fault.id=='B02' else 1.0
        rpm, torque=_driver(t,p)
        if torque_trace_nm is not None:
            torque = float(torque_trace_nm[step])
        if rpm_trace_rpm is not None:
            rpm = float(rpm_trace_rpm[step])
        charge_W = (float(external_charge_trace_W[step]) if external_charge_trace_W is not None
                    else p.external_charge_power_W)
        if external_charge_trace_W is not None and charge_W > 0 and (abs(torque)>1e-9 or abs(rpm)>1e-9):
            raise ValueError(f'CHARGE_MODE_CONFLICT step={step} rpm={rpm:.4g} torque={torque:.4g}')
        if torque < 0 and p.regeneration_torque_scale != 1.0:
            torque *= p.regeneration_torque_scale
        elif torque > 0 and p.traction_torque_scale != 1.0:
            torque *= p.traction_torque_scale
        omega=2*math.pi*rpm/60.0
        p_mech=torque*omega
        copper=p.motor_copper_coeff_w_per_nm2*torque**2
        core=p.motor_iron_coeff_w_per_krpm2*(rpm/1000.0)**2
        if fault.id=='M01':
            copper*=1+(p.motor_loss_fault_multiplier-1)*fault.severity
        p_motor_loss=copper+core
        # Traction: DC->mechanical; regeneration: mechanical->DC.
        # Positive dissipation in BOTH directions.
        p_inv_loss=(p_mech*(1/p.inverter_efficiency-1) if p_mech>=0
                    else (-p_mech)*(1-p.inverter_efficiency))
        if fault.id=='I01' and abs(rpm)>1e-9 and abs(torque)>1e-9:
            # Research assumption: extra I01 dissipation is active only during
            # torque-producing motoring/regeneration. This is NOT a claim about
            # standby consumption in actual Porsche inverter electronics.
            p_inv_loss+=p.inverter_fault_extra_W*fault.severity
        p_gear_loss=abs(p_mech)*p.gearbox_loss_fraction
        # HV auxiliaries are a latent nuisance (NOT imported as observed sensors).
        p_aux=(float(auxiliary_trace_W[step]) if auxiliary_trace_W is not None else
               p.auxiliary_mean_W+p.auxiliary_amplitude_W*math.sin(t/45.0+p.auxiliary_phase_rad))
        # External charging enters the battery-side DC power balance, not motor torque.
        # Charging hardware losses/limits are NOT modeled.
        p_requested=p_mech+p_motor_loss+p_inv_loss+p_gear_loss+p_aux-charge_W
        o, r, r1, q, u = [], [], [], [], []
        # Each 2p group is two independent Thevenin 1RC sources with common V.
        for g in range(N_GROUPS):
            mod=g//GROUPS_PER_MODULE
            for b in range(2):
                r0=p.r0_ohm_cell*r_mult[g][b]*r_age*r_fault
                # resistance increases in cold weather, bounded positive
                r0*=max(0.5,1+p.resistance_cold_coeff_per_K*(p.resistance_reference_C-T[mod]))
                o.append(_ocv(z[g][b],T[mod],p)-pol[g][b])
                r.append(r0)
                r1.append(p.r1_ohm_cell*r_age)
                q.append(p.capacity_ah_cell*q_mult[g][b]*cap_age*cap_fault)
                u.append((g,b))
        # Equivalent circuit voltage V_pack(I) = sum(group open V - Req_group*I)
        pack_ocv=0.0; pack_r=0.0
        for g in range(N_GROUPS):
            a=2*g
            cond_a,cond_b=1/r[a],1/r[a+1]
            pack_ocv+=(o[a]*cond_a+o[a+1]*cond_b)/(cond_a+cond_b)
            pack_r+=1/(cond_a+cond_b)
        I=_positive_power_current(pack_ocv,pack_r,p_requested)
        group_v=[]; branch_current=[]; module_heat=[0.0]*N_MODULES
        rc_dissip_J=rc_storage_J=rc_work_J=ohmic_dissip_J=leakage_dissip_J=0.0
        for g in range(N_GROUPS):
            a=2*g
            cond_a,cond_b=1/r[a],1/r[a+1]
            v=(o[a]*cond_a+o[a+1]*cond_b-I)/(cond_a+cond_b)
            group_v.append(v)
            currents=((o[a]-v)/r[a],(o[a+1]-v)/r[a+1])
            branch_current.append(currents)
            for b,ib in enumerate(currents):
                k=a+b
                z[g][b]=_integrate_soc_strict(z[g][b],ib,q[k],p.dt_s,
                    step=step,group=g,branch=b)
                v_next,q_rc_J,delta_cap_J,work_rc_J=_rc_exact_step(
                    pol[g][b],ib,r1[k],p.rc_tau_s,p.dt_s)
                pol[g][b]=v_next
                q_r0_J=ib*ib*r[k]*p.dt_s
                module_heat[g//GROUPS_PER_MODULE]+=(q_r0_J+q_rc_J)/p.dt_s
                rc_dissip_J+=q_rc_J
                rc_storage_J+=delta_cap_J
                rc_work_J+=work_rc_J
                ohmic_dissip_J+=q_r0_J
            if fault.id=='B04' and g==ix:
                # Branch-local leakage conductance, not voltage sensor offset.
                leakage_A=fault.severity*(p.b04_leak_min_A+p.b04_leak_gain_A)  # ASSUMIDO 0.05..0.50 A
                z[g][leak_idx]=_integrate_soc_strict(
                    z[g][leak_idx],leakage_A,q[2*g+leak_idx],p.dt_s,
                    step=step,group=g,branch=leak_idx,mechanism='leakage')
                q_leak_J=v*leakage_A*p.dt_s
                module_heat[g//GROUPS_PER_MODULE]+=q_leak_J/p.dt_s
                leakage_dissip_J+=q_leak_J
        pack_v=sum(group_v)
        # Heat removal through aggregate coolant boundary: B07 reduces UA.
        cooling_scale=(1-p.b07_cooling_loss_fraction*fault.severity) if fault.id=='B07' else 1.0
        for m in range(N_MODULES):
            thermal_W=module_heat[m]-p.module_cooling_w_per_K*cooling_scale*(T[m]-p.coolant_C)
            T[m]+=p.dt_s*thermal_W/p.module_heat_j_per_K
        motor_T+=p.dt_s*(p_motor_loss-p.motor_cooling_w_per_K*(motor_T-p.coolant_C))/p.motor_heat_j_per_K
        n=lambda std: rng_meas.gauss(0,std) if p.sensor_noise else 0.0
        # group voltage measurement; optional fault B05 in one channel only
        reported_vs=[]
        obs:dict[str,float]={}
        for g,v in enumerate(group_v):
            m,c=divmod(g,GROUPS_PER_MODULE)
            key=f'TAYCAN_HVBAT_MOD{m+1}_C{c+1}_V'
            measured=v+n(p.voltage_noise_V)
            if fault.id=='B05' and g==ix:measured+=p.b05_voltage_offset_V*fault.severity
            obs[key]=measured
            reported_vs.append(measured)
        for m in range(N_MODULES):
            for s in (1,2,3):
                key=f'TAYCAN_HVBAT_MOD{m+1}_T{s}'
                obs[key]=T[m]+(s-2)*p.sensor_temp_spacing_C+n(p.temperature_noise_C)
                if fault.id=='B08' and (m+1)==fault.module and s==fault.temperature_sensor:
                    obs[key]+=p.b08_temperature_offset_C*fault.severity
        # Shared chain means two names are derived from one upstream acquisition;
        # injected bias is pre-fanout, hence labels A/B are observationally equal.
        b06_offset=p.b06_current_offset_A*fault.severity if fault.id=='B06' else 0.0
        if p.acquisition_mode=='shared':
            shared=I+b06_offset+n(p.current_noise_A)
            obs['TAYCAN_BMS_I']=shared
            obs['TAYCAN_HVBAT_CURRENT']=shared
            obs['TAYCAN_BMS_CELL_V_SUM']=sum(reported_vs)
            obs['TAYCAN_HVBAT_CELL_SUM_V']=sum(reported_vs)
        else:
            obs['TAYCAN_BMS_I']=I+(b06_offset if fault.channel=='TAYCAN_BMS_I' else 0)+n(p.current_noise_A)
            obs['TAYCAN_HVBAT_CURRENT']=I+(b06_offset if fault.channel=='TAYCAN_HVBAT_CURRENT' else 0)+n(p.current_noise_A)
            obs['TAYCAN_BMS_CELL_V_SUM']=pack_v+n(p.voltage_noise_V)
            obs['TAYCAN_HVBAT_CELL_SUM_V']=pack_v+n(p.voltage_noise_V)
        obs['TAYCAN_HVBAT_VOLT']=pack_v+n(p.voltage_noise_V)
        obs['TAYCAN_BMS_CELL_V_MAX']=max(reported_vs)
        obs['TAYCAN_BMS_CELL_V_MIN']=min(reported_vs)
        obs['TAYCAN_BMS_CELL_V_MAX_IDX']=float(reported_vs.index(max(reported_vs))+1)
        obs['TAYCAN_BMS_CELL_V_MIN_IDX']=float(reported_vs.index(min(reported_vs))+1)
        # Observer uses only a measured voltage for the group, one measured current,
        # one measured temperature, and ASSUMED OCV/series-resistance calibration.
        # True branch SOC z is never used to generate published SOC estimates.
        observed_I=obs['TAYCAN_BMS_I']
        estimated_group_soc=[]
        for g, measured_v in enumerate(reported_vs):
            m,c=divmod(g,GROUPS_PER_MODULE)
            temp_obs=sum(obs[f'TAYCAN_HVBAT_MOD{m+1}_T{i}'] for i in (1,2,3))/3
            approx_ocv=measured_v + observed_I*(p.r0_ohm_cell/2) + p.soc_observer_ocv_bias_V
            est=(approx_ocv - p.ocv_low_v - p.ocv_temp_coeff_v_per_K*(temp_obs-25))/p.ocv_span_v
            est=max(0.0,min(1.0,est+n(p.soc_observer_noise_frac)))
            obs[f'TAYCAN_HVBAT_MOD{m+1}_C{c+1}_SOC']=100*est
            estimated_group_soc.append(est)
        obs['TAYCAN_BMS_SOC']=100*max(0.0,min(1.0,
                    sum(estimated_group_soc)/N_GROUPS+p.bms_soc_bias_frac))
        # SOH is a coarse BMS proxy from H00 age, not a reading of fault truth.
        obs['TAYCAN_HVBAT_SOH']=100*cap_age
        obs['TAYCAN_BMS_T_MAX']=max(T)+n(p.temperature_noise_C)
        obs['TAYCAN_BMS_T_MIN']=min(T)+n(p.temperature_noise_C)
        obs['TAYCAN_BMS_T_AVG']=sum(T)/N_MODULES+n(p.temperature_noise_C)
        obs['TAYCAN_HVBAT_T']=sum(T)/N_MODULES+n(p.temperature_noise_C)
        obs['TAYCAN_BMS_COOL_IN_T']=p.coolant_C
        obs['TAYCAN_BMS_COOL_OUT_T']=p.coolant_C+sum(module_heat)/p.coolant_exchange_W_per_K
        # Counters integrate exactly one selected acquisition chain. The 'truth'
        # choice is an ablation, NOT a realistic BMS channel or an oracle feature.
        measured_counter_I=(I if p.counter_source=='truth'
                             else obs['TAYCAN_BMS_I'] if p.counter_source=='BMS_I'
                             else obs['TAYCAN_HVBAT_CURRENT'])
        measured_counter_V=obs['TAYCAN_HVBAT_VOLT']
        delta_Ah=measured_counter_I*p.dt_s/3600.0
        delta_kWh=measured_counter_V*measured_counter_I*p.dt_s/3_600_000.0
        if delta_Ah>=0: dchg_Ah+=delta_Ah
        else: chg_Ah-=delta_Ah
        if delta_kWh>=0: dchg_kWh+=delta_kWh
        else: chg_kWh-=delta_kWh
        obs['TAYCAN_HVBAT_TOT_AH_CHRG']=chg_Ah
        obs['TAYCAN_HVBAT_TOT_AH_DCHRG']=dchg_Ah
        obs['TAYCAN_HVBAT_TOT_KWH_CHRG']=chg_kWh
        obs['TAYCAN_HVBAT_TOT_KWH_DCHRG']=dchg_kWh
        iso=p.nominal_isolation_kohm
        if fault.id=='B09':iso*=1-p.b09_iso_loss_fraction*fault.severity
        for key in ['TAYCAN_HV_ISO_POS_SYS','TAYCAN_HVBAT_ISO_POS',
                    'TAYCAN_HV_ISO_NEG_SYS','TAYCAN_HVBAT_ISO_NEG']:
            obs[key]=iso*(1+p.isolation_sensor_modulation_frac*math.sin(t/20+len(key)))
        # HVIL is a logically separate sensing loop, no guaranteed effect of B09.
        obs['TAYCAN_HV_INTERLOCK_DET_V']=p.nominal_hvil_V
        obs['TAYCAN_HV_INTERLOCK_SRC_V']=p.nominal_hvil_V
        obs['TAYCAN_HV_INTERLOCK_SRC_I']=p.nominal_hvil_mA
        obs['TAYCAN_EM_RPM_1']=rpm; obs['TAYCAN_EM_RPM_2']=rpm
        obs['TAYCAN_EM_TORQ_1']=torque*p.front_torque_fraction;obs['TAYCAN_EM_TORQ_2']=torque*(1-p.front_torque_fraction)
        obs['TAYCAN_ENG_MOTOR_RPM']=rpm
        obs['TAYCAN_ENG_TRQ_REQ_1']=torque*p.front_torque_fraction;obs['TAYCAN_ENG_TRQ_REQ_2']=torque*(1-p.front_torque_fraction)
        obs['TAYCAN_EM_PWR_LIM']=0.0
        obs['TAYCAN_EM_NV_PWR_LIM']=0.0
        # DIFF mapping ambiguous: simulated proxy conditional on true meaning.
        obs['TAYCAN_DIFF_MOTOR_T']=(motor_T if p.diff_motor_t_mapping=='winding_proxy'
                                      else p.motor_init_C)+n(p.temperature_noise_C)
        if not set(obs).issubset(CATALOG):
            raise AssertionError('simulator leaked a non-approved OBDb signal')
        obs_rows.append(obs)
        truth_rows.append({'time_s':t,'fault':fault.id,'real_pack_current_A':I,
                           'real_pack_voltage_V':pack_v,'power_dc_W':pack_v*I,
                           'power_mechanical_W':p_mech,'power_motor_loss_W':p_motor_loss,
                           'power_inverter_loss_W':p_inv_loss,'power_gearbox_loss_W':p_gear_loss,
                           'power_auxiliary_W':p_aux,'power_charge_to_dc_bus_W':charge_W,
                           'rc_dissipation_J_step':rc_dissip_J,
                           'rc_capacitor_storage_delta_J_step':rc_storage_J,
                           'rc_input_work_J_step':rc_work_J,
                           'r0_dissipation_J_step':ohmic_dissip_J,
                           'leakage_dissipation_J_step':leakage_dissip_J,
                           'module_heat_generation_J_step':sum(module_heat)*p.dt_s,
                           'power_requested_dc_W':p_requested,'motor_winding_C':motor_T,
                           'group_branch_currents_A':branch_current[ix],
                           'group_branch_soc':tuple(z[ix]),
                           'min_hidden_branch_soc':min(min(pair) for pair in z),
                           'max_hidden_branch_soc':max(max(pair) for pair in z),
                           'mean_hidden_soc':sum(sum(x) for x in z)/(N_GROUPS*2),
                           'fault_module_group':(fault.module,fault.group),
                           'acquisition_mode':p.acquisition_mode})
    return SimResult(obs_rows,truth_rows,fault,{'seed':p.seed,'dt_s':p.dt_s,
        'steps':p.steps,'acquisition_mode':p.acquisition_mode,'model':'synthetic_1RC_168s2p',
        'unobserved_HV_auxiliaries':True,'mapped_motor_temperature':p.diff_motor_t_mapping,
        'counter_source':p.counter_source, 'external_charge_power_W':p.external_charge_power_W,
        'torque_trace_supplied':torque_trace_nm is not None,
        'auxiliary_trace_supplied':auxiliary_trace_W is not None,
        'rpm_trace_supplied':rpm_trace_rpm is not None,
        'charge_trace_supplied':external_charge_trace_W is not None,
        'charge_trace_mode':'parked_only_fail_closed' if external_charge_trace_W is not None else 'constant_ideal_DC_stress',
        'traction_torque_scale':p.traction_torque_scale,
        'regeneration_torque_scale':p.regeneration_torque_scale,
        'candidate_physics_revision':True,
        'rc_heat':'exact_constant_current_dissipation_and_storage_audited',
        'soc_boundary':'fail_closed_no_clipping',
        'soc_observer':'measured_terminal_voltage_ocv_inversion',
        'pack_r0_reference_ohm':N_GROUPS*p.r0_ohm_cell/2,
        'observed_signals_per_row':len(obs_rows[0]),'catalog_size':len(CATALOG)})


def paired_branch_counterfactual(p: ModelConfig, branch: str='A') -> dict:
    """Permutation of *all* hidden branch attributes, not just fault label.

    Assumes no branch-resolved temperature/current sensor: output voltage is
    exactly permutation-invariant in the parallel ECM. No noise here.
    """
    import dataclasses
    pf=dataclasses.replace(p,sensor_noise=False)
    f=Fault('B04',module=7,group=3,branch=branch,severity=1.0)
    a=simulate(f,pf,swap_branches=False)
    b=simulate(f,pf,swap_branches=True)
    voltage_id='TAYCAN_HVBAT_MOD7_C3_V'
    maximum=max(abs(x[voltage_id]-y[voltage_id]) for x,y in zip(a.observations,b.observations))
    # Only approved observations; validate full published vector equivalence.
    diff=max(abs(x[k]-y[k]) for x,y in zip(a.observations,b.observations) for k in x)
    return {'group_voltage_max_abs_difference_V':maximum,
            'all_published_signals_max_abs_difference':diff,
            'steps':p.steps, 'module':f.module,'group':f.group}
