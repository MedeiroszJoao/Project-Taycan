"""Stage 3 CLI; prints a deterministic summary, does not export a dataset."""
import argparse
from .model import ModelConfig,Fault,simulate,paired_branch_counterfactual

def main():
    a=argparse.ArgumentParser(description='Synthetic battery HV / motor / inverter simulator (stage 3)')
    a.add_argument('--fault',choices=('H00','B01','B02','B03','B04','B05','B06','B07','B08','B09','M01','I01'),default='H00')
    a.add_argument('--steps',type=int,default=180)
    a.add_argument('--seed',type=int,default=20261011)
    a.add_argument('--acquisition-mode',choices=('shared','independent'),default='independent')
    a.add_argument('--channel',choices=('TAYCAN_BMS_I','TAYCAN_HVBAT_CURRENT'),default='TAYCAN_BMS_I')
    a.add_argument('--branch',choices=('A','B'),default='A')
    a.add_argument('--severity',type=float,default=1.0)
    a.add_argument('--no-noise',action='store_true')
    a.add_argument('--counter-source',choices=('BMS_I','HVBAT_CURRENT','truth'),default='BMS_I')
    a.add_argument('--diff-motor-t-mapping',choices=('winding_proxy','uninformative'),default='winding_proxy')
    a.add_argument('--permutation-proof',action='store_true')
    args=a.parse_args()
    c=ModelConfig(steps=args.steps,seed=args.seed,acquisition_mode=args.acquisition_mode,sensor_noise=not args.no_noise,counter_source=args.counter_source,diff_motor_t_mapping=args.diff_motor_t_mapping)
    f=Fault(id=args.fault,channel=args.channel,branch=args.branch,severity=args.severity)
    result=simulate(f,c)
    r=result.observations[-1]
    tr=result.truth[-1]
    print(f'FAULT={f.id} SEED={c.seed} MODE={c.acquisition_mode} COUNTER_SOURCE={c.counter_source} DIFF_MAPPING={c.diff_motor_t_mapping} STEPS={c.steps} DT_S={c.dt_s}')
    print(f'CONTRACT_APPROVED_IDS={result.metadata["catalog_size"]} OBSERVED_PER_STEP={result.metadata["observed_signals_per_row"]}')
    print(f'PACK_V={r["TAYCAN_HVBAT_VOLT"]:.4f} V PACK_I_TRUTH={tr["real_pack_current_A"]:.4f} A MOTOR_T_PROXY={r["TAYCAN_DIFF_MOTOR_T"]:.4f} C')
    print(f'R32_CURRENT_DELTA_A={r["TAYCAN_BMS_I"]-r["TAYCAN_HVBAT_CURRENT"]:.6f}')
    print(f'BMS_SOC_EST={r["TAYCAN_BMS_SOC"]:.6f} HIDDEN_SOC_PERCENT={100*tr["mean_hidden_soc"]:.6f} COUNTER_AH_DCHG={r["TAYCAN_HVBAT_TOT_AH_DCHRG"]:.6f}')
    print(f'R33_RESIDUAL_W={tr["power_dc_W"]-tr["power_mechanical_W"]:.4f} LATENT_AUXILIARY_W={tr["power_auxiliary_W"]:.4f}')
    if args.permutation_proof:
        print('B04_SWAP_PROOF='+str(paired_branch_counterfactual(c)))

if __name__=='__main__':main()
