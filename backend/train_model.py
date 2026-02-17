#!/usr/bin/env python
"""Direct model training script"""

import warnings
warnings.filterwarnings('ignore')
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

print('=' * 60)
print('Starting Model Training...')
print('=' * 60)

from model import get_trained_model

print('Calling get_trained_model()...')
model, target_scaler, feature_scaler, meta = get_trained_model()

print()
print('=' * 60)
print('TRAINING COMPLETE!')
print('=' * 60)
print(f'MAE:  {meta["mae"]:.4f} kW')
print(f'RMSE: {meta["rmse"]:.4f} kW')
print(f'R²:   {meta["r2"]:.4f}')
print(f'MAPE: {meta["mape"]:.4f}%')
print('=' * 60)
