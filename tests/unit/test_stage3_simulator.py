"""Deterministic physics/contract tests, not tests of the real Taycan."""
import dataclasses
import unittest
from taycan_sim import ModelConfig, Fault, simulate, paired_branch_counterfactual
from taycan_sim.model import CATALOG, FAULT_IDS


class SimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = ModelConfig(steps=100, sensor_noise=False)
        cls.normal = simulate(Fault('H00'),cls.p)

    def run_fault(self,id,**kw):
        return simulate(Fault(id,**kw),self.p)

    def test_geometry_and_catalog(self):
        row=self.normal.observations[-1]
        self.assertEqual(len(CATALOG),546)
        self.assertEqual(len(row),458)
        self.assertEqual(len([k for k in row if '_C' in k and k.endswith('_V') and '_MOD' in k]),168)
        self.assertTrue(set(row).issubset(CATALOG))
        self.assertNotIn('TAYCAN_HVBAT_MOD29_C1_V',row)
        self.assertEqual(len(self.normal.truth),100)
        self.assertFalse(any('auxiliary' in k.lower() for k in row))

    def test_deterministic_fixed_seed(self):
        self.assertEqual(self.normal.observations,simulate(Fault(),self.p).observations)
        self.assertEqual(self.normal.truth,simulate(Fault(),self.p).truth)

    def test_all_11_faults_execute(self):
        self.assertEqual(len(FAULT_IDS),12)
        for x in FAULT_IDS:
            with self.subTest(x=x):
                s=self.run_fault(x)
                self.assertEqual(len(s.observations),100)
                self.assertTrue(all(v>300 for v in (r['TAYCAN_HVBAT_VOLT'] for r in s.observations)))

    def test_power_balance_includes_nuisance(self):
        for row in self.normal.truth:
            rhs=row['power_mechanical_W']+row['power_motor_loss_W']+row['power_inverter_loss_W']+row['power_gearbox_loss_W']+row['power_auxiliary_W']
            self.assertAlmostEqual(row['power_dc_W'],rhs,places=6)
        self.assertGreater(self.normal.truth[0]['power_auxiliary_W'],0)

    def test_h00_is_not_a_failure_and_aging_changes_soh(self):
        young=simulate(Fault('H00'),dataclasses.replace(self.p,aging_index=0.1))
        old=simulate(Fault('H00'),dataclasses.replace(self.p,aging_index=0.8))
        self.assertGreater(young.observations[-1]['TAYCAN_HVBAT_SOH'],old.observations[-1]['TAYCAN_HVBAT_SOH'])
        self.assertGreater(young.observations[-1]['TAYCAN_HVBAT_VOLT'],old.observations[-1]['TAYCAN_HVBAT_VOLT'])

    def test_b01_capacity_change_without_oracle_soh(self):
        alt=self.run_fault('B01')
        self.assertEqual(alt.observations[-1]['TAYCAN_HVBAT_SOH'],self.normal.observations[-1]['TAYCAN_HVBAT_SOH'])
        self.assertNotEqual(alt.truth[-1]['group_branch_soc'],self.normal.truth[-1]['group_branch_soc'])

    def test_b02_higher_resistance_higher_traction_current(self):
        f=self.run_fault('B02')
        self.assertLess(f.observations[0]['TAYCAN_HVBAT_VOLT'],self.normal.observations[0]['TAYCAN_HVBAT_VOLT'])
        self.assertGreater(f.truth[0]['real_pack_current_A'],self.normal.truth[0]['real_pack_current_A'])

    def test_b03_local_capacity_reduction(self):
        f=self.run_fault('B03')
        self.assertLess(sum(f.truth[-1]['group_branch_soc']),sum(self.normal.truth[-1]['group_branch_soc']))

    def test_b04_intra_pair_permutation_full_observation(self):
        r=paired_branch_counterfactual(self.p)
        self.assertLessEqual(r['group_voltage_max_abs_difference_V'],1e-10)
        self.assertLessEqual(r['all_published_signals_max_abs_difference'],1e-9)
        leak_a=self.run_fault('B04',branch='A')
        leak_b=self.run_fault('B04',branch='B')
        self.assertNotEqual(leak_a.truth[-1]['group_branch_soc'],leak_b.truth[-1]['group_branch_soc'])

    def test_b05_aggregates_depend_on_acquisition(self):
        independent=self.run_fault('B05')
        residual_independent=sum(independent.observations[-1][f'TAYCAN_HVBAT_MOD{m}_C{g}_V'] for m in range(1,29) for g in range(1,7))-independent.observations[-1]['TAYCAN_BMS_CELL_V_SUM']
        shared=simulate(Fault('B05'),dataclasses.replace(self.p,acquisition_mode='shared'))
        residual_shared=sum(shared.observations[-1][f'TAYCAN_HVBAT_MOD{m}_C{g}_V'] for m in range(1,29) for g in range(1,7))-shared.observations[-1]['TAYCAN_BMS_CELL_V_SUM']
        self.assertAlmostEqual(residual_independent,0.07,places=8)
        self.assertAlmostEqual(residual_shared,0.0,places=8)

    def test_b06_independent_channels_symmetric(self):
        a=self.run_fault('B06',channel='TAYCAN_BMS_I')
        b=self.run_fault('B06',channel='TAYCAN_HVBAT_CURRENT')
        ra=a.observations[-1]['TAYCAN_BMS_I']-a.observations[-1]['TAYCAN_HVBAT_CURRENT']
        rb=b.observations[-1]['TAYCAN_BMS_I']-b.observations[-1]['TAYCAN_HVBAT_CURRENT']
        self.assertAlmostEqual(ra,9.0)
        self.assertAlmostEqual(rb,-9.0)
        self.assertAlmostEqual(ra,-rb)

    def test_b06_shared_chain_aliases_fault_origin(self):
        sp=dataclasses.replace(self.p,acquisition_mode='shared')
        a=simulate(Fault('B06',channel='TAYCAN_BMS_I'),sp)
        b=simulate(Fault('B06',channel='TAYCAN_HVBAT_CURRENT'),sp)
        self.assertEqual(a.observations,b.observations)
        self.assertEqual(a.truth,b.truth)
        self.assertEqual(a.observations[-1]['TAYCAN_BMS_I']-a.observations[-1]['TAYCAN_HVBAT_CURRENT'],0)

    def test_b07_thermal_extraction_deteriorates(self):
        f=self.run_fault('B07')
        self.assertGreater(f.observations[-1]['TAYCAN_HVBAT_MOD7_T1'],self.normal.observations[-1]['TAYCAN_HVBAT_MOD7_T1'])

    def test_b08_only_one_thermal_measurement_biased(self):
        f=self.run_fault('B08',module=7,temperature_sensor=2)
        a=f.observations[-1]; b=self.normal.observations[-1]
        self.assertAlmostEqual(a['TAYCAN_HVBAT_MOD7_T2']-b['TAYCAN_HVBAT_MOD7_T2'],7.0)
        self.assertAlmostEqual(a['TAYCAN_HVBAT_MOD7_T1']-b['TAYCAN_HVBAT_MOD7_T1'],0)

    def test_b09_iso_changes_hvil_does_not(self):
        f=self.run_fault('B09')
        x=f.observations[0];n=self.normal.observations[0]
        for sig in ('TAYCAN_HV_ISO_POS_SYS','TAYCAN_HVBAT_ISO_POS','TAYCAN_HV_ISO_NEG_SYS','TAYCAN_HVBAT_ISO_NEG'):
            self.assertLess(x[sig],n[sig])
        for sig in ('TAYCAN_HV_INTERLOCK_DET_V','TAYCAN_HV_INTERLOCK_SRC_V','TAYCAN_HV_INTERLOCK_SRC_I'):
            self.assertEqual(x[sig],n[sig])

    def test_m01_and_i01_losses_increase(self):
        m=self.run_fault('M01')
        i=self.run_fault('I01')
        self.assertGreater(m.truth[-1]['power_motor_loss_W'],self.normal.truth[-1]['power_motor_loss_W'])
        self.assertGreater(i.truth[-1]['power_inverter_loss_W'],self.normal.truth[-1]['power_inverter_loss_W'])
        self.assertGreater(m.truth[-1]['motor_winding_C'],self.normal.truth[-1]['motor_winding_C'])
        self.assertAlmostEqual(i.truth[-1]['motor_winding_C'],self.normal.truth[-1]['motor_winding_C'])

    def test_auxiliary_nuisance_influences_R33(self):
        low=simulate(Fault(),dataclasses.replace(self.p,auxiliary_mean_W=200))
        high=simulate(Fault(),dataclasses.replace(self.p,auxiliary_mean_W=5200))
        rlo=low.truth[0]['power_dc_W']-low.truth[0]['power_mechanical_W']
        rhi=high.truth[0]['power_dc_W']-high.truth[0]['power_mechanical_W']
        self.assertAlmostEqual(rhi-rlo,5000,places=6)
        self.assertAlmostEqual(high.truth[0]['power_motor_loss_W'],low.truth[0]['power_motor_loss_W'])
        self.assertAlmostEqual(high.truth[0]['power_inverter_loss_W'],low.truth[0]['power_inverter_loss_W'])

    def test_i01_is_observationally_aliased_by_auxiliary_load(self):
        inv=self.run_fault('I01')
        aux=simulate(Fault('H00'),dataclasses.replace(self.p,
                 auxiliary_mean_W=self.p.auxiliary_mean_W+self.p.inverter_fault_extra_W))
        self.assertLess(max(abs(x[k]-y[k]) for x,y in zip(inv.observations,aux.observations) for k in x),1e-8)
        self.assertNotEqual(inv.truth[-1]['power_inverter_loss_W'],aux.truth[-1]['power_inverter_loss_W'])
        self.assertNotEqual(inv.truth[-1]['power_auxiliary_W'],aux.truth[-1]['power_auxiliary_W'])

    def test_zero_severity_equals_h00_all_11(self):
        for code in FAULT_IDS[1:]:
            with self.subTest(fault=code):
                f=simulate(Fault(code,severity=0.0),self.p)
                self.assertEqual(f.observations,self.normal.observations)

    def test_parallel_current_conservation(self):
        for t in self.normal.truth:
            self.assertAlmostEqual(sum(t['group_branch_currents_A']),t['real_pack_current_A'],places=9)

    def test_soc_observations_are_not_latent_oracle(self):
        # No-noise case still contains calibrated estimator mismatch.
        obs=self.normal.observations[-1]
        truth=self.normal.truth[-1]
        self.assertGreater(abs(obs['TAYCAN_BMS_SOC']-100*truth['mean_hidden_soc']),0.01)
        self.assertGreater(abs(obs['TAYCAN_HVBAT_MOD7_C3_SOC']-100*sum(truth['group_branch_soc'])/2),0.01)
        # A VOLTAGE-sensor fault must affect reported SOC without changing latent SOC.
        biased=self.run_fault('B05')
        self.assertAlmostEqual(biased.truth[-1]['mean_hidden_soc'],truth['mean_hidden_soc'])
        self.assertGreater(biased.observations[-1]['TAYCAN_HVBAT_MOD7_C3_SOC'],obs['TAYCAN_HVBAT_MOD7_C3_SOC'])

    def test_soc_estimator_sensor_current_dependence(self):
        a=self.run_fault('B06',channel='TAYCAN_BMS_I')
        b=self.run_fault('B06',channel='TAYCAN_HVBAT_CURRENT')
        self.assertNotAlmostEqual(a.observations[-1]['TAYCAN_BMS_SOC'],b.observations[-1]['TAYCAN_BMS_SOC'])
        self.assertEqual(a.truth[-1]['mean_hidden_soc'],b.truth[-1]['mean_hidden_soc'])

    def test_counters_integrate_selected_measured_current_and_voltage(self):
        # Check the *entire observed time series*, not just one snapshot.
        for source,key in [('BMS_I','TAYCAN_BMS_I'),('HVBAT_CURRENT','TAYCAN_HVBAT_CURRENT')]:
            cfg=dataclasses.replace(self.p,counter_source=source, sensor_noise=True,steps=35)
            sim=simulate(Fault('B06',channel=key),cfg)
            expected_ah=sum(max(0,r[key])*cfg.dt_s/3600 for r in sim.observations)
            expected_kwh=sum(max(0,r[key]*r['TAYCAN_HVBAT_VOLT'])*cfg.dt_s/3_600_000 for r in sim.observations)
            self.assertAlmostEqual(sim.observations[-1]['TAYCAN_HVBAT_TOT_AH_DCHRG'],expected_ah,places=12)
            self.assertAlmostEqual(sim.observations[-1]['TAYCAN_HVBAT_TOT_KWH_DCHRG'],expected_kwh,places=12)

    def test_b06_shared_upstream_bias_changes_both_sensor_counters(self):
        cfg=dataclasses.replace(self.p,acquisition_mode='shared')
        for source in ('BMS_I','HVBAT_CURRENT'):
            current_cfg=dataclasses.replace(cfg,counter_source=source)
            baseline=simulate(Fault('H00'),current_cfg)
            for channel in ('TAYCAN_BMS_I','TAYCAN_HVBAT_CURRENT'):
                injected=simulate(Fault('B06',channel=channel),current_cfg)
                delta=injected.observations[-1]['TAYCAN_HVBAT_TOT_AH_DCHRG']-baseline.observations[-1]['TAYCAN_HVBAT_TOT_AH_DCHRG']
                self.assertAlmostEqual(delta,self.p.b06_current_offset_A*self.p.steps*self.p.dt_s/3600,places=10)
        # Truth-only counters do not change for B06: this is explicitly an ablation.
        ablation=dataclasses.replace(cfg,counter_source='truth')
        self.assertEqual(simulate(Fault('B06'),ablation).observations[-1]['TAYCAN_HVBAT_TOT_AH_DCHRG'],simulate(Fault('H00'),ablation).observations[-1]['TAYCAN_HVBAT_TOT_AH_DCHRG'])

    def test_diff_motor_t_mapping_two_cases(self):
        for mapping in ('winding_proxy','uninformative'):
            config=dataclasses.replace(self.p,diff_motor_t_mapping=mapping)
            base=simulate(Fault('H00'),config)
            motor=simulate(Fault('M01'),config)
            inverter=simulate(Fault('I01'),config)
            m_delta=motor.observations[-1]['TAYCAN_DIFF_MOTOR_T']-base.observations[-1]['TAYCAN_DIFF_MOTOR_T']
            i_delta=inverter.observations[-1]['TAYCAN_DIFF_MOTOR_T']-base.observations[-1]['TAYCAN_DIFF_MOTOR_T']
            if mapping=='winding_proxy':self.assertGreater(m_delta,0)
            else:self.assertEqual(m_delta,0)
            self.assertEqual(i_delta,0)

    def test_r0_pack_series_parallel_and_power_feasibility(self):
        from taycan_sim.model import N_GROUPS,_positive_power_current
        p=self.p
        req=N_GROUPS*p.r0_ohm_cell/2
        self.assertAlmostEqual(req,0.0504,places=10)
        # Porsche sheet shows 613V reference and up to 390kW traction peak.
        # We stress 430kW electrical input ASSUMED (losses/aux over peak).
        voltage,stress_power=613.0,430000.0
        i=_positive_power_current(voltage,req,stress_power)
        self.assertGreater(i,0)
        self.assertAlmostEqual((voltage-i*req)*i,stress_power,places=6)
        self.assertLess(i*i*req/stress_power,0.10)

    def test_mode_configuration_validation(self):
        with self.assertRaises(ValueError): ModelConfig(counter_source='missing')
        with self.assertRaises(ValueError): ModelConfig(diff_motor_t_mapping='unknown')

    def test_early_invalid_inputs(self):
        with self.assertRaises(ValueError):Fault('NOT_A_FAULT')
        with self.assertRaises(ValueError):Fault('B04',module=29)
        with self.assertRaises(ValueError):ModelConfig(acquisition_mode='maybe')
        with self.assertRaises(ValueError):ModelConfig(dt_s=-1)


if __name__=='__main__':unittest.main()
