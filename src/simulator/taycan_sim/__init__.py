"""Simulador sintético eletrotérmico restrito ao catálogo aprovado OBDb.

Não é um modelo calibrado do Porsche Taycan nem um dispositivo de diagnóstico.
"""
from .model import ModelConfig, Fault, SimResult, simulate, paired_branch_counterfactual

__all__ = ["ModelConfig", "Fault", "SimResult", "simulate", "paired_branch_counterfactual"]
