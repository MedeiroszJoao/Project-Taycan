"""Explicitly assumed six-hour charge-block input waveform (RESEARCH ONLY).

The sealed preregistration fixes cycle block lengths (12 min each) but does not
uniquely determine the numerical torque/RPM curve. These are transparent toy
waveform values, NOT historical Porsche driving data or approved Stage 4 inputs.
"""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
import math

BLOCKS=('cruise','acceleration','regeneration','rest','charge')
SEGMENT_SECONDS=12*60
PERIOD_SECONDS=60*60
HORIZON_SECONDS=6*60*60

@dataclass(frozen=True)
class DutyInputs:
    torque_nm: list[float]
    rpm: list[float]
    charge_W: list[float]
    mode: list[str]
    dt_s: float
    profile_id: str


def build_duty_inputs(*, dt_s:float=5.0, charge_power_kw:float=40.,
                      profile_id:str='NOMINAL_6H') -> DutyInputs:
    if profile_id not in ('NOMINAL_6H','SHIFT_REGEN_COLD_6H'):
        raise ValueError('unknown profile')
    if not math.isfinite(dt_s) or dt_s<=0 or not math.isclose(SEGMENT_SECONDS/dt_s, round(SEGMENT_SECONDS/dt_s),abs_tol=1e-9):
        raise ValueError('dt must exactly divide 720s segments')
    if not math.isfinite(charge_power_kw) or not 0<=charge_power_kw<=120:
        raise ValueError('charge_power_kw outside research bracket [0,120]')
    n=int(HORIZON_SECONDS/dt_s)
    torque=[];rpm=[];charge=[];mode=[]
    for i in range(n):
        t=i*dt_s
        k=int((t%PERIOD_SECONDS)//SEGMENT_SECONDS)
        phase=(t%SEGMENT_SECONDS)/SEGMENT_SECONDS
        block=BLOCKS[k]
        if block=='cruise':
            tau=42+5*math.sin(phase*2*math.pi)
            speed=3200+120*math.sin(phase*2*math.pi)
        elif block=='acceleration':
            tau=82+22*math.sin(phase*math.pi)
            speed=3400+400*phase
        elif block=='regeneration':
            tau=-(50+12*math.sin(phase*math.pi))
            speed=3000-300*phase
        else:  # physically parked for rest/charge
            tau=0.;speed=0.
        if profile_id=='SHIFT_REGEN_COLD_6H':
            tau *= 1.5 if tau < 0 else .85
        torque.append(tau)
        rpm.append(speed)
        charge.append(charge_power_kw*1000 if block=='charge' else 0.)
        mode.append(block)
    return DutyInputs(torque,rpm,charge,mode,dt_s,profile_id)
