"""Energy-focused falsification tests. Not a seal or stage approval."""
from __future__ import annotations
from pathlib import Path
from dataclasses import replace
import random, sys, unittest, math, hashlib
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src/simulator'))
from candidate_sim import model_energy_consistent as strict, model as baseline

class EnergyConsistency(unittest.TestCase):
    def test_approved_original_unmodified(self):
        f=ROOT/'src/simulator/taycan_sim/model.py'
        self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest(),
          'af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e')

    def test_rc_energy_identity_randomized_signed_inputs(self):
        randomizer=random.Random(190718)
        worst=0.0
        for _ in range(2500):
            v0=randomizer.uniform(-0.25,0.25)
            ib=randomizer.uniform(-350,350)
            r1=10**randomizer.uniform(-5,-2.2)
            tau=10**randomizer.uniform(0,3)
            dt=10**randomizer.uniform(-2,1.3)
            v1,q,dE,W=strict._rc_exact_step(v0,ib,r1,tau,dt)
            self.assertGreaterEqual(q,0)
            self.assertTrue(all(map(math.isfinite,(v1,q,dE,W))))
            residual=abs(W-q-dE)/max(1.0,abs(W),abs(q),abs(dE))
            worst=max(worst,residual)
            self.assertLess(residual,1e-9)
        self.assertLess(worst,1e-9)

    def test_relaxation_without_current_still_dissipates(self):
        v0=.15;r=.00025;tau=75;dt=8.
        v1,q,dE,W=strict._rc_exact_step(v0,0.,r,tau,dt)
        self.assertEqual(W,0.)
        self.assertGreater(q,0.)
        self.assertLess(dE,0.)
        self.assertAlmostEqual(q,-dE,places=7)
        self.assertAlmostEqual(v1,v0*math.exp(-dt/tau),places=12)

    def test_steady_rc_dissipation(self):
        I=-120.;R=.00025;tau=75.;dt=20.
        new,q,dE,W=strict._rc_exact_step(I*R,I,R,tau,dt)
        self.assertAlmostEqual(new,I*R,places=12)
        self.assertAlmostEqual(dE,0,places=10)
        self.assertAlmostEqual(q,I**2*R*dt,places=9)
        self.assertAlmostEqual(W,q,places=9)

    def test_rc_refinement_composes_polarization_states(self):
        v=.08;I=-93.;r=.00025;tau=75.
        full=strict._rc_exact_step(v,I,r,tau,10)
        left=strict._rc_exact_step(v,I,r,tau,5)
        right=strict._rc_exact_step(left[0],I,r,tau,5)
        for i in range(4):
            self.assertAlmostEqual(full[i],(right[0],left[1]+right[1],left[2]+right[2],left[3]+right[3])[i],delta=1e-7)

    def test_soc_violation_fails_closed_in_charging(self):
        cfg=strict.ModelConfig(initial_soc=.985,dt_s=20,steps=120,sensor_noise=False,
            group_soc_spread=0,branch_soc_spread=0,
            driver_torque_baseline=0,driver_torque_swing=0,driver_torque_fast_swing=0,
            external_charge_power_W=180000.)
        with self.assertRaisesRegex(ValueError,'SOC_BOUNDARY_VIOLATION'):
            strict.simulate(p=cfg,torque_trace_nm=[0.]*cfg.steps)
        older=baseline.simulate(p=baseline.ModelConfig(**vars(cfg)),torque_trace_nm=[0.]*cfg.steps)
        self.assertLessEqual(older.truth[-1]['mean_hidden_soc'],.999)
        self.assertGreaterEqual(older.truth[-1]['mean_hidden_soc'],.98)

    def test_soc_violation_fails_closed_in_discharge(self):
        cfg=strict.ModelConfig(initial_soc=.02,dt_s=20,steps=800,sensor_noise=False,
            group_soc_spread=0,branch_soc_spread=0,
            driver_torque_baseline=0,driver_torque_swing=0,driver_torque_fast_swing=0)
        with self.assertRaisesRegex(ValueError,'SOC_BOUNDARY_VIOLATION'):
            strict.simulate(p=cfg,torque_trace_nm=[240.]*cfg.steps)

    def test_both_signed_torque_modes_and_explicit_energy_audit(self):
        cfg=strict.ModelConfig(initial_soc=.6,dt_s=5,steps=100,sensor_noise=False,
            traction_torque_scale=.85,regeneration_torque_scale=1.5,
            external_charge_power_W=9000.)
        torque=[-105 if i%2==0 else 105 for i in range(cfg.steps)]
        r=strict.simulate(p=cfg,torque_trace_nm=torque)
        self.assertEqual(len(r.observations),len(r.truth))
        currents=[x['real_pack_current_A'] for x in r.truth]
        self.assertLess(min(currents),0.)
        self.assertGreater(max(currents),0.)
        for x in r.truth:
            self.assertGreaterEqual(x['rc_dissipation_J_step'],0.)
            self.assertGreaterEqual(x['r0_dissipation_J_step'],0.)
            self.assertAlmostEqual(x['rc_input_work_J_step'],x['rc_dissipation_J_step']+x['rc_capacitor_storage_delta_J_step'],delta=1e-7)
            self.assertAlmostEqual(x['module_heat_generation_J_step'],x['rc_dissipation_J_step']+x['r0_dissipation_J_step']+x['leakage_dissipation_J_step'],delta=1e-7)
            self.assertAlmostEqual(x['power_requested_dc_W'],x['power_dc_W'],delta=1e-6)

    def test_fixed_seed_reproduces_observations_and_truth(self):
        cfg=strict.ModelConfig(initial_soc=.6,dt_s=5,steps=40,sensor_noise=False,seed=823)
        a=strict.simulate(strict.Fault('M01',severity=.75),cfg)
        b=strict.simulate(strict.Fault('M01',severity=.75),cfg)
        self.assertEqual(a.observations,b.observations)
        self.assertEqual(a.truth,b.truth)

    def test_12_hypotheses_pass_local_short_sign_changing_trace(self):
        cfg=strict.ModelConfig(initial_soc=.6,dt_s=5,steps=120,sensor_noise=False,seed=919,
            auxiliary_amplitude_W=0)
        torque=[60+90*math.sin(i/8.) for i in range(cfg.steps)]
        for fid in strict.FAULT_IDS:
            with self.subTest(fid=fid):
                x=strict.simulate(strict.Fault(fid,severity=0 if fid=='H00' else .5),cfg,
                    torque_trace_nm=torque)
                self.assertEqual(len(x.truth),cfg.steps)
                self.assertTrue(all(z['rc_dissipation_J_step']>=0 for z in x.truth))
                self.assertTrue(all(z['r0_dissipation_J_step']>=0 for z in x.truth))
                self.assertTrue(all(0<=z['mean_hidden_soc']<=1 for z in x.truth))

class DutyCycleTests(unittest.TestCase):
    def test_duty_block_grid_and_exact_6h_charge_allocation(self):
        sys.path.insert(0,str(ROOT))
        from scripts.duty_cycle_candidate import build_duty_inputs
        x=build_duty_inputs(dt_s=5,charge_power_kw=45)
        self.assertEqual(len(x.mode),4320)
        self.assertEqual(len(x.charge_W),4320)
        self.assertEqual(x.mode.count('charge'),864)
        self.assertEqual(x.mode.count('rest'),864)
        self.assertEqual(sum(z*5 for z in x.charge_W)/3_600_000,54.)
        for mode,t,r,p in zip(x.mode,x.torque_nm,x.rpm,x.charge_W):
            if mode=='charge':
                self.assertEqual((t,r,p),(0.,0.,45000.))
            elif mode=='rest':
                self.assertEqual((t,r,p),(0.,0.,0.))
            else:self.assertEqual(p,0.)

    def test_nonzero_charge_and_traction_cannot_coexist_in_trace(self):
        p=strict.ModelConfig(steps=3,sensor_noise=False)
        with self.assertRaisesRegex(ValueError,'CHARGE_MODE_CONFLICT'):
            strict.simulate(p=p,torque_trace_nm=[0,30,0],rpm_trace_rpm=[0,3000,0],
                external_charge_trace_W=[100,100,100])

    def test_charge_blocks_zero_iron_loss_and_zero_mechanical_power(self):
        p=strict.ModelConfig(steps=6,dt_s=5,sensor_noise=False,initial_soc=.6)
        x=strict.simulate(p=p,
              torque_trace_nm=[0,40,40,0,0,0],
              rpm_trace_rpm=[0,3000,3000,0,0,0],
              external_charge_trace_W=[0,0,0,25000,25000,25000])
        for i in [3,4,5]:
            self.assertEqual(x.truth[i]['power_motor_loss_W'],0)
            self.assertEqual(x.truth[i]['power_mechanical_W'],0)
            self.assertEqual(x.truth[i]['power_charge_to_dc_bus_W'],25000)
            self.assertLess(x.truth[i]['real_pack_current_A'],0)

    def test_invalid_rpm_charge_traces_rejected(self):
        p=strict.ModelConfig(steps=3,sensor_noise=False)
        for bad in ([1,2],[1,-1,3],[1,float('nan'),3]):
            with self.assertRaises(ValueError):strict.simulate(p=p,rpm_trace_rpm=bad)
        for bad in ([1,2],[1,-1,3],[1,float('nan'),3]):
            with self.assertRaises(ValueError):strict.simulate(p=p,external_charge_trace_W=bad)

if __name__=='__main__':unittest.main()
